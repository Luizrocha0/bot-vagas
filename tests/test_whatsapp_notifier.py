import pytest
from unittest.mock import patch, MagicMock
import requests

from whatsapp_notifier import (
    formatar_mensagem_whatsapp,
    enviar_notificacao_whatsapp,
    testar_conexao_whatsapp
)


class TestWhatsappNotifier:
    """Testes para formatação, envio e teste de conexão via WhatsApp (CallMeBot)."""

    def test_formatar_mensagem_whatsapp_completa(self, sample_vaga, sample_analise_remoto):
        sample_analise_remoto["compatibilidade_percentual"] = 85
        msg = formatar_mensagem_whatsapp(sample_vaga, sample_analise_remoto)

        assert "🔥 *Match Encontrado: 85%" in msg
        assert sample_vaga["titulo"] in msg
        assert sample_vaga["empresa"] in msg
        assert sample_vaga["localizacao"] in msg
        assert sample_vaga["url"] in msg
        assert "Dica do Gemini" in msg
        assert "Atenção / Requisitos a Revisar:" in msg

    def test_formatar_mensagem_whatsapp_sem_campos_opcionais(self, sample_vaga, sample_analise_remoto):
        sample_analise_remoto["compatibilidade_percentual"] = 72
        sample_analise_remoto["requisitos_faltantes"] = []
        sample_analise_remoto["dica_candidatura"] = ""

        msg = formatar_mensagem_whatsapp(sample_vaga, sample_analise_remoto)
        assert "⭐ *Match Encontrado: 72%" in msg
        assert "Atenção / Requisitos a Revisar:" not in msg
        assert "Dica do Gemini" not in msg

    def test_formatar_mensagem_whatsapp_com_campos_none(self):
        vaga_nula = {
            "titulo": None,
            "empresa": None,
            "localizacao": None,
            "url": None
        }
        analise_nula = {
            "compatibilidade_percentual": None,
            "classificacao": None,
            "tipo_modalidade": None,
            "resumo_vaga": None,
            "dica_candidatura": None,
            "pontos_fortes": None,
            "requisitos_faltantes": None
        }
        msg = formatar_mensagem_whatsapp(vaga_nula, analise_nula)
        assert "Vaga Sem Título" in msg
        assert "Empresa Confidencial" in msg
        assert "Não informada" in msg

    def test_formatar_mensagem_whatsapp_com_score_string_e_listas_string(self, sample_vaga):
        analise = {
            "compatibilidade_percentual": "90%",
            "classificacao": "Excelente",
            "pontos_fortes": "React e TypeScript",
            "requisitos_faltantes": "Inglês"
        }
        msg = formatar_mensagem_whatsapp(sample_vaga, analise)
        assert "🔥 *Match Encontrado: 90%" in msg
        assert "• React e TypeScript" in msg
        assert "• Inglês" in msg


    @patch("whatsapp_notifier.requests.get")
    def test_enviar_notificacao_whatsapp_sucesso(self, mock_get, sample_vaga, sample_analise_remoto):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Message queued"
        mock_get.return_value = mock_response

        sucesso = enviar_notificacao_whatsapp(sample_vaga, sample_analise_remoto)
        assert sucesso is True
        mock_get.assert_called_once()
        url_chamada = mock_get.call_args[0][0]
        assert "api.callmebot.com" in url_chamada
        assert "5581999999999" in url_chamada
        assert "test_whatsapp_apikey" in url_chamada

    def test_enviar_notificacao_whatsapp_sem_credenciais(self, monkeypatch, sample_vaga, sample_analise_remoto):
        monkeypatch.delenv("WHATSAPP_PHONE", raising=False)
        monkeypatch.delenv("WHATSAPP_APIKEY", raising=False)

        with patch("whatsapp_notifier.requests.get") as mock_get:
            sucesso = enviar_notificacao_whatsapp(sample_vaga, sample_analise_remoto)
            assert sucesso is False
            mock_get.assert_not_called()

    @patch("whatsapp_notifier.requests.get")
    def test_enviar_notificacao_whatsapp_erro_gateway(self, mock_get, sample_vaga, sample_analise_remoto):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Error: Invalid apikey"
        mock_get.return_value = mock_response

        sucesso = enviar_notificacao_whatsapp(sample_vaga, sample_analise_remoto)
        assert sucesso is False

    @patch("whatsapp_notifier.requests.get")
    def test_enviar_notificacao_whatsapp_excecao_rede(self, mock_get, sample_vaga, sample_analise_remoto):
        mock_get.side_effect = requests.Timeout("Gateway timeout")

        sucesso = enviar_notificacao_whatsapp(sample_vaga, sample_analise_remoto)
        assert sucesso is False

    def test_testar_conexao_whatsapp_sem_credenciais(self, monkeypatch):
        monkeypatch.delenv("WHATSAPP_PHONE", raising=False)
        monkeypatch.delenv("WHATSAPP_APIKEY", raising=False)

        sucesso, msg = testar_conexao_whatsapp()
        assert sucesso is False
        assert "não configurados" in msg

    @patch("whatsapp_notifier.requests.get")
    def test_testar_conexao_whatsapp_sucesso(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_get.return_value = mock_response

        sucesso, msg = testar_conexao_whatsapp()
        assert sucesso is True
        assert "sucesso" in msg.lower()

    @patch("whatsapp_notifier.requests.get")
    def test_testar_conexao_whatsapp_erro_gateway(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Error 401"
        mock_get.return_value = mock_response

        sucesso, msg = testar_conexao_whatsapp()
        assert sucesso is False
        assert "Falha na resposta" in msg
