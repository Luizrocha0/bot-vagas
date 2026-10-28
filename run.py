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

from scrapers import (
    BaseJobScraper,
    LinkedInScraper,
    GupyScraper,
    ProgramathorScraper,
    IndeedScraper
)
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


def buscar_vagas_gupy(keywords, location=None, remote_only=False, max_pages=1):
    """Encaminha busca para o GupyScraper."""
    try:
        scraper = GupyScraper()
        return scraper.buscar_vagas(keywords=keywords, location=location, remote_only=remote_only, max_pages=max_pages)
    except Exception as e:
        print(f"[Aviso] Falha no scraper Gupy: {e}", flush=True)
        return []


def buscar_vagas_programathor(keywords, location=None, remote_only=False, max_pages=1):
    """Encaminha busca para o ProgramathorScraper."""
    try:
        scraper = ProgramathorScraper()
        return scraper.buscar_vagas(keywords=keywords, location=location, remote_only=remote_only, max_pages=max_pages)
    except Exception as e:
        print(f"[Aviso] Falha no scraper Programathor: {e}", flush=True)
        return []


def buscar_vagas_indeed(keywords, location=None, remote_only=False, max_pages=1):
    """Encaminha busca para o IndeedScraper."""
    try:
        scraper = IndeedScraper()
        return scraper.buscar_vagas(keywords=keywords, location=location, remote_only=remote_only, max_pages=max_pages)
    except Exception as e:
        print(f"[Aviso] Falha no scraper Indeed: {e}", flush=True)
        return []


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


def executar_busca(meta_remotas=2, meta_presenciais=2, max_pages_per_term=1, fontes=None, **kwargs):
    print("=" * 60, flush=True)
    print("🚀 CAÇADOR DE VAGAS: JÚNIOR E ESTÁGIO (MULTI-FONTES)", flush=True)
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
    titulos_empresas_vistos = set()

    # Fontes ativas
    fontes_ativas = [f.lower().strip() for f in (fontes or ["linkedin", "gupy", "programathor", "indeed"])]

    for b in buscas:
        termo = b["termo"]
        loc_display = b["location"] if b["location"] else "Brasil (100% Remoto)"
        print(f"🔍 Coletando '{termo}' em '{loc_display}'...", flush=True)

        lotes_por_fonte = []

        # 1. LinkedIn
        if "linkedin" in fontes_ativas:
            vagas_linkedin = buscar_vagas_linkedin(
                keywords=termo,
                location=b["location"],
                geo_id=b["geo_id"],
                remote_only=b["remoto"],
                max_pages=max_pages_per_term
            )
            for v in vagas_linkedin:
                v.setdefault("fonte", "LinkedIn")
            lotes_por_fonte.append(vagas_linkedin)

        # 2. Gupy
        if "gupy" in fontes_ativas:
            vagas_gupy = buscar_vagas_gupy(
                keywords=termo,
                location=b["location"],
                remote_only=b["remoto"],
                max_pages=max_pages_per_term
            )
            lotes_por_fonte.append(vagas_gupy)

        # 3. Programathor
        if "programathor" in fontes_ativas:
            vagas_prog = buscar_vagas_programathor(
                keywords=termo,
                location=b["location"],
                remote_only=b["remoto"],
                max_pages=max_pages_per_term
            )
            lotes_por_fonte.append(vagas_prog)

        # 4. Indeed
        if "indeed" in fontes_ativas:
            vagas_indeed = buscar_vagas_indeed(
                keywords=termo,
                location=b["location"],
                remote_only=b["remoto"],
                max_pages=max_pages_per_term
            )
            lotes_por_fonte.append(vagas_indeed)

        for lote in lotes_por_fonte:
            for v in lote:
                raw_id = v.get("id") or v.get("url") or f"{v.get('titulo')}_{v.get('empresa')}"
                v_id = str(raw_id)
                if v_id in vagas_vistas:
                    continue

                # Deduplicação entre plataformas por Título + Empresa
                t_clean = re.sub(r"[^\w]", "", (v.get("titulo") or "").lower())
                e_clean = re.sub(r"[^\w]", "", (v.get("empresa") or "").lower())
                chave_duplicata = (t_clean, e_clean)
                if chave_duplicata in titulos_empresas_vistos and t_clean:
                    continue

                vagas_vistas.add(v_id)
                if t_clean:
                    titulos_empresas_vistos.add(chave_duplicata)

                v["id"] = v_id
                novas_vagas_encontradas.append(v)

    print(f"\n📊 Total de vagas inéditas filtradas para avaliar: {len(novas_vagas_encontradas)}\n", flush=True)

    candidatas_remotas = []
    candidatas_presenciais = []

    for i, vaga in enumerate(novas_vagas_encontradas, 1):
        v_titulo = vaga.get("titulo") or "Vaga Sem Título"
        v_empresa = vaga.get("empresa") or "Empresa Confidencial"
        v_local = vaga.get("localizacao") or "Brasil"
        v_fonte = vaga.get("fonte") or "LinkedIn"
        print(f"[{i}/{len(novas_vagas_encontradas)}] [{v_fonte}] {v_titulo} @ {v_empresa} ({v_local})", flush=True)

        desc = (vaga.get("descricao") or "").strip()

        # Se for do LinkedIn ou estiver sem descrição completa, tenta obter detalhes
        if v_fonte == "LinkedIn" and len(desc) < 30:
            detalhes = obter_detalhes_vaga(vaga.get("id"))
            desc = (detalhes.get("descricao") or "").strip()
            if detalhes.get("criterios"):
                vaga["criterios"] = detalhes.get("criterios")

        # Fallback inteligente se descrição for curta ou inexistente
        if not desc or len(desc) < 30:
            vaga["descricao"] = (
                f"Vaga de {vaga.get('titulo', 'Desenvolvedor')} na empresa {vaga.get('empresa', 'Confidencial')}, "
                f"localizada em {vaga.get('localizacao', 'Brasil')}. "
                f"Oportunidade na área de tecnologia e desenvolvimento de software para início de carreira."
            )
            vaga.setdefault("criterios", {"Tipo": "Início de Carreira"})
        else:
            vaga["descricao"] = desc

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

        modalidade = str(analise.get("tipo_modalidade") or "").upper()
        eh_jr = analise.get("eh_junior_ou_estagio")
        if isinstance(eh_jr, str):
            eh_jr = eh_jr.strip().lower() in ["true", "sim", "1", "yes"]
        elif eh_jr is None:
            eh_jr = True

        print(f"  🎯 Score: {score}% | Modalidade: {modalidade} | Início de Carreira: {eh_jr}", flush=True)

        # Regra de corte: descarte imediato se score muito baixo, sênior ou modalidade inválida
        if score < 35 or not eh_jr or modalidade not in ["REMOTO", "PRESENCIAL_PE"]:
            print("  ⏭️ Vaga descartada pelos filtros de elegibilidade.\n", flush=True)
            continue

        candidato_info = {
            "vaga": vaga,
            "analise": analise,
            "score": score
        }

        if modalidade == "REMOTO":
            candidatas_remotas.append(candidato_info)
        elif modalidade == "PRESENCIAL_PE":
            candidatas_presenciais.append(candidato_info)

    # Ordenação decrescente por score
    candidatas_remotas.sort(key=lambda x: x["score"], reverse=True)
    candidatas_presenciais.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n📈 Candidatas Remotas elegíveis: {len(candidatas_remotas)}", flush=True)
    print(f"📈 Candidatas Locais (Recife/PE) elegíveis: {len(candidatas_presenciais)}\n", flush=True)

    # 1. Aloca cotas principais
    selecionadas_remotas = candidatas_remotas[:meta_remotas]
    selecionadas_presenciais = candidatas_presenciais[:meta_presenciais]

    # 2. Complementação inteligente de cotas
    sobra_remotas = candidatas_remotas[meta_remotas:]
    sobra_presenciais = candidatas_presenciais[meta_presenciais:]

    # Se faltar presencial e meta_presenciais > 0, complementa com remotas
    if len(selecionadas_presenciais) < meta_presenciais and meta_presenciais > 0:
        deficit_presenciais = meta_presenciais - len(selecionadas_presenciais)
        complemento_remoto = sobra_remotas[:deficit_presenciais]
        selecionadas_remotas.extend(complemento_remoto)
        sobra_remotas = sobra_remotas[deficit_presenciais:]
        if complemento_remoto:
            print(f"ℹ️ Complementando {len(complemento_remoto)} vaga(s) com oportunidades remotas adicionais.", flush=True)

    # Se faltar remota e meta_remotas > 0, complementa com presenciais apenas se meta_presenciais > 0
    if len(selecionadas_remotas) < meta_remotas and meta_remotas > 0 and meta_presenciais > 0:
        deficit_remotas = meta_remotas - len(selecionadas_remotas)
        complemento_presencial = sobra_presenciais[:deficit_remotas]
        selecionadas_presenciais.extend(complemento_presencial)
        sobra_presenciais = sobra_presenciais[deficit_remotas:]
        if complemento_presencial:
            print(f"ℹ️ Complementando {len(complemento_presencial)} vaga(s) com oportunidades locais PE adicionais.", flush=True)

    final_selecionadas = selecionadas_remotas + selecionadas_presenciais

    print("=" * 60, flush=True)
    print(f"🔔 DISPARANDO ALERTAS PARA AS TOP {len(final_selecionadas)} VAGAS SELECIONADAS", flush=True)
    print("=" * 60, flush=True)

    notificadas_com_sucesso = 0
    for item in final_selecionadas:
        vaga = item["vaga"]
        analise = item["analise"]

        enviar_notificacao_telegram(vaga, analise)
        enviar_notificacao_whatsapp(vaga, analise)

        historico.append({
            "vaga_id": vaga.get("id"),
            "fonte": vaga.get("fonte", "LinkedIn"),
            "titulo": vaga.get("titulo"),
            "empresa": vaga.get("empresa"),
            "localizacao": vaga.get("localizacao"),
            "url": vaga.get("url"),
            "score": item["score"],
            "modalidade": analise.get("tipo_modalidade"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        notificadas_com_sucesso += 1

    salvar_vagas_vistas(vagas_vistas)
    salvar_historico(historico)

    print(f"\n✨ Execução concluída! {notificadas_com_sucesso} notificações enviadas com sucesso.", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Caçador de Vagas Júnior e Estágio com IA do Gemini")
    parser.add_argument("--remotas", type=int, default=2, help="Meta de vagas remotas diárias (padrão: 2)")
    parser.add_argument("--presenciais", type=int, default=2, help="Meta de vagas presenciais diárias em Recife/PE (padrão: 2)")
    parser.add_argument("--paginas", type=int, default=1, help="Páginas por termo de busca (padrão: 1)")
    parser.add_argument("--fontes", type=str, default=None, help="Lista de fontes separadas por vírgula (ex: linkedin,gupy,programathor,indeed)")
    parser.add_argument("--test-telegram", action="store_true", help="Testa a conexão e credenciais do Telegram")
    parser.add_argument("--test-whatsapp", action="store_true", help="Testa a conexão e credenciais do WhatsApp")

    args = parser.parse_args(argv)

    if args.test_telegram:
        sucesso, msg = testar_conexao_telegram()
        print(f"[{'SUCESSO' if sucesso else 'FALHA'}] Telegram: {msg}")
        return 0 if sucesso else 1

    if args.test_whatsapp:
        sucesso, msg = testar_conexao_whatsapp()
        print(f"[{'SUCESSO' if sucesso else 'FALHA'}] WhatsApp: {msg}")
        return 0 if sucesso else 1

    fontes_lista = [f.strip().lower() for f in args.fontes.split(",")] if args.fontes else None

    executar_busca(
        meta_remotas=args.remotas,
        meta_presenciais=args.presenciais,
        max_pages_per_term=args.paginas,
        fontes=fontes_lista
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
