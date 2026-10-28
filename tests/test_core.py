import os
import json
import pytest
from unittest.mock import MagicMock

from core.models import Vaga, ResultadoMatch, ModalidadeVaga
from core.selector import QuotaSelector
from core.notifier import NotificationDispatcher
from core.repository import JobRepository
from core.collector import JobCollector
from scrapers.base import BaseJobScraper


class FakeScraper(BaseJobScraper):
    def __init__(self, nome="FakeSource", vagas=None):
        super().__init__(fonte_nome=nome)
        self._vagas = vagas or []

    def buscar_vagas(self, keywords="Junior", location=None, remote_only=False, max_pages=1, **kwargs):
        return self._vagas


class TestDomainModels:
    """Testes para entidades e value objects de domínio."""

    def test_vaga_instanciacao_e_chave_deduplicacao(self):
        vaga = Vaga(
            id="123",
            fonte="LinkedIn",
            titulo="  Desenvolvedor React / Node.js Júnior!  ",
            empresa="  Acme & Co. Corp.  ",
            localizacao="Recife, PE",
            url="https://exemplo.com/123"
        )
        assert vaga.id == "123"
        assert vaga.titulo == "Desenvolvedor React / Node.js Júnior!"
        assert vaga.empresa == "Acme & Co. Corp."
        # Chave normalizada remove pontuação e converte para minúsculas
        t_clean, e_clean = vaga.chave_deduplicacao
        assert "react" in t_clean and "node" in t_clean
        assert "acme" in e_clean

    def test_vaga_from_dict_and_to_dict(self):
        dados = {
            "id": "gupy_99",
            "fonte": "Gupy",
            "titulo": "Dev Junior",
            "empresa": "Tech SA",
            "localizacao": "Remoto",
            "url": "https://gupy.io/job/99",
            "descricao": "Descricao de teste",
            "criterios": {"Nível": "Júnior"}
        }
        vaga = Vaga.from_dict(dados)
        assert vaga.id == "gupy_99"
        assert vaga.to_dict()["fonte"] == "Gupy"

    def test_modalidade_vaga_from_str(self):
        assert ModalidadeVaga.from_str("REMOTO") == ModalidadeVaga.REMOTO
        assert ModalidadeVaga.from_str("100% Remoto") == ModalidadeVaga.REMOTO
        assert ModalidadeVaga.from_str("PRESENCIAL_PE") == ModalidadeVaga.PRESENCIAL_PE
        assert ModalidadeVaga.from_str("Recife - PE") == ModalidadeVaga.PRESENCIAL_PE
        assert ModalidadeVaga.from_str("PRESENCIAL_SP") == ModalidadeVaga.INVALIDA
        assert ModalidadeVaga.from_str(None) == ModalidadeVaga.INVALIDA

    def test_resultado_match_elegibilidade(self):
        match_valido = ResultadoMatch(
            score=85,
            modalidade=ModalidadeVaga.REMOTO,
            eh_junior_ou_estagio=True
        )
        assert match_valido.eh_elegivel() is True

        match_score_baixo = ResultadoMatch(
            score=30,
            modalidade=ModalidadeVaga.REMOTO,
            eh_junior_ou_estagio=True
        )
        assert match_score_baixo.eh_elegivel() is False

        match_nao_junior = ResultadoMatch(
            score=90,
            modalidade=ModalidadeVaga.REMOTO,
            eh_junior_ou_estagio=False
        )
        assert match_nao_junior.eh_elegivel() is False

        match_modalidade_invalida = ResultadoMatch(
            score=90,
            modalidade=ModalidadeVaga.INVALIDA,
            eh_junior_ou_estagio=True
        )
        assert match_modalidade_invalida.eh_elegivel() is False


class TestQuotaSelector:
    """Testes para o seletor de cotas e balanceamento."""

    def test_selecao_balanceada_2_remotas_e_2_presenciais(self):
        remotas = [
            {"id": "r1", "score": 90},
            {"id": "r2", "score": 80},
            {"id": "r3", "score": 70}
        ]
        presenciais = [
            {"id": "p1", "score": 95},
            {"id": "p2", "score": 85},
            {"id": "p3", "score": 75}
        ]

        selector = QuotaSelector(meta_remotas=2, meta_presenciais=2)
        resultado = selector.selecionar_top_vagas(remotas, presenciais)

        assert len(resultado) == 4
        ids = [v["id"] for v in resultado]
        assert ids == ["r1", "r2", "p1", "p2"]

    def test_complementacao_quando_presencial_insuficiente(self):
        remotas = [
            {"id": "r1", "score": 95},
            {"id": "r2", "score": 90},
            {"id": "r3", "score": 85},
            {"id": "r4", "score": 80}
        ]
        presenciais = []

        selector = QuotaSelector(meta_remotas=2, meta_presenciais=2)
        resultado = selector.selecionar_top_vagas(remotas, presenciais)

        assert len(resultado) == 4
        ids = [v["id"] for v in resultado]
        assert ids == ["r1", "r2", "r3", "r4"]

    def test_meta_zero_presenciais_nao_complementa(self):
        remotas = [{"id": "r1", "score": 90}]
        presenciais = [{"id": "p1", "score": 95}]

        selector = QuotaSelector(meta_remotas=2, meta_presenciais=0)
        resultado = selector.selecionar_top_vagas(remotas, presenciais)

        assert len(resultado) == 1
        assert resultado[0]["id"] == "r1"


class TestNotificationDispatcher:
    """Testes para o despachante de notificações."""

    def test_disparo_multiplos_canais(self):
        mock_tel = MagicMock(return_value=True)
        mock_tel.__name__ = "telegram"
        mock_wpp = MagicMock(return_value=True)
        mock_wpp.__name__ = "whatsapp"

        dispatcher = NotificationDispatcher([mock_tel, mock_wpp])
        res = dispatcher.disparar({"titulo": "Dev Jr"}, {"score": 90})

        assert res == {"telegram": True, "whatsapp": True}
        mock_tel.assert_called_once()
        mock_wpp.assert_called_once()

    def test_resiliencia_a_falha_de_um_canal(self):
        mock_falha = MagicMock(side_effect=RuntimeError("Falha de rede"))
        mock_falha.__name__ = "canal_com_erro"
        mock_ok = MagicMock(return_value=True)
        mock_ok.__name__ = "canal_ok"

        dispatcher = NotificationDispatcher([mock_falha, mock_ok])
        res = dispatcher.disparar({"titulo": "Dev Jr"}, {"score": 80})

        assert res["canal_com_erro"] is False
        assert res["canal_ok"] is True


class TestJobCollector:
    """Testes para o coletor e deduplicador de vagas."""

    def test_deduplicacao_por_id_e_por_titulo_empresa(self):
        v1 = {"id": "1", "titulo": "Desenvolvedor React Júnior", "empresa": "TechCorp", "url": "https://a.com"}
        v2_mesmo_id = {"id": "1", "titulo": "Desenvolvedor React Júnior", "empresa": "TechCorp", "url": "https://a.com"}
        v3_mesmo_titulo_empresa_outro_id = {"id": "gupy_2", "titulo": "Desenvolvedor React Júnior", "empresa": "TechCorp", "url": "https://b.com"}
        v4_inedita = {"id": "3", "titulo": "Estagiário de TI", "empresa": "LocalTech", "url": "https://c.com"}

        scraper1 = FakeScraper("linkedin", [v1, v2_mesmo_id])
        scraper2 = FakeScraper("gupy", [v3_mesmo_titulo_empresa_outro_id, v4_inedita])

        collector = JobCollector({
            "linkedin": scraper1,
            "gupy": scraper2
        })

        buscas = [{"termo": "Desenvolvedor Junior", "location": None, "remoto": True}]
        novas = collector.coletar_vagas_ineditas(buscas, max_pages=1)

        # De 4 itens, apenas 2 são únicos (v1 e v4)
        assert len(novas) == 2
        ids = [v["id"] for v in novas]
        assert "1" in ids
        assert "3" in ids
