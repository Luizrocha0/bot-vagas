import pytest
from unittest.mock import patch, MagicMock
import requests

from scrapers.programathor_scraper import ProgramathorScraper


@pytest.fixture
def sample_programathor_html():
    return """
    <html>
      <body>
        <div class="cell-list">
          <a href="/jobs/10001-desenvolvedor-frontend-junior">
            <h3 class="text-24 line-height-30">Desenvolvedor Frontend Júnior</h3>
            <div class="cell-list-content-icon">
              <span><i class="fa fa-briefcase"></i> InovaTech</span>
              <span><i class="fas fa-map-marker-alt"></i> Remoto</span>
              <span><i class="far fa-chart-bar"></i> Júnior</span>
              <span><i class="far fa-file-alt"></i> CLT</span>
            </div>
            <div>
              <span class="tag-list background-gray">React</span>
              <span class="tag-list background-gray">TypeScript</span>
              <span class="tag-list background-gray">Next.js</span>
            </div>
          </a>
        </div>

        <div class="cell-list">
          <a href="/jobs/10002-estagiario-de-desenvolvimento">
            <h3 class="text-24 line-height-30">Estagiário de Desenvolvimento</h3>
            <div class="cell-list-content-icon">
              <span><i class="fa fa-briefcase"></i> Recife Software</span>
              <span><i class="fas fa-map-marker-alt"></i> Recife, PE</span>
              <span><i class="far fa-chart-bar"></i> Estagiário</span>
              <span><i class="far fa-file-alt"></i> Estágio</span>
            </div>
            <div>
              <span class="tag-list background-gray">Python</span>
              <span class="tag-list background-gray">Django</span>
            </div>
          </a>
        </div>

        <div class="cell-list">
          <a href="/jobs/10003-desenvolvedor-full-stack-senior">
            <h3 class="text-24 line-height-30">Desenvolvedor Full Stack Sênior</h3>
            <div class="cell-list-content-icon">
              <span><i class="fa fa-briefcase"></i> Big Corp</span>
              <span><i class="fas fa-map-marker-alt"></i> Remoto</span>
              <span><i class="far fa-chart-bar"></i> Sênior</span>
            </div>
            <div>
              <span class="tag-list background-gray">Java</span>
              <span class="tag-list background-gray">Spring</span>
            </div>
          </a>
        </div>

        <div class="cell-list">
          <a href="/jobs/10004-desenvolvedor-junior-sp">
            <h3 class="text-24 line-height-30">Desenvolvedor Web Júnior</h3>
            <div class="cell-list-content-icon">
              <span><i class="fa fa-briefcase"></i> Paulista Devs</span>
              <span><i class="fas fa-map-marker-alt"></i> São Paulo, SP</span>
              <span><i class="far fa-chart-bar"></i> Júnior</span>
            </div>
            <div>
              <span class="tag-list background-gray">Vue.js</span>
            </div>
          </a>
        </div>
      </body>
    </html>
    """


@pytest.fixture
def sample_programathor_detail_html():
    return """
    <html>
      <body>
        <div class="wrapper-content-job-show">
          Descrição da vaga:
          Venha atuar como Desenvolvedor Frontend Júnior criando componentes em React e TypeScript.
          Requisitos: conhecimento em React, Next.js, Git e boas práticas de código limpo.
        </div>
      </body>
    </html>
    """


class TestProgramathorScraper:
    """Testes unitários completos para o ProgramathorScraper."""

    def test_inicializacao(self):
        scraper = ProgramathorScraper()
        assert scraper.fonte_nome == "Programathor"

    @patch("scrapers.programathor_scraper.requests.get")
    def test_buscar_vagas_remotas_filtra_senior(self, mock_get, sample_programathor_html):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = sample_programathor_html
        mock_get.return_value = mock_resp

        scraper = ProgramathorScraper()
        vagas = scraper.buscar_vagas(keywords="Junior", remote_only=True)

        assert len(vagas) == 1
        vaga = vagas[0]
        assert vaga["id"] == "programathor_10001"
        assert vaga["fonte"] == "Programathor"
        assert vaga["titulo"] == "Desenvolvedor Frontend Júnior"
        assert vaga["empresa"] == "InovaTech"
        assert vaga["localizacao"] == "Remoto"
        assert vaga["url"] == "https://programathor.com.br/jobs/10001-desenvolvedor-frontend-junior"
        assert "React" in vaga["criterios"]["Tags"]
        assert vaga["criterios"]["Nível"] == "Júnior"

    @patch("scrapers.programathor_scraper.requests.get")
    def test_buscar_vagas_recife_pe(self, mock_get, sample_programathor_html):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = sample_programathor_html
        mock_get.return_value = mock_resp

        scraper = ProgramathorScraper()
        vagas = scraper.buscar_vagas(keywords="Estagio", location="Recife, Pernambuco, Brasil", remote_only=False)

        assert len(vagas) == 1
        vaga = vagas[0]
        assert vaga["id"] == "programathor_10002"
        assert vaga["titulo"] == "Estagiário de Desenvolvimento"
        assert vaga["empresa"] == "Recife Software"
        assert "Recife, PE" in vaga["localizacao"]

    @patch("scrapers.programathor_scraper.requests.get")
    def test_obter_detalhes_vaga_sucesso(self, mock_get, sample_programathor_detail_html):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = sample_programathor_detail_html
        mock_get.return_value = mock_resp

        scraper = ProgramathorScraper()
        detalhes = scraper.obter_detalhes("10001-desenvolvedor-frontend-junior")
        assert "Venha atuar como Desenvolvedor Frontend Júnior" in detalhes["descricao"]

    @patch("scrapers.programathor_scraper.requests.get")
    def test_obter_detalhes_vaga_erro_http(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        scraper = ProgramathorScraper()
        detalhes = scraper.obter_detalhes("99999")
        assert detalhes["descricao"] == ""

    @patch("scrapers.programathor_scraper.requests.get")
    def test_buscar_vagas_com_erro_de_conexao(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Falha de rede")

        scraper = ProgramathorScraper()
        vagas = scraper.buscar_vagas(keywords="Junior")
        assert vagas == []

    @patch("scrapers.programathor_scraper.requests.get")
    def test_buscar_vagas_pagina_sem_cards(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><div class='outra-classe'>Nenhum card</div></body></html>"
        mock_get.return_value = mock_resp

        scraper = ProgramathorScraper()
        vagas = scraper.buscar_vagas(keywords="TermoInexistente")
        assert vagas == []
