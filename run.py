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


def executar_busca(min_score=70, remote_only=False, max_pages_per_term=1):
    print("=" * 60)
    print("🚀 INICIANDO VARREDURA DE VAGAS COM O GEMINI & LINKEDIN")
    print("=" * 60)

    # Carrega perfil
    perfil_path = os.path.join(os.path.dirname(__file__), "perfil_candidato.json")
    with open(perfil_path, "r", encoding="utf-8") as f:
        perfil = json.load(f)

    termos_busca = [
        "Desenvolvedor Full Stack",
        "Desenvolvedor Next.js",
        "Desenvolvedor React",
        "Desenvolvedor Nest.js Node.js",
        "Desenvolvedor Junior",
        "Estagio Desenvolvimento Software"
    ]

    vagas_vistas = carregar_vagas_vistas()
    historico = carregar_historico()

    try:
        gemini_client = criar_cliente_gemini()
        print("✅ Cliente Gemini conectado.")
    except Exception as e:
        print(f"\n❌ Erro ao inicializar Gemini: {e}")
        print("💡 Dica rápida:")
        print("   1. Gere uma chave gratuita em: https://aistudio.google.com/app/apikey")
        print("   2. Cole a chave no arquivo .env na linha: GEMINI_API_KEY=sua_chave_aqui\n")
        return

    novas_vagas_encontradas = []

    for termo in termos_busca:
        print(f"\n🔍 Buscando vagas para: '{termo}'...")
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

    print(f"\n📊 Total de vagas inéditas para avaliar: {len(novas_vagas_encontradas)}")

    vagas_notificadas = 0

    for i, vaga in enumerate(novas_vagas_encontradas, 1):
        print(f"\n[{i}/{len(novas_vagas_encontradas)}] Analisando: {vaga['titulo']} - {vaga['empresa']}")
        
        # Busca detalhes da descrição
        detalhes = obter_detalhes_vaga(vaga["id"])
        vaga["descricao"] = detalhes.get("descricao", "")
        vaga["criterios"] = detalhes.get("criterios", {})

        if not vaga["descricao"] or len(vaga["descricao"].strip()) < 50:
            print("  ⚠️ Descrição muito curta ou indisponível. Pulando análise.")
            continue

        # Avaliação com Gemini
        analise = analisar_compatibilidade_vaga(vaga, client=gemini_client)
        score = analise.get("compatibilidade_percentual", 0)
        classificacao = analise.get("classificacao", "N/A")

        print(f"  🎯 Score de Compatibilidade: {score}% ({classificacao})")

        registro = {
            "vaga": vaga,
            "analise": analise,
            "data_analise": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        historico.append(registro)

        # Se atingir o critério de nota mínima
        if score >= min_score and analise.get("vale_a_pena_candidatar", True):
            print(f"  🔥 MATCH CONFIRMADO! Enviando alertas...")
            notificado_tg = enviar_notificacao_telegram(vaga, analise)
            notificado_wpp = enviar_notificacao_whatsapp(vaga, analise)
            if notificado_tg or notificado_wpp:
                vagas_notificadas += 1
        else:
            print(f"  ⏭️ Vaga abaixo do limiar de alerta ({min_score}%). Registrada no histórico.")

        salvar_vagas_vistas(vagas_vistas)
        salvar_historico(historico)
        time.sleep(1.5)  # Intervalo para não estourar rate limit da IA

    print("\n" + "=" * 60)
    print(f"🎉 VARREDURA CONCLUÍDA!")
    print(f"Total avaliadas: {len(novas_vagas_encontradas)}")
    print(f"Total de alertas enviados: {vagas_notificadas}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Caçador de Vagas com Gemini e LinkedIn")
    parser.add_argument("--score", type=int, default=70, help="Nota mínima de match para notificar (ex: 70)")
    parser.add_argument("--remoto", action="store_true", help="Filtrar apenas vagas 100% remotas")
    parser.add_argument("--paginas", type=int, default=1, help="Quantidade de páginas por termo de busca")
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
        executar_busca(min_score=args.score, remote_only=args.remoto, max_pages_per_term=args.paginas)
