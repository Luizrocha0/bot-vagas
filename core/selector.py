from typing import List, Dict, Any, Tuple


class QuotaSelector:
    """
    Serviço de domínio responsável por aplicar as regras de negócio de cotas:
    - Alocação da meta de vagas remotas
    - Alocação da meta de vagas presenciais/híbridas em Recife/PE
    - Complementação inteligente quando há déficit em alguma das modalidades
    """

    def __init__(self, meta_remotas: int = 2, meta_presenciais: int = 2):
        self.meta_remotas = max(0, meta_remotas)
        self.meta_presenciais = max(0, meta_presenciais)

    def selecionar_top_vagas(
        self,
        candidatas_remotas: List[Dict[str, Any]],
        candidatas_presenciais: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Ordena os candidatos por pontuação e aplica as cotas e complementações.
        """
        # Garante ordenação decrescente por score
        remotas_ordenadas = sorted(candidatas_remotas, key=lambda x: x.get("score", 0), reverse=True)
        presenciais_ordenadas = sorted(candidatas_presenciais, key=lambda x: x.get("score", 0), reverse=True)

        # 1. Aloca cotas primárias
        selecionadas_remotas = remotas_ordenadas[:self.meta_remotas]
        selecionadas_presenciais = presenciais_ordenadas[:self.meta_presenciais]

        sobra_remotas = remotas_ordenadas[self.meta_remotas:]
        sobra_presenciais = presenciais_ordenadas[self.meta_presenciais:]

        # 2. Se faltar presencial e meta_presenciais > 0, complementa com remotas
        if len(selecionadas_presenciais) < self.meta_presenciais and self.meta_presenciais > 0:
            deficit_presenciais = self.meta_presenciais - len(selecionadas_presenciais)
            complemento_remoto = sobra_remotas[:deficit_presenciais]
            selecionadas_remotas.extend(complemento_remoto)
            sobra_remotas = sobra_remotas[deficit_presenciais:]

        # 3. Se faltar remota e meta_remotas > 0 e meta_presenciais > 0, complementa com presenciais
        if len(selecionadas_remotas) < self.meta_remotas and self.meta_remotas > 0 and self.meta_presenciais > 0:
            deficit_remotas = self.meta_remotas - len(selecionadas_remotas)
            complemento_presencial = sobra_presenciais[:deficit_remotas]
            selecionadas_presenciais.extend(complemento_presencial)
            sobra_presenciais = sobra_presenciais[deficit_remotas:]

        return selecionadas_remotas + selecionadas_presenciais
