"""
Script de teste real (Smoke Test) para validar a busca na Gupy ao vivo.
Executa chamadas de rede reais contra portal.gupy.io.
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scrapers.gupy_scraper import GupyScraper


def main():
    print("=" * 60)
    print("🔎 TESTE REAL AO VIVO: GupyScraper (portal.gupy.io)")
    print("=" * 60)

    scraper = GupyScraper()

    # 1. Teste de Vagas Remotas (Brasil)
    print("\n🌐 [1/2] Buscando Vagas Remotas ('React Junior' / 'Desenvolvedor Junior')...")
    vagas_remotas = scraper.buscar_vagas(keywords="Desenvolvedor Junior", remote_only=True, max_pages=1)
    if not vagas_remotas:
        vagas_remotas = scraper.buscar_vagas(keywords="React Junior", remote_only=True, max_pages=1)

    print(f"   Encontradas {len(vagas_remotas)} vagas remotas filtradas.")
    for i, v in enumerate(vagas_remotas[:3], 1):
        print(f"   [{i}] {v['titulo']} @ {v['empresa']} ({v['localizacao']})")
        print(f"       URL: {v['url']}")
        print(f"       Descrição: {v['descricao'][:120]}...\n")

    # 2. Teste de Vagas Locais em Recife/PE
    print("\n📍 [2/2] Buscando Vagas Presenciais / Locais em Recife/PE ('Estagio' / 'Desenvolvedor')...")
    vagas_pe = scraper.buscar_vagas(keywords="Estagio", location="Recife, Pernambuco, Brasil", remote_only=False, max_pages=1)
    if not vagas_pe:
        vagas_pe = scraper.buscar_vagas(keywords="Desenvolvedor", location="Recife, Pernambuco, Brasil", remote_only=False, max_pages=1)

    print(f"   Encontradas {len(vagas_pe)} vagas em Recife/PE.")
    for i, v in enumerate(vagas_pe[:3], 1):
        print(f"   [{i}] {v['titulo']} @ {v['empresa']} ({v['localizacao']})")
        print(f"       URL: {v['url']}")
        print(f"       Descrição: {v['descricao'][:120]}...\n")

    total = len(vagas_remotas) + len(vagas_pe)
    print("=" * 60)
    if total > 0:
        print(f"✅ SUCESSO: GupyScraper funcionando perfeitamente ao vivo! Total coletado: {total}")
        sys.exit(0)
    else:
        print("⚠️ AVISO: Nenhuma vaga retornada na busca imediata.")
        sys.exit(1)


if __name__ == "__main__":
    main()
