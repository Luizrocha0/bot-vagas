import os
import sys
import json
import time
import re
import argparse
from dotenv import load_dotenv

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
                dados = json.load(f)
                return dados if isinstance(dados, list) else []
        except Exception:
            return []
    return []


def salvar_historico(historico):
    try:
        with open(MATCH_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Aviso] Falha ao salvar histórico: {e}", flush=True)


def executar_busca(meta_remotas=2, meta_presenciais=2, max_pages_per_term=1, **kwargs):
    print("=" * 60, flush=True)
    print("🚀 CAÇADOR DE VAGAS: JÚNIOR E ESTÁGIO", flush=True)
    print(f"🎯 META DIÁRIA: {meta_remotas} VAGAS REMOTAS + {meta_presenciais} VAGAS LOCAIS (RECIFE/PE)", flush=True)
    print("=" * 60, flush=True)

    buscas = [
        # Remotas no Brasil
        {"termo": "Desenvolvedor Junior", "geo_id": GEO_ID_BRASIL, "location": None, "remoto": True},
        {"termo": "Estagio TI", "geo_id": GEO_ID_BRASIL, "location": None, "remoto": True},
        {"termo": "React Junior", "geo_id": GEO_ID_BRASIL, "location": None, "remoto": True},
        {"termo": "Full Stack Junior", "geo_id": GEO_ID_BRASIL, "location": None, "remoto": True},
        {"termo": "Node Junior", "geo_id": GEO_ID_BRASIL, "location": None, "remoto": True},

        # Presenciais / Híbridas em Recife / Olinda / PE
        {"termo": "Desenvolvedor Junior", "geo_id": None, "location": "Recife, Pernambuco, Brasil", "remoto": False},
        {"termo": "Estagio TI", "geo_id": None, "location": "Recife, Pernambuco, Brasil", "remoto": False},
        {"termo": "Estagio Desenvolvimento", "geo_id": None, "location": "Recife, Pernambuco, Brasil", "remoto": False},
        {"termo": "Desenvolvedor", "geo_id": None, "location": "Recife, Pernambuco, Brasil", "remoto": False},
        {"termo": "Estagio", "geo_id": None, "location": "Recife, Pernambuco, Brasil", "remoto": False},
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
        loc_display = b["location"] if b["location"] else "Brasil (100% Remoto)"
        print(f"🔍 Coletando '{termo}' em '{loc_display}'...", flush=True)
        vagas = buscar_vagas_linkedin(
            keywords=termo,
            location=b["location"],
            geo_id=b["geo_id"],
            remote_only=b["remoto"],
            max_pages=max_pages_per_term
        )

        for v in vagas:
            raw_id = v.get("id") or v.get("url") or f"{v.get('titulo')}_{v.get('empresa')}"
            v_id = str(raw_id)
            if v_id in vagas_vistas:
                continue
            vagas_vistas.add(v_id)
            v["id"] = v_id
            novas_vagas_encontradas.append(v)

    print(f"\n📊 Total de vagas inéditas filtradas para avaliar: {len(novas_vagas_encontradas)}\n", flush=True)

    candidatas_remotas = []
    candidatas_presenciais = []

    for i, vaga in enumerate(novas_vagas_encontradas, 1):
        v_titulo = vaga.get("titulo") or "Vaga Sem Título"
        v_empresa = vaga.get("empresa") or "Empresa Confidencial"
        v_local = vaga.get("localizacao") or "Brasil"
        print(f"[{i}/{len(novas_vagas_encontradas)}] {v_titulo} @ {v_empresa} ({v_local})", flush=True)

        # Tenta obter a descrição detalhada; se não vier, usa fallback inteligente
        detalhes = obter_detalhes_vaga(vaga.get("id"))
        desc = (detalhes.get("descricao") or "").strip()

        if not desc or len(desc) < 30:
            vaga["descricao"] = f"Vaga de {vaga.get('titulo', 'Desenvolvedor')} na empresa {vaga.get('empresa', 'Confidencial')}, localizada em {vaga.get('localizacao', 'Brasil')}. Oportunidade na área de tecnologia e desenvolvimento de software para início de carreira."
            vaga["criterios"] = {"Tipo": "Início de Carreira"}
        else:
            vaga["descricao"] = desc
            vaga["criterios"] = detalhes.get("criterios") or {}

        analise = analisar_compatibilidade_vaga(vaga, client=gemini_client)
        if not isinstance(analise, dict):
            analise = {}

        raw_score = analise.get("compatibilidade_percentual")
        if isinstance(raw_score, str):
            digits = re.sub(r"[^\d]", "", raw_score)
            score = int(digits) if digits else 0
        elif raw_score is not None:
            try:
                score = int(raw_score)
            except (ValueError, TypeError):
                score = 0
        else:
            score = 0
        score = max(0, min(100, score))

        raw_junior = analise.get("eh_junior_ou_estagio")
        if isinstance(raw_junior, str):
            eh_junior = raw_junior.lower() in ("true", "1", "sim", "yes")
        else:
            eh_junior = bool(raw_junior) if raw_junior is not None else True

        modalidade = str(analise.get("tipo_modalidade") or "INVALIDA").upper().strip()
        classificacao = analise.get("classificacao") or "N/A"

        print(f"  🎯 Score: {score}% ({classificacao}) | Nível: {'Júnior/Estágio' if eh_junior else 'Sênior/Outro'} | Modalidade: {modalidade}", flush=True)

        registro = {
            "vaga": vaga,
            "analise": analise,
            "data_analise": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        historico.append(registro)

        # Classifica por modalidade para a entrega das 4 vagas
        if eh_junior and score >= 35:
            if modalidade == "REMOTO":
                candidatas_remotas.append({
                    "vaga": vaga,
                    "analise": analise,
                    "score": score
                })
            elif modalidade == "PRESENCIAL_PE":
                candidatas_presenciais.append({
                    "vaga": vaga,
                    "analise": analise,
                    "score": score
                })

        salvar_vagas_vistas(vagas_vistas)
        salvar_historico(historico)
        time.sleep(0.5)

    candidatas_remotas.sort(key=lambda x: x["score"], reverse=True)
    candidatas_presenciais.sort(key=lambda x: x["score"], reverse=True)

    print("\n" + "=" * 60, flush=True)
    print("📢 SELECIONANDO AS 4 MELHORES VAGAS (2 REMOTAS + 2 PRESENCIAIS)...", flush=True)
    print("=" * 60, flush=True)

    selecionadas_final = []

    # 1. Pega as 2 melhores remotas
    top_remotas = candidatas_remotas[:meta_remotas]
    for r in top_remotas:
        r_tit = r["vaga"].get("titulo") or "Vaga Remota"
        r_emp = r["vaga"].get("empresa") or "Confidencial"
        print(f"🌐 [REMOTA SELECIONADA] {r['score']}% - {r_tit} @ {r_emp}", flush=True)
        selecionadas_final.append(r)

    # 2. Pega as 2 melhores presenciais em Recife/PE
    top_presenciais = candidatas_presenciais[:meta_presenciais]
    for p in top_presenciais:
        p_tit = p["vaga"].get("titulo") or "Vaga Local PE"
        p_emp = p["vaga"].get("empresa") or "Confidencial"
        print(f"📍 [LOCAL PE SELECIONADA] {p['score']}% - {p_tit} @ {p_emp}", flush=True)
        selecionadas_final.append(p)

    # Se faltar em um grupo, complementa com o outro
    total_desejado = meta_remotas + meta_presenciais
    if len(selecionadas_final) < total_desejado:
        if meta_remotas == 0:
            pool_sobras = candidatas_presenciais
        elif meta_presenciais == 0:
            pool_sobras = candidatas_remotas
        else:
            pool_sobras = candidatas_remotas + candidatas_presenciais

        ids_ja_selecionados = {str(item["vaga"].get("id")) for item in selecionadas_final}
        sobras = [x for x in pool_sobras if str(x["vaga"].get("id")) not in ids_ja_selecionados]
        sobras.sort(key=lambda x: x["score"], reverse=True)
        for s in sobras:
            if len(selecionadas_final) >= total_desejado:
                break
            s_id = str(s["vaga"].get("id"))
            if s_id in ids_ja_selecionados:
                continue
            ids_ja_selecionados.add(s_id)
            s_tit = s["vaga"].get("titulo") or "Vaga Complementar"
            s_emp = s["vaga"].get("empresa") or "Confidencial"
            print(f"⭐ [COMPLEMENTAR SELECIONADA] {s['score']}% - {s_tit} @ {s_emp}", flush=True)
            selecionadas_final.append(s)

    # Dispara as mensagens no Telegram
    print(f"\n📨 Disparando {len(selecionadas_final)} notificações para o Telegram...", flush=True)
    for item in selecionadas_final:
        enviar_notificacao_telegram(item["vaga"], item["analise"])
        enviar_notificacao_whatsapp(item["vaga"], item["analise"])
        time.sleep(0.5)

    print("\n" + "=" * 60, flush=True)
    print("🎉 VARREDURA CONCLUÍDA COM SUCESSO!", flush=True)
    print(f"Total avaliadas: {len(novas_vagas_encontradas)}", flush=True)
    print(f"Total enviadas no Telegram: {len(selecionadas_final)} ({meta_remotas} Remotas + {meta_presenciais} Locais)", flush=True)
    print("=" * 60, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bot Caçador de Vagas com Gemini e LinkedIn")
    parser.add_argument("--remotas", type=int, default=2, help="Quantidade de vagas remotas diárias (padrão: 2)")
    parser.add_argument("--presenciais", type=int, default=2, help="Quantidade de vagas presenciais em PE (padrão: 2)")
    parser.add_argument("--paginas", type=int, default=1, help="Quantidade de páginas por termo de busca")
    parser.add_argument("--test-telegram", action="store_true", help="Testa a conexão com o bot do Telegram")
    parser.add_argument("--test-whatsapp", action="store_true", help="Testa a conexão com o WhatsApp")

    args = parser.parse_args(argv)

    if args.test_telegram:
        sucesso, msg = testar_conexao_telegram()
        print(f"Resultado do teste Telegram: {'✅' if sucesso else '❌'} {msg}", flush=True)
        return 0 if sucesso else 1
    elif args.test_whatsapp:
        sucesso, msg = testar_conexao_whatsapp()
        print(f"Resultado do teste WhatsApp: {'✅' if sucesso else '❌'} {msg}", flush=True)
        return 0 if sucesso else 1
    else:
        executar_busca(
            meta_remotas=args.remotas,
            meta_presenciais=args.presenciais,
            max_pages_per_term=args.paginas
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
