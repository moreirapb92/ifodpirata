"""
Sincronizacao UNICA do Firebird local para o portal online.
Uso: python sync_once_online.py

Le PORTAL_URL e PORTAL_API_KEY do ambiente (ou .env).
Envia produtos, grupos, clientes, fotos para o portal online via /api/sync/full.
"""
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync-once")

# Garantir que o diretorio raiz esta no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.sync import sync_data_to_portal


def main():
    portal_url = os.getenv("PORTAL_URL", "http://localhost:5000")
    api_key = os.getenv("PORTAL_API_KEY", "")

    print("=" * 60)
    print("  SINCRONIZACAO UNICA - FIREBIRD HOST -> PORTAL ONLINE")
    print("=" * 60)
    print(f"  Portal URL: {portal_url}")
    print(f"  API Key:    {'[configurada]' if api_key else '[NAO CONFIGURADA]'}")
    print()

    if not api_key:
        log.error("PORTAL_API_KEY nao configurada!")
        log.error("Crie um arquivo .env baseado no .env.example com a chave correta.")
        sys.exit(1)

    log.info("Iniciando sync...")
    resultado = sync_data_to_portal()

    print()
    if resultado:
        print("  [OK] Sincronizacao concluida com sucesso!")
        print()
        print("  Acesse o portal para verificar:")
        print(f"    {portal_url}/loja2")
        print(f"    {portal_url}/api/loja/produtos?pagina=1&busca=")
        print(f"    {portal_url}/admin (para ver pedidos)")
    else:
        print("  [FALHA] Sync retornou erro. Verifique os logs acima.")
        sys.exit(1)


if __name__ == "__main__":
    main()
