import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

from .base import BaseJobScraper


class IndeedScraper(BaseJobScraper):
    """
    Scraper para o Indeed Brasil (br.indeed.com) com fallback automático
    para repositórios da comunidade tech brasileira (backend-br/vagas e frontendbr/vagas)
    em caso de bloqueio por Cloudflare (403/Challenge).
    """

    def __init__(self):
        super().__init__(fonte_nome="Indeed")
        self.indeed_base_url = "https://br.indeed.com/jobs"
        self.github_repos = [
            "frontendbr/vagas",
            "backend-br/vagas"
        ]

    def buscar_vagas(
        self,
        keywords: str = "Junior",
        location: Optional[str] = None,
        remote_only: bool = False,
        max_pages: int = 1,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Executa a busca no Indeed; se bloqueado por Cloudflare, recorre ao agregador tech.
        """
        vagas = self._buscar_indeed_direto(keywords, location, remote_only, max_pages)
        if vagas is not None and len(vagas) > 0:
            return vagas

        # Fallback resiliente
        return self._buscar_agregador_fallback(keywords, location, remote_only)

    def _buscar_indeed_direto(
        self,
        keywords: str,
        location: Optional[str],
        remote_only: bool,
        max_pages: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Tenta requisitar diretamente o portal Indeed."""
        vagas = []
        loc_param = location or ("Remoto" if remote_only else "Brasil")
        params = {
            "q": keywords,
            "l": loc_param
        }

        try:
            response = requests.get(
                self.indeed_base_url,
                headers=self.get_headers(),
                params=params,
                timeout=8
            )
            if response.status_code == 200:
                parsed = self._parse_indeed_html(response.text, remote_only=remote_only, location=location)
                return parsed
            else:
                return None
        except Exception:
            return None

    def _parse_indeed_html(
        self,
        html_content: str,
        remote_only: bool = False,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Analisa o HTML de resultados do Indeed."""
        vagas = []
        soup = BeautifulSoup(html_content, "html.parser")
        cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|jobCard"))

        busca_pe = False
        if location:
            loc_lower = location.lower()
            if any(termo in loc_lower for termo in ["recife", "pernambuco", "pe", "olinda", "porto digital"]):
                busca_pe = True

        for card in cards:
            title_elem = card.find("h2", class_=re.compile(r"jobTitle"))
            titulo = title_elem.get_text(strip=True) if title_elem else ""
            if not titulo or self.eh_vaga_senior(titulo):
                continue

            company_elem = card.find("span", class_=re.compile(r"companyName|company"))
            empresa = company_elem.get_text(strip=True) if company_elem else "Empresa Confidencial"

            loc_elem = card.find("div", class_=re.compile(r"companyLocation|location"))
            local = loc_elem.get_text(strip=True) if loc_elem else "Brasil"

            if self.eh_local_estrangeiro(local):
                continue

            is_remote = "remoto" in local.lower() or "home office" in local.lower()

            if remote_only and not is_remote:
                continue

            if location and busca_pe:
                local_lower = local.lower()
                is_pe = any(c in local_lower for c in ["recife", "pernambuco", "pe", "olinda", "porto digital", "jaboatão"])
                if not is_pe:
                    continue

            link_elem = card.find("a", href=True)
            job_key = card.get("data-jk") or (link_elem.get("data-jk") if link_elem else None)
            if not job_key and link_elem:
                jk_match = re.search(r"jk=([a-zA-Z0-9]+)", link_elem["href"])
                if jk_match:
                    job_key = jk_match.group(1)

            job_id = job_key or f"indeed_{len(vagas)+1}"
            job_url = f"https://br.indeed.com/viewjob?jk={job_key}" if job_key else "https://br.indeed.com"

            snippet_elem = card.find("div", class_=re.compile(r"job-snippet|snippet"))
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            vagas.append(
                self.padronizar_vaga(
                    id=job_id,
                    titulo=titulo,
                    empresa=empresa,
                    localizacao=local,
                    url=job_url,
                    descricao=snippet,
                    criterios={"Modalidade": "Remoto" if is_remote else "Presencial/Híbrido"},
                    fonte="Indeed"
                )
            )

        return vagas

    def _buscar_agregador_fallback(
        self,
        keywords: str,
        location: Optional[str],
        remote_only: bool
    ) -> List[Dict[str, Any]]:
        """
        Consulta vagas em repositórios abertos de tecnologia brasileiros
        quando o Indeed estiver sob Cloudflare challenge.
        """
        vagas = []
        vistas_ids = set()
        kw_lower = keywords.lower()
        busca_pe = False
        if location:
            loc_lower = location.lower()
            if any(termo in loc_lower for termo in ["recife", "pernambuco", "pe", "olinda", "porto digital"]):
                busca_pe = True

        for repo in self.github_repos:
            api_url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=15"
            try:
                resp = requests.get(api_url, headers=self.get_headers(), timeout=8)
                if resp.status_code != 200:
                    continue

                issues = resp.json()
                if not isinstance(issues, list):
                    continue

                for issue in issues:
                    issue_id = str(issue.get("id"))
                    if issue_id in vistas_ids:
                        continue

                    raw_title = issue.get("title") or ""
                    labels = [l.get("name", "") for l in issue.get("labels", []) if isinstance(l, dict)]
                    labels_str = " ".join(labels).lower()

                    # Descarte de sênior
                    if self.eh_vaga_senior(raw_title) or "sênior" in labels_str or "senior" in labels_str:
                        continue

                    # Localização e modalidade a partir do título e labels
                    is_remote = "remoto" in raw_title.lower() or "remoto" in labels_str
                    is_pe = any(c in raw_title.lower() or c in labels_str for c in ["recife", "pernambuco", "pe", "porto digital"])

                    if remote_only and not is_remote:
                        continue

                    if location and busca_pe and not is_pe:
                        continue

                    # Filtragem por relevância de palavras-chave
                    texto_completo = f"{raw_title} {issue.get('body', '')} {labels_str}".lower()
                    termos_busca = [t for t in re.split(r"\s+", kw_lower) if len(t) > 2]
                    if termos_busca and not any(t in texto_completo for t in termos_busca):
                        continue

                    # Extração amigável de cargo e empresa do título
                    titulo_limpo = re.sub(r"^\[.*?\]\s*", "", raw_title).strip()
                    empresa = "Empresa Confidencial"
                    if " na " in titulo_limpo:
                        partes = titulo_limpo.split(" na ", 1)
                        titulo_limpo = partes[0].strip()
                        empresa = partes[1].split("|")[0].split("-")[0].strip()
                    elif " - " in titulo_limpo:
                        partes = titulo_limpo.split(" - ", 1)
                        titulo_limpo = partes[0].strip()
                        empresa = partes[1].split("|")[0].strip()

                    loc_final = "Remoto" if is_remote else ("Recife, PE" if is_pe else "Brasil")
                    body = (issue.get("body") or "").strip()
                    desc = body[:1200] if body else f"Vaga de {titulo_limpo} na empresa {empresa}."

                    vistas_ids.add(issue_id)
                    vagas.append(
                        self.padronizar_vaga(
                            id=issue_id,
                            titulo=titulo_limpo,
                            empresa=empresa,
                            localizacao=loc_final,
                            url=issue.get("html_url") or "",
                            descricao=desc,
                            criterios={"Modalidade": "Remoto" if is_remote else "Presencial", "Labels": labels},
                            publicado_em=issue.get("created_at", "Recente")[:10],
                            fonte="Indeed (Agregador Tech)"
                        )
                    )

            except Exception as e:
                print(f"[Aviso] Falha no agregador fallback ({repo}): {e}", flush=True)
                continue

        return vagas
