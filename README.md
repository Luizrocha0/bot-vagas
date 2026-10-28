# 🤖 Caçador de Vagas com IA do Gemini (Multi-Fontes) 🎯

[![Testes Automatizados](https://img.shields.io/badge/Testes-266%20Passando-brightgreen)](tests/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Google Gemini API](https://img.shields.io/badge/AI-Google%20Gemini%20Flash-orange.svg)](https://aistudio.google.com/)
[![Notificações](https://img.shields.io/badge/Alertas-Telegram%20%7C%20WhatsApp-25D366.svg)](#-notificações)
[![Arquitetura](https://img.shields.io/badge/Design-Clean%20Architecture%20%26%20SOLID-purple.svg)](core/)

Robô inteligente e autônomo projetado para minerar, filtrar e avaliar vagas de tecnologia (**Estágio**, **Júnior** e **Trainee**) em múltiplas plataformas de emprego (**LinkedIn**, **Gupy**, **Programathor**, **Indeed**), analisando cada oportunidade linha por linha com a **IA do Google Gemini** em relação ao currículo do candidato e notificando as melhores oportunidades em tempo real via **Telegram** e **WhatsApp**.

> [!TIP]
> **Quer começar agora com o seu próprio currículo?**  
> Leia nosso [📚 Tutorial Completo Passo a Passo](TUTORIAL.md) ou use o assistente interativo `python setup.py`!

---

## 🌟 Principais Recursos

- 🌐 **Multi-Fontes de Vagas:** Scrapers modulares e resilientes para **LinkedIn**, **Gupy**, **Programathor** e **Indeed**.
- 🧠 **Análise Semântica com IA:** Utiliza o Google Gemini (`gemini-3.1-flash-lite`, `gemini-3.5-flash`, `gemini-3.8-flash`) com fallback automático para calcular a compatibilidade técnica do candidato (0% a 100%).
- ⚖️ **Balanceamento Inteligente de Cotas:** Separação precisa de cotas de vagas **Remotas** e **Presenciais/Locais**, com complementação dinâmica quando uma das modalidades não atinge a meta.
- 🚫 **Deduplicação Inteligente:** Evita repetição de vagas já avaliadas ou notificadas através de persistência em histórico.
- 📱 **Alertas Imediatos:** Disparo formatado com resumo técnico, pontos fortes, requisitos faltantes e link direto no Telegram e WhatsApp.
- ☁️ **100% Gratuito:** Pode ser executado localmente ou de forma autônoma na nuvem via **GitHub Actions** sem custos.

---

## ⚡ Início Rápido em 3 Minutos

### 1. Clonar o projeto e instalar dependências
```bash
git clone https://github.com/Luizrocha0/bot-vagas.git
cd bot-vagas
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Rodar o Assistente de Configuração
O assistente guia a configuração da sua chave Gemini gratuita do [Google AI Studio](https://aistudio.google.com/app/apikey), seus alertas no Telegram e seu currículo:
```bash
python setup.py
```

### 3. Verificar a Saúde do Ambiente
```bash
python setup.py --check
```

### 4. Executar o Robô
```bash
# Busca padrão (2 vagas remotas + 2 locais)
python run.py

# Ou buscando apenas 1 vaga rápida de demonstração:
python run.py --remotas 1 --presenciais 1 --fontes gupy,programathor
```

---

## 🏗️ Arquitetura do Sistema

O projeto adota os princípios de **Clean Architecture**, **Clean Code** e **SOLID**:

```
bot-vagas/
├── core/                       # Domínio e regras de negócio puras
│   ├── models.py               # Entidades de domínio (Vaga, ResultadoMatch, ModalidadeVaga)
│   ├── collector.py            # JobCollector (orquestração e deduplicação de scrapers)
│   ├── selector.py             # QuotaSelector (balanceamento inteligente de cotas)
│   ├── notifier.py             # NotificationDispatcher (pipeline de alertas)
│   └── repository.py           # JobRepository (persistência de estado e histórico)
├── scrapers/                   # Scrapers modulares de plataformas de vagas
│   ├── base.py                 # BaseJobScraper (Template Method & contrato)
│   ├── linkedin.py             # LinkedInScraper (busca anônima e extração detalhada)
│   ├── gupy.py                 # GupyScraper (API pública com paginação)
│   ├── programathor.py         # ProgramathorScraper (scraping web de vagas tech)
│   └── indeed.py               # IndeedScraper (feed estruturado RSS/HTML)
├── gemini_matcher.py           # Integração com a Google Gemini API e cálculo de match
├── telegram_notifier.py        # Módulo de mensageria para Telegram Bot API
├── whatsapp_notifier.py        # Módulo de mensageria para WhatsApp (CallMeBot)
├── setup.py                    # Assistente CLI de Onboarding e validação de ambiente
├── run.py                      # Orquestrador de execução e CLI principal
├── scheduler.py                # Agendador contínuo local
├── perfil_candidato.json       # Currículo e preferências ativas
├── perfil_candidato.example.json # Modelo de currículo genérico documentado
└── tests/                      # Suíte de 266 testes unitários e de integração
```

---

## 🧪 Testes Automatizados (TDD)

O projeto possui cobertura completa de testes automatizados com mocks para APIs externas e scrapers:

```bash
pytest -v
```

Resultado atual: **266 testes passando em menos de 3 segundos**!

---

## ☁️ Automação Gratuita na Nuvem (GitHub Actions)

Você pode deixar o robô executando automaticamente nos servidores do GitHub sem precisar deixar seu computador ligado.

Veja o guia detalhado em [📚 TUTORIAL.md - Etapa 6](TUTORIAL.md#-etapa-6-automação-100-gratuita-no-github-actions).

---

## 📄 Licença

Distribuído sob a licença MIT.
