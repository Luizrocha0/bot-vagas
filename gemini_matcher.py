import os
import json
import re
from typing import Dict, Any, Optional
from google import genai
from google.genai import types


def carregar_perfil(caminho: Optional[str] = None) -> Dict[str, Any]:
    """Carrega o perfil estruturado do candidato a partir de perfil_candidato.json ou caminho customizado."""
    perfil_path = caminho or os.getenv("PERFIL_CANDIDATO_PATH") or os.path.join(os.path.dirname(__file__), "perfil_candidato.json")
    if not os.path.exists(perfil_path):
        return {}
    try:
        with open(perfil_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def criar_cliente_gemini() -> genai.Client:
    """Instancia o cliente oficial do Google Gemini via GEMINI_API_KEY."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")
    return genai.Client(api_key=api_key)


def limpar_json_resposta(texto: Optional[str]) -> str:
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


def _extrair_stack_perfil(perfil: Dict[str, Any]) -> str:
    """Extrai uma representação textual das tecnologias do perfil."""
    preferencias = perfil.get("preferencias_busca") or {}
    palavras_chave = preferencias.get("palavras_chave")
    if palavras_chave and isinstance(palavras_chave, list):
        return ", ".join([str(p) for p in palavras_chave])

    competencias = perfil.get("competencias") or {}
    if isinstance(competencias, dict):
        itens = []
        for techs in competencias.values():
            if isinstance(techs, list):
                itens.extend([str(t) for t in techs])
        if itens:
            return ", ".join(itens[:15])

    return "Next.js, React, TypeScript, Node.js, Nest.js, Fastify, Java 17 / Spring Boot, Tailwind CSS, PostgreSQL, Python."


def _gerar_prompt_analise(vaga: Dict[str, Any], perfil: Dict[str, Any]) -> str:
    """Monta o prompt de avaliação técnica alinhado às diretrizes de contratação."""
    formacao = perfil.get('formacao') or {}
    curso = formacao.get('curso', 'Tecnologia da Informação') if isinstance(formacao, dict) else 'Tecnologia da Informação'
    instituicao = formacao.get('instituicao', 'CESAR School') if isinstance(formacao, dict) else 'CESAR School'
    nome_candidato = perfil.get('nome') or 'Luiz Henrique'
    local_candidato = perfil.get('localizacao') or 'Olinda / Recife - PE, Brasil'

    preferencias = perfil.get('preferencias_busca') or {}
    niveis = preferencias.get('niveis')
    if niveis and isinstance(niveis, list):
        objetivo_txt = ", ".join([str(n).upper() for n in niveis])
    else:
        objetivo_txt = "ESTÁGIO, TRAINEE ou DESENVOLVEDOR JÚNIOR"

    stack_formatada = _extrair_stack_perfil(perfil)
    descricao_vaga = (vaga.get('descricao') or '')[:4000]
    criterios_vaga = vaga.get('criterios') or {}

    return f"""
Você é um recrutador técnico avaliando vagas de tecnologia para {nome_candidato}.

---
### DADOS DO CANDIDATO:
Nome: {nome_candidato}
Local: {local_candidato}
Objetivo: {objetivo_txt}
Formação: {curso} na {instituicao}.
Stack Principal: {stack_formatada}

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
   - Se for Presencial ou Híbrida compatível com a região do candidato ({local_candidato} ou Recife, Olinda, Região Metropolitana de Pernambuco / PE): defina "tipo_modalidade": "PRESENCIAL_PE".
   - Se for Presencial ou Híbrida FORA da região de {local_candidato} (ex: presencial em SP, RJ, Curitiba, EUA ou qualquer cidade incompatível): defina "tipo_modalidade": "INVALIDA", "compatibilidade_percentual": 0 e "vale_a_pena_candidatar": false.
2. **SENIORIDADE:**
   - Se a vaga for Sênior, Tech Lead, Staff ou exigir mais de 2 anos de experiência: defina score = 10 e "vale_a_pena_candidatar": false.
   - Se for ESTÁGIO ou JÚNIOR compatível com a stack ({stack_formatada}): atribua notas entre 65% e 95% e "vale_a_pena_candidatar": true.

Responda ESTRITAMENTE em formato JSON com o seguinte schema:
{{
  "compatibilidade_percentual": <inteiro de 0 a 100>,
  "classificacao": "<Excelente | Boa | Moderada | Baixa>",
  "tipo_modalidade": "<REMOTO | PRESENCIAL_PE | INVALIDA>",
  "eh_junior_ou_estagio": <true ou false>,
  "resumo_vaga": "<1 a 2 frases claras>",
  "pontos_fortes": ["<ponto 1>", "<ponto 2>"],
  "requisitos_faltantes": ["<requisito se houver>"],
  "dica_candidatura": "<dica prática para o candidato>",
  "vale_a_pena_candidatar": <true ou false>
}}
"""


def _sanitizar_resposta_gemini(resultado: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitiza e valida os campos retornados pela IA para garantir consistência de tipos."""
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


def analisar_compatibilidade_vaga(
    vaga: Dict[str, Any],
    client: Optional[genai.Client] = None,
    perfil: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compara uma vaga com o perfil do candidato usando a API do Gemini.
    Classifica a vaga estritamente em: Remoto (Brasil) ou Presencial/Híbrido.
    """
    if client is None:
        client = criar_cliente_gemini()

    if perfil is None:
        perfil = carregar_perfil()
    prompt = _gerar_prompt_analise(vaga, perfil)

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

            return _sanitizar_resposta_gemini(resultado)
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
