import abc
import random
import re
from typing import List, Dict, Any, Optional

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]


class BaseJobScraper(abc.ABC):
    """
    Classe base abstrata para todos os scrapers de vagas de emprego.
    Padroniza métodos de filtragem, normalização de schema e cabeçalhos HTTP.
    """

    def __init__(self, fonte_nome: str = "Desconhecida"):
        self.fonte_nome = fonte_nome

    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Gera cabeçalhos HTTP com User-Agent rotativo e suporte a pt-BR."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    @staticmethod
    def eh_vaga_senior(titulo: str) -> bool:
        """
        Identifica se a vaga é de nível Sênior, Staff, Lead ou Especialista para descartar de imediato.
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

        # Captura 'sr', 'sr.', '(sr)', '- sr', 'snr', 'snr.' com limites de palavra
        if re.search(r"\b(sr|snr)\b|\b(sr|snr)\.", t):
            return True

        # Níveis numéricos/romanos tipicamente sênior (ex: 'Dev Java III', 'Nível 3', 'Nível III')
        if re.search(r"\b(desenvolvedor|engenheiro|dev|software engineer|analista|programador)\b.*\b(iii|iv|v)\b", t):
            return True
        if re.search(r"\bn[íi]vel\s*(?:3|iii|4|iv)\b", t):
            return True

        return False

    @staticmethod
    def eh_local_estrangeiro(localizacao: str) -> bool:
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
            "nova zelândia", "new vintage", "new zealand", "japão", "japan", "tokyo",
            "china", "pequim", "beijing", "singapura", "singapore",
            "israel", "tel aviv", "dubai", "emirados árabes", "uae",
            "áfrica do sul", "south africa"
        ]
        for termo in paises_e_cidades_estrangeiras:
            if termo in loc:
                return True

        # Siglas estrangeiras com ou sem pontuação (EUA, USA, UK, US, etc.)
        loc_sem_pontos = re.sub(r"\.", "", loc)
        if re.search(r"\b(eua|usa|uk|us)\b", loc_sem_pontos):
            return True

        return False

    def padronizar_vaga(
        self,
        id: str,
        titulo: str,
        empresa: str,
        localizacao: str,
        url: str,
        descricao: str = "",
        criterios: Optional[Dict[str, Any]] = None,
        publicado_em: str = "Recente",
        fonte: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Padroniza o dicionário da vaga para o schema unificado do sistema.
        """
        raw_id = str(id).strip()
        fonte_efetiva = fonte or self.fonte_nome
        
        # Garante prefixo identificador da fonte no ID se ainda não estiver presente
        prefix = f"{fonte_efetiva.lower()}_"
        id_final = raw_id if raw_id.startswith(prefix) else f"{prefix}{raw_id}"

        # Se descrição estiver vazia, define fallback inteligente
        desc_limpa = (descricao or "").strip()
        if not desc_limpa or len(desc_limpa) < 30:
            desc_final = (
                f"Vaga de {titulo or 'Desenvolvedor'} na empresa {empresa or 'Confidencial'}, "
                f"localizada em {localizacao or 'Brasil'}. "
                f"Oportunidade na área de tecnologia e desenvolvimento de software para início de carreira."
            )
            criterios_final = criterios or {"Tipo": "Início de Carreira"}
        else:
            desc_final = desc_limpa
            criterios_final = criterios or {}

        return {
            "id": id_final,
            "fonte": fonte_efetiva,
            "titulo": (titulo or "Vaga Sem Título").strip(),
            "empresa": (empresa or "Empresa Confidencial").strip(),
            "localizacao": (localizacao or "Brasil").strip(),
            "url": (url or "").strip(),
            "descricao": desc_final,
            "criterios": criterios_final,
            "publicado_em": (publicado_em or "Recente").strip()
        }

    @abc.abstractmethod
    def buscar_vagas(
        self,
        keywords: str = "Desenvolvedor Junior",
        location: Optional[str] = None,
        remote_only: bool = False,
        max_pages: int = 1,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Método abstrato que deve ser implementado por cada fonte específica.
        Deve retornar uma lista de dicionários padronizados com o schema unificado.
        """
        pass
