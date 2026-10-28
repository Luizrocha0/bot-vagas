import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

from .base import BaseJobScraper


class ProgramathorScraper(BaseJobScraper):
    """
    Scraper oficial para o Programathor (programathor.com.br).
    Especializado em oportunidades para desenvolvedores de software no Brasil.
    """

    def __init__(self):
        super().__init__(fonte_nome="Programathor")
        self.base_url = "https://programathor.com.br/jobs"

    def buscar_vagas(
        self,
        keywords: str = "Junior",
        location: Optional[str] = None,
        remote_only: bool = False,
        max_pages: int = 1,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Busca vagas no Programathor com filtros por nível e localização.
        """
        vagas_encontradas = []

        busca_pe = False
        if location:
            loc_lower = location.lower()
            if any(termo in loc_lower for termo in ["recife", "pernambuco", "pe", "olinda", "porto digital"]):
                busca_pe = True

        for page in range(1, max_pages + 1):
            params = {
                "q": keywords,
                "page": page
            }
            try:
                response = requests.get(
                    self.base_url,
                    headers=self.get_headers(),
                    params=params,
                    timeout=10
                )
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.find_all("div", class_="cell-list")
                if not cards:
                    break

                for card in cards:
                    vaga = self._processar_card(card, remote_only=remote_only, busca_pe=busca_pe, location=location)
                    if vaga:
                        vagas_encontradas.append(vaga)

            except Exception as e:
                print(f"[Aviso] Falha ao consultar Programathor para '{keywords}' (pág {page}): {e}", flush=True)
                break

        return vagas_encontradas

    def _processar_card(
        self,
        card: Any,
        remote_only: bool,
        busca_pe: bool,
        location: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai e valida dados de um card de vaga do Programathor.
        """
        link_elem = card.find("a")
        if not link_elem:
            return None

        href = link_elem.get("href") or ""
        if not href:
            return None

        title_elem = card.find("h3")
        titulo = title_elem.get_text(strip=True) if title_elem else ""
        if not titulo or self.eh_vaga_senior(titulo):
            return None

        # Extração de ícones/metadados
        empresa = "Empresa Confidencial"
        local = "Brasil"
        nivel = "Não especificado"
        contrato = "CLT"

        company_icon = card.find("i", class_="fa-briefcase")
        if company_icon and company_icon.parent:
            empresa = company_icon.parent.get_text(strip=True)

        location_icon = card.find("i", class_=re.compile(r"map-marker"))
        if location_icon and location_icon.parent:
            local = location_icon.parent.get_text(strip=True)

        level_icon = card.find("i", class_=re.compile(r"chart-bar"))
        if level_icon and level_icon.parent:
            nivel = level_icon.parent.get_text(strip=True)

        contract_icon = card.find("i", class_=re.compile(r"file-alt"))
        if contract_icon and contract_icon.parent:
            contrato = contract_icon.parent.get_text(strip=True)

        # Filtro de senioridade pelo metadado de nível do card
        nivel_lower = nivel.lower()
        if any(s in nivel_lower for s in ["sênior", "senior", "lead", "staff", "especialista"]):
            return None

        # Tags de stack
        tag_elems = card.find_all("span", class_="tag-list")
        tags = [t.get_text(strip=True) for t in tag_elems if t.get_text(strip=True)]

        is_remote = "remoto" in local.lower() or "home office" in local.lower()

        # Filtro de local estrangeiro
        if self.eh_local_estrangeiro(local):
            return None

        # Filtro de apenas remoto
        if remote_only and not is_remote:
            return None

        # Filtro de Recife / PE
        if location and busca_pe:
            local_lower = local.lower()
            is_pe = any(c in local_lower for c in ["recife", "pernambuco", "pe", "olinda", "porto digital", "jaboatão"])
            if not is_pe:
                return None

        # ID e URL
        slug = href.lstrip("/").replace("jobs/", "")
        job_id_match = re.search(r"^(\d+)", slug)
        job_id = job_id_match.group(1) if job_id_match else slug
        full_url = f"https://programathor.com.br/jobs/{slug}"

        # Descrição estruturada a partir dos metadados e tags
        tags_str = ", ".join(tags) if tags else "Tecnologia e Desenvolvimento"
        descricao_fallback = (
            f"Vaga de {titulo} na empresa {empresa}. "
            f"Local de trabalho: {local}. Nível de experiência: {nivel}. "
            f"Modalidade de contratação: {contrato}. "
            f"Stack e tecnologias da oportunidade: {tags_str}."
        )

        criterios = {
            "Nível": nivel,
            "Contrato": contrato,
            "Tags": tags,
            "Modalidade": "Remoto" if is_remote else "Presencial/Híbrido"
        }

        return self.padronizar_vaga(
            id=job_id,
            titulo=titulo,
            empresa=empresa,
            localizacao=local,
            url=full_url,
            descricao=descricao_fallback,
            criterios=criterios,
            fonte="Programathor"
        )

    def obter_detalhes(self, job_slug_or_id: str) -> Dict[str, Any]:
        """
        Obtém a descrição detalhada da vaga a partir da página pública do Programathor.
        """
        target = str(job_slug_or_id).strip()
        if not target:
            return {"descricao": "", "criterios": {}}

        if not target.startswith("http"):
            if not target.startswith("jobs/"):
                url = f"https://programathor.com.br/jobs/{target}"
            else:
                url = f"https://programathor.com.br/{target}"
        else:
            url = target

        try:
            response = requests.get(url, headers=self.get_headers(), timeout=8)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                wrapper = soup.find("div", class_="wrapper-content-job-show")
                desc_texto = wrapper.get_text(separator="\n", strip=True) if wrapper else ""
                return {
                    "descricao": desc_texto,
                    "criterios": {}
                }
            return {"descricao": "", "criterios": {}}
        except Exception:
            return {"descricao": "", "criterios": {}}
