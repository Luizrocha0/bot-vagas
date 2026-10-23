import os
import requests
import html

def enviar_notificacao_telegram(vaga, analise):
    """
    Envia uma mensagem formatada com os dados da vaga e o resultado do match via Telegram Bot.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[Aviso] Telegram não configurado no .env.", flush=True)
        return False

    score = analise.get("compatibilidade_percentual", 0)
    classificacao = analise.get("classificacao", "")
    tipo_modalidade = analise.get("tipo_modalidade", "REMOTO")
    titulo = html.escape(vaga.get("titulo", "Vaga Sem Título"))
    empresa = html.escape(vaga.get("empresa", "Empresa Confidencial"))
    localizacao = html.escape(vaga.get("localizacao", "Não informada"))
    url = vaga.get("url", "")
    resumo = html.escape(analise.get("resumo_vaga", ""))
    dica = html.escape(analise.get("dica_candidatura", ""))

    badge_modalidade = "🌐 <b>100% REMOTO (BRASIL)</b>" if tipo_modalidade == "REMOTO" else "📍 <b>LOCAL (RECIFE / OLINDA - PE)</b>"
    emoji_score = "🔥" if score >= 80 else "⭐" if score >= 65 else "📌"

    pontos_fortes = "\n".join([f"  • {html.escape(p)}" for p in analise.get("pontos_fortes", [])])
    gaps = "\n".join([f"  • {html.escape(g)}" for g in analise.get("requisitos_faltantes", [])])

    msg = f"""{emoji_score} <b>Match Encontrado: {score}% ({classificacao})</b>
{badge_modalidade}

💼 <b>{titulo}</b>
🏢 <b>Empresa:</b> {empresa}
📍 <b>Local:</b> {localizacao}

📝 <b>Resumo:</b>
{resumo}

✅ <b>Pontos Fortes no seu Perfil:</b>
{pontos_fortes if pontos_fortes else "  • Compatibilidade com stack geral."}
"""

    if gaps:
        msg += f"""
⚠️ <b>Requisitos Faltantes / Atenção:</b>
{gaps}
"""

    if dica:
        msg += f"""
💡 <b>Dica do Gemini para Candidatura:</b>
{dica}
"""

    msg += f"""
🔗 <a href="{url}">Acessar Vaga no LinkedIn</a>
"""

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[Telegram] Notificação enviada para: {vaga.get('titulo')}", flush=True)
            return True
        else:
            print(f"[Erro Telegram] Falha no envio: {resp.text}", flush=True)
            return False
    except Exception as e:
        print(f"[Erro Telegram]: {e}", flush=True)
        return False


def testar_conexao_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return False, "Credenciais ausentes no arquivo .env"

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🤖 <b>Bot de Vagas Conectado com Sucesso!</b>\nVocê receberá alertas aqui sempre que novas vagas compatíveis forem encontradas.",
        "parse_mode": "HTML"
    }

    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        if resp.status_code == 200:
            return True, "Mensagem de teste enviada com sucesso ao Telegram!"
        else:
            return False, f"Falha na API do Telegram: {resp.text}"
    except Exception as e:
        return False, str(e)
