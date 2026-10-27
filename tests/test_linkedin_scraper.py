import os
import json
import pytest
from unittest.mock import patch, MagicMock
import requests

import linkedin_scraper
from linkedin_scraper import (
    eh_vaga_senior,
    eh_local_estrangeiro,
    get_headers,
    carregar_vagas_vistas,
    salvar_vagas_vistas,
    buscar_vagas_linkedin,
    obter_detalhes_vaga,
    USER_AGENTS,
    GEO_ID_BRASIL
)


class TestFiltroSenioridade:
    """Testes unitários para a função eh_vaga_senior."""

    @pytest.mark.parametrize("titulo", [
        "Engenheiro de Software Sênior",
        "Senior Backend Developer",
        "Desenvolvedor Node.js Sr.",
        "Desenvolvedor Java sr ",
        "Engenheiro de Dados /sr",
        "Full Stack Developer -sr",
        "Staff Software Engineer",
        "Tech Lead Python",
        "Lead Frontend Engineer",
        "Principal Software Engineer",
        "Especialista Cloud AWS",
        "Cloud Specialist",
        "Engineering Manager",
        "Head of Engineering",
        "Diretor de TI",
        "Director of Technology",
        "Software Architect",
        "Arquiteto de Soluções",
        "Desenvolvedor Pleno/Senior",
        "Desenvolvedor Pleno / Sênior",
        "Desenvolvedor pl/sr",
        "Desenvolvedor Backend Sr",
        "Engenheiro SR",
        "Dev - Sr",
        "Desenvolvedor (Sr)",
        "Dev Jr / Sr",
        "Snr Developer",
        "Snr. Software Engineer",
        "Dev - Snr",
        "Desenvolvedor Snr",
        "Dev (Snr)",
        "Engenheiro de Software III",
        "Desenvolvedor III",
        "Dev Java III",
        "Desenvolvedor Nível 3",
        "Desenvolvedor Nível III",
    ])
    def test_deve_identificar_vagas_seniores(self, titulo):
        assert eh_vaga_senior(titulo) is True

    @pytest.mark.parametrize("titulo", [
        "Desenvolvedor Junior",
        "Desenvolvedor Júnior",
        "Estagiário de TI",
        "Estágio em Desenvolvimento de Software",
        "Junior Full Stack Developer",
        "Desenvolvedor Frontend Jr",
        "Desenvolvedor Pleno",
        "Trainee em Engenharia de Software",
        "Assistente de Tecnologia",
        "Programador Web Iniciante",
        "Engenheiro SRE",
        "Israel Tech Developer",
    ])
    def test_nao_deve_descartar_vagas_iniciantes_ou_pleno(self, titulo):
        assert eh_vaga_senior(titulo) is False

    def test_titulo_vazio(self):
        assert eh_vaga_senior("") is False

    def test_titulo_none_ou_invalido(self):
        assert eh_vaga_senior(None) is False
        assert eh_vaga_senior(12345) is False

    def test_case_insensitivity(self):
        assert eh_vaga_senior("DEV SÊNIOR") is True
        assert eh_vaga_senior("TECH LEAD") is True


class TestFiltroLocalidade:
    """Testes unitários para a função eh_local_estrangeiro."""

    @pytest.mark.parametrize("local", [
        "United States",
        "New York, Estados Unidos",
        "San Francisco, CA, United States",
        "Toronto, Canada",
        "Vancouver, Canadá",
        "London, United Kingdom",
        "London, UK",
        "Reino Unido",
        "Berlin, Germany",
        "Alemanha",
        "Varsóvia, Polônia",
        "Poland",
        "Paris, France",
        "França",
        "Bangalore, India",
        "Índia",
        "Austin, Texas, USA",
        "Miami, FL, EUA",
        "Manchester, UK",
        "Lisboa, Portugal",
        "Buenos Aires, Argentina",
        "New York, U.S.A.",
        "San Francisco, CA, U.S.",
        "Miami, Florida, E.U.A.",
        "London, U.K.",
        "Dublin, Ireland",
        "Montevideo, Uruguay",
        "Tokyo, Japan",
        "Asunción, Paraguay",
        "San Francisco, CA",
        "New York, NY",
        "Seattle, WA",
        "Silicon Valley",
    ])
    def test_deve_identificar_locais_estrangeiros(self, local):
        assert eh_local_estrangeiro(local) is True

    @pytest.mark.parametrize("local", [
        "Recife, Pernambuco, Brasil",
        "Olinda, PE, Brasil",
        "São Paulo, SP",
        "Remoto, Brasil",
        "Rio de Janeiro, Brazil",
        "Porto Alegre, RS, Brasil",
        "Brasil",
        "Brazil",
    ])
    def test_nao_deve_descartar_locais_nacionais(self, local):
        assert eh_local_estrangeiro(local) is False

    def test_local_estrangeiro_com_mencao_a_brasil(self):
        # Quando contém termos estrangeiros mas também menciona Brasil/brazil,
        # o filtro considera como elegível (ex: multinacional com sede no exterior mas operando no Brasil)
        assert eh_local_estrangeiro("United States, Brasil") is False
        assert eh_local_estrangeiro("London, United Kingdom, Brazil") is False

    def test_local_vazio(self):
        assert eh_local_estrangeiro("") is False

    def test_local_none_ou_invalido(self):
        assert eh_local_estrangeiro(None) is False
        assert eh_local_estrangeiro(999) is False


class TestHeadersEArmazenamento:
    """Testes para headers HTTP e persistência de vagas vistas."""

    def test_get_headers(self):
        headers = get_headers()
        assert "User-Agent" in headers
        assert headers["User-Agent"] in USER_AGENTS
        assert "Accept" in headers
        assert "Accept-Language" in headers

    def test_carregar_vagas_vistas_inexistente(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "vagas_inexistentes.json"
        monkeypatch.setattr(linkedin_scraper, "SEEN_JOBS_FILE", str(fake_file))
        assert carregar_vagas_vistas() == set()

    def test_carregar_e_salvar_vagas_vistas(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "vagas_teste.json"
        monkeypatch.setattr(linkedin_scraper, "SEEN_JOBS_FILE", str(fake_file))

        dados_iniciais = {"12345", "67890"}
        salvar_vagas_vistas(dados_iniciais)

        assert fake_file.exists()
        carregados = carregar_vagas_vistas()
        assert carregados == dados_iniciais

    def test_carregar_vagas_vistas_arquivo_corrompido(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "vagas_corrompidas.json"
        fake_file.write_text("{ json invalido : [", encoding="utf-8")
        monkeypatch.setattr(linkedin_scraper, "SEEN_JOBS_FILE", str(fake_file))

        assert carregar_vagas_vistas() == set()


class TestBuscarVagasLinkedin:
    """Testes para busca e parsing de cards de vagas do LinkedIn."""

    @patch("linkedin_scraper.requests.get")
    def test_busca_sucesso_com_filtros_e_parsing(self, mock_get, sample_linkedin_search_html):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_linkedin_search_html
        mock_get.return_value = mock_response

        vagas = buscar_vagas_linkedin(keywords="Desenvolvedor Junior", location="Recife", max_pages=1)

        # Do HTML de exemplo com 4 vagas:
        # - 1001 (Desenvolvedor Junior, Recife) -> DEVE passar
        # - 1002 (Engenheiro Sênior) -> DEVE ser filtrada (sênior)
        # - 1003 (Developer Junior, New York, US) -> DEVE ser filtrada (exterior)
        # - 1004 (Estagiário de TI, Brasil) -> DEVE passar
        assert len(vagas) == 2
        assert vagas[0]["id"] == "1001"
        assert vagas[0]["titulo"] == "Desenvolvedor Junior"
        assert vagas[0]["empresa"] == "Empresa Alfa"
        assert vagas[0]["localizacao"] == "Recife, Pernambuco, Brasil"
        assert vagas[0]["publicado_em"] == "Há 1 hora"

        assert vagas[1]["id"] == "1004"
        assert vagas[1]["titulo"] == "Estagiário de TI"
        assert vagas[1]["empresa"] == "Empresa Delta"

        # Verifica chamada ao endpoint com os parâmetros corretos
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["keywords"] == "Desenvolvedor Junior"
        assert kwargs["params"]["location"] == "Recife"
        assert kwargs["params"]["start"] == 0

    @patch("linkedin_scraper.requests.get")
    def test_busca_com_geo_id_e_remote_only(self, mock_get, sample_linkedin_search_html):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_linkedin_search_html
        mock_get.return_value = mock_response

        buscar_vagas_linkedin(
            keywords="React Junior",
            geo_id=GEO_ID_BRASIL,
            remote_only=True,
            max_pages=1
        )

        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["geoId"] == GEO_ID_BRASIL
        assert kwargs["params"]["f_WT"] == "2"

    @patch("linkedin_scraper.requests.get")
    def test_busca_paginacao_multiplas_paginas(self, mock_get, sample_linkedin_search_html):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_linkedin_search_html

        starts_chamados = []
        def fake_get(*args, **kwargs):
            starts_chamados.append(kwargs["params"]["start"])
            return mock_response

        mock_get.side_effect = fake_get

        vagas = buscar_vagas_linkedin(keywords="Estagio", max_pages=2)

        assert mock_get.call_count == 2
        # Página 0: start 0; Página 1: start 10
        assert starts_chamados == [0, 10]
        # 2 vagas válidas por página * 2 páginas = 4 vagas
        assert len(vagas) == 4


    @patch("linkedin_scraper.requests.get")
    def test_busca_retorna_vazio_quando_status_nao_200(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        vagas = buscar_vagas_linkedin(keywords="Python Junior")
        assert vagas == []

    @patch("linkedin_scraper.requests.get")
    def test_busca_resiliente_a_excecao_de_rede(self, mock_get):
        mock_get.side_effect = requests.RequestException("Conexão falhou")

        vagas = buscar_vagas_linkedin(keywords="Java Junior")
        assert vagas == []

    @patch("linkedin_scraper.requests.get")
    def test_busca_ignora_cards_sem_titulo_ou_link(self, mock_get):
        html_cards_invalidos = """
        <ul>
            <li>
                <!-- Card sem link -->
                <h3 class="base-search-card__title">Desenvolvedor Junior</h3>
            </li>
            <li>
                <!-- Card sem título -->
                <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/999">Link</a>
            </li>
            <li>
                <!-- Card com fallback para campos ausentes -->
                <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/888">Link</a>
                <h3 class="base-search-card__title">Desenvolvedor Trainee</h3>
            </li>
        </ul>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_cards_invalidos
        mock_get.return_value = mock_response

        vagas = buscar_vagas_linkedin(keywords="Trainee")
        assert len(vagas) == 1
        assert vagas[0]["id"] == "888"
        assert vagas[0]["empresa"] == "Empresa Confidencial"
        assert vagas[0]["localizacao"] == "Brasil"
        assert vagas[0]["publicado_em"] == "Recente"


class TestObterDetalhesVaga:
    """Testes para extração de detalhes da vaga via endpoint público do LinkedIn."""

    @patch("linkedin_scraper.requests.get")
    def test_obter_detalhes_sucesso(self, mock_get, sample_linkedin_job_detail_html):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_linkedin_job_detail_html
        mock_get.return_value = mock_response

        detalhes = obter_detalhes_vaga("1001")

        assert "Python e APIs REST" in detalhes["descricao"]
        assert detalhes["criterios"]["Nível de experiência"] == "Júnior"
        assert detalhes["criterios"]["Tipo de trabalho"] == "Tempo integral"
        mock_get.assert_called_once()
        assert "1001" in mock_get.call_args[0][0]

    @patch("linkedin_scraper.requests.get")
    def test_obter_detalhes_status_erro_retorna_fallback_vazio(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        detalhes = obter_detalhes_vaga("9999")
        assert detalhes == {"descricao": "", "criterios": {}}

    @patch("linkedin_scraper.requests.get")
    def test_obter_detalhes_timeout_ou_excecao_retorna_fallback_vazio(self, mock_get):
        mock_get.side_effect = requests.Timeout("Tempo limite de 6s excedido")

        detalhes = obter_detalhes_vaga("9999")
        assert detalhes == {"descricao": "", "criterios": {}}

    @patch("linkedin_scraper.requests.get")
    def test_obter_detalhes_html_sem_conteudo(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<div>Vaga sem dados</div>"
        mock_get.return_value = mock_response

        detalhes = obter_detalhes_vaga("1001")
        assert detalhes == {"descricao": "", "criterios": {}}

    @patch("linkedin_scraper.requests.get")
    def test_obter_detalhes_job_id_vazio_ou_none_retorna_fallback_sem_requisicao(self, mock_get):
        detalhes_none = obter_detalhes_vaga(None)
        detalhes_vazio = obter_detalhes_vaga("")
        assert detalhes_none == {"descricao": "", "criterios": {}}
        assert detalhes_vazio == {"descricao": "", "criterios": {}}
        mock_get.assert_not_called()

    def test_carregar_vagas_vistas_formato_dict(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "vagas_dict.json"
        fake_file.write_text(json.dumps({"1001": True, "1002": False}), encoding="utf-8")
        monkeypatch.setattr(linkedin_scraper, "SEEN_JOBS_FILE", str(fake_file))
        assert carregar_vagas_vistas() == {"1001", "1002"}

    @patch("linkedin_scraper.requests.get")
    def test_busca_converte_links_relativos_em_absolutos(self, mock_get):
        html_link_relativo = """
        <ul>
            <li>
                <a class="base-card__full-link" href="/jobs/view/777888?refId=xyz">Link</a>
                <h3 class="base-search-card__title">Desenvolvedor Junior Python</h3>
                <span class="job-search-card__location">Recife, PE</span>
            </li>
        </ul>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_link_relativo
        mock_get.return_value = mock_response

        vagas = buscar_vagas_linkedin(keywords="Python Junior")
        assert len(vagas) == 1
        assert vagas[0]["id"] == "777888"
        assert vagas[0]["url"] == "https://www.linkedin.com/jobs/view/777888"

    @patch("linkedin_scraper.requests.get")
    def test_obter_detalhes_extrai_id_quando_recebe_url_ou_composto(self, mock_get, sample_linkedin_job_detail_html):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_linkedin_job_detail_html
        mock_get.return_value = mock_response

        # Passando URL completa em vez de apenas o ID numérico
        detalhes = obter_detalhes_vaga("https://www.linkedin.com/jobs/view/555444333")
        assert "Python e APIs REST" in detalhes["descricao"]
        assert mock_get.call_count == 1
        assert "555444333" in mock_get.call_args[0][0]
        assert "https://" not in mock_get.call_args[0][0].split("/api/jobPosting/")[1]
