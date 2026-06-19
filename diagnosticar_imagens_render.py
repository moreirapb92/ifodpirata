"""
Diagnostico de imagens no portal online (Render).
Testa a URL de foto de N produtos e mostra o status HTTP de cada uma.
"""
import os
import sys
import json
import urllib.request
import urllib.error

PORTAL_URL = os.getenv("PORTAL_URL", "https://ifodpirata.onrender.com")
LIMITE = 20

def api_get(path):
    url = f"{PORTAL_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read(), resp.status
    except urllib.error.HTTPError as e:
        return e.read(), e.code
    except Exception as e:
        return str(e).encode(), 0

def main():
    print("=" * 64)
    print(f"  DIAGNOSTICO DE IMAGENS  -  {PORTAL_URL}")
    print("=" * 64)

    # 1. Buscar produtos
    body, status = api_get("/api/loja/produtos?pagina=1&busca=")
    if status != 200:
        print(f"  [ERRO] /api/loja/produtos retornou HTTP {status}")
        print(f"  Resposta: {body[:300]}")
        sys.exit(1)

    data = json.loads(body)
    todos = data.get("produtos", [])
    print(f"\n  Total de produtos retornados: {data.get('total', '?')}")
    print(f"  Produtos nesta pagina: {len(todos)}")

    com_foto = [p for p in todos if p.get("foto")]
    sem_foto = [p for p in todos if not p.get("foto")]
    print(f"  Com campo foto preenchido: {len(com_foto)}")
    print(f"  Sem foto: {len(sem_foto)}")

    if not com_foto:
        print("\n  NENHUM produto com foto encontrado no portal.")
        print("  Execute 'python sincronizar_render.py' primeiro.")
        sys.exit(0)

    # 2. Testar URLs de foto
    print(f"\n  Testando URLs de foto dos primeiros {min(LIMITE, len(com_foto))} produtos...")
    print()

    testar = com_foto[:LIMITE]
    ok = 0
    erro_404 = 0
    erro_outro = 0

    for p in testar:
        pid = p.get("id_produto") or p.get("id")
        nome = str(p.get("produto", "?") or "?")[:40]
        url_foto = f"/api/loja/produto/{pid}/foto"

        img_body, img_status = api_get(url_foto)
        tamanho = len(img_body)

        # Detectar se retornou HTML (erro) ou imagem
        is_html = img_body[:10].strip().lower().startswith(b"<!") or img_body[:10].strip().lower().startswith(b"<html")
        tipo = "HTML" if is_html else "imagem" if img_status == 200 and tamanho > 100 else "desconhecido"

        status_str = f"HTTP {img_status}"
        if img_status == 200:
            status_str += f" ({tamanho} bytes, {tipo})"
            ok += 1
        elif img_status == 404:
            status_str += " (nao encontrada)"
            erro_404 += 1
        else:
            status_str += f" (resposta: {img_body[:80]})"
            erro_outro += 1

        print(f"    ID={pid:5d} | {nome:40s} | {status_str}")

    # 3. Resumo
    print()
    print("  " + "-" * 48)
    print(f"  Resumo:")
    print(f"    Testados:     {len(testar)}")
    print(f"    OK (200):     {ok}")
    print(f"    Nao encontrado (404): {erro_404}")
    print(f"    Outro erro:   {erro_outro}")
    print()
    if ok == 0:
        print("  Diagnostico: As imagens NAO estao no servidor Render.")
        print("  Solucao: Executar 'python sincronizar_fotos_render.py'")
    elif ok < len(testar):
        print("  Diagnostico: Algumas imagens estao presentes, outras faltando.")
        print("  Solucao: Executar 'python sincronizar_fotos_render.py' para enviar as faltantes.")
    else:
        print("  Diagnostico: Todas as imagens testadas estam OK!")

if __name__ == "__main__":
    main()
