import os
import sys
import socket
import pytest

# Garante que o diretório raiz esteja no sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    """
    Impede qualquer conexão de rede real via socket e resolução DNS externa.
    Se algum teste esquecer de mockar requisições externas, falhará imediatamente com pytest.fail.
    """
    def guarded_connect(self, address):
        pytest.fail(
            f"Tentativa de conexão de rede externa bloqueada para {address}. "
            "Certifique-se de usar unittest.mock para simular chamadas de rede!"
        )

    def guarded_connect_ex(self, address):
        pytest.fail(
            f"Tentativa de conexão de rede externa bloqueada para {address}. "
            "Certifique-se de usar unittest.mock para simular chamadas de rede!"
        )

    def guarded_sendto(self, *args, **kwargs):
        pytest.fail(
            "Tentativa de envio UDP para rede externa bloqueada. "
            "Certifique-se de usar unittest.mock para simular chamadas de rede!"
        )

    def guarded_getaddrinfo(host, port, *args, **kwargs):
        if host in ("localhost", "127.0.0.1", "::1"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port))]
        pytest.fail(
            f"Tentativa de resolução DNS externa bloqueada para '{host}'. "
            "Certifique-se de usar unittest.mock para simular chamadas de rede!"
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket.socket, "sendto", guarded_sendto)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """
    Remove tempos de espera de time.sleep durante os testes para execução ultra-rápida.
    """
    monkeypatch.setattr("time.sleep", lambda *args, **kwargs: None)


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """
    Define variáveis de ambiente padrão de teste para garantir isolamento.
    """
    monkeypatch.setenv("GEMINI_API_KEY", "test-fake-gemini-api-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TEST_TOKEN_TELEGRAM")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654321")
    monkeypatch.setenv("WHATSAPP_PHONE", "5581999999999")
    monkeypatch.setenv("WHATSAPP_APIKEY", "test_whatsapp_apikey")


@pytest.fixture
def sample_vaga():
    return {
        "id": "1001",
        "titulo": "Desenvolvedor Junior Frontend",
        "empresa": "Tech Solutions",
        "localizacao": "Remoto, Brasil",
        "url": "https://www.linkedin.com/jobs/view/1001",
        "publicado_em": "Há 2 horas",
        "descricao": "Vaga para desenvolvedor júnior com experiência em React e TypeScript.",
        "criterios": {"Nível de experiência": "Júnior", "Setor": "Tecnologia"}
    }


@pytest.fixture
def sample_vaga_presencial():
    return {
        "id": "2001",
        "titulo": "Desenvolvedor Full Stack Junior",
        "empresa": "Recife Tech",
        "localizacao": "Recife, Pernambuco, Brasil",
        "url": "https://www.linkedin.com/jobs/view/2001",
        "publicado_em": "Há 1 dia",
        "descricao": "Atuar presencialmente no Porto Digital em Recife com Java e Spring Boot.",
        "criterios": {"Nível de experiência": "Júnior"}
    }


@pytest.fixture
def sample_analise_remoto():
    return {
        "compatibilidade_percentual": 88,
        "classificacao": "Excelente",
        "tipo_modalidade": "REMOTO",
        "eh_junior_ou_estagio": True,
        "resumo_vaga": "Excelente oportunidade para início de carreira em frontend moderno.",
        "pontos_fortes": ["React", "TypeScript", "Next.js"],
        "requisitos_faltantes": ["Testes automatizados com Jest"],
        "dica_candidatura": "Destaque seus projetos desenvolvidos com Next.js e TypeScript.",
        "vale_a_pena_candidatar": True
    }


@pytest.fixture
def sample_analise_presencial():
    return {
        "compatibilidade_percentual": 92,
        "classificacao": "Excelente",
        "tipo_modalidade": "PRESENCIAL_PE",
        "eh_junior_ou_estagio": True,
        "resumo_vaga": "Vaga presencial no Porto Digital em Recife para Java e Spring.",
        "pontos_fortes": ["Java 17", "Spring Boot", "PostgreSQL"],
        "requisitos_faltantes": [],
        "dica_candidatura": "Mencione sua proximidade geográfica e projetos acadêmicos.",
        "vale_a_pena_candidatar": True
    }


@pytest.fixture
def sample_analise_invalida():
    return {
        "compatibilidade_percentual": 0,
        "classificacao": "Baixa",
        "tipo_modalidade": "INVALIDA",
        "eh_junior_ou_estagio": False,
        "resumo_vaga": "Vaga presencial em São Paulo, incompatível com residência em PE.",
        "pontos_fortes": [],
        "requisitos_faltantes": ["Residência em SP"],
        "dica_candidatura": "",
        "vale_a_pena_candidatar": False
    }


@pytest.fixture
def sample_linkedin_search_html():
    return """
    <ul>
        <li>
            <div class="base-search-card">
                <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/desenvolvedor-junior-1001?refId=123">
                    <h3 class="base-search-card__title">Desenvolvedor Junior</h3>
                </a>
                <h4 class="base-search-card__subtitle">Empresa Alfa</h4>
                <span class="job-search-card__location">Recife, Pernambuco, Brasil</span>
                <time datetime="2026-10-27">Há 1 hora</time>
            </div>
        </li>
        <li>
            <div class="base-search-card">
                <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/engenheiro-senior-1002?refId=123">
                    <h3 class="base-search-card__title">Engenheiro Sênior de Backend</h3>
                </a>
                <h4 class="base-search-card__subtitle">Empresa Beta</h4>
                <span class="job-search-card__location">Remoto, Brasil</span>
                <time datetime="2026-10-27">Há 2 horas</time>
            </div>
        </li>
        <li>
            <div class="base-search-card">
                <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/developer-junior-1003?refId=123">
                    <h3 class="base-search-card__title">Developer Junior</h3>
                </a>
                <h4 class="base-search-card__subtitle">Empresa Gamma</h4>
                <span class="job-search-card__location">New York, United States</span>
                <time datetime="2026-10-27">Há 3 horas</time>
            </div>
        </li>
        <li>
            <div class="base-search-card">
                <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/estagiario-ti-1004?refId=123">
                    <h3 class="base-search-card__title">Estagiário de TI</h3>
                </a>
                <h4 class="base-search-card__subtitle">Empresa Delta</h4>
                <span class="job-search-card__location">Brasil</span>
                <time datetime="2026-10-27">Há 4 horas</time>
            </div>
        </li>
    </ul>
    """


@pytest.fixture
def sample_linkedin_job_detail_html():
    return """
    <div class="job-view-layout">
        <div class="show-more-less-html__markup">
            Estamos buscando uma pessoa Desenvolvedora Júnior com conhecimentos em Python e APIs REST.
            Trabalho com metodologias ágeis e arquitetura moderna.
        </div>
        <ul class="description__job-criteria-list">
            <li class="description__job-criteria-item">
                <h3>Nível de experiência</h3>
                <span>Júnior</span>
            </li>
            <li class="description__job-criteria-item">
                <h3>Tipo de trabalho</h3>
                <span>Tempo integral</span>
            </li>
        </ul>
    </div>
    """
