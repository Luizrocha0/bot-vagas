import requests
from bs4 import BeautifulSoup
import time
import json
import os
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

SEEN_JOBS_FILE = os.path.join(os.path.dirname(__file__), "vagas_vistas.json")


def carregar_vagas_vistas():
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def salvar_vagas_vistas(vagas_set):
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(vagas_set), f, indent=2, ensure_ascii=False)


def buscar_vagas_linkedin(keywords="Full Stack Next.js", location="Brasil", remote_only=False, max_pages=1):
    """
    Busca vagas no LinkedIn através da API pública para visitantes (sem login).
    """
    vagas = []
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    params = {
        "keywords": keywords,
        "location": location,
        "start": 0,
    }

    if remote_only:
        # f_WT=2 é o filtro de Remoto no LinkedIn
        params["f_WT"] = "2"

    for page in range(max_pages):
        params["start"] = page * 10
        try:
            response = requests.get(base_url, headers=HEADERS, params=params, timeout=12)
            if response.status_code != 200:
                print(f"[Aviso] Status {response.status_code} ao buscar '{keywords}' na página {page+1}")
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

                raw_url = link_elem.get("href", "").split("?")[0]
                job_id_match = re.search(r"-(\d+)$", raw_url) or re.search(r"/view/.*?(\d+)", raw_url)
                job_id = job_id_match.group(1) if job_id_match else raw_url

                vagas.append({
                    "id": job_id,
                    "titulo": title_elem.get_text(strip=True),
                    "empresa": company_elem.get_text(strip=True) if company_elem else "Empresa Confidencial",
                    "localizacao": location_elem.get_text(strip=True) if location_elem else "Não informado",
                    "url": raw_url,
                    "publicado_em": time_elem.get_text(strip=True) if time_elem else "Recente"
                })

            time.sleep(1.0)  # Intervalo educado entre requisições
        except Exception as e:
            print(f"[Erro] Falha ao consultar página {page+1} de '{keywords}': {e}")
            break

    return vagas


def obter_detalhes_vaga(job_id):
    """
    Obtém a descrição completa da vaga pública no LinkedIn.
    """
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
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
    except Exception as e:
        print(f"[Aviso] Não foi possível obter detalhes para o ID {job_id}: {e}")
        return {"descricao": "", "criterios": {}}
