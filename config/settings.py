import os

# Firebird connection
FB_HOST = os.getenv("FB_HOST", "")
FB_DATABASE = os.getenv("FB_DATABASE", r"C:\TSD\Host\HOST.FDB")
FB_USER = os.getenv("FB_USER", "SYSDBA")
FB_PASSWORD = os.getenv("FB_PASSWORD", "masterkey")
FB_PORT = int(os.getenv("FB_PORT", "3050"))

def get_fb_dsn():
    if FB_HOST:
        return f"{FB_HOST}/{FB_PORT}:{FB_DATABASE}"
    return FB_DATABASE


# Portal (Flask)
PORTAL_HOST = os.getenv("PORTAL_HOST", "0.0.0.0")
PORTAL_PORT = int(os.getenv("PORTAL_PORT", "5000"))
PORTAL_SECRET_KEY = os.getenv("PORTAL_SECRET_KEY", "ifodpirata-dev-key-change-in-production")

# Sync
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))
PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:5000")
PORTAL_API_KEY = os.getenv("PORTAL_API_KEY", "agent-api-key-change-me")

# Destino dos pedidos aceitos no portal: "ORCAMENTO" (padrao) ou "PRVD"
DESTINO_PEDIDO = os.getenv("DESTINO_PEDIDO", "ORCAMENTO")

# Modo dry-run: quando True, le os pedidos mas nao grava no Firebird
# Apenas mostra no terminal o que seria gravado
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "sim", "yes")
