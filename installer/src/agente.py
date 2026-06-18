#!/usr/bin/env python3
"""
Agente de Sincronizacao IfodPirata
CLI: testar conexao, sync, importar pedidos, modo continuo
Lê config.ini do mesmo diretório do executavel.
"""
import os
import sys
import argparse
import logging
import configparser
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent


def load_config():
    config = configparser.ConfigParser()
    config_ini = BASE_DIR / "config.ini"
    if not config_ini.exists():
        print(f"ERRO: config.ini nao encontrado em {config_ini}")
        print("Copie config.ini.example para config.ini e edite com seus dados.")
        sys.exit(1)
    config.read(str(config_ini))
    
    mappings = {
        ("portal", "PORTAL_URL"): "PORTAL_URL",
        ("portal", "EMPRESA_SLUG"): "EMPRESA_SLUG",
        ("portal", "PORTAL_API_KEY"): "PORTAL_API_KEY",
        ("firebird", "FDB_PATH"): "FB_DATABASE",
        ("firebird", "USER"): "FB_USER",
        ("firebird", "PASSWORD"): "FB_PASSWORD",
        ("agent", "DESTINO_PEDIDO"): "DESTINO_PEDIDO",
        ("agent", "DRY_RUN"): "DRY_RUN",
        ("agent", "INTERVALO_SYNC"): "SYNC_INTERVAL_SECONDS",
        ("imagens", "IMAGENS_PRODUTOS_DIR"): "IMAGENS_PRODUTOS_DIR",
    }
    for (section, key), env_var in mappings.items():
        if section in config and key in config[section]:
            os.environ[env_var] = config[section][key].strip()

    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "agente.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return config


def get_config_value(config, section, key, default=""):
    if section in config and key in config[section]:
        return config[section][key].strip()
    return default


def cmd_testar(config):
    log = logging.getLogger("testar")
    log.info("=" * 50)
    log.info("TESTE DE CONEXAO - IfodPirata Agente")
    log.info("=" * 50)

    portal_url = get_config_value(config, "portal", "PORTAL_URL", "")
    api_key = get_config_value(config, "portal", "PORTAL_API_KEY", "")
    slug = get_config_value(config, "portal", "EMPRESA_SLUG", "")

    log.info(f"Portal URL: {portal_url}")
    log.info(f"Empresa Slug: {slug}")
    log.info(f"API Key: {api_key[:8] if api_key else 'NAO CONFIGURADA'}...")
    log.info(f"Firebird DB: {get_config_value(config, 'firebird', 'FDB_PATH', '')}")
    log.info(f"Destino Pedido: {get_config_value(config, 'agent', 'DESTINO_PEDIDO', 'ORCAMENTO')}")
    log.info(f"Dry Run: {get_config_value(config, 'agent', 'DRY_RUN', 'true')}")
    log.info(f"Intervalo Sync: {get_config_value(config, 'agent', 'INTERVALO_SYNC', '60')}s")

    log.info("---")
    ok = True

    if not portal_url:
        log.error("FALHA: PORTAL_URL nao configurada")
        ok = False
    if not api_key:
        log.error("FALHA: PORTAL_API_KEY nao configurada")
        ok = False
    if not slug:
        log.warning("AVISO: EMPRESA_SLUG nao configurada, usando 'demo'")

    if portal_url and api_key:
        try:
            url = f"{portal_url.rstrip('/')}/api/sync/pedidos-pendentes"
            req = urllib.request.Request(url, headers={"X-API-Key": api_key})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            log.info(f"Portal OK: {len(data)} pedido(s) pendente(s)")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")[:200]
            log.error(f"Portal FALHA: HTTP {e.code} - {body}")
            ok = False
        except Exception as e:
            log.error(f"Portal FALHA: {e}")
            ok = False

    fdb_path = get_config_value(config, "firebird", "FDB_PATH", "")
    if fdb_path:
        try:
            import fdb
            conn = fdb.connect(
                dsn=fdb_path,
                user=get_config_value(config, "firebird", "USER", "SYSDBA"),
                password=get_config_value(config, "firebird", "PASSWORD", "masterkey"),
                charset="WIN1252",
            )
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM RDB$DATABASE")
            cur.fetchone()
            cur.close()
            conn.close()
            log.info(f"Firebird OK: {fdb_path}")
        except ImportError:
            log.error("Firebird FALHA: modulo fdb nao instalado")
            ok = False
        except Exception as e:
            log.error(f"Firebird FALHA: {e}")
            ok = False
    else:
        log.warning("AVISO: Firebird DB nao configurado (FDB_PATH vazio)")

    log.info("---")
    if ok:
        log.info("RESULTADO: Todas as conexoes OK")
    else:
        log.error("RESULTADO: Uma ou mais conexoes FALHARAM")
    log.info("=" * 50)
    return ok


def cmd_sync_once(config):
    log = logging.getLogger("sync")
    log.info("Sincronizando dados para o portal...")
    try:
        from config import settings
        from agent.sync import sync_data_to_portal, import_and_update_pedidos
        sync_data_to_portal()
        log.info("Verificando pedidos pendentes...")
        import_and_update_pedidos()
        log.info("Sincronizacao concluida.")
    except Exception as e:
        log.error(f"Erro na sincronizacao: {e}")
        return False
    return True


def cmd_importar_pedidos(config):
    log = logging.getLogger("import")
    log.info("Importando pedidos ACEITOS do portal...")
    try:
        from agent.importer_online import PortalAPI, importar_todos_pedidos
        api = PortalAPI()
        if not api.testar_conexao():
            log.error("Nao foi possivel conectar ao portal")
            return False
        imp, err, pul = importar_todos_pedidos(api)
        log.info(f"Resultado: {imp} importados, {err} com erro")
        return err == 0
    except Exception as e:
        log.error(f"Erro ao importar pedidos: {e}")
        return False


def cmd_run(config):
    log = logging.getLogger("run")
    log.info("Modo continuo - Pressione Ctrl+C para parar")
    try:
        from agent.sync import run_forever
        run_forever()
    except KeyboardInterrupt:
        log.info("Agente parado pelo usuario")
    except Exception as e:
        log.error(f"Erro no modo continuo: {e}")

def cmd_show_config(config):
    print("=" * 50)
    print("CONFIGURACAO ATUAL")
    print("=" * 50)
    for section in config.sections():
        print(f"\n[{section}]")
        for key, value in config[section].items():
            if "key" in key.lower() or "password" in key.lower() or "secret" in key.lower():
                masked = value[:6] + "..." if len(value) > 6 else "***"
                print(f"  {key} = {masked}")
            else:
                print(f"  {key} = {value}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Agente de Sincronizacao IfodPirata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  agente.exe --testar           Testar conexoes com portal e Firebird
  agente.exe --sync-once        Sincronizar produtos e importar pedidos (unica vez)
  agente.exe --importar-pedidos Importar apenas pedidos ACEITOS
  agente.exe --run              Rodar em modo continuo (sync a cada N segundos)
  agente.exe --config           Mostrar configuracao atual
        """,
    )
    parser.add_argument("--testar", action="store_true", help="Testar conexoes com portal e Firebird")
    parser.add_argument("--sync-once", action="store_true", help="Sincronizar dados e importar pedidos (unica vez)")
    parser.add_argument("--importar-pedidos", action="store_true", help="Importar pedidos ACEITOS do portal")
    parser.add_argument("--run", action="store_true", help="Rodar em modo continuo (sync automatico)")
    parser.add_argument("--config", action="store_true", help="Mostrar configuracao atual (senhas mascaradas)")

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()
    config = load_config()

    if args.testar:
        sys.exit(0 if cmd_testar(config) else 1)
    elif args.sync_once:
        sys.exit(0 if cmd_sync_once(config) else 1)
    elif args.importar_pedidos:
        sys.exit(0 if cmd_importar_pedidos(config) else 1)
    elif args.run:
        cmd_run(config)
    elif args.config:
        cmd_show_config(config)


if __name__ == "__main__":
    main()
