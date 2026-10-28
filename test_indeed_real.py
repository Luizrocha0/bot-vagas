"""
Script de teste real (Smoke Test) para validar a busca no IndeedScraper ao vivo.
Tenta Indeed direto e utiliza o agregador tech brasileiro caso haja proteção Cloudflare.
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scrapers.indeed_scraper import IndeedScraper


def main():
    print("=" * 60)
    print("🔎 TESTE REAL AO VIVO: IndeedScraper / Agregador Tech Brasil")
    print("=" * 60)

    scraper = IndeedScraper()

    # 1. Teste de Vagas Remotas (Brasil)
    print("\n🌐 [1/2] Buscando Vagas Remotas ('Junior' / 'React')...")
    vagas_remotas = scraper.buscar_vagas(keywords="Junior", remote_only=True, max_pages=1)
    if not vagas_remotas:
        vagas_remotas = scraper.buscar_vagas(keywords="React", remote_only=True, max_pages=1)

    print(f"   Encontradas {len(vagas_remotas)} vagas remotas filtradas.")
    for i, v in enumerate(vagas_remotas[:3], 1):
        print(f"   [{i}] {v['titulo']} @ {v['empresa']} ({v['localizacao']})")
        print(f"       Fonte: {v['fonte']}")
        print(f"       URL: {v['url']}")
        print(f"       Descrição: {v['descricao'][:120]}...\n")

    # 2. Teste de Vagas Locais em Recife/PE
    print("\n📍 [2/2] Buscando Vagas Locais ('Desenvolvedor' / 'Estagio')...")
    vagas_pe = scraper.buscar_vagas(keywords="Desenvolvedor", location="Recife, Pernambuco, Brasil", remote_only=False, max_pages=1)
    print(f"   Encontradas {len(vagas_pe)} vagas em Recife/PE.")
    for i, v in enumerate(vagas_pe[:3], 1):
        print(f"   [{i}] {v['titulo']} @ {v['empresa']} ({v['localizacao']})")
        print(f"       Fonte: {v['fonte']}")
        print(f"       URL: {v['url']}")
        print(f"       Descrição: {v['descricao'][:120]}...\n")

    total = len(vagas_remotas) + len(vagas_pe)
    print("=" * 60)
    if total > 0:
        print(f"✅ SUCESSO: IndeedScraper funcionando perfeitamente ao vivo! Total coletado: {total}")
        sys.exit(0)
    else:
        print("⚠️ AVISO: Nenhuma vaga retornada na busca imediata.")
        sys.exit(1)


if __name__ == "__main__":
    main()
