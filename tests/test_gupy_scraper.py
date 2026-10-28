import json
import pytest
from unittest.mock import patch, MagicMock
import requests

from scrapers.gupy_scraper import GupyScraper


@pytest.fixture
def sample_gupy_payload():
    return {
        "props": {
            "pageProps": {
                "initialJobList": {
                    "data": [
                        {
                            "id": 101,
                            "name": "Desenvolvedor(a) Front-end Júnior (React)",
                            "careerPageName": "Nubank",
                            "type": "vacancy_type_effective",
                            "publishedAt": "2026-10-27T14:00:00.000Z",
                            "isRemoteWork": True,
                            "city": "São Paulo",
                            "state": "SP",
                            "country": "Brasil",
                            "jobUrl": "https://nubank.gupy.io/job/101",
                            "workplaceType": "remote",
                            "description": "Venha ser Dev Júnior no Nubank trabalhando com React, Next.js e TypeScript."
                        },
                        {
                            "id": 102,
                            "name": "Estágio em Desenvolvimento de Sistemas",
                            "careerPageName": "Porto Digital Labs",
                            "type": "vacancy_type_internship",
                            "publishedAt": "2026-10-27T15:00:00.000Z",
                            "isRemoteWork": False,
                            "city": "Recife",
                            "state": "PE",
                            "country": "Brasil",
                            "jobUrl": "https://portodigital.gupy.io/job/102",
                            "workplaceType": "on-site",
                            "description": "Estágio presencial no Porto Digital em Recife para atuar com backend Python e Django."
                        },
                        {
                            "id": 103,
                            "name": "Engenheiro de Software Sênior (Tech Lead)",
                            "careerPageName": "MegaCorp",
                            "type": "vacancy_type_effective",
                            "publishedAt": "2026-10-27T16:00:00.000Z",
                            "isRemoteWork": True,
                            "city": "São Paulo",
                            "state": "SP",
                            "country": "Brasil",
                            "jobUrl": "https://megacorp.gupy.io/job/103",
                            "workplaceType": "remote",
                            "description": "Vaga sênior para arquitetura de microsserviços."
                        },
                        {
                            "id": 104,
                            "name": "Desenvolvedor Junior Presencial Curitiba",
                            "careerPageName": "Curitiba Devs",
                            "type": "vacancy_type_effective",
                            "publishedAt": "2026-10-27T17:00:00.000Z",
                            "isRemoteWork": False,
                            "city": "Curitiba",
                            "state": "PR",
                            "country": "Brasil",
                            "jobUrl": "https://curitibadevs.gupy.io/job/104",
                            "workplaceType": "on-site",
                            "description": "Vaga 100% presencial em Curitiba, sem modelo híbrido ou remoto."
                        }
                    ],
                    "pagination": {
                        "offset": 0,
                        "limit": 10,
                        "total": 4
                    }
                }
            }
        }
    }


def make_gupy_html(payload):
    json_str = json.dumps(payload)
    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <script id="__NEXT_DATA__" type="application/json">{json_str}</script>
      </head>
      <body><div>Gupy Portal</div></body>
    </html>
    """


class TestGupyScraper:
    """Testes unitários completos para o GupyScraper."""

    def test_inicializacao(self):
        scraper = GupyScraper()
        assert scraper.fonte_nome == "Gupy"

    @patch("scrapers.gupy_scraper.requests.get")
    def test_buscar_vagas_remotas_filtra_senior_e_presencial(self, mock_get, sample_gupy_payload):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = make_gupy_html(sample_gupy_payload)
        mock_get.return_value = mock_resp

        scraper = GupyScraper()
        vagas = scraper.buscar_vagas(keywords="React Junior", remote_only=True)

        assert len(vagas) == 1
        vaga = vagas[0]
        assert vaga["id"] == "gupy_101"
        assert vaga["fonte"] == "Gupy"
        assert vaga["titulo"] == "Desenvolvedor(a) Front-end Júnior (React)"
        assert vaga["empresa"] == "Nubank"
        assert vaga["localizacao"] == "Remoto"
        assert vaga["url"] == "https://nubank.gupy.io/job/101"
        assert "React, Next.js e TypeScript" in vaga["descricao"]

    @patch("scrapers.gupy_scraper.requests.get")
    def test_buscar_vagas_recife_pe(self, mock_get, sample_gupy_payload):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = make_gupy_html(sample_gupy_payload)
        mock_get.return_value = mock_resp

        scraper = GupyScraper()
        vagas = scraper.buscar_vagas(keywords="Estagio", location="Recife, Pernambuco, Brasil", remote_only=False)

        assert len(vagas) == 1
        vaga = vagas[0]
        assert vaga["id"] == "gupy_102"
        assert vaga["titulo"] == "Estágio em Desenvolvimento de Sistemas"
        assert vaga["empresa"] == "Porto Digital Labs"
        assert "Recife, PE" in vaga["localizacao"]

    @patch("scrapers.gupy_scraper.requests.get")
    def test_buscar_vagas_todas_sem_filtro_local(self, mock_get, sample_gupy_payload):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = make_gupy_html(sample_gupy_payload)
        mock_get.return_value = mock_resp

        scraper = GupyScraper()
        # Sem filtro de localidade nem remote_only: traz 101, 102 e 104 (103 é sênior e é filtrada)
        vagas = scraper.buscar_vagas(keywords="Desenvolvedor", location=None, remote_only=False)

        assert len(vagas) == 3
        ids = [v["id"] for v in vagas]
        assert "gupy_101" in ids
        assert "gupy_102" in ids
        assert "gupy_104" in ids
        assert "gupy_103" not in ids

    @patch("scrapers.gupy_scraper.requests.get")
    def test_html_sem_next_data(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>Sem script de dados</body></html>"
        mock_get.return_value = mock_resp

        scraper = GupyScraper()
        vagas = scraper.buscar_vagas(keywords="React Junior")
        assert vagas == []

    @patch("scrapers.gupy_scraper.requests.get")
    def test_html_com_next_data_invalido(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><script id="__NEXT_DATA__">{invalid json</script></html>'
        mock_get.return_value = mock_resp

        scraper = GupyScraper()
        vagas = scraper.buscar_vagas(keywords="React Junior")
        assert vagas == []

    @patch("scrapers.gupy_scraper.requests.get")
    def test_erro_http_ou_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Timeout ao conectar com Gupy")

        scraper = GupyScraper()
        vagas = scraper.buscar_vagas(keywords="React Junior")
        assert vagas == []

    @patch("scrapers.gupy_scraper.requests.get")
    def test_status_code_diferente_de_200(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_get.return_value = mock_resp

        scraper = GupyScraper()
        vagas = scraper.buscar_vagas(keywords="React Junior")
        assert vagas == []

    @patch("scrapers.gupy_scraper.requests.get")
    def test_dados_com_lista_vazia(self, mock_get):
        empty_payload = {
            "props": {
                "pageProps": {
                    "initialJobList": {
                        "data": []
                    }
                }
            }
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = make_gupy_html(empty_payload)
        mock_get.return_value = mock_resp

        scraper = GupyScraper()
        vagas = scraper.buscar_vagas(keywords="TermoInexistente")
        assert vagas == []
