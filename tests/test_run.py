import os
import json
import pytest
from unittest.mock import patch, MagicMock, call

import run
from run import (
    carregar_historico,
    salvar_historico,
    executar_busca
)


@pytest.fixture(autouse=True)
def mock_scrapers_secundarios_padrao(monkeypatch):
    """Garante que por padrão scrapers de terceiros retornem vazio nos testes legados."""
    monkeypatch.setattr(run, "buscar_vagas_gupy", lambda *a, **kw: [])
    monkeypatch.setattr(run, "buscar_vagas_programathor", lambda *a, **kw: [])
    monkeypatch.setattr(run, "buscar_vagas_indeed", lambda *a, **kw: [])
    monkeypatch.setattr(run, "obter_detalhes_vaga", lambda *a, **kw: {"descricao": "Descrição mock padrão longa para teste de fluxo.", "criterios": {}})




class TestPersistenciaHistorico:
    """Testes de persistência do histórico de matches avaliados."""

    def test_carregar_historico_arquivo_inexistente(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "historico_inexistente.json"
        monkeypatch.setattr(run, "MATCH_HISTORY_FILE", str(fake_file))
        assert carregar_historico() == []

    def test_carregar_historico_arquivo_invalido(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "historico_corrompido.json"
        fake_file.write_text("{ json quebrado", encoding="utf-8")
        monkeypatch.setattr(run, "MATCH_HISTORY_FILE", str(fake_file))
        assert carregar_historico() == []

    def test_carregar_historico_conteudo_dicionario_ou_null_retorna_lista_vazia(self, tmp_path, monkeypatch):
        fake_dict_file = tmp_path / "historico_dict.json"
        fake_dict_file.write_text('{"matches": []}', encoding="utf-8")
        monkeypatch.setattr(run, "MATCH_HISTORY_FILE", str(fake_dict_file))
        assert carregar_historico() == []

        fake_null_file = tmp_path / "historico_null.json"
        fake_null_file.write_text('null', encoding="utf-8")
        monkeypatch.setattr(run, "MATCH_HISTORY_FILE", str(fake_null_file))
        assert carregar_historico() == []

    def test_salvar_e_carregar_historico(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "historico_teste.json"
        monkeypatch.setattr(run, "MATCH_HISTORY_FILE", str(fake_file))

        dados = [{"vaga_id": "1", "score": 90}]
        salvar_historico(dados)

        assert fake_file.exists()
        assert carregar_historico() == dados


class TestBalanceamentoECotas:
    """Testes da regra de negócio: distribuição exata de 2 remotas + 2 presenciais (PE) e complementação."""

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_distribuicao_balanceada_2_remotas_e_2_presenciais(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        # Vagas retornadas na busca
        vagas_simuladas = [
            {"id": "rem_1", "titulo": "Dev React Jr", "empresa": "A", "localizacao": "Brasil"},
            {"id": "rem_2", "titulo": "Dev Node Jr", "empresa": "B", "localizacao": "Brasil"},
            {"id": "rem_3", "titulo": "Dev Python Jr", "empresa": "C", "localizacao": "Brasil"},
            {"id": "pres_1", "titulo": "Dev Java Jr", "empresa": "D", "localizacao": "Recife, PE"},
            {"id": "pres_2", "titulo": "Estágio TI", "empresa": "E", "localizacao": "Recife, PE"},
            {"id": "pres_3", "titulo": "Dev Fullstack Jr", "empresa": "F", "localizacao": "Recife, PE"},
        ]

        # Simula apenas o primeiro termo retornando as vagas para simplificar o teste
        mock_buscar.side_effect = [vagas_simuladas] + [[]] * 9
        mock_detalhes.return_value = {"descricao": "Descrição completa da vaga com mais de 30 caracteres válidos.", "criterios": {}}

        # Simula scores e modalidades diferentes
        def fake_analise(vaga, client=None):
            scores = {
                "rem_1": (90, "REMOTO"),
                "rem_2": (80, "REMOTO"),
                "rem_3": (70, "REMOTO"),
                "pres_1": (95, "PRESENCIAL_PE"),
                "pres_2": (85, "PRESENCIAL_PE"),
                "pres_3": (75, "PRESENCIAL_PE"),
            }
            score, mod = scores[vaga["id"]]
            return {
                "compatibilidade_percentual": score,
                "tipo_modalidade": mod,
                "eh_junior_ou_estagio": True,
                "classificacao": "Excelente"
            }

        mock_analisar.side_effect = fake_analise

        executar_busca(meta_remotas=2, meta_presenciais=2, max_pages_per_term=1)

        # Deve disparar exatamente 4 notificações
        assert mock_tel.call_count == 4
        assert mock_wpp.call_count == 4

        vagas_notificadas = [chamada[0][0]["id"] for chamada in mock_tel.call_args_list]

        # Devem ser as 2 melhores remotas (rem_1: 90, rem_2: 80) e as 2 melhores presenciais (pres_1: 95, pres_2: 85)
        assert vagas_notificadas == ["rem_1", "rem_2", "pres_1", "pres_2"]

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_complementacao_de_cota_quando_nao_ha_vagas_presenciais(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        # Apenas vagas remotas disponíveis
        vagas_simuladas = [
            {"id": "r1", "titulo": "Vaga 1", "empresa": "A", "localizacao": "Brasil"},
            {"id": "r2", "titulo": "Vaga 2", "empresa": "B", "localizacao": "Brasil"},
            {"id": "r3", "titulo": "Vaga 3", "empresa": "C", "localizacao": "Brasil"},
            {"id": "r4", "titulo": "Vaga 4", "empresa": "D", "localizacao": "Brasil"},
            {"id": "r5", "titulo": "Vaga 5", "empresa": "E", "localizacao": "Brasil"},
        ]
        mock_buscar.side_effect = [vagas_simuladas] + [[]] * 9
        mock_detalhes.return_value = {"descricao": "Descrição válida com bastante texto técnico.", "criterios": {}}

        def fake_analise(vaga, client=None):
            scores = {"r1": 95, "r2": 90, "r3": 85, "r4": 80, "r5": 70}
            return {
                "compatibilidade_percentual": scores[vaga["id"]],
                "tipo_modalidade": "REMOTO",
                "eh_junior_ou_estagio": True,
                "classificacao": "Boa"
            }

        mock_analisar.side_effect = fake_analise

        executar_busca(meta_remotas=2, meta_presenciais=2, max_pages_per_term=1)

        # Mesmo sem presenciais, cota de 4 deve ser preenchida pelas melhores remotas restantes
        assert mock_tel.call_count == 4
        vagas_notificadas = [chamada[0][0]["id"] for chamada in mock_tel.call_args_list]
        assert vagas_notificadas == ["r1", "r2", "r3", "r4"]

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_complementacao_quando_ha_apenas_1_remota(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        # 1 remota e 3 locais
        vagas_simuladas = [
            {"id": "r1", "titulo": "Dev Remoto", "empresa": "A", "localizacao": "Brasil"},
            {"id": "p1", "titulo": "Dev Presencial 1", "empresa": "B", "localizacao": "Recife, PE"},
            {"id": "p2", "titulo": "Dev Presencial 2", "empresa": "C", "localizacao": "Recife, PE"},
            {"id": "p3", "titulo": "Dev Presencial 3", "empresa": "D", "localizacao": "Recife, PE"},
        ]
        mock_buscar.side_effect = [vagas_simuladas] + [[]] * 9
        mock_detalhes.return_value = {"descricao": "Descrição válida com bastante texto técnico.", "criterios": {}}

        def fake_analise(vaga, client=None):
            if vaga["id"] == "r1":
                return {"compatibilidade_percentual": 80, "tipo_modalidade": "REMOTO", "eh_junior_ou_estagio": True}
            scores = {"p1": 95, "p2": 90, "p3": 85}
            return {"compatibilidade_percentual": scores[vaga["id"]], "tipo_modalidade": "PRESENCIAL_PE", "eh_junior_ou_estagio": True}

        mock_analisar.side_effect = fake_analise

        executar_busca(meta_remotas=2, meta_presenciais=2, max_pages_per_term=1)

        assert mock_tel.call_count == 4
        vagas_notificadas = [chamada[0][0]["id"] for chamada in mock_tel.call_args_list]
        # 1 remota + 2 presenciais da meta + 1 presencial complementar
        assert "r1" in vagas_notificadas
        assert "p1" in vagas_notificadas
        assert "p2" in vagas_notificadas
        assert "p3" in vagas_notificadas

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_meta_zero_presenciais_nao_complementa_com_presenciais(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        # 2 remotas e 2 presenciais
        vagas_simuladas = [
            {"id": "r1", "titulo": "Dev Remoto 1", "empresa": "A", "localizacao": "Brasil"},
            {"id": "r2", "titulo": "Dev Remoto 2", "empresa": "B", "localizacao": "Brasil"},
            {"id": "p1", "titulo": "Dev Presencial 1", "empresa": "C", "localizacao": "Recife, PE"},
            {"id": "p2", "titulo": "Dev Presencial 2", "empresa": "D", "localizacao": "Recife, PE"},
        ]
        mock_buscar.side_effect = [vagas_simuladas] + [[]] * 9
        mock_detalhes.return_value = {"descricao": "Descrição válida com bastante texto técnico.", "criterios": {}}

        def fake_analise(vaga, client=None):
            if vaga["id"].startswith("r"):
                return {"compatibilidade_percentual": 80, "tipo_modalidade": "REMOTO", "eh_junior_ou_estagio": True}
            return {"compatibilidade_percentual": 90, "tipo_modalidade": "PRESENCIAL_PE", "eh_junior_ou_estagio": True}

        mock_analisar.side_effect = fake_analise

        # Executa com meta_remotas=4 e meta_presenciais=0 (ex: REMOTE_ONLY)
        executar_busca(meta_remotas=4, meta_presenciais=0, max_pages_per_term=1)

        # Não deve complementar com vagas presenciais porque meta_presenciais=0
        assert mock_tel.call_count == 2
        vagas_notificadas = [chamada[0][0]["id"] for chamada in mock_tel.call_args_list]
        assert vagas_notificadas == ["r1", "r2"]
        assert "p1" not in vagas_notificadas
        assert "p2" not in vagas_notificadas

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_complementacao_com_vagas_sem_id_explicito_nao_colidem_como_none(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        # Vagas sem a chave "id" explícita
        vagas_simuladas = [
            {"titulo": "Dev Sem ID 1", "empresa": "Alfa Corp", "url": "https://linkedin.com/jobs/view/111", "localizacao": "Brasil"},
            {"titulo": "Dev Sem ID 2", "empresa": "Beta Corp", "url": "https://linkedin.com/jobs/view/222", "localizacao": "Brasil"},
        ]
        mock_buscar.side_effect = [vagas_simuladas] + [[]] * 9
        mock_detalhes.return_value = {"descricao": "Descrição detalhada com texto suficiente para análise.", "criterios": {}}

        def fake_analise(vaga, client=None):
            score = 90 if "1" in vaga.get("titulo", "") else 80
            return {"compatibilidade_percentual": score, "tipo_modalidade": "REMOTO", "eh_junior_ou_estagio": True}

        mock_analisar.side_effect = fake_analise

        # Meta de 2 remotas: ambas devem ser selecionadas e notificadas sem colidir em None
        executar_busca(meta_remotas=2, meta_presenciais=0, max_pages_per_term=1)

        assert mock_tel.call_count == 2
        notificados = [chamada[0][0]["titulo"] for chamada in mock_tel.call_args_list]
        assert "Dev Sem ID 1" in notificados
        assert "Dev Sem ID 2" in notificados


class TestFallbackInteligenteDescricao:
    """Testes do fallback de descrição quando o scraper de detalhes falha ou retorna texto curto."""

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_aciona_fallback_quando_descricao_vazia(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        vaga = {"id": "job_sem_desc", "titulo": "Desenvolvedor Junior", "empresa": "Tech Corp", "localizacao": "Recife, PE"}
        mock_buscar.side_effect = [[vaga]] + [[]] * 9

        # Scraper de detalhes falha e retorna dicionário com descrição vazia
        mock_detalhes.return_value = {"descricao": "", "criterios": {}}

        vaga_analisada_recebida = {}
        def interceptar_analise(v, client=None):
            nonlocal vaga_analisada_recebida
            vaga_analisada_recebida = dict(v)
            return {
                "compatibilidade_percentual": 75,
                "tipo_modalidade": "PRESENCIAL_PE",
                "eh_junior_ou_estagio": True
            }

        mock_analisar.side_effect = interceptar_analise

        executar_busca(meta_remotas=2, meta_presenciais=2, max_pages_per_term=1)

        # Confirma que a vaga NÃO foi descartada e recebeu o fallback inteligente
        assert vaga_analisada_recebida != {}
        assert "Vaga de Desenvolvedor Junior na empresa Tech Corp" in vaga_analisada_recebida["descricao"]
        assert "área de tecnologia e desenvolvimento de software para início de carreira" in vaga_analisada_recebida["descricao"]
        assert vaga_analisada_recebida["criterios"] == {"Tipo": "Início de Carreira"}

        # Confirma que a vaga com fallback foi notificada
        assert mock_tel.call_count == 1
        assert mock_tel.call_args[0][0]["id"] == "job_sem_desc"

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_aciona_fallback_quando_descricao_curta_menor_que_30_caracteres(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        vaga = {"id": "job_curto", "titulo": "Estágio TI", "empresa": "Alfa", "localizacao": "Recife"}
        mock_buscar.side_effect = [[vaga]] + [[]] * 9
        mock_detalhes.return_value = {"descricao": "Vaga rápida", "criterios": {}}

        vaga_analisada_recebida = {}
        def interceptar_analise(v, client=None):
            nonlocal vaga_analisada_recebida
            vaga_analisada_recebida = dict(v)
            return {"compatibilidade_percentual": 70, "tipo_modalidade": "PRESENCIAL_PE", "eh_junior_ou_estagio": True}

        mock_analisar.side_effect = interceptar_analise

        executar_busca()

        assert "área de tecnologia e desenvolvimento de software para início de carreira" in vaga_analisada_recebida["descricao"]
        assert mock_tel.call_count == 1

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_preserva_descricao_completa_quando_sucesso(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        vaga = {"id": "job_ok", "titulo": "Dev Junior", "empresa": "Beta", "localizacao": "Brasil"}
        mock_buscar.side_effect = [[vaga]] + [[]] * 9

        desc_real = "Esta é uma descrição original e completa com mais de 30 caracteres detalhando a stack."
        mock_detalhes.return_value = {"descricao": desc_real, "criterios": {"Experiência": "Júnior"}}

        vaga_analisada_recebida = {}
        def interceptar_analise(v, client=None):
            nonlocal vaga_analisada_recebida
            vaga_analisada_recebida = dict(v)
            return {"compatibilidade_percentual": 80, "tipo_modalidade": "REMOTO", "eh_junior_ou_estagio": True}

        mock_analisar.side_effect = interceptar_analise

        executar_busca()

        assert vaga_analisada_recebida["descricao"] == desc_real
        assert vaga_analisada_recebida["criterios"] == {"Experiência": "Júnior"}


class TestFiltrosDeduplicacaoEInicializacao:
    """Testes de deduplicação de vagas já vistas, filtros de corte e erros de inicialização."""

    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_pula_vagas_ja_vistas(self, mock_gemini_init, mock_buscar, mock_tel, mock_wpp, monkeypatch):
        # ID '101' já está em vagas vistas
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: {"101"})
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        vagas = [
            {"id": "101", "titulo": "Dev Antiga", "empresa": "A", "localizacao": "Brasil"},
            {"id": "102", "titulo": "Dev Nova", "empresa": "B", "localizacao": "Brasil"},
        ]
        mock_buscar.side_effect = [vagas] + [[]] * 9

        with patch("run.obter_detalhes_vaga") as mock_detalhes, \
             patch("run.analisar_compatibilidade_vaga") as mock_analisar, \
             patch("run.salvar_vagas_vistas") as mock_salvar_vistas, \
             patch("run.salvar_historico"):

            mock_detalhes.return_value = {"descricao": "desc", "criterios": {}}
            mock_analisar.return_value = {"compatibilidade_percentual": 80, "tipo_modalidade": "REMOTO", "eh_junior_ou_estagio": True}

            executar_busca()

            # Apenas a vaga 102 deve ser avaliada
            assert mock_detalhes.call_count == 1
            assert mock_detalhes.call_args[0][0] == "102"
            assert mock_tel.call_count == 1
            assert mock_wpp.call_count == 1

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_descarta_vagas_com_score_baixo_ou_nao_junior(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        vagas = [
            {"id": "v1", "titulo": "Vaga Score Baixo", "empresa": "A", "localizacao": "Brasil"},
            {"id": "v2", "titulo": "Vaga Nao Junior", "empresa": "B", "localizacao": "Brasil"},
            {"id": "v3", "titulo": "Vaga Invalida", "empresa": "C", "localizacao": "SP"},
        ]
        mock_buscar.side_effect = [vagas] + [[]] * 9
        mock_detalhes.return_value = {"descricao": "Descrição longa e completa da vaga para teste.", "criterios": {}}

        mock_analisar.side_effect = [
            # Score < 35
            {"compatibilidade_percentual": 20, "tipo_modalidade": "REMOTO", "eh_junior_ou_estagio": True},
            # Não é júnior/estágio
            {"compatibilidade_percentual": 80, "tipo_modalidade": "REMOTO", "eh_junior_ou_estagio": False},
            # Modalidade inválida (ex: presencial SP)
            {"compatibilidade_percentual": 80, "tipo_modalidade": "INVALIDA", "eh_junior_ou_estagio": True},
        ]

        executar_busca()

        # Nenhuma vaga deve ser notificada
        mock_tel.assert_not_called()
        mock_wpp.assert_not_called()

    @patch("run.criar_cliente_gemini")
    def test_interrompe_execucao_se_gemini_falhar_na_inicializacao(self, mock_gemini_init, monkeypatch):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        mock_gemini_init.side_effect = ValueError("GEMINI_API_KEY ausente")

        with patch("run.buscar_vagas_linkedin") as mock_buscar:
            executar_busca()
            # Não deve realizar buscas se a IA não pôde ser inicializada
            mock_buscar.assert_not_called()

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.obter_detalhes_vaga")
    @patch("run.buscar_vagas_linkedin")
    @patch("run.criar_cliente_gemini")
    def test_execucao_tolerante_a_campos_ausentes_e_score_string(
        self,
        mock_gemini_init,
        mock_buscar,
        mock_detalhes,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        # Vaga sem id, sem título e sem empresa explícitos
        vagas = [{"url": "https://linkedin.com/jobs/view/999"}]
        mock_buscar.side_effect = [vagas] + [[]] * 9
        mock_detalhes.return_value = {"descricao": "Descrição detalhada com mais de 30 caracteres.", "criterios": {}}

        # Análise com score string e júnior como string
        mock_analisar.return_value = {
            "compatibilidade_percentual": "85%",
            "tipo_modalidade": "REMOTO",
            "eh_junior_ou_estagio": "sim",
            "classificacao": "Boa"
        }

        executar_busca(meta_remotas=1, meta_presenciais=0)
        assert mock_tel.call_count == 1
        assert mock_wpp.call_count == 1


class TestCLIOrquestrador:
    """Testes dos argumentos de linha de comando suportados pelo script run.py."""

    @patch("run.testar_conexao_telegram")
    def test_cli_test_telegram(self, mock_test_tel):
        mock_test_tel.return_value = (True, "Conectado!")
        rc = run.main(["--test-telegram"])
        assert rc == 0
        mock_test_tel.assert_called_once()

    @patch("run.testar_conexao_whatsapp")
    def test_cli_test_whatsapp(self, mock_test_wpp):
        mock_test_wpp.return_value = (True, "WhatsApp Conectado!")
        rc = run.main(["--test-whatsapp"])
        assert rc == 0
        mock_test_wpp.assert_called_once()

    @patch("run.executar_busca")
    def test_cli_executar_busca_com_argumentos(self, mock_executar):
        rc = run.main(["--remotas", "3", "--presenciais", "1", "--paginas", "2"])
        assert rc == 0
        mock_executar.assert_called_once_with(
            meta_remotas=3,
            meta_presenciais=1,
            max_pages_per_term=2,
            fontes=None
        )


class TestMultiFontesIntegracao:
    """Testes de integração multi-fontes, deduplicação entre portais e parâmetros de seleção."""

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.criar_cliente_gemini")
    def test_coleta_multi_fontes_integrada(
        self,
        mock_gemini,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        # Vaga de cada fonte
        v_linkedin = [{"id": "1", "fonte": "LinkedIn", "titulo": "Dev React Jr", "empresa": "Tech A", "localizacao": "Brasil", "descricao": "desc longa dev react junior"}]
        v_gupy = [{"id": "gupy_2", "fonte": "Gupy", "titulo": "Dev Node Jr", "empresa": "Tech B", "localizacao": "Remoto", "descricao": "desc longa dev node junior"}]
        v_prog = [{"id": "programathor_3", "fonte": "Programathor", "titulo": "Dev Python Jr", "empresa": "Tech C", "localizacao": "Recife, PE", "descricao": "desc longa dev python junior"}]
        v_indeed = [{"id": "indeed_4", "fonte": "Indeed", "titulo": "Estágio TI", "empresa": "Tech D", "localizacao": "Recife, PE", "descricao": "desc longa estagio ti recife"}]

        monkeypatch.setattr(run, "buscar_vagas_linkedin", lambda *a, **kw: v_linkedin if kw.get("keywords") == "Desenvolvedor Junior" and kw.get("remote_only") else [])
        monkeypatch.setattr(run, "buscar_vagas_gupy", lambda *a, **kw: v_gupy if kw.get("keywords") == "Desenvolvedor Junior" and kw.get("remote_only") else [])
        monkeypatch.setattr(run, "buscar_vagas_programathor", lambda *a, **kw: v_prog if kw.get("keywords") == "Desenvolvedor Junior" and not kw.get("remote_only") else [])
        monkeypatch.setattr(run, "buscar_vagas_indeed", lambda *a, **kw: v_indeed if kw.get("keywords") == "Desenvolvedor Junior" and not kw.get("remote_only") else [])

        def fake_analise(v, client=None):
            mod = "REMOTO" if "Remoto" in v.get("localizacao", "") or "Brasil" in v.get("localizacao", "") else "PRESENCIAL_PE"
            return {
                "compatibilidade_percentual": 90,
                "tipo_modalidade": mod,
                "eh_junior_ou_estagio": True,
                "classificacao": "Excelente"
            }

        mock_analisar.side_effect = fake_analise

        executar_busca(meta_remotas=2, meta_presenciais=2, max_pages_per_term=1)

        # Todas as 4 vagas foram selecionadas e notificadas
        assert mock_tel.call_count == 4
        assert mock_wpp.call_count == 4

        fontes_notificadas = [c[0][0]["fonte"] for c in mock_tel.call_args_list]
        assert "LinkedIn" in fontes_notificadas
        assert "Gupy" in fontes_notificadas
        assert "Programathor" in fontes_notificadas
        assert "Indeed" in fontes_notificadas

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.criar_cliente_gemini")
    def test_deduplicacao_entre_plataformas(
        self,
        mock_gemini,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        # Mesma vaga publicada no LinkedIn e na Gupy
        v_linkedin = [{"id": "link_101", "fonte": "LinkedIn", "titulo": "Desenvolvedor React Júnior", "empresa": "Nubank", "localizacao": "Brasil", "descricao": "desc"}]
        v_gupy = [{"id": "gupy_202", "fonte": "Gupy", "titulo": "Desenvolvedor React Júnior", "empresa": "Nubank", "localizacao": "Remoto", "descricao": "desc"}]

        monkeypatch.setattr(run, "buscar_vagas_linkedin", lambda *a, **kw: v_linkedin if kw.get("keywords") == "Desenvolvedor Junior" else [])
        monkeypatch.setattr(run, "buscar_vagas_gupy", lambda *a, **kw: v_gupy if kw.get("keywords") == "Desenvolvedor Junior" else [])

        mock_analisar.return_value = {
            "compatibilidade_percentual": 90,
            "tipo_modalidade": "REMOTO",
            "eh_junior_ou_estagio": True
        }

        executar_busca(meta_remotas=2, meta_presenciais=0, max_pages_per_term=1)

        # Deve disparar apenas 1 notificação porque a vaga é a mesma
        assert mock_tel.call_count == 1
        assert mock_wpp.call_count == 1
        assert mock_tel.call_args[0][0]["empresa"] == "Nubank"

    @patch("run.salvar_historico")
    @patch("run.salvar_vagas_vistas")
    @patch("run.enviar_notificacao_whatsapp")
    @patch("run.enviar_notificacao_telegram")
    @patch("run.analisar_compatibilidade_vaga")
    @patch("run.criar_cliente_gemini")
    def test_filtro_por_parametro_fontes(
        self,
        mock_gemini,
        mock_analisar,
        mock_tel,
        mock_wpp,
        mock_salvar_vistas,
        mock_salvar_hist,
        monkeypatch
    ):
        monkeypatch.setattr(run, "carregar_vagas_vistas", lambda: set())
        monkeypatch.setattr(run, "carregar_historico", lambda: [])

        chamou_linkedin = False
        chamou_gupy = False

        def spy_linkedin(*a, **kw):
            nonlocal chamou_linkedin
            chamou_linkedin = True
            return []

        def spy_gupy(*a, **kw):
            nonlocal chamou_gupy
            chamou_gupy = True
            return [{"id": "g1", "fonte": "Gupy", "titulo": "Dev Jr", "empresa": "Emp A", "localizacao": "Remoto", "descricao": "desc longa"}]

        monkeypatch.setattr(run, "buscar_vagas_linkedin", spy_linkedin)
        monkeypatch.setattr(run, "buscar_vagas_gupy", spy_gupy)

        mock_analisar.return_value = {"compatibilidade_percentual": 80, "tipo_modalidade": "REMOTO", "eh_junior_ou_estagio": True}

        # Executa solicitando apenas a Gupy
        executar_busca(meta_remotas=1, meta_presenciais=0, fontes=["gupy"])

        assert chamou_gupy is True
        assert chamou_linkedin is False
        assert mock_tel.call_count == 1


