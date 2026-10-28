import os
import sys
import json
import time
import re
import argparse
from typing import List, Dict, Any, Optional, Tuple
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

from core import (
    Vaga,
    ResultadoMatch,
    ModalidadeVaga,
    JobCollector,
    QuotaSelector,
    NotificationDispatcher,
    JobRepository
)

MATCH_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "historico_matches.json")


def carregar_historico(caminho: Optional[str] = None) -> List[Dict[str, Any]]:
    """Carrega o histórico de matches através do caminho configurado."""
    path = caminho or MATCH_HISTORY_FILE
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return dados if isinstance(dados, list) else []
        except Exception:
            return []
    return []


def salvar_historico(historico: List[Dict[str, Any]], caminho: Optional[str] = None) -> None:
    """Persiste o histórico de matches em disco."""
    path = caminho or MATCH_HISTORY_FILE
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Aviso] Falha ao salvar histórico: {e}", flush=True)


def buscar_vagas_gupy(keywords: str, location: Optional[str] = None, remote_only: bool = False, max_pages: int = 1, **kwargs) -> List[Dict[str, Any]]:
    """Encaminha busca para o GupyScraper."""
    try:
        scraper = GupyScraper()
        return scraper.buscar_vagas(keywords=keywords, location=location, remote_only=remote_only, max_pages=max_pages, **kwargs)
    except Exception as e:
        print(f"[Aviso] Falha no scraper Gupy: {e}", flush=True)
        return []


def buscar_vagas_programathor(keywords: str, location: Optional[str] = None, remote_only: bool = False, max_pages: int = 1, **kwargs) -> List[Dict[str, Any]]:
    """Encaminha busca para o ProgramathorScraper."""
    try:
        scraper = ProgramathorScraper()
        return scraper.buscar_vagas(keywords=keywords, location=location, remote_only=remote_only, max_pages=max_pages, **kwargs)
    except Exception as e:
        print(f"[Aviso] Falha no scraper Programathor: {e}", flush=True)
        return []


def buscar_vagas_indeed(keywords: str, location: Optional[str] = None, remote_only: bool = False, max_pages: int = 1, **kwargs) -> List[Dict[str, Any]]:
    """Encaminha busca para o IndeedScraper."""
    try:
        scraper = IndeedScraper()
        return scraper.buscar_vagas(keywords=keywords, location=location, remote_only=remote_only, max_pages=max_pages, **kwargs)
    except Exception as e:
        print(f"[Aviso] Falha no scraper Indeed: {e}", flush=True)
        return []


def obter_termos_busca_padrao() -> List[Dict[str, Any]]:
    """Retorna a matriz de termos de busca padrão para vagas remotas e presenciais."""
    return [
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


class _ScraperAdapter(BaseJobScraper):
    """Adaptador de função de busca para a interface BaseJobScraper."""
    def __init__(self, nome: str, func):
        super().__init__(fonte_nome=nome)
        self.func = func

    def buscar_vagas(self, keywords="Junior", location=None, remote_only=False, max_pages=1, **kwargs):
        return self.func(keywords=keywords, location=location, remote_only=remote_only, max_pages=max_pages, **kwargs)


def criar_coletor_padrao() -> JobCollector:
    """Configura e instancia o coletor desacoplado com todas as fontes registradas."""
    return JobCollector({
        "linkedin": _ScraperAdapter("LinkedIn", lambda *a, **kw: buscar_vagas_linkedin(*a, **kw)),
        "gupy": _ScraperAdapter("Gupy", lambda *a, **kw: buscar_vagas_gupy(*a, **kw)),
        "programathor": _ScraperAdapter("Programathor", lambda *a, **kw: buscar_vagas_programathor(*a, **kw)),
        "indeed": _ScraperAdapter("Indeed", lambda *a, **kw: buscar_vagas_indeed(*a, **kw)),
    })


def enriquecer_descricao_vaga(vaga: Dict[str, Any]) -> None:
    """
    Garante que a vaga possua uma descrição detalhada para a IA avaliar.
    Se for do LinkedIn e curta, tenta obter detalhes via API pública; se falhar, aplica fallback contextual.
    """
    v_fonte = vaga.get("fonte") or "LinkedIn"
    desc = (vaga.get("descricao") or "").strip()

    if v_fonte == "LinkedIn" and len(desc) < 30:
        detalhes = obter_detalhes_vaga(vaga.get("id"))
        desc = (detalhes.get("descricao") or "").strip()
        if detalhes.get("criterios"):
            vaga["criterios"] = detalhes.get("criterios")

    if not desc or len(desc) < 30:
        vaga["descricao"] = (
            f"Vaga de {vaga.get('titulo', 'Desenvolvedor')} na empresa {vaga.get('empresa', 'Confidencial')}, "
            f"localizada em {vaga.get('localizacao', 'Brasil')}. "
            f"Oportunidade na área de tecnologia e desenvolvimento de software para início de carreira."
        )
        if not vaga.get("criterios"):
            vaga["criterios"] = {"Tipo": "Início de Carreira"}
    else:
        vaga["descricao"] = desc


def avaliar_candidatos(
    novas_vagas: List[Dict[str, Any]],
    gemini_client: Any
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Avalia a compatibilidade das vagas inéditas via Gemini e separa em remotas e presenciais elegíveis.
    """
    candidatas_remotas = []
    candidatas_presenciais = []

    for i, vaga in enumerate(novas_vagas, 1):
        v_titulo = vaga.get("titulo") or "Vaga Sem Título"
        v_empresa = vaga.get("empresa") or "Empresa Confidencial"
        v_local = vaga.get("localizacao") or "Brasil"
        v_fonte = vaga.get("fonte") or "LinkedIn"

        print(f"[{i}/{len(novas_vagas)}] [{v_fonte}] {v_titulo} @ {v_empresa} ({v_local})", flush=True)

        enriquecer_descricao_vaga(vaga)

        analise = analisar_compatibilidade_vaga(vaga, client=gemini_client)
        match_obj = ResultadoMatch.from_dict(analise)

        print(f"  🎯 Score: {match_obj.score}% | Modalidade: {match_obj.modalidade.value} | Início de Carreira: {match_obj.eh_junior_ou_estagio}", flush=True)

        if not match_obj.eh_elegivel(limiar_score=35):
            print("  ⏭️ Vaga descartada pelos filtros de elegibilidade.\n", flush=True)
            continue

        candidato_info = {
            "vaga": vaga,
            "analise": analise,
            "score": match_obj.score
        }

        if match_obj.modalidade == ModalidadeVaga.REMOTO:
            candidatas_remotas.append(candidato_info)
        elif match_obj.modalidade == ModalidadeVaga.PRESENCIAL_PE:
            candidatas_presenciais.append(candidato_info)

    return candidatas_remotas, candidatas_presenciais


def disparar_alertas(
    selecionadas: List[Dict[str, Any]],
    historico: List[Dict[str, Any]],
    dispatcher: Optional[NotificationDispatcher] = None
) -> int:
    """Dispara notificações para as vagas aprovadas e atualiza o histórico."""
    if dispatcher is None:
        dispatcher = NotificationDispatcher([
            enviar_notificacao_telegram,
            enviar_notificacao_whatsapp
        ])

    print("=" * 60, flush=True)
    print(f"🔔 DISPARANDO ALERTAS PARA AS TOP {len(selecionadas)} VAGAS SELECIONADAS", flush=True)
    print("=" * 60, flush=True)

    notificadas = 0
    for item in selecionadas:
        vaga = item["vaga"]
        analise = item["analise"]

        dispatcher.disparar(vaga, analise)

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
        notificadas += 1

    return notificadas


def executar_busca(
    meta_remotas: int = 2,
    meta_presenciais: int = 2,
    max_pages_per_term: int = 1,
    fontes: Optional[List[str]] = None,
    **kwargs
) -> None:
    """
    Orquestrador principal (Use Case / Facade).
    Aplica os princípios de Clean Code (Step-Down Rule) e Clean Architecture.
    """
    print("=" * 60, flush=True)
    print("🚀 CAÇADOR DE VAGAS: JÚNIOR E ESTÁGIO (MULTI-FONTES)", flush=True)
    print(f"🎯 META DIÁRIA: {meta_remotas} VAGAS REMOTAS + {meta_presenciais} VAGAS LOCAIS (RECIFE/PE)", flush=True)
    print("=" * 60, flush=True)

    try:
        gemini_client = criar_cliente_gemini()
        print("✅ Conectado com sucesso à IA do Gemini.", flush=True)
    except Exception as e:
        print(f"\n❌ Erro ao inicializar Gemini: {e}", flush=True)
        return

    vagas_vistas = carregar_vagas_vistas()
    historico = carregar_historico()

    # 1. Coleta e deduplicação de vagas através das fontes ativas
    collector = criar_coletor_padrao()
    buscas = obter_termos_busca_padrao()
    novas_vagas = collector.coletar_vagas_ineditas(
        buscas=buscas,
        fontes_ativas=fontes,
        max_pages=max_pages_per_term,
        vagas_vistas=vagas_vistas
    )

    print(f"\n📊 Total de vagas inéditas filtradas para avaliar: {len(novas_vagas)}\n", flush=True)

    # 2. Avaliação de compatibilidade com a IA do Gemini
    remotas, presenciais = avaliar_candidatos(novas_vagas, gemini_client)

    print(f"\n📈 Candidatas Remotas elegíveis: {len(remotas)}", flush=True)
    print(f"📈 Candidatas Locais (Recife/PE) elegíveis: {len(presenciais)}\n", flush=True)

    # 3. Seleção e balanceamento inteligente de cotas
    selector = QuotaSelector(meta_remotas=meta_remotas, meta_presenciais=meta_presenciais)
    selecionadas = selector.selecionar_top_vagas(remotas, presenciais)

    # 4. Disparo de alertas em todos os canais configurados
    notificadas = disparar_alertas(selecionadas, historico)

    # 5. Persistência de estado
    salvar_vagas_vistas(vagas_vistas)
    salvar_historico(historico)

    print(f"\n✨ Execução concluída! {notificadas} notificações enviadas com sucesso.", flush=True)


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
