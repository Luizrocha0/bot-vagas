import json
import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

from .base import BaseJobScraper


class GupyScraper(BaseJobScraper):
    """
    Scraper oficial para o portal Gupy (portal.gupy.io).
    Utiliza a estrutura __NEXT_DATA__ embutida pelo Next.js no portal de busca.
    """

    def __init__(self):
        super().__init__(fonte_nome="Gupy")
        self.base_url = "https://portal.gupy.io/job-search/term="

    def buscar_vagas(
        self,
        keywords: str = "Desenvolvedor Junior",
        location: Optional[str] = None,
        remote_only: bool = False,
        max_pages: int = 1,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Executa a busca de vagas na Gupy usando os termos informados.
        """
        termo_encoded = urllib.parse.quote(keywords)
        vagas_filtradas = []

        # Identifica se a busca pede localidade em Pernambuco / Recife
        busca_pe = False
        if location:
            loc_lower = location.lower()
            if any(termo in loc_lower for termo in ["recife", "pernambuco", "pe", "olinda", "porto digital"]):
                busca_pe = True

        for page in range(max_pages):
            offset = page * 10
            url = f"{self.base_url}{termo_encoded}"
            if offset > 0:
                url = f"{url}&offset={offset}"

            try:
                response = requests.get(
                    url,
                    headers=self.get_headers(),
                    timeout=10
                )
                if response.status_code != 200:
                    break

                jobs = self._extrair_jobs_next_data(response.text)
                if not jobs:
                    break

                for item in jobs:
                    vaga_dict = self._processar_job_item(item, remote_only=remote_only, busca_pe=busca_pe, location=location)
                    if vaga_dict:
                        vagas_filtradas.append(vaga_dict)

            except Exception as e:
                print(f"[Aviso] Falha ao consultar Gupy para '{keywords}' (pág {page+1}): {e}", flush=True)
                break

        return vagas_filtradas

    def _extrair_jobs_next_data(self, html_content: str) -> List[Dict[str, Any]]:
        """Extrai a lista de vagas do script __NEXT_DATA__ no HTML."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            script_elem = soup.find("script", id="__NEXT_DATA__")
            if not script_elem or not script_elem.string:
                return []

            data = json.loads(script_elem.string)
            props = data.get("props", {}).get("pageProps", {})
            initial_job_list = props.get("initialJobList", {})
            return initial_job_list.get("data", []) or []
        except Exception:
            return []

    def _processar_job_item(
        self,
        item: Dict[str, Any],
        remote_only: bool,
        busca_pe: bool,
        location: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Filtra e padroniza um item de vaga da Gupy.
        """
        titulo = item.get("name") or ""
        if not titulo or self.eh_vaga_senior(titulo):
            return None

        workplace_type = (item.get("workplaceType") or "").lower()
        is_remote = item.get("isRemoteWork") is True or workplace_type == "remote"
        city = (item.get("city") or "").strip()
        state = (item.get("state") or "").strip()

        # Determina string de localização amigável
        if is_remote:
            loc_str = "Remoto"
        elif city and state:
            loc_str = f"{city}, {state}" + (" (Híbrido)" if workplace_type == "hybrid" else "")
        elif city:
            loc_str = f"{city}" + (" (Híbrido)" if workplace_type == "hybrid" else "")
        else:
            loc_str = "Brasil"

        # Se for estrangeiro
        if self.eh_local_estrangeiro(loc_str):
            return None

        # Filtro de modalidade remota
        if remote_only and not is_remote:
            return None

        # Filtro de localidade específica (ex: Recife / PE)
        if location and busca_pe:
            state_clean = state.upper().strip()
            city_lower = city.lower().strip()
            if state_clean in ["PE", "PERNAMBUCO"]:
                is_pe = True
            elif state_clean and state_clean not in ["PE", "PERNAMBUCO"]:
                is_pe = False
            else:
                cidades_pe = ["recife", "olinda", "jaboatão", "jaboatao", "paulista", "camaragibe", "porto digital"]
                is_pe = any(c in city_lower for c in cidades_pe)

            if not is_pe:
                return None

        job_id = str(item.get("id"))
        job_url = item.get("jobUrl") or f"https://portal.gupy.io/job-search/job/{job_id}"
        empresa = item.get("careerPageName") or "Empresa Parceira Gupy"
        descricao = item.get("description") or ""
        publicado = item.get("publishedAt") or "Recente"

        criterios = {
            "Tipo": item.get("type", "Efetivo"),
            "Modalidade": "Remoto" if is_remote else ("Híbrido" if workplace_type == "hybrid" else "Presencial"),
            "Cidade": city,
            "Estado": state
        }

        return self.padronizar_vaga(
            id=job_id,
            titulo=titulo,
            empresa=empresa,
            localizacao=loc_str,
            url=job_url,
            descricao=descricao,
            criterios=criterios,
            publicado_em=publicado,
            fonte="Gupy"
        )
