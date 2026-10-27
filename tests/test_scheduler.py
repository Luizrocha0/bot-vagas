import pytest
from unittest.mock import patch, MagicMock
import scheduler
from scheduler import job


class TestScheduler:
    """Testes unitários para o agendador de execução periódica (scheduler.py)."""

    @patch("scheduler.executar_busca")
    def test_job_remoto_apenas(self, mock_executar, monkeypatch):
        monkeypatch.setattr(scheduler, "REMOTE_ONLY", True)
        job()
        mock_executar.assert_called_once_with(
            meta_remotas=4,
            meta_presenciais=0,
            max_pages_per_term=1
        )

    @patch("scheduler.executar_busca")
    def test_job_balanceado_remoto_e_presencial(self, mock_executar, monkeypatch):
        monkeypatch.setattr(scheduler, "REMOTE_ONLY", False)
        job()
        mock_executar.assert_called_once_with(
            meta_remotas=2,
            meta_presenciais=2,
            max_pages_per_term=1
        )

    @patch("scheduler.schedule")
    @patch("scheduler.job")
    def test_iniciar_agendador_registra_horarios(self, mock_job, mock_schedule, monkeypatch):
        monkeypatch.setattr(scheduler, "HORARIOS", ["09:00", "15:00"])
        # Evita entrar no loop infinito while True
        monkeypatch.setattr(scheduler.time, "sleep", MagicMock(side_effect=KeyboardInterrupt))

        with pytest.raises(KeyboardInterrupt):
            scheduler.iniciar_agendador()

        # Deve agendar para os 2 horários configurados
        assert mock_schedule.every().day.at.call_count == 2
        # Deve executar uma vez imediatamente na inicialização
        mock_job.assert_called_once()
