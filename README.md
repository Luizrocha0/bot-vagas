# 🤖 Caçador de Vagas com Gemini AI & WhatsApp / Telegram 🎯

Um bot autônomo e inteligente projetado sob medida para o perfil de **Luiz Henrique Rocha Silva** (Desenvolvedor Full Stack: Next.js, Nest.js, TypeScript, React, Java/Spring Boot, Python).

O bot faz varreduras em tempo real por vagas abertas no **LinkedIn**, lê as descrições completas e usa a **Gemini API** para avaliar a compatibilidade semântica. Se encontrar um match relevante (score $\ge 70\%$), ele envia um relatório detalhado diretamente para o seu **WhatsApp** (e/ou Telegram)!

---

## 📁 Estrutura do Projeto (`C:\Users\Mignac\Desktop\bot-vagas`)

```text
bot-vagas/
├── perfil_candidato.json   # Seu perfil, competências, stack e projetos
├── linkedin_scraper.py     # Coleta pública de vagas e descrições no LinkedIn
├── gemini_matcher.py       # Cérebro de IA: cálculo de score, análise de gaps e dicas
├── whatsapp_notifier.py    # Notificador formatado para WhatsApp (CallMeBot)
├── telegram_notifier.py    # Notificador para Telegram (opcional)
├── run.py                  # Ponto de entrada para execução manual
├── scheduler.py            # Serviço de agendamento automático diário (09:00, 14:00, 19:00)
├── test_scraper.py         # Script rápido para testar busca ao vivo
├── vagas_vistas.json       # Histórico de vagas já analisadas (evita repetições)
├── historico_matches.json  # Relatório completo de todos os matches gerados
├── .env                    # Suas credenciais locais
└── requirements.txt        # Dependências instaladas
```

---

## 🟢 Como Ativar as Notificações no WhatsApp (Gratuito em 1 minuto)

Usamos a API do **CallMeBot**, que permite bots em Python enviarem mensagens gratuitas diretamente para o seu número pessoal de WhatsApp, sem necessidade de servidores complexos.

### Passo a Passo:
1. Adicione o número do bot aos seus contatos do WhatsApp:
   * **Número:** `+34 644 76 66 43` (ou alternativo: `+34 644 59 71 67`)
   * *(Pode salvar com o nome "CallMeBot Gateway")*
2. Abra uma conversa com ele no WhatsApp e envie exatamente a seguinte mensagem:
   ```text
   I allow callmebot to send me messages
   ```
3. Em poucos segundos, ele responderá com uma mensagem contendo sua chave:
   > *"CallMeBot API Key: 123456"*
4. Abra o arquivo [`.env`](file:///C:/Users/Mignac/Desktop/bot-vagas/.env) e preencha:
   ```env
   WHATSAPP_PHONE=5581985227931
   WHATSAPP_APIKEY=sua_chave_recebida_aqui
   ```
5. Teste o envio no terminal:
   ```powershell
   python run.py --test-whatsapp
   ```
   Você receberá uma mensagem de confirmação instantaneamente no seu WhatsApp!

---

## 🔑 Como Obter a Chave da Gemini API (Gratuita)

1. Acesse o [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Clique em **"Create API Key"** e copie a chave gerada.
3. No arquivo [`.env`](file:///C:/Users/Mignac/Desktop/bot-vagas/.env), cole:
   ```env
   GEMINI_API_KEY=AIzaSy...
   ```

---

## 🚀 Como Executar

### 1. Fazer uma varredura manual agora:
```powershell
python run.py
```

* **Filtrar apenas vagas 100% remotas:**
  ```powershell
  python run.py --remoto
  ```

* **Definir nota de corte mais exigente (ex: 80%):**
  ```powershell
  python run.py --score 80
  ```

### 2. Deixar monitorando diariamente em segundo plano:
```powershell
python scheduler.py
```

O bot roda automaticamente nos horários programados (`09:00`, `14:00`, `19:00`) e manda a notificação no seu WhatsApp sempre que uma vaga compatível nova surgir.
