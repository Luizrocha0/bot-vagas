import os
import json
import pytest
from unittest.mock import patch, MagicMock

import setup
from setup import (
    verificar_ambiente,
    validar_chave_gemini,
    salvar_env,
    inicializar_perfil_candidato,
    main
)


class TestVerificacaoAmbiente:
    """Testes de diagnóstico do ambiente."""

    def test_verificar_ambiente_estrutura(self):
        diag = verificar_ambiente()
        assert isinstance(diag, dict)
        assert "python_valido" in diag
        assert "python_versao" in diag
        assert "dependencias" in diag
        assert "env_existe" in diag
        assert "perfil_existe" in diag
        assert "gemini_configurado" in diag


class TestValidacaoChaveGemini:
    """Testes da validação de chaves da API do Gemini."""

    def test_validar_chave_vazia_retorna_falso(self):
        valida, msg = validar_chave_gemini("")
        assert valida is False
        assert "não informada" in msg

        valida, msg = validar_chave_gemini("   ")
        assert valida is False

    @patch("google.genai.Client")
    def test_validar_chave_sucesso(self, mock_client_cls):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "OK"
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        valida, msg = validar_chave_gemini("chave-teste-ai-studio")
        assert valida is True
        assert "sucesso" in msg

    @patch("google.genai.Client")
    def test_validar_chave_erro_api(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("403 API_KEY_INVALID")
        mock_client_cls.return_value = mock_client

        valida, msg = validar_chave_gemini("chave-invalida")
        assert valida is False
        assert "403 API_KEY_INVALID" in msg


class TestSalvarEnv:
    """Testes de criação e atualização segura do arquivo .env."""

    def test_salvar_env_novo_arquivo(self, tmp_path):
        env_file = tmp_path / ".env_teste"
        chaves = {"GEMINI_API_KEY": "AIzaSyTest123", "TELEGRAM_CHAT_ID": "987654321"}

        sucesso = salvar_env(chaves, caminho_env=str(env_file))
        assert sucesso is True
        assert env_file.exists()

        conteudo = env_file.read_text(encoding="utf-8")
        assert "GEMINI_API_KEY=AIzaSyTest123" in conteudo
        assert "TELEGRAM_CHAT_ID=987654321" in conteudo

    def test_salvar_env_preserva_existentes_e_atualiza(self, tmp_path):
        env_file = tmp_path / ".env_teste"
        env_file.write_text("CHAVE_ANTIGA=valor123\nGEMINI_API_KEY=antiga\n", encoding="utf-8")

        chaves_novas = {"GEMINI_API_KEY": "nova_chave"}
        sucesso = salvar_env(chaves_novas, caminho_env=str(env_file))

        assert sucesso is True
        conteudo = env_file.read_text(encoding="utf-8")
        assert "CHAVE_ANTIGA=valor123" in conteudo
        assert "GEMINI_API_KEY=nova_chave" in conteudo


class TestInicializarPerfilCandidato:
    """Testes de inicialização do perfil a partir de template e dados dinâmicos."""

    def test_inicializar_perfil_template_inexistente(self, tmp_path):
        destino = tmp_path / "perfil.json"
        sucesso = inicializar_perfil_candidato(
            destino=str(destino),
            origem_template=str(tmp_path / "nao_existe.json")
        )
        assert sucesso is False
        assert not destino.exists()

    def test_inicializar_perfil_com_dados_customizados(self, tmp_path):
        origem = tmp_path / "template.json"
        origem.write_text(json.dumps({
            "nome": "Default",
            "localizacao": "Default",
            "titulo": "Default",
            "preferencias_busca": {
                "cargos_alvo": [],
                "palavras_chave": []
            }
        }), encoding="utf-8")

        destino = tmp_path / "novo_perfil.json"
        dados = {
            "nome": "Carlos Silva",
            "localizacao": "Florianópolis, SC - Brasil",
            "titulo": "Desenvolvedor Backend",
            "cargos_alvo": "Backend Junior, Python Junior",
            "stack": "Python, Django, FastAPI, Docker"
        }

        sucesso = inicializar_perfil_candidato(
            destino=str(destino),
            origem_template=str(origem),
            dados_basicos=dados
        )

        assert sucesso is True
        assert destino.exists()

        resultado = json.loads(destino.read_text(encoding="utf-8"))
        assert resultado["nome"] == "Carlos Silva"
        assert resultado["localizacao"] == "Florianópolis, SC - Brasil"
        assert resultado["titulo"] == "Desenvolvedor Backend"
        assert resultado["preferencias_busca"]["cargos_alvo"] == ["Backend Junior", "Python Junior"]
        assert resultado["preferencias_busca"]["palavras_chave"] == ["Python", "Django", "FastAPI", "Docker"]


class TestMainSetupCLI:
    """Testes dos argumentos de linha de comando de setup.py."""

    @patch("setup.executar_check")
    def test_main_arg_check(self, mock_check):
        codigo = main(["--check"])
        assert codigo == 0
        mock_check.assert_called_once()

    @patch("setup.executar_teste_ia", return_value=True)
    def test_main_arg_test_sucesso(self, mock_teste):
        codigo = main(["--test"])
        assert codigo == 0
        mock_teste.assert_called_once()

    @patch("setup.executar_teste_ia", return_value=False)
    def test_main_arg_test_falha(self, mock_teste):
        codigo = main(["--test"])
        assert codigo == 1

    @patch("setup.inicializar_perfil_candidato", return_value=True)
    def test_main_arg_init_cv(self, mock_init):
        codigo = main(["--init-cv"])
        assert codigo == 0
        mock_init.assert_called_once()
