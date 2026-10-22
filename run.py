import os
import sys
import json
import time
import argparse
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Carrega variáveis do .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from linkedin_scraper import (
    buscar_vagas_linkedin,
    obter_detalhes_vaga,
    carregar_vagas_vistas,
    salvar_vagas_vistas
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


def executar_busca(min_score=50, remote_only=False, max_pages_per_term=1, meta_diaria=2):
    print("=" * 60)
    print("🚀 CAÇADOR DE VAGAS: JÚNIOR E ESTÁGIO (BRASIL / RECIFE & OLINDA)")
    print(f"🎯 Meta: Garantir pelo menos {meta_diaria} vagas diárias qualificadas")
    print("=" * 60)

    # Buscas estratégicas divididas por abrangência nacional (remoto) e local (Recife/PE)
    buscas = [
        {"termo": "Estagio Desenvolvimento Software", "local": "Brasil"},
        {"termo": "Estagio Frontend", "local": "Brasil"},
        {"termo": "Estagio TI", "local": "Brasil"},
        {"termo": "Desenvolvedor Junior", "local": "Brasil"},
        {"termo": "Desenvolvedor Full Stack Junior", "local": "Brasil"},
        {"termo": "Desenvolvedor React Junior", "local": "Brasil"},
        {"termo": "Desenvolvedor Node Junior", "local": "Brasil"},
        {"termo": "Desenvolvedor", "local": "Recife, Pernambuco, Brasil"},
        {"termo": "Estagio TI", "local": "Recife, Pernambuco, Brasil"},
    ]

    vagas_vistas = carregar_vagas_vistas()
    historico = carregar_historico()

    try:
        gemini_client = criar_cliente_gemini()
        print("✅ Conectado à API do Gemini.")
    except Exception as e:
        print(f"\n❌ Erro ao inicializar Gemini: {e}")
        return

    novas_vagas_encontradas = []

    for b in buscas:
        termo = b["termo"]
        local = b["local"]
        print(f"🔍 Buscando '{termo}' em '{local}'...")
        vagas = buscar_vagas_linkedin(
            keywords=termo,
            location=local,
            remote_only=remote_only,
            max_pages=max_pages_per_term
        )

        for v in vagas:
            v_id = str(v.get("id"))
            if v_id in vagas_vistas:
                continue
            vagas_vistas.add(v_id)
            novas_vagas_encontradas.append(v)

    print(f"\n📊 Total de vagas filtradas no Brasil para avaliar: {len(novas_vagas_encontradas)}")

    candidatas_aprovadas = []

    for i, vaga in enumerate(novas_vagas_encontradas, 1):
        print(f"\n[{i}/{len(novas_vagas_encontradas)}] {vaga['titulo']} - {vaga['empresa']} ({vaga['localizacao']})")
        
        detalhes = obter_detalhes_vaga(vaga["id"])
        vaga["descricao"] = detalhes.get("descricao", "")
        vaga["criterios"] = detalhes.get("criterios", {})

        if not vaga["descricao"] or len(vaga["descricao"].strip()) < 40:
            print("  ⚠️ Descrição indisponível ou curta demais. Pulando.")
            continue

        analise = analisar_compatibilidade_vaga(vaga, client=gemini_client)
        score = analise.get("compatibilidade_percentual", 0)
        eh_junior = analise.get("eh_junior_ou_estagio", True)
        atende_local = analise.get("atende_localizacao", True)
        classificacao = analise.get("classificacao", "N/A")

        print(f"  🎯 Score: {score}% ({classificacao}) | Júnior/Estágio: {'Sim' if eh_junior else 'Não'} | Local OK: {'Sim' if atende_local else 'Não'}")

        registro = {
            "vaga": vaga,
            "analise": analise,
            "data_analise": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        historico.append(registro)

        # Adiciona à lista de aprovadas se for compatível com a modalidade e nível
        if eh_junior and atende_local and score >= 30:
            candidatas_aprovadas.append({
                "vaga": vaga,
                "analise": analise,
                "score": score
            })

        salvar_vagas_vistas(vagas_vistas)
        salvar_historico(historico)
        time.sleep(1.2)

    # Ordena da melhor compatibilidade para a menor
    candidatas_aprovadas.sort(key=lambda x: x["score"], reverse=True)

    print("\n" + "=" * 60)
    print("📢 DISPARANDO NOTIFICAÇÕES PARA O TELEGRAM...")
    print("=" * 60)

    notificadas = []

    # 1. Notifica as que bateram a nota mínima estipulada
    for item in candidatas_aprovadas:
        if item["score"] >= min_score and item["analise"].get("vale_a_pena_candidatar", True):
            print(f"🔥 Notificando vaga ({item['score']}%): {item['vaga']['titulo']} @ {item['vaga']['empresa']}")
            enviar_notificacao_telegram(item["vaga"], item["analise"])
            enviar_notificacao_whatsapp(item["vaga"], item["analise"])
            notificadas.append(item["vaga"]["id"])

    # 2. Garante a entrega mínima diária com as melhores do dia
    if len(notificadas) < meta_diaria and candidatas_aprovadas:
        print(f"\n⚡ Completando a meta diária de {meta_diaria} vagas...")
        for item in candidatas_aprovadas:
            if item["vaga"]["id"] not in notificadas:
                print(f"⭐ Entregando ({item['score']}%): {item['vaga']['titulo']} @ {item['vaga']['empresa']}")
                enviar_notificacao_telegram(item["vaga"], item["analise"])
                enviar_notificacao_whatsapp(item["vaga"], item["analise"])
                notificadas.append(item["vaga"]["id"])
                if len(notificadas) >= meta_diaria:
                    break

    print("\n" + "=" * 60)
    print("🎉 VARREDURA CONCLUÍDA!")
    print(f"Total avaliadas: {len(novas_vagas_encontradas)}")
    print(f"Total entregues hoje: {len(notificadas)}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Caçador de Vagas com Gemini e LinkedIn")
    parser.add_argument("--score", type=int, default=50, help="Nota mínima de match para notificar (padrão: 50)")
    parser.add_argument("--remoto", action="store_true", help="Filtrar apenas vagas 100% remotas")
    parser.add_argument("--paginas", type=int, default=1, help="Quantidade de páginas por termo de busca")
    parser.add_argument("--meta", type=int, default=2, help="Meta mínima de vagas por dia (padrão: 2)")
    parser.add_argument("--test-telegram", action="store_true", help="Testa a conexão com o bot do Telegram")
    parser.add_argument("--test-whatsapp", action="store_true", help="Testa a conexão com o WhatsApp")

    args = parser.parse_args()

    if args.test_telegram:
        sucesso, msg = testar_conexao_telegram()
        print(f"Resultado do teste Telegram: {'✅' if sucesso else '❌'} {msg}")
    elif args.test_whatsapp:
        sucesso, msg = testar_conexao_whatsapp()
        print(f"Resultado do teste WhatsApp: {'✅' if sucesso else '❌'} {msg}")
    else:
        executar_busca(
            min_score=args.score,
            remote_only=args.remoto,
            max_pages_per_term=args.paginas,
            meta_diaria=args.meta
        )
