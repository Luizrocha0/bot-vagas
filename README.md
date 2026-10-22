# 🤖 Caçador de Vagas com Gemini AI & WhatsApp / Telegram 🎯

Bot 100% autônomo na nuvem (GitHub Actions), projetado sob medida para o perfil de **Luiz Henrique Rocha Silva** (Desenvolvedor Full Stack: Next.js, Nest.js, TypeScript, React, Java/Spring Boot, Python).

O bot faz varreduras diárias automáticas por vagas no **LinkedIn**, lê as descrições completas e usa a **Gemini API** para avaliar a compatibilidade. Quando encontra um match relevante (score $\ge 70\%$), ele envia um relatório detalhado com links diretos diretamente no seu **WhatsApp** (e/ou Telegram)!

---

## ☁️ Como Rodar 100% no GitHub Actions (Sem depender do seu PC ligado)

Você só precisa criar um repositório no seu GitHub e subir este código. O GitHub disponibiliza **2.000 minutos gratuitos por mês** em servidores na nuvem (o bot consome menos de 30 minutos por mês!).

### Passo 1: Criar o Repositório no GitHub
1. Acesse [github.com/new](https://github.com/new).
2. Nomeie o repositório como `bot-vagas` (pode ser **Privado** ou **Público**).
3. **Não** marque para adicionar README ou .gitignore (já criamos aqui).
4. Clique em **"Create repository"**.

### Passo 2: Subir os Arquivos do seu PC para o GitHub
No PowerShell, dentro da pasta do projeto, execute (substitua pelo link do seu repositório criado):

```powershell
cd C:\Users\Mignac\Desktop\bot-vagas
git remote add origin https://github.com/Luizrocha0/bot-vagas.git
git push -u origin main
```

### Passo 3: Cadastrar os Segredos (Secrets) no GitHub
Como o arquivo `.env` nunca sobe para a internet por segurança, você adiciona as chaves nos **Secrets** do GitHub:

1. No seu repositório no GitHub, clique em **Settings** ⚙️ > **Secrets and variables** > **Actions**.
2. Clique no botão verde **"New repository secret"** e adicione:
   * **`GEMINI_API_KEY`**: Sua chave gerada em [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   * **`WHATSAPP_PHONE`**: `5581985227931`
   * **`WHATSAPP_APIKEY`**: Chave recebida do CallMeBot no WhatsApp
   * *(Opcional)* **`TELEGRAM_BOT_TOKEN`** e **`TELEGRAM_CHAT_ID`**

### Passo 4: Habilitar Permissão de Escrita do Bot
Para o GitHub Actions salvar o histórico de vagas vistas (para nunca mandar vagas repetidas):
1. No seu repositório no GitHub, vá em **Settings** ⚙️ > **Actions** > **General**.
2. Role até a seção **"Workflow permissions"**.
3. Selecione a opção: **"Read and write permissions"**.
4. Clique em **Save**.

---

## ⏰ Quando o Bot Roda na Nuvem?

O arquivo [`.github/workflows/job_hunter.yml`](.github/workflows/job_hunter.yml) está configurado com um agendador (*cron*) para rodar nos servidores do GitHub todos os dias nos seguintes horários de Brasília:
* **09:00 da manhã**
* **14:00 da tarde**
* **19:00 da noite**

> 💡 **Quer testar na hora sem esperar o horário?**  
> No GitHub, acesse a aba **Actions** > selecione **Caçador de Vagas Diário** > clique em **"Run workflow"**. O GitHub iniciará a busca imediatamente e você receberá as vagas no WhatsApp em instantes!
