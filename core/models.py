import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


class ModalidadeVaga(str, Enum):
    """Tipos de modalidade admitidos pelo caçador de vagas."""
    REMOTO = "REMOTO"
    PRESENCIAL_PE = "PRESENCIAL_PE"
    INVALIDA = "INVALIDA"

    @classmethod
    def from_str(cls, val: Optional[str]) -> "ModalidadeVaga":
        if not val or not isinstance(val, str):
            return cls.INVALIDA
        v = val.strip().upper()
        if "REMOTO" in v or "REMOTE" in v:
            return cls.REMOTO
        if "PRESENCIAL_PE" in v or "RECIFE" in v or "PE" in v:
            return cls.PRESENCIAL_PE
        return cls.INVALIDA


@dataclass
class Vaga:
    """
    Entidade de domínio que representa uma vaga de emprego normalizada.
    Encapsula regras de deduplicação e normalização de atributos.
    """
    id: str
    fonte: str = "LinkedIn"
    titulo: str = "Vaga Sem Título"
    empresa: str = "Empresa Confidencial"
    localizacao: str = "Brasil"
    url: str = ""
    descricao: str = ""
    criterios: Dict[str, Any] = field(default_factory=dict)
    publicado_em: str = "Recente"

    def __post_init__(self):
        self.id = str(self.id or "").strip()
        self.fonte = str(self.fonte or "LinkedIn").strip()
        self.titulo = str(self.titulo or "Vaga Sem Título").strip()
        self.empresa = str(self.empresa or "Empresa Confidencial").strip()
        self.localizacao = str(self.localizacao or "Brasil").strip()
        self.url = str(self.url or "").strip()
        self.descricao = str(self.descricao or "").strip()
        self.publicado_em = str(self.publicado_em or "Recente").strip()
        if not isinstance(self.criterios, dict):
            self.criterios = {}

    @property
    def chave_deduplicacao(self) -> Tuple[str, str]:
        """Gera chave limpa (título + empresa) para evitar duplicatas entre plataformas."""
        t_clean = re.sub(r"[^\w]", "", self.titulo.lower())
        e_clean = re.sub(r"[^\w]", "", self.empresa.lower())
        return (t_clean, e_clean)

    def to_dict(self) -> Dict[str, Any]:
        """Converte a entidade de domínio para o dicionário padrão do sistema."""
        return {
            "id": self.id,
            "fonte": self.fonte,
            "titulo": self.titulo,
            "empresa": self.empresa,
            "localizacao": self.localizacao,
            "url": self.url,
            "descricao": self.descricao,
            "criterios": self.criterios,
            "publicado_em": self.publicado_em
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Vaga":
        """Instancia uma Vaga a partir de um dicionário, com fallbacks seguros."""
        if not isinstance(data, dict):
            data = {}
        raw_id = data.get("id") or data.get("url") or f"{data.get('titulo')}_{data.get('empresa')}"
        return cls(
            id=str(raw_id),
            fonte=data.get("fonte", "LinkedIn"),
            titulo=data.get("titulo", "Vaga Sem Título"),
            empresa=data.get("empresa", "Empresa Confidencial"),
            localizacao=data.get("localizacao", "Brasil"),
            url=data.get("url", ""),
            descricao=data.get("descricao", ""),
            criterios=data.get("criterios") or {},
            publicado_em=data.get("publicado_em", "Recente")
        )


@dataclass
class ResultadoMatch:
    """
    Value Object que representa o resultado da análise de compatibilidade via Gemini.
    """
    score: int
    modalidade: ModalidadeVaga
    eh_junior_ou_estagio: bool
    classificacao: str = ""
    resumo_vaga: str = ""
    pontos_fortes: List[str] = field(default_factory=list)
    requisitos_faltantes: List[str] = field(default_factory=list)
    dica_candidatura: str = ""
    vale_a_pena_candidatar: bool = True

    def __post_init__(self):
        self.score = max(0, min(100, int(self.score or 0)))

    def eh_elegivel(self, limiar_score: int = 35) -> bool:
        """Determina se a vaga atende aos critérios mínimos de início de carreira e localidade."""
        if self.score < limiar_score:
            return False
        if not self.eh_junior_ou_estagio:
            return False
        if self.modalidade not in (ModalidadeVaga.REMOTO, ModalidadeVaga.PRESENCIAL_PE):
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compatibilidade_percentual": self.score,
            "tipo_modalidade": self.modalidade.value,
            "eh_junior_ou_estagio": self.eh_junior_ou_estagio,
            "classificacao": self.classificacao,
            "resumo_vaga": self.resumo_vaga,
            "pontos_fortes": self.pontos_fortes,
            "requisitos_faltantes": self.requisitos_faltantes,
            "dica_candidatura": self.dica_candidatura,
            "vale_a_pena_candidatar": self.vale_a_pena_candidatar
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ResultadoMatch":
        if not isinstance(data, dict):
            data = {}

        raw_score = data.get("compatibilidade_percentual")
        if isinstance(raw_score, str):
            digits = re.sub(r"[^\d]", "", raw_score)
            score = int(digits) if digits else 0
        elif raw_score is not None:
            try:
                score = int(raw_score)
            except (ValueError, TypeError):
                score = 0
        else:
            score = 0

        modalidade = ModalidadeVaga.from_str(data.get("tipo_modalidade"))

        eh_jr = data.get("eh_junior_ou_estagio")
        if isinstance(eh_jr, str):
            eh_jr = eh_jr.strip().lower() in ["true", "sim", "1", "yes"]
        elif eh_jr is None:
            eh_jr = True

        return cls(
            score=score,
            modalidade=modalidade,
            eh_junior_ou_estagio=bool(eh_jr),
            classificacao=str(data.get("classificacao") or ""),
            resumo_vaga=str(data.get("resumo_vaga") or ""),
            pontos_fortes=data.get("pontos_fortes") or [],
            requisitos_faltantes=data.get("requisitos_faltantes") or [],
            dica_candidatura=str(data.get("dica_candidatura") or ""),
            vale_a_pena_candidatar=bool(data.get("vale_a_pena_candidatar", True))
        )
