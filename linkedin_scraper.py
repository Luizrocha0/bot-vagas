import requests
from bs4 import BeautifulSoup
import time
import json
import os
import re
from typing import List, Dict, Any, Optional

from scrapers.base import BaseJobScraper, USER_AGENTS

SEEN_JOBS_FILE = os.path.join(os.path.dirname(__file__), "vagas_vistas.json")
GEO_ID_BRASIL = "106057199"

# Funções utilitárias preservadas para retrocompatibilidade
eh_vaga_senior = BaseJobScraper.eh_vaga_senior
eh_local_estrangeiro = BaseJobScraper.eh_local_estrangeiro
get_headers = BaseJobScraper.get_headers


def carregar_vagas_vistas():
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    return set(str(x) for x in dados)
                elif isinstance(dados, dict):
                    return set(str(k) for k in dados.keys())
                return set()
        except Exception:
            return set()
    return set()


def salvar_vagas_vistas(vagas_set):
    try:
        with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(vagas_set), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Aviso] Falha ao salvar vagas vistas: {e}", flush=True)


class LinkedInScraper(BaseJobScraper):
    """
    Scraper para o LinkedIn baseado na API pública de visitantes (guest API).
    """

    def __init__(self):
        super().__init__(fonte_nome="LinkedIn")

    def buscar_vagas(
        self,
        keywords: str = "Desenvolvedor Junior",
        location: Optional[str] = None,
        remote_only: bool = False,
        max_pages: int = 1,
        geo_id: Optional[str] = GEO_ID_BRASIL,
        **kwargs
    ) -> List[Dict[str, Any]]:
        return buscar_vagas_linkedin(
            keywords=keywords,
            location=location,
            geo_id=geo_id,
            remote_only=remote_only,
            max_pages=max_pages
        )

    def obter_detalhes(self, job_id: str) -> Dict[str, Any]:
        return obter_detalhes_vaga(job_id)


def buscar_vagas_linkedin(keywords="Desenvolvedor Junior", location=None, geo_id=GEO_ID_BRASIL, remote_only=False, max_pages=1):
    """
    Busca vagas no LinkedIn através da API pública para visitantes.
    """
    vagas = []
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    params = {
        "keywords": keywords,
        "start": 0,
    }

    if location:
        params["location"] = location
    elif geo_id:
        params["geoId"] = geo_id

    if remote_only:
        params["f_WT"] = "2"

    for page in range(max_pages):
        params["start"] = page * 10
        try:
            response = requests.get(base_url, headers=get_headers(), params=params, timeout=8)
            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("li")
            if not job_cards:
                break

            for card in job_cards:
                title_elem = card.find("h3", class_="base-search-card__title")
                company_elem = card.find("h4", class_="base-search-card__subtitle")
                location_elem = card.find("span", class_="job-search-card__location")
                link_elem = card.find("a", class_="base-card__full-link")
                time_elem = card.find("time")

                if not title_elem or not link_elem:
                    continue

                titulo = title_elem.get_text(strip=True)
                local = location_elem.get_text(strip=True) if location_elem else "Brasil"

                if eh_vaga_senior(titulo):
                    continue

                if eh_local_estrangeiro(local):
                    continue

                href_val = link_elem.get("href") or ""
                raw_url = href_val.split("?")[0]
                if raw_url.startswith("/"):
                    raw_url = f"https://www.linkedin.com{raw_url}"
                job_id_match = re.search(r"-(\d+)$", raw_url) or re.search(r"/view/.*?(\d+)", raw_url)
                job_id = job_id_match.group(1) if job_id_match else (raw_url or f"vaga_{titulo}")

                vagas.append({
                    "id": job_id,
                    "fonte": "LinkedIn",
                    "titulo": titulo,
                    "empresa": company_elem.get_text(strip=True) if company_elem else "Empresa Confidencial",
                    "localizacao": local,
                    "url": raw_url,
                    "publicado_em": time_elem.get_text(strip=True) if time_elem else "Recente"
                })

            time.sleep(0.5)
        except Exception as e:
            print(f"[Aviso] Busca '{keywords}' na pág {page+1} finalizada: {e}", flush=True)
            break

    return vagas


def obter_detalhes_vaga(job_id):
    """
    Obtém a descrição completa da vaga pública no LinkedIn.
    """
    if not job_id:
        return {"descricao": "", "criterios": {}}

    target_id = str(job_id).strip()
    # Se recebeu uma URL completa ou identificador composto, extrai os dígitos do ID
    if "/" in target_id or not target_id.isalnum():
        match = re.search(r"-(\d+)$", target_id) or re.search(r"/view/.*?(\d+)", target_id) or re.search(r"(\d{8,})", target_id)
        if match:
            target_id = match.group(1)

    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{target_id}"
    try:
        response = requests.get(url, headers=get_headers(), timeout=6)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            desc_elem = soup.find("div", class_="show-more-less-html__markup")
            criterios = {}
            for item in soup.find_all("li", class_="description__job-criteria-item"):
                header = item.find("h3")
                val = item.find("span")
                if header and val:
                    criterios[header.get_text(strip=True)] = val.get_text(strip=True)

            descricao_texto = desc_elem.get_text(separator="\n", strip=True) if desc_elem else ""
            return {
                "descricao": descricao_texto,
                "criterios": criterios
            }
        else:
            return {"descricao": "", "criterios": {}}
    except Exception:
        return {"descricao": "", "criterios": {}}
