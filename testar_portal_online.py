"""
Teste de conexao com o portal online (Render).
Uso: python testar_portal_online.py
"""
"""
Teste de conexao com o portal online (Render).
Uso: python testar_portal_online.py
"""
import os
import sys
import urllib.request
import json

# Carregar config do .env (se existir) antes de ler os getenv abaixo
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.isfile(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip()
                if _k not in os.environ:
                    os.environ[_k] = _v

OK = "\033[92mOK\033[0m"
FAIL = "\033[91mFALHA\033[0m"
PULA = "\033[93mPULOU\033[0m"

def testar(nome, url, headers=None, esperar=200):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
            if status == esperar:
                print(f"  [{OK}] {nome} ({status})")
                return body
            else:
                print(f"  [{FAIL}] {nome} - status {status} (esperava {esperar})")
                return None
    except urllib.error.HTTPError as e:
        print(f"  [{FAIL}] {nome} - HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  [{FAIL}] {nome} - {e}")
        return None


def main():
    portal_url = os.getenv("PORTAL_URL", "https://ifodpirata.onrender.com")
    api_key = os.getenv("PORTAL_API_KEY", "")

    print("=" * 60)
    print("  TESTE DE CONEXAO COM O PORTAL ONLINE")
    print("=" * 60)
    print(f"  Portal URL: {portal_url}")
    print(f"  API Key:    {'[configurada]' if api_key else '[NAO CONFIGURADA]'}")
    print()

    # 1. Pagina inicial
    print("[1] Pagina inicial /")
    testar("GET /", f"{portal_url}/")

    # 2. Loja2
    print("[2] Loja publica /loja2")
    body = testar("GET /loja2", f"{portal_url}/loja2")
    if body and "LOJA2" in body.upper():
        print(f"       Conteudo: tem 'LOJA2' - pagina parece correta")

    # 3. API de produtos (publica, sem auth)
    print("[3] API produtos (GET /api/loja/produtos)")
    body = testar("GET produtos", f"{portal_url}/api/loja/produtos?pagina=1&busca=")
    if body:
        try:
            d = json.loads(body)
            total = d.get("total", 0)
            com_foto = sum(1 for p in d.get("produtos", []) if p.get("foto"))
            print(f"       Total: {total} produtos, {com_foto} com foto nesta pagina")
        except Exception:
            pass

    # 4. API grupos (publica, sem auth)
    print("[4] API grupos (GET /api/loja/grupos)")
    body = testar("GET grupos", f"{portal_url}/api/loja/grupos")
    if body:
        try:
            g = json.loads(body)
            print(f"       Total: {len(g)} grupos")
        except Exception:
            pass

    # 5. Teste de autenticacao (sync pedidos - requer API Key)
    print("[5] Teste de autenticacao (GET /api/sync/pedidos-pendentes)")
    if api_key:
        headers = {"X-API-Key": api_key}
        body = testar("GET pedidos-pendentes", f"{portal_url}/api/sync/pedidos-pendentes", headers=headers)
        if body is not None:
            print("       API key ACEITA pelo portal")
        else:
            print("       API key REJEITADA - verifique se a chave esta correta")
    else:
        print(f"  [{PULA}] Configure PORTAL_API_KEY no .env para testar autenticacao")

    # 6. Resumo
    print()
    print("-" * 60)
    if body is not None or True:
        print("  Para sincronizar os dados do HOST com o portal:")
        print()
        print("    python sync_once_online.py")
        print()
        print("  Para sync continuo (a cada 60s):")
        print()
        print("    python run_agent.py")


if __name__ == "__main__":
    main()
