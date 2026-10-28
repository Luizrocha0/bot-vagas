"""
Camada Core da aplicação Bot-Vagas.
Implementa os princípios de Clean Architecture, SOLID e Clean Code:
- models: Entidades e Value Objects de domínio
- collector: Coletor e deduplicador desacoplado de vagas
- selector: Gerenciador de cotas e balanceamento de vagas
- notifier: Despachante unificado de notificações
- repository: Persistência desacoplada de histórico e vagas vistas
"""

from .models import Vaga, ResultadoMatch, ModalidadeVaga
from .collector import JobCollector
from .selector import QuotaSelector
from .notifier import NotificationDispatcher
from .repository import JobRepository

__all__ = [
    "Vaga",
    "ResultadoMatch",
    "ModalidadeVaga",
    "JobCollector",
    "QuotaSelector",
    "NotificationDispatcher",
    "JobRepository"
]
