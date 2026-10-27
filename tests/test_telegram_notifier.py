import os
import pytest
from unittest.mock import patch, MagicMock
import requests

from telegram_notifier import enviar_notificacao_telegram, testar_conexao_telegram


class TestFormatacaoENotificacaoTelegram:
    """Testes para formatação HTML, badges, emojis e envio de notificações."""

    @patch("telegram_notifier.requests.post")
    def test_envio_sucesso_remoto_com_badge_e_emoji_fogo(self, mock_post, sample_vaga, sample_analise_remoto):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Score >= 80 -> emoji 🔥; modalidade REMOTO -> badge 100% REMOTO
        sample_analise_remoto["compatibilidade_percentual"] = 85
        resultado = enviar_notificacao_telegram(sample_vaga, sample_analise_remoto)

        assert resultado is True
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        payload = kwargs["json"]

        assert payload["chat_id"] == "987654321"
        assert payload["parse_mode"] == "HTML"
        assert payload["disable_web_page_preview"] is False

        texto_msg = payload["text"]
        assert "🔥" in texto_msg
        assert "🌐 <b>100% REMOTO (BRASIL)</b>" in texto_msg
        assert sample_vaga["titulo"] in texto_msg
        assert sample_vaga["empresa"] in texto_msg
        assert sample_vaga["url"] in texto_msg
        assert "Acessar Vaga no LinkedIn" in texto_msg
        assert "⚠️ <b>Requisitos Faltantes / Atenção:</b>" in texto_msg
        assert "💡 <b>Dica do Gemini para Candidatura:</b>" in texto_msg

    @patch("telegram_notifier.requests.post")
    def test_envio_presencial_badge_local_e_emoji_estrela(self, mock_post, sample_vaga_presencial, sample_analise_presencial):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Score 70 -> emoji ⭐ (>= 65 e < 80); modalidade PRESENCIAL_PE -> badge LOCAL PE
        sample_analise_presencial["compatibilidade_percentual"] = 70
        resultado = enviar_notificacao_telegram(sample_vaga_presencial, sample_analise_presencial)

        assert resultado is True
        texto_msg = mock_post.call_args[1]["json"]["text"]
        assert "⭐" in texto_msg
        assert "📍 <b>LOCAL (RECIFE / OLINDA - PE)</b>" in texto_msg
        assert "Recife, Pernambuco, Brasil" in texto_msg

    @patch("telegram_notifier.requests.post")
    def test_score_baixo_emoji_pin(self, mock_post, sample_vaga, sample_analise_remoto):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        sample_analise_remoto["compatibilidade_percentual"] = 50
        resultado = enviar_notificacao_telegram(sample_vaga, sample_analise_remoto)

        assert resultado is True
        texto_msg = mock_post.call_args[1]["json"]["text"]
        assert "📌" in texto_msg

    @patch("telegram_notifier.requests.post")
    def test_escape_html_contra_tags_maliciosas_ou_invalidas(self, mock_post, sample_vaga, sample_analise_remoto):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Conteúdo que poderia quebrar o parser HTML do Telegram
        sample_vaga["titulo"] = "Dev <C++ & Java> <b>"
        sample_vaga["empresa"] = "Empresa & Filhos <Tech>"
        sample_vaga["url"] = "https://www.linkedin.com/jobs/view/12345?refId=xyz&trackingId=abc\"quote"
        sample_analise_remoto["resumo_vaga"] = "Resumo com <script>alert(1)</script>"

        enviar_notificacao_telegram(sample_vaga, sample_analise_remoto)

        texto_msg = mock_post.call_args[1]["json"]["text"]
        assert "&lt;C++ &amp; Java&gt;" in texto_msg
        assert "&amp; Filhos &lt;Tech&gt;" in texto_msg
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in texto_msg
        assert "<script>" not in texto_msg
        assert '<a href="https://www.linkedin.com/jobs/view/12345?refId=xyz&amp;trackingId=abc&quot;quote">' in texto_msg

    @patch("telegram_notifier.requests.post")
    def test_secao_gaps_e_dica_omitidas_quando_vazias(self, mock_post, sample_vaga, sample_analise_remoto):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        sample_analise_remoto["requisitos_faltantes"] = []
        sample_analise_remoto["dica_candidatura"] = ""

        enviar_notificacao_telegram(sample_vaga, sample_analise_remoto)

        texto_msg = mock_post.call_args[1]["json"]["text"]
        assert "Requisitos Faltantes" not in texto_msg
        assert "Dica do Gemini" not in texto_msg

    @patch("telegram_notifier.requests.post")
    def test_envio_com_campos_none_nao_deve_lancar_excecao(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

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

        sucesso = enviar_notificacao_telegram(vaga_nula, analise_nula)
        assert sucesso is True
        mock_post.assert_called_once()
        texto_msg = mock_post.call_args[1]["json"]["text"]
        assert "Vaga Sem Título" in texto_msg
        assert "Empresa Confidencial" in texto_msg

    @patch("telegram_notifier.requests.post")
    def test_envio_com_score_string_e_pontos_fortes_string(self, mock_post, sample_vaga):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        analise = {
            "compatibilidade_percentual": "85%",
            "tipo_modalidade": "REMOTO",
            "pontos_fortes": "React e TypeScript",
            "requisitos_faltantes": "Inglês Fluente"
        }
        sucesso = enviar_notificacao_telegram(sample_vaga, analise)
        assert sucesso is True
        texto = mock_post.call_args[1]["json"]["text"]
        assert "🔥" in texto
        assert "Match Encontrado: 85%" in texto
        assert "• React e TypeScript" in texto


    def test_retorna_false_se_credenciais_ausentes(self, monkeypatch, sample_vaga, sample_analise_remoto):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        with patch("telegram_notifier.requests.post") as mock_post:
            sucesso = enviar_notificacao_telegram(sample_vaga, sample_analise_remoto)
            assert sucesso is False
            mock_post.assert_not_called()

    @patch("telegram_notifier.requests.post")
    def test_retorna_false_em_resposta_erro_http(self, mock_post, sample_vaga, sample_analise_remoto):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"ok": false, "description": "Bad Request: can\'t parse entities"}'
        mock_post.return_value = mock_response

        sucesso = enviar_notificacao_telegram(sample_vaga, sample_analise_remoto)
        assert sucesso is False

    @patch("telegram_notifier.requests.post")
    def test_retorna_false_em_excecao_de_rede_ou_timeout(self, mock_post, sample_vaga, sample_analise_remoto):
        mock_post.side_effect = requests.Timeout("Timeout ao enviar mensagem")

        sucesso = enviar_notificacao_telegram(sample_vaga, sample_analise_remoto)
        assert sucesso is False


class TestTestarConexaoTelegram:
    """Testes para a função de teste de conexão com o Telegram."""

    def test_sem_credenciais_retorna_aviso(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        sucesso, msg = testar_conexao_telegram()
        assert sucesso is False
        assert "Credenciais ausentes" in msg

    @patch("telegram_notifier.requests.post")
    def test_conexao_sucesso_retorna_true(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        sucesso, msg = testar_conexao_telegram()
        assert sucesso is True
        assert "sucesso" in msg.lower()

    @patch("telegram_notifier.requests.post")
    def test_conexao_erro_api_retorna_false(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        sucesso, msg = testar_conexao_telegram()
        assert sucesso is False
        assert "Unauthorized" in msg

    @patch("telegram_notifier.requests.post")
    def test_conexao_excecao_retorna_false(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Falha DNS")

        sucesso, msg = testar_conexao_telegram()
        assert sucesso is False
        assert "Falha DNS" in msg
