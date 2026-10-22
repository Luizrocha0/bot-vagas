import os
import json
from google import genai
from google.genai import types

def carregar_perfil():
    perfil_path = os.path.join(os.path.dirname(__file__), "perfil_candidato.json")
    with open(perfil_path, "r", encoding="utf-8") as f:
        return json.load(f)

def criar_cliente_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")
    return genai.Client(api_key=api_key)

def analisar_compatibilidade_vaga(vaga, client=None):
    """
    Compara uma vaga com o perfil de Luiz Henrique usando a API do Gemini.
    Foco estrito em Estágio e Júnior no Brasil / Recife.
    """
    if client is None:
        client = criar_cliente_gemini()

    perfil = carregar_perfil()

    prompt = f"""
Você é um recrutador técnico avaliando vagas de tecnologia no Brasil para o estudante Luiz Henrique.

---
### DADOS DO CANDIDATO:
Nome: {perfil.get('nome')}
Local: Olinda / Recife - PE, Brasil.
Objetivo: ESTÁGIO, TRAINEE ou DESENVOLVEDOR JÚNIOR.
Formação: {perfil.get('formacao', {}).get('curso')} na {perfil.get('formacao', {}).get('instituicao')} (Porto Digital - Previsão 2027).
Stack: Next.js, React, TypeScript, Node.js, Nest.js, Fastify, Java 17 / Spring Boot, Tailwind CSS, PostgreSQL, Python.
Modalidades Aceitas:
- 100% Remoto (Brasil)
- Presencial ou Híbrido (apenas em Recife / Olinda / Região Metropolitana de PE)

---
### DADOS DA VAGA:
Título: {vaga.get('titulo')}
Empresa: {vaga.get('empresa')}
Localização: {vaga.get('localizacao')}

Descrição:
\"\"\"
{vaga.get('descricao', '')[:4000]}
\"\"\"

---
### REGRAS:
1. Se a vaga for Sênior, Tech Lead ou exigir mais de 2 anos de experiência: defina score = 10 e "vale_a_pena_candidatar" = false.
2. Se a vaga for presencial fora de PE (ex: presencial em SP ou RJ): defina score = 0 e "vale_a_pena_candidatar" = false.
3. Se for ESTÁGIO ou JÚNIOR (Remoto no Brasil ou presencial em Recife/PE) com React, Node, TypeScript, Java ou desenvolvimento web geral: dê nota ALTA (entre 70% e 95%) e marque "vale_a_pena_candidatar" = true.

Responda ESTRITAMENTE em JSON:
{{
  "compatibilidade_percentual": <inteiro de 0 a 100>,
  "classificacao": "<Excelente | Boa | Moderada | Baixa>",
  "eh_junior_ou_estagio": <true ou false>,
  "atende_localizacao": <true ou false>,
  "resumo_vaga": "<1 a 2 frases>",
  "pontos_fortes": ["<ponto 1>", "<ponto 2>"],
  "requisitos_faltantes": ["<requisito se houver>"],
  "dica_candidatura": "<dica prática para o Luiz>",
  "vale_a_pena_candidatar": <true ou false>
}}
"""

    modelos = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
    ultimo_erro = None

    for mod in modelos:
        try:
            response = client.models.generate_content(
                model=mod,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            return json.loads(response.text)
        except Exception as e:
            ultimo_erro = e
            continue

    print(f"[Erro no Gemini Matcher]: {ultimo_erro}")
    return {
        "compatibilidade_percentual": 0,
        "classificacao": "Erro",
        "eh_junior_ou_estagio": False,
        "atende_localizacao": False,
        "resumo_vaga": "Erro na análise da IA",
        "pontos_fortes": [],
        "requisitos_faltantes": [],
        "dica_candidatura": "",
        "vale_a_pena_candidatar": False,
        "erro": str(ultimo_erro)
    }
