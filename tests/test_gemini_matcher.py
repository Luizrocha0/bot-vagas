import os
import json
import pytest
from unittest.mock import MagicMock, patch

import gemini_matcher
from gemini_matcher import (
    carregar_perfil,
    criar_cliente_gemini,
    analisar_compatibilidade_vaga,
    limpar_json_resposta
)


class TestClienteEPerfilGemini:
    """Testes de inicialização do cliente Gemini e leitura do perfil do candidato."""

    def test_carregar_perfil_existente(self):
        perfil = carregar_perfil()
        assert isinstance(perfil, dict)
        assert "nome" in perfil
        assert "formacao" in perfil
        assert "competencias" in perfil
        assert "curso" in perfil["formacao"]


    def test_criar_cliente_gemini_sucesso(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "chave-valida-teste")
        with patch("gemini_matcher.genai.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value = mock_instance

            cliente = criar_cliente_gemini()
            assert cliente == mock_instance
            mock_client_cls.assert_called_once_with(api_key="chave-valida-teste")

    def test_criar_cliente_gemini_sem_api_key_dispara_value_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="GEMINI_API_KEY não foi encontrada"):
            criar_cliente_gemini()


class TestAnalisarCompatibilidadeVaga:
    """Testes de compatibilidade, geração de prompt, parsing JSON e resiliência."""

    def test_prompt_contem_dados_candidato_e_vaga(self, sample_vaga):
        mock_client = MagicMock()
        mock_response = MagicMock()
        resposta_ia = {
            "compatibilidade_percentual": 80,
            "classificacao": "Boa",
            "tipo_modalidade": "REMOTO",
            "eh_junior_ou_estagio": True,
            "resumo_vaga": "Vaga júnior remota.",
            "pontos_fortes": ["React", "TypeScript"],
            "requisitos_faltantes": [],
            "dica_candidatura": "Reforce seus projetos.",
            "vale_a_pena_candidatar": True
        }
        mock_response.text = json.dumps(resposta_ia)
        mock_client.models.generate_content.return_value = mock_response

        analisar_compatibilidade_vaga(sample_vaga, client=mock_client)

        mock_client.models.generate_content.assert_called_once()
        _, kwargs = mock_client.models.generate_content.call_args
        prompt_enviado = kwargs["contents"]

        # Valida dados do candidato no prompt
        assert "Luiz Henrique" in prompt_enviado
        assert "Next.js" in prompt_enviado

        # Valida dados da vaga no prompt
        assert sample_vaga["titulo"] in prompt_enviado
        assert sample_vaga["empresa"] in prompt_enviado
        assert sample_vaga["localizacao"] in prompt_enviado

        # Valida regras de modalidade no prompt
        assert "REMOTO" in prompt_enviado
        assert "PRESENCIAL_PE" in prompt_enviado
        assert "INVALIDA" in prompt_enviado

    def test_analise_classificacao_remoto_sucesso(self, sample_vaga, sample_analise_remoto):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_analise_remoto)
        mock_client.models.generate_content.return_value = mock_response

        resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)

        assert resultado["tipo_modalidade"] == "REMOTO"
        assert resultado["compatibilidade_percentual"] == 88
        assert resultado["classificacao"] == "Excelente"
        assert resultado["vale_a_pena_candidatar"] is True

    def test_analise_classificacao_presencial_pe_sucesso(self, sample_vaga_presencial, sample_analise_presencial):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_analise_presencial)
        mock_client.models.generate_content.return_value = mock_response

        resultado = analisar_compatibilidade_vaga(sample_vaga_presencial, client=mock_client)

        assert resultado["tipo_modalidade"] == "PRESENCIAL_PE"
        assert resultado["compatibilidade_percentual"] == 92
        assert resultado["eh_junior_ou_estagio"] is True

    def test_analise_classificacao_invalida_fora_de_pe(self, sample_vaga, sample_analise_invalida):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_analise_invalida)
        mock_client.models.generate_content.return_value = mock_response

        resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)

        assert resultado["tipo_modalidade"] == "INVALIDA"
        assert resultado["compatibilidade_percentual"] == 0
        assert resultado["vale_a_pena_candidatar"] is False

    def test_fallback_entre_modelos_quando_primeiro_falha_com_503_ou_429(self, sample_vaga, sample_analise_remoto):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_analise_remoto)

        # 1º modelo (gemini-3.1-flash-lite) falha com 503 / indisponível
        # 2º modelo (gemini-3.5-flash) responde com sucesso
        mock_client.models.generate_content.side_effect = [
            Exception("503 Service Unavailable / Model overloaded"),
            mock_response
        ]

        resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)

        assert mock_client.models.generate_content.call_count == 2
        primeiro_modelo = mock_client.models.generate_content.call_args_list[0][1]["model"]
        segundo_modelo = mock_client.models.generate_content.call_args_list[1][1]["model"]

        assert primeiro_modelo == "gemini-3.1-flash-lite"
        assert segundo_modelo == "gemini-3.5-flash"
        assert resultado["tipo_modalidade"] == "REMOTO"
        assert resultado["compatibilidade_percentual"] == 88

    def test_fallback_quando_ia_retorna_json_invalido(self, sample_vaga, sample_analise_remoto):
        mock_client = MagicMock()
        mock_sucesso = MagicMock()
        mock_sucesso.text = json.dumps(sample_analise_remoto)

        mock_invalido = MagicMock()
        mock_invalido.text = "Isto não é um JSON válido { broken"

        # 1º modelo retorna texto não-JSON
        # 2º modelo retorna JSON válido
        mock_client.models.generate_content.side_effect = [
            mock_invalido,
            mock_sucesso
        ]

        resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)

        assert mock_client.models.generate_content.call_count == 2
        assert resultado["tipo_modalidade"] == "REMOTO"
        assert resultado["compatibilidade_percentual"] == 88

    def test_falha_total_de_todos_os_modelos_retorna_objeto_erro_seguro(self, sample_vaga):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            Exception("503 Unavailable"),
            Exception("429 Rate Limit"),
            Exception("500 Internal Server Error")
        ]

        resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)

        assert mock_client.models.generate_content.call_count == 3
        assert resultado["compatibilidade_percentual"] == 0
        assert resultado["classificacao"] == "Erro"
        assert resultado["tipo_modalidade"] == "INVALIDA"
        assert resultado["eh_junior_ou_estagio"] is False
        assert resultado["vale_a_pena_candidatar"] is False
        assert "500 Internal Server Error" in resultado["erro"]

    def test_descricao_longa_e_truncada_em_4000_caracteres(self, sample_vaga):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({"compatibilidade_percentual": 70, "tipo_modalidade": "REMOTO"})
        mock_client.models.generate_content.return_value = mock_response

        sample_vaga["descricao"] = "A" * 6000
        analisar_compatibilidade_vaga(sample_vaga, client=mock_client)

        _, kwargs = mock_client.models.generate_content.call_args
        prompt = kwargs["contents"]
        assert "A" * 4000 in prompt
        assert "A" * 4001 not in prompt

    def test_cria_cliente_automaticamente_se_nenhum_for_passado(self, sample_vaga, sample_analise_remoto):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_analise_remoto)
        mock_client.models.generate_content.return_value = mock_response

        with patch("gemini_matcher.criar_cliente_gemini", return_value=mock_client) as mock_criar:
            resultado = analisar_compatibilidade_vaga(sample_vaga, client=None)
            mock_criar.assert_called_once()
            assert resultado["compatibilidade_percentual"] == 88

    def test_analise_com_resposta_envolvida_em_markdown_json_codeblock(self, sample_vaga, sample_analise_remoto):
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Modelo retorna JSON envolto em ```json ... ```
        mock_response.text = f"```json\n{json.dumps(sample_analise_remoto)}\n```"
        mock_client.models.generate_content.return_value = mock_response

        resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)
        assert resultado["tipo_modalidade"] == "REMOTO"
        assert resultado["compatibilidade_percentual"] == 88

    def test_analise_com_vaga_contendo_campos_nulos(self, sample_analise_remoto):
        vaga_com_nulos = {
            "titulo": "Desenvolvedor Junior",
            "empresa": "Tech Solutions",
            "localizacao": "Remoto",
            "descricao": None,
            "criterios": None
        }
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_analise_remoto)
        mock_client.models.generate_content.return_value = mock_response

        # Não deve lançar TypeError: 'NoneType' object is not subscriptable
        resultado = analisar_compatibilidade_vaga(vaga_com_nulos, client=mock_client)
        assert resultado["tipo_modalidade"] == "REMOTO"

    @pytest.mark.parametrize("entrada,esperado", [
        ('```json\n{"score": 90}\n```', '{"score": 90}'),
        ('```\n{"score": 85}\n```', '{"score": 85}'),
        ('{"score": 80}', '{"score": 80}'),
        ('Aqui está a resposta:\n```json\n{"score": 95}\n```\nQualquer dúvida avise!', '{"score": 95}'),
        ('Preâmbulo sem bloco ``` {"score": 70} pos-escrito', '{"score": 70}'),
        ('```json\n{"score": 85}\nNota explicativa interna\n```', '{"score": 85}'),
        ('```json\n{"score": 88, "detalhes": {"sub": 1}}\n```', '{"score": 88, "detalhes": {"sub": 1}}'),
        ('', ''),
        (None, ''),
    ])
    def test_limpar_json_resposta(self, entrada, esperado):
        assert limpar_json_resposta(entrada) == esperado

    def test_analise_com_score_como_string_ou_percentual(self, sample_vaga):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "compatibilidade_percentual": "85%",
            "classificacao": "Boa",
            "tipo_modalidade": "REMOTO",
            "eh_junior_ou_estagio": "sim",
            "resumo_vaga": "Boa vaga",
            "pontos_fortes": "React",
            "requisitos_faltantes": None,
            "dica_candidatura": "",
            "vale_a_pena_candidatar": "sim"
        })
        mock_client.models.generate_content.return_value = mock_response

        resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)
        assert resultado["compatibilidade_percentual"] == 85
        assert isinstance(resultado["compatibilidade_percentual"], int)
        assert resultado["eh_junior_ou_estagio"] is True
        assert resultado["vale_a_pena_candidatar"] is True
        assert resultado["pontos_fortes"] == ["React"]
        assert resultado["requisitos_faltantes"] == []

    def test_analise_com_perfil_contendo_formacao_nula(self, sample_vaga, sample_analise_remoto):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_analise_remoto)
        mock_client.models.generate_content.return_value = mock_response

        with patch("gemini_matcher.carregar_perfil", return_value={"nome": None, "formacao": None}):
            resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)
            assert resultado["tipo_modalidade"] == "REMOTO"
            assert resultado["compatibilidade_percentual"] == 88

    def test_analise_quando_modelo_retorna_array_json_nao_dicionario(self, sample_vaga, sample_analise_remoto):
        mock_client = MagicMock()
        mock_invalido = MagicMock()
        mock_invalido.text = '["resposta", "invalida", "sem", "objeto"]'
        mock_sucesso = MagicMock()
        mock_sucesso.text = json.dumps(sample_analise_remoto)

        mock_client.models.generate_content.side_effect = [mock_invalido, mock_sucesso]

        resultado = analisar_compatibilidade_vaga(sample_vaga, client=mock_client)
        assert mock_client.models.generate_content.call_count == 2
        assert resultado["compatibilidade_percentual"] == 88

    def test_carregar_perfil_inexistente_ou_corrompido(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "perfil_inexistente.json"
        monkeypatch.setattr(gemini_matcher, "os", MagicMock(path=os.path))
        with patch("gemini_matcher.open", side_effect=FileNotFoundError):
            assert carregar_perfil() == {}

