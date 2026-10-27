import os
import requests
import urllib.parse
import re

def formatar_mensagem_whatsapp(vaga, analise):
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
    titulo = str(vaga.get("titulo") or "Vaga Sem Título")
    empresa = str(vaga.get("empresa") or "Empresa Confidencial")
    localizacao = str(vaga.get("localizacao") or "Não informada")
    url = str(vaga.get("url") or "")
    resumo = str(analise.get("resumo_vaga") or "")
    dica = str(analise.get("dica_candidatura") or "")

    emoji_score = "🔥" if score >= 80 else "⭐" if score >= 70 else "📌"

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

    pontos_fortes = "\n".join([f"  • {p}" for p in lista_pontos if p])
    gaps = "\n".join([f"  • {g}" for g in lista_gaps if g])

    msg = f"{emoji_score} *Match Encontrado: {score}% ({classificacao})*\n\n"
    msg += f"💼 *Cargo:* {titulo}\n"
    msg += f"🏢 *Empresa:* {empresa}\n"
    msg += f"📍 *Local:* {localizacao}\n\n"

    if resumo:
        msg += f"📝 *Resumo:*\n{resumo}\n\n"

    if pontos_fortes:
        msg += f"✅ *Pontos Fortes no seu Perfil:*\n{pontos_fortes}\n\n"

    if gaps:
        msg += f"⚠️ *Atenção / Requisitos a Revisar:*\n{gaps}\n\n"

    if dica:
        msg += f"💡 *Dica do Gemini para Candidatura:*\n{dica}\n\n"

    msg += f"🔗 *Acessar Vaga no LinkedIn:*\n{url}"

    return msg


def enviar_notificacao_whatsapp(vaga, analise):
    """
    Envia a mensagem de alerta para o WhatsApp configurado via CallMeBot API (gratuita).
    """
    phone = os.getenv("WHATSAPP_PHONE", "").replace("+", "").replace(" ", "").replace("-", "")
    apikey = os.getenv("WHATSAPP_APIKEY", "")

    if not phone or not apikey:
        print("[Aviso] WhatsApp não configurado (WHATSAPP_PHONE ou WHATSAPP_APIKEY ausente no .env).")
        return False

    texto = formatar_mensagem_whatsapp(vaga, analise)
    texto_encoded = urllib.parse.quote(texto)

    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={texto_encoded}&apikey={apikey}"

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200 and "error" not in resp.text.lower():
            print(f"[WhatsApp] Notificação enviada com sucesso para: {vaga.get('titulo')}")
            return True
        else:
            print(f"[Erro WhatsApp] Resposta do gateway: {resp.text}")
            return False
    except Exception as e:
        print(f"[Erro WhatsApp]: {e}")
        return False


def testar_conexao_whatsapp():
    """
    Envia uma mensagem de teste para verificar se o WhatsApp está recebendo notificações.
    """
    phone = os.getenv("WHATSAPP_PHONE", "").replace("+", "").replace(" ", "").replace("-", "")
    apikey = os.getenv("WHATSAPP_APIKEY", "")

    if not phone or not apikey:
        return False, "WHATSAPP_PHONE ou WHATSAPP_APIKEY não configurados no .env"

    msg = "🤖 *Bot de Vagas Conectado ao WhatsApp!* \nVocê receberá alertas diários de vagas compatíveis diretamente por aqui."
    texto_encoded = urllib.parse.quote(msg)

    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={texto_encoded}&apikey={apikey}"

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200 and "error" not in resp.text.lower():
            return True, "Mensagem de teste enviada com sucesso para o seu WhatsApp!"
        else:
            return False, f"Falha na resposta do WhatsApp API: {resp.text}"
    except Exception as e:
        return False, str(e)
