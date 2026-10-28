#!/usr/bin/env python3
"""
Assistente de Onboarding e Validação do Caçador de Vagas.
Permite que qualquer pessoa configure seu próprio ambiente, cadastre seu currículo
e use sua própria chave gratuita da Gemini API (Google AI Studio).
"""

import os
import sys
import json
import shutil
import argparse
from typing import Dict, Any, Tuple, Optional
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
PERFIL_PATH = os.path.join(BASE_DIR, "perfil_candidato.json")
EXAMPLE_PERFIL_PATH = os.path.join(BASE_DIR, "perfil_candidato.example.json")

load_dotenv(ENV_PATH)


def verificar_ambiente() -> Dict[str, Any]:
    """Valida a saúde do ambiente Python, dependências, arquivos e variáveis de ambiente."""
    resultado = {
        "python_valido": sys.version_info >= (3, 10),
        "python_versao": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "dependencias": {},
        "env_existe": os.path.exists(ENV_PATH),
        "perfil_existe": os.path.exists(PERFIL_PATH),
        "gemini_configurado": bool(os.getenv("GEMINI_API_KEY")),
        "telegram_configurado": bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")),
        "whatsapp_configurado": bool(os.getenv("WHATSAPP_PHONE_NUMBER_ID") and os.getenv("WHATSAPP_ACCESS_TOKEN")),
    }

    pacotes_obrigatorios = ["google.genai", "dotenv", "bs4", "requests"]
    for pacote in pacotes_obrigatorios:
        try:
            __import__(pacote)
            resultado["dependencias"][pacote] = True
        except ImportError:
            resultado["dependencias"][pacote] = False

    return resultado


def validar_chave_gemini(api_key: str) -> Tuple[bool, str]:
    """Testa se uma chave da API do Gemini é válida no Google AI Studio."""
    if not api_key or not api_key.strip():
        return False, "Chave de API não informada."

    chave_limpa = api_key.strip()
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=chave_limpa)
        # Teste leve com gemini-3.1-flash-lite
        resposta = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents="Responda estritamente 'OK'",
            config=types.GenerateContentConfig(temperature=0.1)
        )
        texto = getattr(resposta, "text", "") or ""
        if "OK" in texto.upper():
            return True, "Chave validada com sucesso! Conexão com Gemini funcionando."
        return True, f"Chave aceita pela API (resposta: {texto.strip()})."
    except Exception as e:
        return False, f"Falha ao validar chave no Gemini: {str(e)}"


def salvar_env(chaves: Dict[str, str], caminho_env: str = ENV_PATH) -> bool:
    """Atualiza ou adiciona variáveis no arquivo .env sem apagar as variáveis existentes."""
    try:
        dados_existentes = {}
        if os.path.exists(caminho_env):
            with open(caminho_env, "r", encoding="utf-8") as f:
                for line in f:
                    linha = line.strip()
                    if linha and not linha.startswith("#") and "=" in linha:
                        k, v = linha.split("=", 1)
                        dados_existentes[k.strip()] = v.strip()

        # Atualiza com as novas chaves
        for k, v in chaves.items():
            if v is not None and v.strip() != "":
                dados_existentes[k.strip()] = v.strip()

        linhas_salvar = [
            "# Configurações do Caçador de Vagas",
            "# Gerado automaticamente pelo assistente setup.py",
            ""
        ]
        for k, v in dados_existentes.items():
            linhas_salvar.append(f"{k}={v}")

        with open(caminho_env, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas_salvar) + "\n")
        return True
    except Exception as e:
        print(f"[Erro ao salvar .env]: {e}")
        return False


def inicializar_perfil_candidato(
    destino: str = PERFIL_PATH,
    origem_template: str = EXAMPLE_PERFIL_PATH,
    dados_basicos: Optional[Dict[str, Any]] = None
) -> bool:
    """Cria um perfil_candidato.json com dados customizados a partir do template."""
    try:
        if not os.path.exists(origem_template):
            print(f"[Erro]: Template {origem_template} não foi encontrado.")
            return False

        with open(origem_template, "r", encoding="utf-8") as f:
            conteudo = json.load(f)

        if dados_basicos:
            if "nome" in dados_basicos and dados_basicos["nome"]:
                conteudo["nome"] = dados_basicos["nome"]
            if "localizacao" in dados_basicos and dados_basicos["localizacao"]:
                conteudo["localizacao"] = dados_basicos["localizacao"]
            if "titulo" in dados_basicos and dados_basicos["titulo"]:
                conteudo["titulo"] = dados_basicos["titulo"]
            if "cargos_alvo" in dados_basicos and dados_basicos["cargos_alvo"]:
                cargos = [c.strip() for c in dados_basicos["cargos_alvo"].split(",") if c.strip()]
                conteudo["preferencias_busca"]["cargos_alvo"] = cargos
            if "stack" in dados_basicos and dados_basicos["stack"]:
                stack_list = [s.strip() for s in dados_basicos["stack"].split(",") if s.strip()]
                conteudo["preferencias_busca"]["palavras_chave"] = stack_list

        with open(destino, "w", encoding="utf-8") as f:
            json.dump(conteudo, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Erro ao inicializar perfil]: {e}")
        return False


def executar_check():
    """Executa a verificação completa de saúde do ambiente e imprime o diagnóstico."""
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DO AMBIENTE (Caçador de Vagas)")
    print("=" * 60)

    diag = verificar_ambiente()
    print(f"🐍 Python {diag['python_versao']}: {'✅ OK' if diag['python_valido'] else '❌ Requer Python 3.10+'}")

    print("\n📦 Dependências:")
    for pacote, instalado in diag["dependencias"].items():
        print(f"  - {pacote}: {'✅ Instalado' if instalado else '❌ Não instalado (execute pip install -r requirements.txt)'}")

    print("\n📄 Arquivos de Configuração:")
    print(f"  - .env: {'✅ Presente' if diag['env_existe'] else '⚠️ Ausente (execute python setup.py)'}")
    print(f"  - perfil_candidato.json: {'✅ Configurado' if diag['perfil_existe'] else '⚠️ Ausente (execute python setup.py)'}")

    print("\n🔑 Serviços e Notificações:")
    print(f"  - Google Gemini API: {'✅ Configurada' if diag['gemini_configurado'] else '❌ GEMINI_API_KEY não definida'}")
    print(f"  - Telegram Notifier: {'✅ Configurado' if diag['telegram_configurado'] else '⚪ Não configurado (opcional)'}")
    print(f"  - WhatsApp Notifier: {'✅ Configurado' if diag['whatsapp_configurado'] else '⚪ Não configurado (opcional)'}")
    print("=" * 60)


def executar_teste_ia():
    """Testa a IA do Gemini usando a GEMINI_API_KEY configurada no .env."""
    load_dotenv(ENV_PATH, override=True)
    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        print("❌ GEMINI_API_KEY não encontrada no arquivo .env ou no sistema.")
        print("💡 Obtenha uma chave gratuita em: https://aistudio.google.com/app/apikey")
        return False

    print("🤖 Testando comunicação com a IA do Google Gemini...")
    sucesso, msg = validar_chave_gemini(chave)
    if sucesso:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")
    return sucesso


def executar_wizard_interativo():
    """Assistente CLI passo a passo amigável para onboarding de novos usuários."""
    print("=" * 65)
    print("🧙 BEM-VINDO AO ASSISTENTE DE ONBOARDING - CAÇADOR DE VAGAS")
    print("=" * 65)
    print("Configure seu robô de vagas em 3 minutos!")
    print("Ele usará a sua própria chave GRATUITA da Gemini API.")
    print("=" * 65)

    novas_envs = {}

    # 1. Chave Gemini API
    load_dotenv(ENV_PATH, override=True)
    chave_atual = os.getenv("GEMINI_API_KEY", "")
    print("\n[Etapa 1/3] Chave da API do Google Gemini (IA)")
    print("O bot precisa da API Gemini para analisar a compatibilidade do seu currículo.")
    print("👉 Crie sua chave gratuita em: https://aistudio.google.com/app/apikey")

    if chave_atual:
        mascarada = chave_atual[:6] + "..." + chave_atual[-4:] if len(chave_atual) > 10 else "******"
        usar_atual = input(f"Chave já encontrada ({mascarada}). Deseja manter? (S/n): ").strip().lower()
        if usar_atual == "n":
            chave_atual = ""

    if not chave_atual:
        while True:
            chave_digitada = input("Cole sua GEMINI_API_KEY: ").strip()
            if not chave_digitada:
                print("⚠️ A chave é obrigatória para a IA avaliar suas vagas.")
                continue
            print("⏳ Validando chave junto ao Google AI Studio...")
            valida, msg = validar_chave_gemini(chave_digitada)
            if valida:
                print(f"✅ {msg}")
                novas_envs["GEMINI_API_KEY"] = chave_digitada
                break
            else:
                print(f"❌ {msg}")
                tentar_novamente = input("Deseja tentar outra chave? (S/n): ").strip().lower()
                if tentar_novamente == "n":
                    novas_envs["GEMINI_API_KEY"] = chave_digitada
                    break
    else:
        novas_envs["GEMINI_API_KEY"] = chave_atual

    # 2. Telegram Notifier (Opcional)
    print("\n[Etapa 2/3] Alertas no Telegram (Recomendado)")
    print("O bot envia as melhores vagas direto no seu Telegram pessoal.")
    configurar_tel = input("Deseja configurar alertas no Telegram agora? (S/n): ").strip().lower()
    if configurar_tel != "n":
        print("\nPara configurar o Telegram:")
        print(" 1. Abra o Telegram e procure por @BotFather")
        print(" 2. Envie /newbot e siga as instruções para obter o HTTP API TOKEN")
        print(" 3. Envie uma mensagem qualquer para o seu bot criado")
        print(" 4. Abra o bot @userinfobot no Telegram para descobrir seu ID numérico")
        tel_token = input("Cole o TELEGRAM_BOT_TOKEN: ").strip()
        tel_chat_id = input("Cole o seu TELEGRAM_CHAT_ID: ").strip()
        if tel_token and tel_chat_id:
            novas_envs["TELEGRAM_BOT_TOKEN"] = tel_token
            novas_envs["TELEGRAM_CHAT_ID"] = tel_chat_id
            print("✅ Dados do Telegram registrados.")
    else:
        print("⚪ Configuração do Telegram pulada (você pode configurar depois no .env).")

    # Salva .env
    salvar_env(novas_envs)
    print("\n💾 Arquivo .env atualizado com sucesso!")

    # 3. Perfil do Candidato (perfil_candidato.json)
    print("\n[Etapa 3/3] Cadastro do Seu Currículo e Preferências")
    perfil_existe = os.path.exists(PERFIL_PATH)
    if perfil_existe:
        try:
            with open(PERFIL_PATH, "r", encoding="utf-8") as f:
                perfil_atual = json.load(f)
            nome_cadastrado = perfil_atual.get("nome", "Desconhecido")
        except Exception:
            nome_cadastrado = "Existente"
        print(f"Já existe um perfil cadastrado para: {nome_cadastrado}")
        recriar = input("Deseja sobrescrever com seu próprio currículo agora? (s/N): ").strip().lower()
        deve_criar_cv = (recriar == "s")
    else:
        deve_criar_cv = True

    if deve_criar_cv:
        print("\nVamos preencher seus dados básicos para a IA:")
        nome = input("Seu Nome Completo: ").strip()
        localizacao = input("Sua Cidade e Estado (ex: São Paulo, SP - Brasil): ").strip()
        cargos = input("Cargos Alvo separados por vírgula (ex: Desenvolvedor Junior, Estágio TI): ").strip()
        stack = input("Principais Tecnologias separadas por vírgula (ex: React, Node.js, TypeScript): ").strip()

        dados = {
            "nome": nome,
            "localizacao": localizacao,
            "titulo": f"Desenvolvedor(a) Júnior | {stack}" if stack else "Desenvolvedor(a) Júnior",
            "cargos_alvo": cargos,
            "stack": stack
        }

        if inicializar_perfil_candidato(PERFIL_PATH, EXAMPLE_PERFIL_PATH, dados):
            print(f"✅ Arquivo {PERFIL_PATH} criado com sucesso!")
            print(f"💡 Dica: Você pode abrir e editar o arquivo perfil_candidato.json a qualquer momento para enriquecer sua formação e projetos!")
    else:
        print(f"⚪ Perfil mantido em: {PERFIL_PATH}")

    print("\n" + "=" * 65)
    print("🎉 PARABÉNS! CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 65)
    print("Para buscar suas vagas agora, basta executar:")
    print("  python run.py")
    print("\nPara agendar buscas diárias automáticas:")
    print("  python scheduler.py")
    print("=" * 65)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Assistente de Onboarding e Setup do Caçador de Vagas")
    parser.add_argument("--check", action="store_true", help="Executa diagnóstico de saúde do ambiente")
    parser.add_argument("--test", action="store_true", help="Valida a chave da API Gemini e conexão com a IA")
    parser.add_argument("--init-cv", action="store_true", help="Copia perfil_candidato.example.json para perfil_candidato.json")

    args = parser.parse_args(argv)

    if args.check:
        executar_check()
        return 0

    if args.test:
        sucesso = executar_teste_ia()
        return 0 if sucesso else 1

    if args.init_cv:
        sucesso = inicializar_perfil_candidato()
        print(f"[{'SUCESSO' if sucesso else 'ERRO'}] Perfil inicializado a partir do template.")
        return 0 if sucesso else 1

    executar_wizard_interativo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
