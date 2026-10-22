import sys
import json

# Garante suporte a UTF-8 no Windows para prints e emojis
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from linkedin_scraper import buscar_vagas_linkedin, obter_detalhes_vaga

def testar():
    print("=" * 60)
    print("🧪 TESTE DE BUSCA DE VAGAS EM TEMPO REAL NO LINKEDIN")
    print("=" * 60)

    termo = "Desenvolvedor Next.js"
    print(f"Buscando vagas abertas para: '{termo}'...")
    vagas = buscar_vagas_linkedin(keywords=termo, location="Brasil", max_pages=1)

    print(f"\nTotal de vagas encontradas: {len(vagas)}\n")

    for i, v in enumerate(vagas[:3], 1):
        print(f"[{i}] {v['titulo']} @ {v['empresa']}")
        print(f"    📍 Local: {v['localizacao']}")
        print(f"    🔗 URL: {v['url']}")
        
        detalhes = obter_detalhes_vaga(v['id'])
        desc = detalhes.get('descricao', '').strip()
        print(f"    📄 Prévia da Descrição: {desc[:200]}...")
        print("-" * 60)

if __name__ == "__main__":
    testar()
