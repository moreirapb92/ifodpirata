"""
Sync Engine - Agente de sincronizacao automatica.

Responsabilidades:
1. LER produtos, precos, estoque, grupos, clientes do Firebird e ENVIAR ao Portal.
2. Sincronizar dados do emitente.

IMPORTACAO de pedidos e MANUAL (via web ou CLI).
O agente NAO importa pedidos automaticamente.
"""
import time
import json
import logging
import urllib.request
import urllib.error

from config.settings import PORTAL_URL, PORTAL_API_KEY, SYNC_INTERVAL_SECONDS
from agent.reader import exportar_tudo
from agent.utils import sanitize_for_json
from agent.db import query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync")


def api_post(path, data):
    url = f"{PORTAL_URL}{path}"
    body = json.dumps(sanitize_for_json(data)).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": PORTAL_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log.error(f"HTTP {e.code} on POST {path}: {e.read().decode()}")
        return None
    except Exception as e:
        log.error(f"Error on POST {path}: {e}")
        return None


def api_get(path):
    url = f"{PORTAL_URL}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "X-API-Key": PORTAL_API_KEY,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log.warning(f"HTTP {e.code} on GET {path}")
        return []
    except Exception as e:
        log.warning(f"Error on GET {path}: {e}")
        return []


def sync_data_to_portal():
    """Envia produtos, clientes, grupos, etc. para o portal."""
    log.info("Sincronizando dados para o portal...")

    # --- Diagnostic: EMITENTE ---
    sql_emit = "SELECT * FROM EMITENTE WHERE ID = 1"
    cols, rows = query(sql_emit)
    log.info(f"  [EMITENTE] SQL: {sql_emit}")
    log.info(f"  [EMITENTE] Total na tabela: {len(rows)}")
    if rows:
        d = dict(zip(cols, rows[0]))
        log.info(f"  [EMITENTE] FANTASIA={d.get('FANTASIA')!r}  RAZ_SOCIAL={d.get('RAZ_SOCIAL')!r}")

    # --- Diagnostic: CLIENTES ---
    sql_cli_total = "SELECT COUNT(*) FROM CLIENTES"
    _, rows_total = query(sql_cli_total)
    total_cli = rows_total[0][0]
    log.info(f"  [CLIENTES] Total na tabela (sem filtro): {total_cli}")

    sql_cli_status = "SELECT DISTINCT STATUS FROM CLIENTES"
    _, rows_status = query(sql_cli_status)
    log.info(f"  [CLIENTES] STATUS encontrados: {[r[0] for r in rows_status]}")

    try:
        # Count total ATIVO products in Firebird for logging
        sql_total_prod = "SELECT COUNT(*) FROM PRODUTOS WHERE STATUS = 'ATIVO'"
        _, rows_total = query(sql_total_prod)
        total_firebird_ativos = rows_total[0][0]

        data = exportar_tudo()
        prods = len(data.get("produtos", []))
        ignorados = total_firebird_ativos - prods
        log.info(f"  [PRODUTOS] Ativos no Firebird: {total_firebird_ativos}")
        log.info(f"  [PRODUTOS] Ignorados (descricao vazia): {ignorados}")
        log.info(f"  [PRODUTOS] Enviados ao portal: {prods}")
        if prods > 0:
            com_foto = sum(1 for p in data["produtos"] if p.get("FOTO"))
            sem_foto = prods - com_foto
            log.info(f"  [PRODUTOS] Com foto: {com_foto} | Sem foto: {sem_foto}")
            if com_foto > 0:
                log.info("  Exemplos de caminhos de imagem:")
                for p in data["produtos"][:5]:
                    if p.get("FOTO"):
                        log.info(f"    ID={p['ID_PRODUTO']} -> {p['FOTO']}")
            log.info("Primeiros 10 produtos (codigo | descricao | preco):")
            for p in data["produtos"][:10]:
                cod = p.get("ID_PRODUTO", "?")
                desc = p.get("PRODUTO", "?")[:45]
                preco = p.get("VALOR_VENDA", 0)
                log.info(f"  ID={cod:5d} | {desc:45s} | R$ {preco:>8.2f}")
        clis = len(data.get("clientes", []))
        grps = len(data.get("grupos", []))
        subg = len(data.get("subgrupos", []))
        marcas = len(data.get("marcas", []))
        vends = len(data.get("vendedores", []))
        log.info(f"  [CLIENTES] SQL (reader): SELECT c.ID_CLIENTE, ... FROM CLIENTES c LEFT JOIN ... WHERE c.STATUS = 'ATIVO'")
        log.info(f"  [CLIENTES] Apos filtro STATUS='ATIVO': {clis} clientes")
        log.info(f"Lidos do Firebird: {total_firebird_ativos} produtos ({ignorados} ignorados), {clis} clientes, {grps} grupos, {subg} subgrupos, {marcas} marcas, {vends} vendedores")
        if data.get("emitente"):
            log.info(f"Emitente: {data['emitente'].get('FANTASIA', 'N/A')}")
        result = api_post("/api/sync/full", data)
        if result:
            log.info(f"Sync enviado com sucesso: {result.get('produtos', 0)} produtos, {result.get('clientes', 0)} clientes")
            return True
        else:
            log.warning("Falha ao enviar sync - portal retornou erro")
            return False
    except Exception as e:
        log.error(f"Erro ao sincronizar dados: {e}")
        return False


def run_once():
    """Executa um ciclo de sincronizacao de dados (apenas produtos)."""
    log.info("=" * 50)
    log.info("Iniciando ciclo de sincronizacao (apenas dados)")
    sync_data_to_portal()
    log.info("Importacao de pedidos: MANUAL (use a pagina web ou CLI)")
    log.info("Ciclo finalizado")
    log.info("=" * 50)


def run_forever():
    """Executa sincronizacao continua de dados (sem importar pedidos)."""
    log.info(f"Iniciando sync engine (intervalo: {SYNC_INTERVAL_SECONDS}s)")
    log.info(f"Portal URL: {PORTAL_URL}")
    log.info("Modo: apenas sincronizacao de dados (produtos, clientes, etc.)")
    log.info("Importacao de pedidos: MANUAL via /admin/pedidos-importacao ou CLI")
    log.info("Pressione Ctrl+C para parar")

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            log.info("Sync engine parado pelo usuario")
            break
        except Exception as e:
            log.error(f"Erro no ciclo: {e}")
        time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()
