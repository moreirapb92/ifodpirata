"""
Importa pedidos ACEITOS do portal online para o Firebird local (HOST).
Uso: python importar_pedidos_online.py

Le PORTAL_URL e PORTAL_API_KEY do ambiente (ou .env).
"""
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("cli")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.importer_online import PortalAPI, importar_todos_pedidos


def main():
    portal_url = os.getenv("PORTAL_URL", "")
    api_key = os.getenv("PORTAL_API_KEY", "")

    print("=" * 60)
    print("  IMPORTACAO DE PEDIDOS - PORTAL ONLINE -> HOST LOCAL")
    print("=" * 60)
    print(f"  Portal URL: {portal_url}")
    print(f"  API Key:    {'[configurada]' if api_key else '[NAO CONFIGURADA]'}")
    print()

    if not api_key:
        log.error("PORTAL_API_KEY nao configurada!")
        sys.exit(1)

    api = PortalAPI()

    log.info("Testando conexao com o portal...")
    if not api.testar_conexao():
        log.error("Nao foi possivel conectar ao portal. Verifique PORTAL_URL e PORTAL_API_KEY.")
        sys.exit(1)

    log.info("Conexao OK!")

    importados, erros, pulados = importar_todos_pedidos(api)

    print()
    print("-" * 60)
    if importados > 0:
        print(f"  {importados} pedido(s) importado(s) com sucesso para o HOST!")
    if erros > 0:
        print(f"  {erros} pedido(s) com erro - veja os logs acima.")
    if importados == 0 and erros == 0:
        print("  Nenhum pedido pendente para importar.")
    print()


if __name__ == "__main__":
    main()
