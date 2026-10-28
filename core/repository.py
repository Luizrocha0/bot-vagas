import os
import json
from typing import Set, List, Dict, Any


class JobRepository:
    """
    Repositório de persistência para vagas vistas e histórico de matches avaliados.
    Isola detalhes de I/O em disco do restante da aplicação.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(__file__))
        self.seen_jobs_file = os.path.join(self.base_dir, "vagas_vistas.json")
        self.history_file = os.path.join(self.base_dir, "historico_matches.json")

    def carregar_vagas_vistas(self) -> Set[str]:
        """Carrega conjunto de IDs de vagas já processadas."""
        if os.path.exists(self.seen_jobs_file):
            try:
                with open(self.seen_jobs_file, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    if isinstance(dados, list):
                        return set(str(x) for x in dados)
                    elif isinstance(dados, dict):
                        return set(str(k) for k in dados.keys())
                    return set()
            except Exception:
                return set()
        return set()

    def salvar_vagas_vistas(self, vagas_set: Set[str]) -> None:
        """Salva conjunto de IDs de vagas no arquivo JSON."""
        try:
            with open(self.seen_jobs_file, "w", encoding="utf-8") as f:
                json.dump(list(vagas_set), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Aviso] Falha ao salvar vagas vistas: {e}", flush=True)

    def carregar_historico(self) -> List[Dict[str, Any]]:
        """Carrega a lista histórica de vagas avaliadas."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    return dados if isinstance(dados, list) else []
            except Exception:
                return []
        return []

    def salvar_historico(self, historico: List[Dict[str, Any]]) -> None:
        """Persiste o histórico de matches em disco."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(historico, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Aviso] Falha ao salvar histórico: {e}", flush=True)
