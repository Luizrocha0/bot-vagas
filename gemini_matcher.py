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
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada. Configure-a no arquivo .env.")
    return genai.Client(api_key=api_key)

def analisar_compatibilidade_vaga(vaga, client=None):
    """
    Compara uma vaga com o perfil do candidato usando a API do Gemini com foco em Estágio e Júnior.
    """
    if client is None:
        client = criar_cliente_gemini()

    perfil = carregar_perfil()

    prompt = f"""
Você é um recrutador técnico sênior especializado em vagas para DESENVOLVEDORES EM INÍCIO DE CARREIRA (ESTÁGIO E JÚNIOR).
Sua missão é avaliar a compatibilidade entre o perfil de Luiz Henrique e a vaga aberta.

---
### PERFIL DO CANDIDATO:
Nome: {perfil.get('nome')}
Objetivo: Vagas de ESTÁGIO, TRAINEE ou DESENVOLVEDOR JÚNIOR / ASSOCIATE.
Formação: {perfil.get('formacao', {}).get('curso')} na {perfil.get('formacao', {}).get('instituicao')} ({perfil.get('formacao', {}).get('previsao_conclusao')}).
Stack Principal: Next.js, React, TypeScript, Node.js, Nest.js, Fastify, Java 17 / Spring Boot, Tailwind CSS, PostgreSQL.
Projetos Práticos: Landing Page comercial (SSR/SEO), Plataforma de Apostas (Fastify + IA), Pipeline Cloud (Databricks/PySpark), Arena PE (Spring Boot + React + JWT).

---
### DADOS DA VAGA:
Título: {vaga.get('titulo')}
Empresa: {vaga.get('empresa')}
Localização: {vaga.get('localizacao')}
Critérios: {json.dumps(vaga.get('criterios', {}), ensure_ascii=False)}

Descrição:
\"\"\"
{vaga.get('descricao', '')[:4000]}
\"\"\"

---
### REGRAS CRÍTICAS DE AVALIAÇÃO:
1. **SENIORIDADE:**
   - Se a descrição da vaga exigir mais de 2 a 3 anos de experiência prévia, ou for claramente voltada para Pleno avançado / Sênior / Especialista, atribua "compatibilidade_percentual": 15 e "vale_a_pena_candidatar": false.
   - Se a vaga for de **ESTÁGIO**, **TRAINEE**, **JÚNIOR**, **ASSOCIATE** ou **ENTRY LEVEL**, dê prioridade máxima!
2. **STACK TÉCNICA:**
   - Se for uma vaga de Estágio ou Júnior pedindo React, Next.js, TypeScript, JavaScript, Node.js, Spring Boot, Python ou desenvolvimento web geral, atribua nota ALTA (entre 70% e 95%) e marque "vale_a_pena_candidatar": true.
3. Responda ESTRITAMENTE em formato JSON com o seguinte schema:

{{
  "compatibilidade_percentual": <inteiro de 0 a 100>,
  "classificacao": "<Excelente | Boa | Moderada | Baixa>",
  "eh_junior_ou_estagio": <true ou false>,
  "resumo_vaga": "<1 a 2 frases claras resumindo o objetivo da vaga e stack principal>",
  "pontos_fortes": [
    "<ponto forte conectando skills do Luiz aos requisitos da vaga>",
    "<ponto forte 2>"
  ],
  "requisitos_faltantes": [
    "<tecnologia ou requisito que a vaga cita e ele pode aprimorar>"
  ],
  "dica_candidatura": "<conselho prático de pitch para o Luiz destacar no currículo ou entrevista>",
  "vale_a_pena_candidatar": <true ou false>
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        resultado = json.loads(response.text)
        return resultado
    except Exception as e:
        print(f"[Erro no Gemini Matcher]: {e}")
        return {
            "compatibilidade_percentual": 0,
            "classificacao": "Erro",
            "eh_junior_ou_estagio": False,
            "resumo_vaga": "Não foi possível analisar a vaga com a IA.",
            "pontos_fortes": [],
            "requisitos_faltantes": [],
            "dica_candidatura": "",
            "vale_a_pena_candidatar": False,
            "erro": str(e)
        }
