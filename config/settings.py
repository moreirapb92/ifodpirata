import os
from pathlib import Path

# Carregar .env se existir
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.is_file():
    with open(str(_env_file), "r") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip()
                if _k not in os.environ:
                    os.environ[_k] = _v

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

# Modo online: quando True, o portal NAO tenta conectar no Firebird
# Toda importacao de pedidos para ORCAMENTO/DAV deve ser feita pelo agente local
#
# Auto-detect: se a env var RENDER estiver presente (Render sempre define),
#              ou se fdb nao estiver instalado, considera MODO_ONLINE=true
_MODO_ONLINE_ENV = os.getenv("MODO_ONLINE", None)
if _MODO_ONLINE_ENV is not None:
    MODO_ONLINE = _MODO_ONLINE_ENV.lower() in ("true", "1", "sim", "yes")
else:
    # Auto-detect: Render ou fdb ausente
    if os.getenv("RENDER"):
        MODO_ONLINE = True
    else:
        try:
            import fdb
            MODO_ONLINE = False
        except ImportError:
            MODO_ONLINE = True

# Sync
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))
PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:5000")
PORTAL_API_KEY = os.getenv("PORTAL_API_KEY", "agent-api-key-change-me")

# Destino dos pedidos aceitos no portal: "ORCAMENTO" (padrao) ou "PRVD"
DESTINO_PEDIDO = os.getenv("DESTINO_PEDIDO", "ORCAMENTO")

# Modo dry-run: quando True, le os pedidos mas nao grava no Firebird
# Apenas mostra no terminal o que seria gravado
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "sim", "yes")
