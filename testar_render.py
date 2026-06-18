"""
Testa se o portal online (Render) esta funcionando e populado.
Uso:
  python testar_render.py
"""
import os
import sys
import urllib.request
import json

PORTAL_URL = os.getenv("PORTAL_URL", "https://ifodpirata.onrender.com")

OK = "\033[92mOK\033[0m"
FAIL = "\033[91mFALHA\033[0m"


def testar(nome, url, esperar=200):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
            if status == esperar:
                return body
            else:
                print(f"  [{FAIL}] {nome} - status {status}")
                return None
    except urllib.error.HTTPError as e:
        print(f"  [{FAIL}] {nome} - HTTP {e.code}")
        return None
    except Exception as e:
        print(f"  [{FAIL}] {nome} - {e}")
        return None


def main():
    print("=" * 56)
    print("  TESTAR RENDER  -  Verificando portal online")
    print("=" * 56)
    print(f"  URL: {PORTAL_URL}")
    print()

    erros = 0

    # 1. Online
    print("[1] Portal online")
    body = testar("GET /", f"{PORTAL_URL}/")
    if body:
        print(f"       OK - pagina inicial acessivel")
    else:
        erros += 1

    # 2. Loja2
    print("[2] Loja publica /loja2")
    body = testar("GET /loja2", f"{PORTAL_URL}/loja2")
    if body:
        print(f"       OK - loja carregada ({len(body)} bytes)")
    else:
        erros += 1

    # 3. Produtos
    print("[3] Produtos /api/loja/produtos")
    body = testar("GET produtos", f"{PORTAL_URL}/api/loja/produtos?pagina=1&busca=")
    total_prod = 0
    total_foto = 0
    if body:
        try:
            d = json.loads(body)
            total_prod = d.get("total", 0)
            produtos = d.get("produtos", [])
            total_foto = sum(1 for p in produtos if p.get("foto"))
            print(f"       Total no portal: {total_prod} produtos")
            print(f"       Com foto (pag 1): {total_foto}/{len(produtos)}")
        except Exception:
            print(f"       Resposta invalida (nao e JSON)")
            erros += 1
    else:
        erros += 1

    # 4. Grupos
    print("[4] Grupos /api/loja/grupos")
    body = testar("GET grupos", f"{PORTAL_URL}/api/loja/grupos")
    total_grp = 0
    if body:
        try:
            grupos = json.loads(body)
            total_grp = len(grupos)
            print(f"       Total no portal: {total_grp} grupos")
        except Exception:
            print(f"       Resposta invalida")
            erros += 1
    else:
        erros += 1

    # 5. Resumo
    print()
    print("-" * 56)
    if erros > 0:
        print(f"  {erros} teste(s) com falha")
    else:
        print("  Todos os testes passaram!")

    if total_prod == 0:
        print()
        print("  [ATENCAO] Portal online sem produtos!")
        print("  Execute o comando abaixo para sincronizar:")
        print()
        print("    python sincronizar_render.py")
        print()
    else:
        print()
        print(f"  Portal OK com {total_prod} produtos e {total_grp} grupos.")
        print()
        print(f"  Loja: {PORTAL_URL}/loja2")

    return erros


if __name__ == "__main__":
    sys.exit(main())
