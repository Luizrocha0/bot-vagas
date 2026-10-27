import os
import json
import re
from google import genai
from google.genai import types

def carregar_perfil():
    perfil_path = os.path.join(os.path.dirname(__file__), "perfil_candidato.json")
    if not os.path.exists(perfil_path):
        return {}
    try:
        with open(perfil_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}

def criar_cliente_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")
    return genai.Client(api_key=api_key)

def limpar_json_resposta(texto):
    """
    Remove blocos de formatação markdown (```json ... ```) se presentes na resposta do modelo,
    inclusive quando há texto introdutório, conclusivo ou comentários ao redor do objeto JSON.
    """
    if not texto:
        return ""
    t = str(texto).strip()
    first_brace = t.find("{")
    last_brace = t.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return t[first_brace : last_brace + 1].strip()
    return t


def analisar_compatibilidade_vaga(vaga, client=None):
    """
    Compara uma vaga com o perfil de Luiz Henrique usando a API do Gemini.
    Classifica a vaga estritamente em: Remoto (Brasil) ou Presencial/Híbrido (Recife/PE).
    """
    if client is None:
        client = criar_cliente_gemini()

    perfil = carregar_perfil()
    if not isinstance(perfil, dict):
        perfil = {}

    formacao = perfil.get('formacao') or {}
    curso = formacao.get('curso', 'Tecnologia da Informação') if isinstance(formacao, dict) else 'Tecnologia da Informação'
    instituicao = formacao.get('instituicao', 'CESAR School') if isinstance(formacao, dict) else 'CESAR School'
    nome_candidato = perfil.get('nome') or 'Luiz Henrique'

    descricao_vaga = (vaga.get('descricao') or '')[:4000]
    criterios_vaga = vaga.get('criterios') or {}

    prompt = f"""
Você é um recrutador técnico avaliando vagas de tecnologia para Luiz Henrique.

---
### DADOS DO CANDIDATO:
Nome: {nome_candidato}
Local: Olinda / Recife - PE, Brasil.
Objetivo: ESTÁGIO, TRAINEE ou DESENVOLVEDOR JÚNIOR.
Formação: {curso} na {instituicao} (Porto Digital - Previsão 2027).
Stack Principal: Next.js, React, TypeScript, Node.js, Nest.js, Fastify, Java 17 / Spring Boot, Tailwind CSS, PostgreSQL, Python.

---
### DADOS DA VAGA:
Título: {vaga.get('titulo')}
Empresa: {vaga.get('empresa')}
Localização Declarada: {vaga.get('localizacao')}
Critérios: {json.dumps(criterios_vaga, ensure_ascii=False)}

Descrição:
\"\"\"
{descricao_vaga}
\"\"\"

---
### REGRAS CRÍTICAS:
1. **MODALIDADE E LOCALIZAÇÃO:**
   - Se for 100% Remota (Brasil ou aceitando do Brasil): defina "tipo_modalidade": "REMOTO".
   - Se for Presencial ou Híbrida em Recife, Olinda ou cidades da Região Metropolitana de Pernambuco: defina "tipo_modalidade": "PRESENCIAL_PE".
   - Se for Presencial ou Híbrida FORA de Pernambuco (ex: presencial em SP, RJ, Curitiba, EUA): defina "tipo_modalidade": "INVALIDA", "compatibilidade_percentual": 0 e "vale_a_pena_candidatar": false.
2. **SENIORIDADE:**
   - Se a vaga for Sênior, Tech Lead, Staff ou exigir mais de 2 anos de experiência: defina score = 10 e "vale_a_pena_candidatar": false.
   - Se for ESTÁGIO ou JÚNIOR compatível com a stack (React, Node, TypeScript, Java, Python, web): atribua notas entre 65% e 95% e "vale_a_pena_candidatar": true.

Responda ESTRITAMENTE em formato JSON com o seguinte schema:
{{
  "compatibilidade_percentual": <inteiro de 0 a 100>,
  "classificacao": "<Excelente | Boa | Moderada | Baixa>",
  "tipo_modalidade": "<REMOTO | PRESENCIAL_PE | INVALIDA>",
  "eh_junior_ou_estagio": <true ou false>,
  "resumo_vaga": "<1 a 2 frases claras>",
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
            raw_text = getattr(response, "text", "") or ""
            texto_limpo = limpar_json_resposta(raw_text)
            resultado = json.loads(texto_limpo)
            if not isinstance(resultado, dict):
                raise ValueError("Resposta do modelo não é um objeto JSON válido")

            # Sanitização do score para inteiro seguro [0, 100]
            raw_score = resultado.get("compatibilidade_percentual")
            if isinstance(raw_score, str):
                digits = re.sub(r"[^\d]", "", raw_score)
                score_int = int(digits) if digits else 0
            elif raw_score is not None:
                try:
                    score_int = int(raw_score)
                except (ValueError, TypeError):
                    score_int = 0
            else:
                score_int = 0
            resultado["compatibilidade_percentual"] = max(0, min(100, score_int))

            # Sanitização da modalidade
            mod_val = str(resultado.get("tipo_modalidade") or "INVALIDA").upper().strip()
            if mod_val not in ("REMOTO", "PRESENCIAL_PE", "INVALIDA"):
                mod_val = "INVALIDA"
            resultado["tipo_modalidade"] = mod_val

            # Sanitização de júnior
            raw_junior = resultado.get("eh_junior_ou_estagio")
            if isinstance(raw_junior, str):
                resultado["eh_junior_ou_estagio"] = raw_junior.lower() in ("true", "1", "sim", "yes")
            else:
                resultado["eh_junior_ou_estagio"] = bool(raw_junior)

            # Sanitização de vale_a_pena_candidatar
            raw_vale = resultado.get("vale_a_pena_candidatar")
            if isinstance(raw_vale, str):
                resultado["vale_a_pena_candidatar"] = raw_vale.lower() in ("true", "1", "sim", "yes")
            else:
                resultado["vale_a_pena_candidatar"] = bool(raw_vale) if raw_vale is not None else False

            # Sanitização de listas
            if not isinstance(resultado.get("pontos_fortes"), list):
                pf = resultado.get("pontos_fortes")
                resultado["pontos_fortes"] = [str(pf)] if pf else []
            if not isinstance(resultado.get("requisitos_faltantes"), list):
                rf = resultado.get("requisitos_faltantes")
                resultado["requisitos_faltantes"] = [str(rf)] if rf else []

            return resultado
        except Exception as e:
            ultimo_erro = e
            continue

    print(f"[Erro no Gemini Matcher]: {ultimo_erro}", flush=True)
    return {
        "compatibilidade_percentual": 0,
        "classificacao": "Erro",
        "tipo_modalidade": "INVALIDA",
        "eh_junior_ou_estagio": False,
        "resumo_vaga": "Erro na análise da IA",
        "pontos_fortes": [],
        "requisitos_faltantes": [],
        "dica_candidatura": "",
        "vale_a_pena_candidatar": False,
        "erro": str(ultimo_erro)
    }
