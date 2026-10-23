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
GEO_ID_BRASIL = "106057199"

# Sessão persistente reutiliza conexões TCP/SSL (3x mais rápida)
session = requests.Session()
session.headers.update(HEADERS)


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


def eh_vaga_senior(titulo):
    """
    Identifica se a vaga é de nível Sênior, Staff ou Lead para descartar de imediato.
    """
    t = titulo.lower()
    termos_proibidos = [
        "senior", "sênior", "sr.", "sr ", "/sr", "-sr", "staff", "lead",
        "principal", "especialista", "specialist", "manager", "head",
        "diretor", "director", "tech lead", "architect", "arquiteto",
        "pleno/senior", "pleno / sênior", "pl/sr"
    ]
    return any(termo in t for termo in termos_proibidos)


def eh_local_estrangeiro(localizacao):
    """
    Descarta vagas do exterior (EUA, Europa, etc.).
    """
    loc = localizacao.lower()
    paises_estrangeiros = [
        "estados unidos", "united states", "canada", "canadá",
        "india", "índia", "reino unido", "united kingdom", "london",
        "germany", "alemanha", "poland", "polônia", "france", "frança"
    ]
    for p in paises_estrangeiros:
        if p in loc and "brazil" not in loc and "brasil" not in loc:
            return True
    return False


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
            response = session.get(base_url, params=params, timeout=6)
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

                raw_url = link_elem.get("href", "").split("?")[0]
                job_id_match = re.search(r"-(\d+)$", raw_url) or re.search(r"/view/.*?(\d+)", raw_url)
                job_id = job_id_match.group(1) if job_id_match else raw_url

                vagas.append({
                    "id": job_id,
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
    Obtém a descrição completa da vaga pública no LinkedIn com timeout ágil de 5s.
    """
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        response = session.get(url, timeout=5)
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
        # Se demorar mais de 5s, pula rápido para a próxima
        return {"descricao": "", "criterios": {}}
