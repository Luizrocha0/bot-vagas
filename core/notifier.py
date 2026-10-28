from typing import Callable, List, Dict, Any, Optional


class NotificationDispatcher:
    """
    Despachante de notificações (Padrão Observer / Composite).
    Encapsula o envio de alertas para múltiplos canais (Telegram, WhatsApp, etc.)
    sem acoplar o orquestrador aos canais individuais.
    """

    def __init__(self, notifiers: Optional[List[Callable[[Dict[str, Any], Dict[str, Any]], bool]]] = None):
        self.notifiers = notifiers or []

    def registrar_notificador(self, notifier_func: Callable[[Dict[str, Any], Dict[str, Any]], bool]) -> None:
        """Registra um novo canal de notificação."""
        self.notifiers.append(notifier_func)

    def disparar(self, vaga: Dict[str, Any], analise: Dict[str, Any]) -> Dict[str, bool]:
        """Dispara a notificação para todos os canais registrados."""
        resultados = {}
        for func in self.notifiers:
            nome = getattr(func, "__name__", str(func))
            try:
                sucesso = func(vaga, analise)
                resultados[nome] = bool(sucesso)
            except Exception as e:
                print(f"[Aviso] Erro no notificador {nome}: {e}", flush=True)
                resultados[nome] = False
        return resultados
