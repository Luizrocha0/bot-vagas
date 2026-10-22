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


def executar_busca(min_score=55, remote_only=False, max_pages_per_term=1, meta_diaria=2):
    print("=" * 60)
    print("🚀 INICIANDO CAÇADOR DE VAGAS: FOCO EM ESTÁGIO E JÚNIOR")
    print(f"🎯 Meta: Garantir pelo menos {meta_diaria} vagas compatíveis")
    print("=" * 60)

    # Termos de busca focados exclusivamente em Estágio e Júnior
    termos_busca = [
        "Estagio Desenvolvimento Software",
        "Estagio Frontend",
        "Estagio TI",
        "Desenvolvedor Junior",
        "Desenvolvedor Full Stack Junior",
        "Desenvolvedor React Junior",
        "Desenvolvedor Frontend Junior",
        "Desenvolvedor Node Junior",
        "Junior Software Engineer",
        "Software Engineer Intern"
    ]

    vagas_vistas = carregar_vagas_vistas()
    historico = carregar_historico()

    try:
        gemini_client = criar_cliente_gemini()
        print("✅ Cliente Gemini conectado com sucesso.")
    except Exception as e:
        print(f"\n❌ Erro ao inicializar Gemini: {e}")
        print("💡 Dica rápida:")
        print("   1. Gere uma chave gratuita em: https://aistudio.google.com/app/apikey")
        print("   2. Cole a chave no arquivo .env ou nos Secrets do GitHub.\n")
        return

    novas_vagas_encontradas = []

    for termo in termos_busca:
        print(f"🔍 Buscando: '{termo}'...")
        vagas = buscar_vagas_linkedin(
            keywords=termo,
            location="Brasil",
            remote_only=remote_only,
            max_pages=max_pages_per_term
        )

        for v in vagas:
            v_id = str(v.get("id"))
            if v_id in vagas_vistas:
                continue
            vagas_vistas.add(v_id)
            novas_vagas_encontradas.append(v)

    print(f"\n📊 Total de vagas inéditas filtradas para avaliar: {len(novas_vagas_encontradas)}")

    candidatas_avaliadas = []

    for i, vaga in enumerate(novas_vagas_encontradas, 1):
        print(f"\n[{i}/{len(novas_vagas_encontradas)}] {vaga['titulo']} @ {vaga['empresa']}")
        
        detalhes = obter_detalhes_vaga(vaga["id"])
        vaga["descricao"] = detalhes.get("descricao", "")
        vaga["criterios"] = detalhes.get("criterios", {})

        if not vaga["descricao"] or len(vaga["descricao"].strip()) < 40:
            print("  ⚠️ Descrição indisponível. Pulando.")
            continue

        analise = analisar_compatibilidade_vaga(vaga, client=gemini_client)
        score = analise.get("compatibilidade_percentual", 0)
        eh_junior_estagio = analise.get("eh_junior_ou_estagio", True)
        classificacao = analise.get("classificacao", "N/A")

        print(f"  🎯 Score: {score}% ({classificacao}) | É Júnior/Estágio: {'Sim' if eh_junior_estagio else 'Não'}")

        registro = {
            "vaga": vaga,
            "analise": analise,
            "data_analise": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        historico.append(registro)

        # Guarda na lista de candidatas apenas se for júnior/estágio
        if eh_junior_estagio and score > 25:
            candidatas_avaliadas.append({
                "vaga": vaga,
                "analise": analise,
                "score": score
            })

        salvar_vagas_vistas(vagas_vistas)
        salvar_historico(historico)
        time.sleep(1.2)

    # Ordena da melhor compatibilidade para a menor
    candidatas_avaliadas.sort(key=lambda x: x["score"], reverse=True)

    print("\n" + "=" * 60)
    print("📢 DISPARANDO NOTIFICAÇÕES SELECIONADAS...")
    print("=" * 60)

    notificadas = []

    # 1. Notifica primeiro as que atingiram a nota mínima de corte (ex: >= 55%)
    for item in candidatas_avaliadas:
        if item["score"] >= min_score and item["analise"].get("vale_a_pena_candidatar", True):
            print(f"🔥 Vaga Selecionada ({item['score']}%): {item['vaga']['titulo']} - {item['vaga']['empresa']}")
            enviar_notificacao_telegram(item["vaga"], item["analise"])
            enviar_notificacao_whatsapp(item["vaga"], item["analise"])
            notificadas.append(item["vaga"]["id"])

    # 2. Garante a meta de pelo menos 2 vagas se houverem vagas júnior/estágio disponíveis
    if len(notificadas) < meta_diaria:
        restantes = meta_diaria - len(notificadas)
        print(f"\n⚡ Meta diária de {meta_diaria} vagas ainda não atingida ({len(notificadas)} enviadas).")
        print(f"   Selecionando as {restantes} melhores opções júnior/estágio do dia...")

        for item in candidatas_avaliadas:
            if item["vaga"]["id"] not in notificadas:
                print(f"⭐ Entregando para completar a meta ({item['score']}%): {item['vaga']['titulo']}")
                enviar_notificacao_telegram(item["vaga"], item["analise"])
                enviar_notificacao_whatsapp(item["vaga"], item["analise"])
                notificadas.append(item["vaga"]["id"])
                if len(notificadas) >= meta_diaria:
                    break

    print("\n" + "=" * 60)
    print("🎉 VARREDURA CONCLUÍDA!")
    print(f"Total avaliadas: {len(novas_vagas_encontradas)}")
    print(f"Total de vagas enviadas hoje: {len(notificadas)}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Caçador de Vagas com Gemini e LinkedIn")
    parser.add_argument("--score", type=int, default=55, help="Nota mínima de match para notificar (padrão: 55)")
    parser.add_argument("--remoto", action="store_true", help="Filtrar apenas vagas 100% remotas")
    parser.add_argument("--paginas", type=int, default=1, help="Quantidade de páginas por termo de busca")
    parser.add_argument("--meta", type=int, default=2, help="Meta mínima de vagas a entregar por dia (padrão: 2)")
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
