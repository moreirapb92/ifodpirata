"""
Sincroniza o Firebird local com o portal online (Render).
Uso direto:
  python sincronizar_render.py
Ou com env vars explicitas:
  set PORTAL_URL=https://ifodpirata.onrender.com
  set PORTAL_API_KEY=MINHA_CHAVE
  python sincronizar_render.py
"""
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync-render")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import PORTAL_URL, PORTAL_API_KEY
from agent.sync import sync_data_to_portal
from agent.db import query


def main():
    print("=" * 64)
    print("  SINCRONIZAR RENDER  -  Firebird HOST  >>  Portal Online")
    print("=" * 64)
    print(f"  Portal URL:  {PORTAL_URL}")
    print(f"  API Key:     {'[configurada]' if PORTAL_API_KEY else '[FALTANDO]'}")
    print()

    if not PORTAL_API_KEY:
        log.error("PORTAL_API_KEY nao configurada!")
        log.error("Defina a variavel de ambiente ou crie um arquivo .env")
        sys.exit(1)

    # --- Estatisticas do Firebird ---
    log.info("Conectando ao Firebird local (HOST)...")

    try:
        cols_emit, rows_emit = query("SELECT FANTASIA, RAZ_SOCIAL FROM EMITENTE WHERE ID = 1")
        emitente = rows_emit[0] if rows_emit else ("?", "?")
        fantasia_raw = str(emitente[0] or "").strip()
        fantasia = fantasia_raw if fantasia_raw.lower() not in ("null", "none", "") else str(emitente[1] or "Minha Loja").strip()
        log.info(f"  Emitente: {fantasia}")

        _, rows = query("SELECT COUNT(*) FROM PRODUTOS WHERE STATUS = 'ATIVO'")
        total_prod = rows[0][0] if rows else 0

        _, rows_foto = query("SELECT COUNT(*) FROM PRODUTOS WHERE STATUS = 'ATIVO' AND FOTO IS NOT NULL AND FOTO != ''")
        total_foto = rows_foto[0][0] if rows_foto else 0

        _, rows_grp = query("SELECT COUNT(*) FROM PRODUTOS_GRUPO")
        total_grp = rows_grp[0][0] if rows_grp else 0

        _, rows_cli = query("SELECT COUNT(*) FROM CLIENTES WHERE STATUS = 'ATIVO'")
        total_cli = rows_cli[0][0] if rows_cli else 0

        log.info(f"  Produtos ativos: {total_prod}")
        log.info(f"  Com foto:        {total_foto}")
        log.info(f"  Grupos:          {total_grp}")
        log.info(f"  Clientes ativos: {total_cli}")
        print()
    except Exception as e:
        log.error(f"Erro ao consultar Firebird: {e}")
        sys.exit(1)

    # --- Sincronizar ---
    log.info("Enviando dados para o portal online...")
    resultado = sync_data_to_portal()

    print()
    if resultado:
        print("  " + "-" * 48)
        print("  [OK] Portal online atualizado com sucesso!")
        print()
        print(f"  Dados enviados:")
        print(f"    Produtos:  {total_prod}")
        print(f"    Com foto:  {total_foto}")
        print(f"    Grupos:    {total_grp}")
        print(f"    Clientes:  {total_cli}")
        print(f"    Emitente:  {fantasia}")
        print()
        print(f"  Acesse:  {PORTAL_URL}/loja2")
    else:
        print("  [FALHA] Erro ao sincronizar. Verifique os logs acima.")
        sys.exit(1)


if __name__ == "__main__":
    main()
