import requests
from bs4 import BeautifulSoup
import time
import json
import os
import re
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

SEEN_JOBS_FILE = os.path.join(os.path.dirname(__file__), "vagas_vistas.json")
GEO_ID_BRASIL = "106057199"


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }


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


def eh_vaga_senior(titulo):
    """
    Identifica se a vaga é de nível Sênior, Staff ou Lead para descartar de imediato.
    """
    if not titulo or not isinstance(titulo, str):
        return False
    t = titulo.lower()
    termos_proibidos = [
        "senior", "sênior", "staff", "lead",
        "principal", "especialista", "specialist", "manager", "head",
        "diretor", "director", "tech lead", "architect", "arquiteto",
        "pleno/senior", "pleno / sênior", "pl/sr"
    ]
    if any(termo in t for termo in termos_proibidos):
        return True

    # Captura 'sr', 'sr.', '(sr)', '- sr', 'snr', 'snr.', etc. com limites de palavra
    if re.search(r"\b(sr|snr)\b|\b(sr|snr)\.", t):
        return True

    # Níveis numéricos/romanos tipicamente sênior (ex: 'Engenheiro III', 'Desenvolvedor III', 'Dev Java III', 'Nível 3', 'Nível III')
    if re.search(r"\b(desenvolvedor|engenheiro|dev|software engineer|analista|programador)\b.*\b(iii|iv|v)\b", t):
        return True
    if re.search(r"\bn[íi]vel\s*(?:3|iii|4|iv)\b", t):
        return True

    return False


def eh_local_estrangeiro(localizacao):
    """
    Descarta vagas do exterior (EUA, Europa, etc.).
    """
    if not localizacao or not isinstance(localizacao, str):
        return False
    loc = localizacao.lower()

    # Se contiver menção explícita a brasil/brazil, não considera estrangeiro
    if "brazil" in loc or "brasil" in loc:
        return False

    paises_e_cidades_estrangeiras = [
        # América do Norte e polos tech
        "estados unidos", "united states", "canada", "canadá",
        "san francisco", "new york", "seattle", "austin", "chicago",
        "los angeles", "boston", "silicon valley",
        # Europa
        "reino unido", "united kingdom", "london", "germany", "alemanha",
        "berlin", "munich", "poland", "polônia", "france", "frança", "paris",
        "portugal", "lisboa", "lisbon", "espanha", "spain", "madrid", "barcelona",
        "itália", "italy", "roma", "milan", "milão",
        "netherlands", "holanda", "amsterdam", "irlanda", "ireland", "dublin",
        "suécia", "sweden", "suíça", "switzerland", "bélgica", "belgium",
        "austria", "áustria",
        # América Latina (fora do Brasil)
        "argentina", "buenos aires", "chile", "colômbia", "colombia",
        "méxico", "mexico", "uruguai", "uruguay", "montevideo", "montevidéu",
        "paraguai", "paraguay",
        # Ásia / Oceania / Oriente Médio / África
        "india", "índia", "bangalore", "australia", "austrália",
        "nova zelândia", "new zealand", "japão", "japan", "tokyo",
        "china", "pequim", "beijing", "singapura", "singapore",
        "israel", "tel aviv", "dubai", "emirados árabes", "uae",
        "áfrica do sul", "south africa"
    ]
    for termo in paises_e_cidades_estrangeiras:
        if termo in loc:
            return True

    # Siglas estrangeiras com ou sem pontuação (EUA, USA, UK, US, E.U.A., U.S.A., U.K., U.S.)
    loc_sem_pontos = re.sub(r"\.", "", loc)
    if re.search(r"\b(eua|usa|uk|us)\b", loc_sem_pontos):
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
