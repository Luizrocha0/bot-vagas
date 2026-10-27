import os
import requests
import html
import re

def enviar_notificacao_telegram(vaga, analise):
    """
    Envia uma mensagem formatada com os dados da vaga e o resultado do match via Telegram Bot.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[Aviso] Telegram não configurado no .env.", flush=True)
        return False

    raw_score = analise.get("compatibilidade_percentual")
    if isinstance(raw_score, str):
        digits = re.sub(r"[^\d]", "", raw_score)
        score = int(digits) if digits else 0
    elif raw_score is not None:
        try:
            score = int(raw_score)
        except (ValueError, TypeError):
            score = 0
    else:
        score = 0
    score = max(0, min(100, score))

    classificacao = analise.get("classificacao") or ""
    tipo_modalidade = analise.get("tipo_modalidade") or "REMOTO"
    titulo = html.escape(str(vaga.get("titulo") or "Vaga Sem Título"))
    empresa = html.escape(str(vaga.get("empresa") or "Empresa Confidencial"))
    localizacao = html.escape(str(vaga.get("localizacao") or "Não informada"))
    url = vaga.get("url") or ""
    url_escaped = html.escape(str(url), quote=True)
    resumo = html.escape(str(analise.get("resumo_vaga") or ""))
    dica = html.escape(str(analise.get("dica_candidatura") or ""))

    badge_modalidade = "🌐 <b>100% REMOTO (BRASIL)</b>" if tipo_modalidade == "REMOTO" else "📍 <b>LOCAL (RECIFE / OLINDA - PE)</b>"
    emoji_score = "🔥" if score >= 80 else "⭐" if score >= 65 else "📌"

    lista_pontos = analise.get("pontos_fortes") or []
    if isinstance(lista_pontos, str):
        lista_pontos = [lista_pontos]
    elif not isinstance(lista_pontos, list):
        lista_pontos = []

    lista_gaps = analise.get("requisitos_faltantes") or []
    if isinstance(lista_gaps, str):
        lista_gaps = [lista_gaps]
    elif not isinstance(lista_gaps, list):
        lista_gaps = []

    pontos_fortes = "\n".join([f"  • {html.escape(str(p))}" for p in lista_pontos if p])
    gaps = "\n".join([f"  • {html.escape(str(g))}" for g in lista_gaps if g])

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
🔗 <a href="{url_escaped}">Acessar Vaga no LinkedIn</a>
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
