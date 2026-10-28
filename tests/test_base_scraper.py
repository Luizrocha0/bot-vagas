import pytest
from scrapers.base import BaseJobScraper, USER_AGENTS


class DummyScraper(BaseJobScraper):
    """Subclasse concreta para testar BaseJobScraper."""
    def __init__(self):
        super().__init__(fonte_nome="DummyPortal")

    def buscar_vagas(self, keywords="Desenvolvedor Junior", location=None, remote_only=False, max_pages=1, **kwargs):
        return [
            self.padronizar_vaga(
                id="999",
                titulo="Dev Jr",
                empresa="Empresa Teste",
                localizacao="Recife, PE",
                url="https://exemplo.com/vaga/999"
            )
        ]


class TestBaseJobScraper:
    """Testes unitários para BaseJobScraper."""

    def test_instanciacao_abstrata_falha(self):
        """Não deve ser possível instanciar BaseJobScraper diretamente."""
        with pytest.raises(TypeError):
            BaseJobScraper()

    def test_instanciacao_subclasse_sucesso(self):
        """Subclasse concreta deve instanciar com sucesso."""
        scraper = DummyScraper()
        assert scraper.fonte_nome == "DummyPortal"
        vagas = scraper.buscar_vagas()
        assert len(vagas) == 1
        assert vagas[0]["fonte"] == "DummyPortal"
        assert vagas[0]["id"] == "dummyportal_999"

    def test_get_headers(self):
        """Headers devem possuir User-Agent conhecido e Accept-Language pt-BR."""
        headers = DummyScraper.get_headers()
        assert "User-Agent" in headers
        assert headers["User-Agent"] in USER_AGENTS
        assert "pt-BR" in headers["Accept-Language"]

    @pytest.mark.parametrize("titulo,esperado", [
        ("Engenheiro Sênior", True),
        ("Senior Developer", True),
        ("Tech Lead", True),
        ("Staff Engineer", True),
        ("Dev Pleno/Senior", True),
        ("Desenvolvedor Jr", False),
        ("Estagiário de Software", False),
        ("Desenvolvedor Frontend Júnior", False),
        ("Junior Full Stack", False),
        ("", False),
        (None, False)
    ])
    def test_eh_vaga_senior(self, titulo, esperado):
        assert BaseJobScraper.eh_vaga_senior(titulo) == esperado

    @pytest.mark.parametrize("local,esperado", [
        ("San Francisco, CA, United States", True),
        ("New York, USA", True),
        ("London, United Kingdom", True),
        ("Lisboa, Portugal", True),
        ("Buenos Aires, Argentina", True),
        ("Recife, Pernambuco, Brasil", False),
        ("São Paulo, SP, Brazil", False),
        ("Remoto (Brasil)", False),
        ("Remoto", False),
        ("", False),
        (None, False)
    ])
    def test_eh_local_estrangeiro(self, local, esperado):
        assert BaseJobScraper.eh_local_estrangeiro(local) == esperado

    def test_padronizar_vaga_completa(self):
        scraper = DummyScraper()
        vaga = scraper.padronizar_vaga(
            id="12345",
            titulo="  Desenvolvedor React Júnior  ",
            empresa="  Startup Legal  ",
            localizacao="  Recife, PE  ",
            url="https://exemplo.com/vagas/12345",
            descricao="Esta é uma descrição completa com mais de trinta caracteres para teste.",
            criterios={"Modalidade": "Híbrido"},
            publicado_em="Hoje",
            fonte="CustomPortal"
        )
        assert vaga["id"] == "customportal_12345"
        assert vaga["fonte"] == "CustomPortal"
        assert vaga["titulo"] == "Desenvolvedor React Júnior"
        assert vaga["empresa"] == "Startup Legal"
        assert vaga["localizacao"] == "Recife, PE"
        assert vaga["url"] == "https://exemplo.com/vagas/12345"
        assert "Esta é uma descrição completa" in vaga["descricao"]
        assert vaga["criterios"] == {"Modalidade": "Híbrido"}
        assert vaga["publicado_em"] == "Hoje"

    def test_padronizar_vaga_fallback_descricao_curta(self):
        scraper = DummyScraper()
        vaga = scraper.padronizar_vaga(
            id="dummyportal_555",
            titulo="Estágio em TI",
            empresa="Empresa X",
            localizacao="Recife, PE",
            url="https://exemplo.com/555",
            descricao="curta"
        )
        # ID já continha o prefixo
        assert vaga["id"] == "dummyportal_555"
        assert vaga["fonte"] == "DummyPortal"
        assert "Vaga de Estágio em TI na empresa Empresa X" in vaga["descricao"]
        assert vaga["criterios"] == {"Tipo": "Início de Carreira"}

    def test_padronizar_vaga_fallback_campos_nulos(self):
        scraper = DummyScraper()
        vaga = scraper.padronizar_vaga(
            id="abc",
            titulo=None,
            empresa=None,
            localizacao=None,
            url=None,
            descricao=None
        )
        assert vaga["id"] == "dummyportal_abc"
        assert vaga["titulo"] == "Vaga Sem Título"
        assert vaga["empresa"] == "Empresa Confidencial"
        assert vaga["localizacao"] == "Brasil"
        assert vaga["url"] == ""
        assert len(vaga["descricao"]) > 30
