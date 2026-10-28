import pytest
from unittest.mock import patch, MagicMock
import requests

from scrapers.indeed_scraper import IndeedScraper


@pytest.fixture
def sample_indeed_html():
    return """
    <html>
      <body>
        <div class="job_seen_beacon">
          <h2 class="jobTitle"><span>Desenvolvedor Frontend Junior</span></h2>
          <span class="companyName">Alpha Tech</span>
          <div class="companyLocation">Remoto</div>
          <div class="job-snippet">Desenvolvimento de interfaces modernas em React e TypeScript.</div>
          <a href="/rc/clk?jk=abc1001" data-jk="abc1001">Candidatar-se</a>
        </div>

        <div class="job_seen_beacon">
          <h2 class="jobTitle"><span>Estagiário de Software</span></h2>
          <span class="companyName">Porto Digital Dev</span>
          <div class="companyLocation">Recife, PE</div>
          <div class="job-snippet">Estágio presencial para desenvolvimento web com Python e Node.</div>
          <a href="/rc/clk?jk=abc1002" data-jk="abc1002">Candidatar-se</a>
        </div>

        <div class="job_seen_beacon">
          <h2 class="jobTitle"><span>Senior Software Architect</span></h2>
          <span class="companyName">Global Systems</span>
          <div class="companyLocation">Remoto</div>
          <div class="job-snippet">Arquiteto com experiência em microsserviços.</div>
          <a href="/rc/clk?jk=abc1003" data-jk="abc1003">Candidatar-se</a>
        </div>

        <div class="job_seen_beacon">
          <h2 class="jobTitle"><span>Desenvolvedor Junior Presencial</span></h2>
          <span class="companyName">Curitiba Labs</span>
          <div class="companyLocation">Curitiba, PR</div>
          <div class="job-snippet">Vaga em Curitiba presencial.</div>
          <a href="/rc/clk?jk=abc1004" data-jk="abc1004">Candidatar-se</a>
        </div>
      </body>
    </html>
    """


@pytest.fixture
def sample_github_fallback_issues():
    return [
        {
            "id": 8801,
            "title": "[Remoto] Desenvolvedor(a) Júnior React na Startup Brasil",
            "body": "Descrição da vaga: Buscamos dev júnior com foco em React, Next.js e TypeScript.",
            "html_url": "https://github.com/frontendbr/vagas/issues/8801",
            "created_at": "2026-10-27T12:00:00Z",
            "labels": [{"name": "Remoto"}, {"name": "Júnior"}]
        },
        {
            "id": 8802,
            "title": "[Recife/PE] Estágio em Desenvolvimento de Sistemas na RecifeTech",
            "body": "Descrição da vaga: Estágio presencial em Recife para estudantes de ADS.",
            "html_url": "https://github.com/backend-br/vagas/issues/8802",
            "created_at": "2026-10-27T13:00:00Z",
            "labels": [{"name": "Recife"}, {"name": "Estágio"}]
        },
        {
            "id": 8803,
            "title": "[Remoto] Desenvolvedor Sênior Java na MegaCorp",
            "body": "Descrição: Vaga sênior de backend.",
            "html_url": "https://github.com/backend-br/vagas/issues/8803",
            "created_at": "2026-10-27T14:00:00Z",
            "labels": [{"name": "Remoto"}, {"name": "Sênior"}]
        }
    ]


class TestIndeedScraper:
    """Testes unitários completos para o IndeedScraper."""

    def test_inicializacao(self):
        scraper = IndeedScraper()
        assert scraper.fonte_nome == "Indeed"

    def test_parse_indeed_html_remoto(self, sample_indeed_html):
        scraper = IndeedScraper()
        vagas = scraper._parse_indeed_html(sample_indeed_html, remote_only=True, location=None)

        assert len(vagas) == 1
        vaga = vagas[0]
        assert vaga["id"] == "indeed_abc1001"
        assert vaga["fonte"] == "Indeed"
        assert vaga["titulo"] == "Desenvolvedor Frontend Junior"
        assert vaga["empresa"] == "Alpha Tech"
        assert vaga["localizacao"] == "Remoto"
        assert vaga["url"] == "https://br.indeed.com/viewjob?jk=abc1001"
        assert "React e TypeScript" in vaga["descricao"]

    def test_parse_indeed_html_recife_pe(self, sample_indeed_html):
        scraper = IndeedScraper()
        vagas = scraper._parse_indeed_html(sample_indeed_html, remote_only=False, location="Recife, Pernambuco, Brasil")

        assert len(vagas) == 1
        vaga = vagas[0]
        assert vaga["id"] == "indeed_abc1002"
        assert vaga["titulo"] == "Estagiário de Software"
        assert vaga["empresa"] == "Porto Digital Dev"
        assert "Recife, PE" in vaga["localizacao"]

    @patch("scrapers.indeed_scraper.requests.get")
    def test_busca_direta_indeed_sucesso(self, mock_get, sample_indeed_html):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = sample_indeed_html
        mock_get.return_value = mock_resp

        scraper = IndeedScraper()
        vagas = scraper.buscar_vagas(keywords="Junior", remote_only=True)

        assert len(vagas) == 1
        assert vagas[0]["id"] == "indeed_abc1001"

    @patch("scrapers.indeed_scraper.requests.get")
    def test_fallback_quando_indeed_retorna_403(self, mock_get, sample_github_fallback_issues):
        def mock_get_dispatcher(url, *args, **kwargs):
            mock_resp = MagicMock()
            if "indeed.com" in url:
                mock_resp.status_code = 403
                mock_resp.text = "Cloudflare Challenge"
            elif "api.github.com" in url:
                mock_resp.status_code = 200
                mock_resp.json.return_value = sample_github_fallback_issues
            return mock_resp

        mock_get.side_effect = mock_get_dispatcher

        scraper = IndeedScraper()
        vagas = scraper.buscar_vagas(keywords="React", remote_only=True)

        assert len(vagas) == 1
        vaga = vagas[0]
        assert "8801" in vaga["id"]
        assert vaga["titulo"] == "Desenvolvedor(a) Júnior React"
        assert vaga["empresa"] == "Startup Brasil"
        assert vaga["localizacao"] == "Remoto"

    @patch("scrapers.indeed_scraper.requests.get")
    def test_erro_geral_retorna_lista_vazia(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Erro geral de rede")

        scraper = IndeedScraper()
        vagas = scraper.buscar_vagas(keywords="Junior")
        assert vagas == []
