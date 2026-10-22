import os
import requests
import urllib.parse

def formatar_mensagem_whatsapp(vaga, analise):
    score = analise.get("compatibilidade_percentual", 0)
    classificacao = analise.get("classificacao", "")
    titulo = vaga.get("titulo", "Vaga Sem Título")
    empresa = vaga.get("empresa", "Empresa Confidencial")
    localizacao = vaga.get("localizacao", "Não informada")
    url = vaga.get("url", "")
    resumo = analise.get("resumo_vaga", "")
    dica = analise.get("dica_candidatura", "")

    emoji_score = "🔥" if score >= 80 else "⭐" if score >= 70 else "📌"

    pontos_fortes = "\n".join([f"  • {p}" for p in analise.get("pontos_fortes", [])])
    gaps = "\n".join([f"  • {g}" for g in analise.get("requisitos_faltantes", [])])

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
