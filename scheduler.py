import schedule
import time
import os
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from run import executar_busca

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

HORARIOS = os.getenv("EXECUCAO_HORARIOS", "09:00,14:00,19:00").split(",")
MIN_SCORE = int(os.getenv("MIN_SCORE", "70"))
REMOTE_ONLY = os.getenv("REMOTE_ONLY", "false").lower() == "true"

def job():
    print(f"\n⏰ Executando rotina programada de busca às {time.strftime('%H:%M:%S')}...")
    if REMOTE_ONLY:
        executar_busca(meta_remotas=4, meta_presenciais=0, max_pages_per_term=1)
    else:
        executar_busca(meta_remotas=2, meta_presenciais=2, max_pages_per_term=1)

def iniciar_agendador():
    print("=" * 60)
    print("🤖 SERVIÇO DE MONITORAMENTO DE VAGAS EM SEGUNDO PLANO")
    print(f"Horários configurados para checagem diária: {', '.join(HORARIOS)}")
    print(f"Critério de alerta: Match >= {MIN_SCORE}%")
    print(f"Apenas remoto: {'Sim' if REMOTE_ONLY else 'Não (Remoto + Brasil/Híbrido)'}")
    print("=" * 60)

    for h in HORARIOS:
        h_limpo = h.strip()
        if h_limpo:
            schedule.every().day.at(h_limpo).do(job)
            print(f" -> Agendado para rodar diariamente às {h_limpo}")

    print("\nPressione Ctrl+C para encerrar o monitoramento a qualquer momento.\n")

    # Executa uma vez na inicialização para testar
    job()

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    iniciar_agendador()
