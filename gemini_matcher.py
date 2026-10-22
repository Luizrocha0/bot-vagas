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
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada. Configure-a no arquivo .env ou nos Secrets.")
    return genai.Client(api_key=api_key)

def analisar_compatibilidade_vaga(vaga, client=None):
    """
    Compara uma vaga com o perfil de Luiz Henrique usando a API do Gemini 3.8 Flash.
    Foco em Estágio e Júnior, no Brasil (Remoto ou Recife/Olinda/PE).
    """
    if client is None:
        client = criar_cliente_gemini()

    perfil = carregar_perfil()

    prompt = f"""
Você é um recrutador técnico sênior especializado no mercado de tecnologia do Brasil, focado em desenvolvedores em início de carreira.
Avalie a compatibilidade entre o candidato Luiz Henrique e a vaga aberta descrita abaixo.

---
### PERFIL DO CANDIDATO:
Nome: {perfil.get('nome')}
Localização Atual: Olinda / Recife - PE, Brasil.
Objetivo: Vagas de ESTÁGIO, TRAINEE ou DESENVOLVEDOR JÚNIOR.
Formação: {perfil.get('formacao', {}).get('curso')} na {perfil.get('formacao', {}).get('instituicao')} (Porto Digital - Previsão 2027).
Stack Principal: Next.js, React, TypeScript, Node.js, Nest.js, Fastify, Java 17 / Spring Boot, Tailwind CSS, PostgreSQL, Python.
Modalidades Aceitas:
- 100% Remoto (qualquer lugar do Brasil)
- Híbrido ou Presencial (apenas em Recife / Olinda / Região Metropolitana de PE)

---
### DADOS DA VAGA:
Título: {vaga.get('titulo')}
Empresa: {vaga.get('empresa')}
Localização Declarada: {vaga.get('localizacao')}
Critérios: {json.dumps(vaga.get('criterios', {}), ensure_ascii=False)}

Descrição:
\"\"\"
{vaga.get('descricao', '')[:4000]}
\"\"\"

---
### REGRAS CRÍTICAS DE AVALIAÇÃO:
1. **LOCALIZAÇÃO E MODALIDADE:**
   - Se for vaga PRESENCIAL ou HÍBRIDA fora de Pernambuco (ex: presencial em São Paulo, Curitiba, exterior), descarte: "compatibilidade_percentual": 0, "vale_a_pena_candidatar": false.
   - Vagas 100% REMOTAS no Brasil ou presenciais/híbridas em Recife/Olinda/PE são VÁLIDAS.
2. **SENIORIDADE:**
   - Se a vaga exigir mais de 2 anos de experiência ou for voltada para Pleno/Sênior/Lead/Staff, descarte: "compatibilidade_percentual": 10, "vale_a_pena_candidatar": false.
   - Se a vaga for de ESTÁGIO, TRAINEE ou JÚNIOR, priorize com notas entre 70% e 95%!
3. **STACK:**
   - Se envolver React, Next.js, Node.js, TypeScript, Spring Boot, Java, Python ou desenvolvimento web geral em nível Júnior/Estágio, dê nota ALTA.

Responda ESTRITAMENTE em formato JSON com o seguinte schema:
{{
  "compatibilidade_percentual": <inteiro de 0 a 100>,
  "classificacao": "<Excelente | Boa | Moderada | Baixa>",
  "eh_junior_ou_estagio": <true ou false>,
  "atende_localizacao": <true ou false>,
  "resumo_vaga": "<1 a 2 frases claras resumindo o objetivo da vaga e modalidade/stack>",
  "pontos_fortes": [
    "<ponto forte conectando skills do Luiz aos requisitos da vaga>",
    "<ponto forte 2>"
  ],
  "requisitos_faltantes": [
    "<tecnologia ou requisito que ele pode aprimorar>"
  ],
  "dica_candidatura": "<conselho prático de pitch para o Luiz>",
  "vale_a_pena_candidatar": <true ou false>
}}
"""

    modelos = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
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
            resultado = json.loads(response.text)
            return resultado
        except Exception as e:
            ultimo_erro = e
            continue

    print(f"[Erro no Gemini Matcher]: {ultimo_erro}")
    return {
        "compatibilidade_percentual": 0,
        "classificacao": "Erro",
        "eh_junior_ou_estagio": False,
        "atende_localizacao": False,
        "resumo_vaga": "Não foi possível analisar a vaga com a IA.",
        "pontos_fortes": [],
        "requisitos_faltantes": [],
        "dica_candidatura": "",
        "vale_a_pena_candidatar": False,
        "erro": str(ultimo_erro)
    }
