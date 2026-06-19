"""
Sincroniza as imagens dos produtos do Firebird local para o portal Render.
Envia apenas arquivos que existem no disco e que ainda nao estao no servidor.

Uso:
  python sincronizar_fotos_render.py

Opcoes:
  --force    Reenviar todas as fotos, mesmo se ja existirem no servidor
  --limit N  Enviar no maximo N fotos (para testes)
"""
import os
import sys
import time
import json
import logging
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync-fotos")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import PORTAL_URL, PORTAL_API_KEY

LIMITE = None
FORCE = False

# Diretorio local de imagens
IMAGENS_LOCAL_DIR = os.getenv("IMAGENS_PRODUTOS_DIR", "").strip() or r"C:\TSD\Host\imgProdutos"


def upload_foto(produto_id, nome_arquivo, caminho_local):
    """Envia uma foto para o portal via multipart form."""
    url = f"{PORTAL_URL}/api/sync/produto-foto"

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    nome_arq = os.path.basename(nome_arquivo)

    with open(caminho_local, "rb") as f:
        dados = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="produto_id"\r\n\r\n'
        f"{produto_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="nome_arquivo"\r\n\r\n'
        f"{nome_arq}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="arquivo"; filename="{nome_arq}"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + dados + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-API-Key": PORTAL_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        erro_body = e.read().decode("utf-8", errors="replace")[:200]
        log.error(f"HTTP {e.code} ao enviar {nome_arq}: {erro_body}")
        return None
    except Exception as e:
        log.error(f"Erro ao enviar {nome_arq}: {e}")
        return None


def main():
    global LIMITE, FORCE

    # Parse args simples
    for arg in sys.argv[1:]:
        if arg == "--force":
            FORCE = True
        elif arg.startswith("--limit="):
            LIMITE = int(arg.split("=", 1)[1])

    print("=" * 64)
    print("  SINCRONIZAR FOTOS  -  Firebird HOST  >>  Portal Online")
    print("=" * 64)
    print(f"  Portal URL:      {PORTAL_URL}")
    print(f"  Diretorio local: {IMAGENS_LOCAL_DIR}")
    print(f"  Force reupload:  {FORCE}")
    if LIMITE:
        print(f"  Limite:          {LIMITE} fotos")
    print()

    if not PORTAL_API_KEY:
        log.error("PORTAL_API_KEY nao configurada!")
        sys.exit(1)

    if not os.path.isdir(IMAGENS_LOCAL_DIR):
        log.error(f"Diretorio de imagens nao encontrado: {IMAGENS_LOCAL_DIR}")
        sys.exit(1)

    # 1. Buscar produtos com foto no Firebird
    log.info("Conectando ao Firebird local (HOST)...")
    try:
        from agent.db import query
        cols, rows = query(
            "SELECT ID_PRODUTO, FOTO, PRODUTO FROM PRODUTOS WHERE FOTO IS NOT NULL AND FOTO != '' AND STATUS = 'ATIVO'"
        )
    except Exception as e:
        log.error(f"Erro ao consultar Firebird: {e}")
        sys.exit(1)

    total_com_foto = len(rows)
    log.info(f"  Produtos com foto no Firebird: {total_com_foto}")

    if total_com_foto == 0:
        log.warning("Nenhum produto com foto encontrado no Firebird.")
        sys.exit(0)

    # 2. Verificar quais arquivos existem no disco local
    produtos = []
    for row in rows:
        d = dict(zip(cols, row))
        nome_arq = str(d["FOTO"] or "").strip()
        if not nome_arq:
            continue
        caminho = os.path.join(IMAGENS_LOCAL_DIR, nome_arq)
        if os.path.isfile(caminho):
            produtos.append({
                "id": d["ID_PRODUTO"],
                "foto": nome_arq,
                "caminho": caminho,
                "tamanho": os.path.getsize(caminho),
                "nome": str(d.get("PRODUTO") or "?")[:40],
            })
        else:
            log.warning(f"  Arquivo nao encontrado no disco: {nome_arq} (produto ID={d['ID_PRODUTO']})")

    log.info(f"  Arquivos encontrados no disco: {len(produtos)}")
    log.info(f"  Arquivos faltando no disco: {total_com_foto - len(produtos)}")

    if not produtos:
        log.error("Nenhum arquivo de imagem encontrado para enviar.")
        sys.exit(1)

    # 3. Enviar
    print()
    log.info("Enviando fotos para o portal...")
    print()

    if LIMITE:
        produtos = produtos[:LIMITE]

    enviados = 0
    ignorados = 0
    erros = 0
    total = len(produtos)

    for i, p in enumerate(produtos, 1):
        nome_arq = p["foto"]
        log.info(f"  [{i}/{total}] ID={p['id']} | {nome_arq} | {p['nome']} ({p['tamanho']} bytes)")

        if not FORCE:
            # Check if already exists via HEAD request
            check_url = f"{PORTAL_URL}/api/loja/produto-imagem/{nome_arq}"
            try:
                req_check = urllib.request.Request(check_url, method="HEAD")
                with urllib.request.urlopen(req_check, timeout=10) as resp:
                    if resp.status == 200:
                        log.info(f"    -> Ja existe no servidor, ignorando")
                        ignorados += 1
                        continue
            except Exception:
                pass

        result = upload_foto(p["id"], nome_arq, p["caminho"])
        if result and result.get("ok"):
            status = result.get("status", "saved")
            if status == "already_exists":
                log.info(f"    -> Ja existe (confirmado), ignorando")
                ignorados += 1
            else:
                log.info(f"    -> Enviado com sucesso")
                enviados += 1
        else:
            log.error(f"    -> FALHA ao enviar")
            erros += 1

        # Pequena pausa entre envios para nao sobrecarregar
        if i < total:
            time.sleep(0.3)

    # 4. Resumo
    print()
    print("  " + "-" * 48)
    print(f"  Resumo do envio de fotos:")
    print(f"    Total com foto no Firebird: {total_com_foto}")
    print(f"    Arquivos no disco local:    {len(produtos)}")
    print(f"    Enviados:                   {enviados}")
    print(f"    Ignorados (ja existiam):    {ignorados}")
    print(f"    Erros:                      {erros}")
    print()
    if erros == 0 and enviados + ignorados > 0:
        print("  [OK] Sincronizacao de fotos concluida!")
    else:
        print("  [FALHA] Alguns erros ocorreram. Verifique os logs acima.")


if __name__ == "__main__":
    main()
