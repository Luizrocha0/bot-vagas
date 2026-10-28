import re
from typing import List, Dict, Any, Set, Tuple, Optional
from scrapers.base import BaseJobScraper
from .models import Vaga


class JobCollector:
    """
    Coletor desacoplado de vagas (Open/Closed Principle).
    Permite registrar novos scrapers dinamicamente e orquestrar buscas
    com deduplicação de dois níveis: ID único e (Título normalizado + Empresa).
    """

    def __init__(self, scrapers: Optional[Dict[str, BaseJobScraper]] = None):
        self.scrapers: Dict[str, BaseJobScraper] = scrapers or {}

    def registrar_scraper(self, nome: str, scraper: BaseJobScraper) -> None:
        """Registra um scraper no catálogo de fontes."""
        self.scrapers[nome.lower().strip()] = scraper

    def coletar_vagas_ineditas(
        self,
        buscas: List[Dict[str, Any]],
        fontes_ativas: Optional[List[str]] = None,
        max_pages: int = 1,
        vagas_vistas: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executa as buscas em todas as fontes ativas, deduplicando por ID e Título+Empresa.
        """
        if vagas_vistas is None:
            vagas_vistas = set()

        fontes = [f.lower().strip() for f in (fontes_ativas or list(self.scrapers.keys()))]
        titulos_empresas_vistos: Set[Tuple[str, str]] = set()
        novas_vagas: List[Dict[str, Any]] = []

        for b in buscas:
            termo = b.get("termo", "")
            location = b.get("location")
            remote_only = b.get("remoto", False)
            geo_id = b.get("geo_id")

            loc_display = location if location else "Brasil (100% Remoto)"
            print(f"🔍 Coletando '{termo}' em '{loc_display}'...", flush=True)

            for nome_fonte, scraper in self.scrapers.items():
                if nome_fonte not in fontes:
                    continue

                try:
                    kwargs = {}
                    if geo_id:
                        kwargs["geo_id"] = geo_id

                    vagas_brutas = scraper.buscar_vagas(
                        keywords=termo,
                        location=location,
                        remote_only=remote_only,
                        max_pages=max_pages,
                        **kwargs
                    )
                except Exception as e:
                    print(f"[Aviso] Falha ao coletar de {nome_fonte}: {e}", flush=True)
                    vagas_brutas = []

                for v_item in vagas_brutas:
                    vaga_obj = Vaga.from_dict(v_item)
                    v_id = vaga_obj.id

                    # 1. Filtro por ID já visto anteriormente
                    if v_id in vagas_vistas:
                        continue

                    # 2. Deduplicação cross-platform por Título + Empresa
                    chave_dup = vaga_obj.chave_deduplicacao
                    if chave_dup[0] and chave_dup in titulos_empresas_vistos:
                        continue

                    vagas_vistas.add(v_id)
                    if chave_dup[0]:
                        titulos_empresas_vistos.add(chave_dup)

                    v_dict = vaga_obj.to_dict()
                    novas_vagas.append(v_dict)

        return novas_vagas
