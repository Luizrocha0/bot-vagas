import os
import sys
import json
import time
import argparse
from dotenv import load_dotenv

# Força descarregamento imediato do buffer de terminal para GitHub Actions
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from linkedin_scraper import (
    buscar_vagas_linkedin,
    obter_detalhes_vaga,
    carregar_vagas_vistas,
    salvar_vagas_vistas,
    GEO_ID_BRASIL
)
from gemini_matcher import analisar_compatibilidade_vaga, criar_cliente_gemini
from telegram_notifier import enviar_notificacao_telegram, testar_conexao_telegram
from whatsapp_notifier import enviar_notificacao_whatsapp, testar_conexao_whatsapp

MATCH_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "historico_matches.json")


def carregar_historico():
    if os.path.exists(MATCH_HISTORY_FILE):
        try:
            with open(MATCH_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def salvar_historico(historico):
    with open(MATCH_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)


def executar_busca(min_score=50, remote_only=False, max_pages_per_term=1, meta_diaria=2, max_vagas=20):
    print("=" * 60, flush=True)
    print("🚀 CAÇADOR DE VAGAS: JÚNIOR E ESTÁGIO (BRASIL / RECIFE & OLINDA)", flush=True)
    print(f"🎯 Meta: Garantir pelo menos {meta_diaria} vagas | Limite da rodada: {max_vagas} vagas", flush=True)
    print("=" * 60, flush=True)

    buscas = [
        {"termo": "Desenvolvedor Junior", "geo_id": GEO_ID_BRASIL, "location": None},
        {"termo": "Estagio TI", "geo_id": GEO_ID_BRASIL, "location": None},
        {"termo": "React Junior", "geo_id": GEO_ID_BRASIL, "location": None},
        {"termo": "Node Junior", "geo_id": GEO_ID_BRASIL, "location": None},
        {"termo": "Full Stack Junior", "geo_id": GEO_ID_BRASIL, "location": None},
        {"termo": "Estagio", "geo_id": None, "location": "Recife, Pernambuco, Brasil"},
        {"termo": "Desenvolvedor", "geo_id": None, "location": "Recife, Pernambuco, Brasil"},
    ]

    vagas_vistas = carregar_vagas_vistas()
    historico = carregar_historico()

    try:
        gemini_client = criar_cliente_gemini()
        print("✅ Conectado com sucesso à IA do Gemini.", flush=True)
    except Exception as e:
        print(f"\n❌ Erro ao inicializar Gemini: {e}", flush=True)
        return

    novas_vagas_encontradas = []

    for b in buscas:
        termo = b["termo"]
        loc_display = b["location"] if b["location"] else "Brasil (Remoto/Nacional)"
        print(f"🔍 Coletando vagas para '{termo}' em '{loc_display}'...", flush=True)
        vagas = buscar_vagas_linkedin(
            keywords=termo,
            location=b["location"],
            geo_id=b["geo_id"],
            remote_only=remote_only,
            max_pages=max_pages_per_term
        )

        for v in vagas:
            v_id = str(v.get("id"))
            if v_id in vagas_vistas:
                continue
            vagas_vistas.add(v_id)
            novas_vagas_encontradas.append(v)
            if len(novas_vagas_encontradas) >= max_vagas:
                break

        if len(novas_vagas_encontradas) >= max_vagas:
            print(f"⚡ Limite de {max_vagas} vagas novas atingido para avaliação ágil.", flush=True)
            break

    print(f"\n📊 Total de vagas inéditas para avaliar agora: {len(novas_vagas_encontradas)}\n", flush=True)

    candidatas_aprovadas = []
    notificadas = []

    for i, vaga in enumerate(novas_vagas_encontradas, 1):
        print(f"[{i}/{len(novas_vagas_encontradas)}] {vaga['titulo']} @ {vaga['empresa']} ({vaga['localizacao']})", flush=True)
        
        detalhes = obter_detalhes_vaga(vaga["id"])
        vaga["descricao"] = detalhes.get("descricao", "")
        vaga["criterios"] = detalhes.get("criterios", {})

        if not vaga["descricao"] or len(vaga["descricao"].strip()) < 30:
            print("  ⚠️ Descrição indisponível ou curta demais. Pulando.", flush=True)
            continue

        analise = analisar_compatibilidade_vaga(vaga, client=gemini_client)
        score = analise.get("compatibilidade_percentual", 0)
        eh_junior = analise.get("eh_junior_ou_estagio", True)
        atende_local = analise.get("atende_localizacao", True)
        classificacao = analise.get("classificacao", "N/A")

        print(f"  🎯 Score: {score}% ({classificacao}) | Júnior/Estágio: {'Sim' if eh_junior else 'Não'} | Local OK: {'Sim' if atende_local else 'Não'}", flush=True)

        registro = {
            "vaga": vaga,
            "analise": analise,
            "data_analise": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        historico.append(registro)

        # Envia no Telegram NA HORA se for compatível
        if eh_junior and atende_local and score >= min_score and analise.get("vale_a_pena_candidatar", True):
            print(f"  🔥 MATCH CONFIRMADO! Enviando agora para o Telegram...", flush=True)
            enviar_notificacao_telegram(vaga, analise)
            enviar_notificacao_whatsapp(vaga, analise)
            notificadas.append(vaga["id"])
        elif eh_junior and atende_local and score >= 25:
            candidatas_aprovadas.append({
                "vaga": vaga,
                "analise": analise,
                "score": score
            })

        salvar_vagas_vistas(vagas_vistas)
        salvar_historico(historico)
        time.sleep(0.8)

    # Se ainda faltar para a meta de 2 vagas, envia a melhor opção encontrada
    if len(notificadas) < meta_diaria and candidatas_aprovadas:
        candidatas_aprovadas.sort(key=lambda x: x["score"], reverse=True)
        print(f"\n⚡ Completando a meta diária com as melhores opções avaliadas...", flush=True)
        for item in candidatas_aprovadas:
            if item["vaga"]["id"] not in notificadas:
                print(f"⭐ Entregando ({item['score']}%): {item['vaga']['titulo']} @ {item['vaga']['empresa']}", flush=True)
                enviar_notificacao_telegram(item["vaga"], item["analise"])
                enviar_notificacao_whatsapp(item["vaga"], item["analise"])
                notificadas.append(item["vaga"]["id"])
                if len(notificadas) >= meta_diaria:
                    break

    print("\n" + "=" * 60, flush=True)
    print("🎉 VARREDURA CONCLUÍDA!", flush=True)
    print(f"Total avaliadas: {len(novas_vagas_encontradas)}", flush=True)
    print(f"Total enviadas no Telegram: {len(notificadas)}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Caçador de Vagas com Gemini e LinkedIn")
    parser.add_argument("--score", type=int, default=50, help="Nota mínima de match para notificar (padrão: 50)")
    parser.add_argument("--remoto", action="store_true", help="Filtrar apenas vagas 100% remotas")
    parser.add_argument("--paginas", type=int, default=1, help="Quantidade de páginas por termo de busca")
    parser.add_argument("--meta", type=int, default=2, help="Meta mínima de vagas por dia (padrão: 2)")
    parser.add_argument("--max-vagas", type=int, default=20, help="Quantidade máxima de vagas a avaliar por execução")
    parser.add_argument("--test-telegram", action="store_true", help="Testa a conexão com o bot do Telegram")
    parser.add_argument("--test-whatsapp", action="store_true", help="Testa a conexão com o WhatsApp")

    args = parser.parse_args()

    if args.test_telegram:
        sucesso, msg = testar_conexao_telegram()
        print(f"Resultado do teste Telegram: {'✅' if sucesso else '❌'} {msg}", flush=True)
    elif args.test_whatsapp:
        sucesso, msg = testar_conexao_whatsapp()
        print(f"Resultado do teste WhatsApp: {'✅' if sucesso else '❌'} {msg}", flush=True)
    else:
        executar_busca(
            min_score=args.score,
            remote_only=args.remoto,
            max_pages_per_term=args.paginas,
            meta_diaria=args.meta,
            max_vagas=args.max_vagas
        )
