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
    Compara uma vaga com o perfil do candidato usando a API do Gemini.
    Retorna um dicionário com score de compatibilidade, pontos fortes, lacunas e dicas.
    """
    if client is None:
        client = criar_cliente_gemini()

    perfil = carregar_perfil()

    prompt = f"""
Você é um especialista sênior em Recrutamento Tech e Seleção para desenvolvedores de software.
Sua missão é avaliar minuciosamente a compatibilidade entre o perfil do candidato e a descrição de uma vaga aberta de tecnologia.

---
### DADOS DO CANDIDATO:
Nome: {perfil.get('nome')}
Título: {perfil.get('titulo')}
Localização: {perfil.get('localizacao')}
Formação: {perfil.get('formacao', {}).get('curso')} na {perfil.get('formacao', {}).get('instituicao')} ({perfil.get('formacao', {}).get('previsao_conclusao')})
Resumo: {perfil.get('resumo_profissional')}

Competências Técnicas:
- Front-end: {', '.join(perfil.get('competencias', {}).get('frontend', []))}
- Back-end: {', '.join(perfil.get('competencias', {}).get('backend', []))}
- Linguagens: {', '.join(perfil.get('competencias', {}).get('linguagens', []))}
- Bancos de Dados: {', '.join(perfil.get('competencias', {}).get('bancos_de_dados', []))}
- Dados & IA: {', '.join(perfil.get('competencias', {}).get('dados_e_ia', []))}
- DevOps & Ferramentas: {', '.join(perfil.get('competencias', {}).get('devops_e_ferramentas', []))}

Projetos Relevantes:
{json.dumps(perfil.get('experiencias_e_projetos', []), ensure_ascii=False, indent=2)}

---
### DADOS DA VAGA:
Título da Vaga: {vaga.get('titulo')}
Empresa: {vaga.get('empresa')}
Localização: {vaga.get('localizacao')}
Critérios Adicionais: {json.dumps(vaga.get('criterios', {}), ensure_ascii=False)}

Descrição da Vaga:
\"\"\"
{vaga.get('descricao', '')[:4000]}
\"\"\"

---
### INSTRUÇÕES DE AVALIAÇÃO:
1. Avalie a aderência técnica real (stack principal: Next.js, React, Node.js, Nest.js, TypeScript, Java/Spring Boot, SQL).
2. Avalie o nível de senioridade (o candidato tem perfil forte para Estágio, Júnior ou Pleno com foco em desenvolvimento ágil).
3. Seja honesto e criterioso: não dê notas infladas. O objetivo é ajudar o candidato a focar nas vagas certas.
4. Responda ESTRITAMENTE em formato JSON com o seguinte schema:

{{
  "compatibilidade_percentual": <inteiro de 0 a 100>,
  "classificacao": "<Excelente | Boa | Moderada | Baixa>",
  "resumo_vaga": "<1 a 2 frases claras resumindo o objetivo da vaga e stack principal>",
  "pontos_fortes": [
    "<ponto forte 1 conectando skills do candidato aos requisitos da vaga>",
    "<ponto forte 2>"
  ],
  "requisitos_faltantes": [
    "<tecnologia ou requisito que a vaga exige e o candidato não listou explicitamente>"
  ],
  "dica_candidatura": "<conselho prático de como o candidato deve ajustar o pitch, currículo ou portfólio para esta vaga>",
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
            "resumo_vaga": "Não foi possível analisar a vaga com a IA.",
            "pontos_fortes": [],
            "requisitos_faltantes": [],
            "dica_candidatura": "",
            "vale_a_pena_candidatar": False,
            "erro": str(e)
        }
