"""
Deploy completo: repovoa o portal Render apos cada deploy.
Uso:
  python deploy_completo.py

Pre-requisito: configurar PORTAL_URL e PORTAL_API_KEY no ambiente.
"""
import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error

PORTAL_URL = os.getenv("PORTAL_URL", "").strip()
PORTAL_API_KEY = os.getenv("PORTAL_API_KEY", "").strip()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def e(msg):
    print(f"  [!] {msg}")


def ok(msg):
    print(f"  [OK] {msg}")


def title(msg):
    print()
    print("=" * 60)
    print(f"  {msg}")
    print("=" * 60)


def run_script(name, args=None):
    """Roda um script Python local e retorna (returncode, output)."""
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, name)]
    if args:
        cmd.extend(args)
    env = os.environ.copy()
    env["PORTAL_URL"] = PORTAL_URL
    env["PORTAL_API_KEY"] = PORTAL_API_KEY
    print(f"  Executando: python {name}")
    print()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        bufsize=1,
    )
    output_lines = []
    for line in proc.stdout:
        line = line.rstrip()
        output_lines.append(line)
        # Filter: hide individual photo lines, show only summary & progress
        is_photo_line = (
            "]" in line
            and ("ID=" in line or "->" in line or "Com foto" in line)
            and "Resumo" not in line
            and "Arquivos" not in line
            and "Enviados" not in line
            and "Ignorados" not in line
            and "Erros" not in line
            and "Conectando" not in line
        )
        if is_photo_line and "Enviado com sucesso" in line:
            # Show only every 100th photo or first/last
            try:
                parts = line.split("[")[1].split("/")[0].strip()
                num = int(parts)
                if num % 100 == 0 or num <= 3:
                    print(line)
            except (IndexError, ValueError):
                pass
        elif is_photo_line and "FALHA" in line:
            print(line)
        elif not is_photo_line:
            print(line)
    proc.wait()
    return proc.returncode, "\n".join(output_lines)


def api_get(path):
    url = f"{PORTAL_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", errors="replace"), e.code
    except Exception as e:
        return str(e), 0


def main():
    print()
    print("=" * 60)
    print("  DEPLOY COMPLETO  -  Repovoar Render apos deploy")
    print("=" * 60)
    print()

    # ── Validar env vars ──
    if not PORTAL_URL:
        print("  [ERRO] Configure PORTAL_URL antes de rodar:")
        print("    PowerShell: $env:PORTAL_URL=\"https://ifodpirata.onrender.com\"")
        print("    CMD:        set PORTAL_URL=https://ifodpirata.onrender.com")
        print()
        sys.exit(1)
    if not PORTAL_API_KEY:
        print("  [ERRO] Configure PORTAL_API_KEY antes de rodar:")
        print("    PowerShell: $env:PORTAL_API_KEY=\"SUA_CHAVE\"")
        print("    CMD:        set PORTAL_API_KEY=SUA_CHAVE")
        print()
        sys.exit(1)

    print(f"  Portal: {PORTAL_URL}")
    print(f"  API Key: {'[configurada]' if PORTAL_API_KEY else '[FALTANDO]'}")
    print()

    erros = 0

    # ── Etapa 1: Testar ──
    title("Etapa 1/4 - Testando portal online")
    rc1, _ = run_script("testar_render.py")
    if rc1 != 0:
        print()
        e("Teste inicial falhou. Verifique se o Render esta no ar.")
        # Continue anyway - might be empty (expected after deploy)
    print()

    # ── Etapa 2: Sincronizar dados ──
    title("Etapa 2/4 - Sincronizando produtos, grupos, clientes")
    rc2, _ = run_script("sincronizar_render.py")
    if rc2 != 0:
        print()
        e("Falha na sincronizacao de dados!")
        erros += 1
    print()

    # ── Etapa 3: Sincronizar fotos ──
    title("Etapa 3/4 - Sincronizando fotos dos produtos")
    print("  Enviando fotos do Firebird para o Render...")
    print("  (isso pode levar varios minutos com 5500+ fotos)")
    print()
    rc3, out3 = run_script("sincronizar_fotos_render.py")
    if rc3 != 0:
        print()
        e("Algumas fotos podem nao ter sido enviadas (veja logs acima).")
        e("Produtos e dados ja estao no ar - as fotos nao afetam o funcionamento da loja.")
        # Don't increment erros - photos are optional
    print()

    # ── Etapa 4: Verificacao final ──
    title("Etapa 4/4 - Conferindo resultado final")
    rc4, _ = run_script("testar_render.py")
    if rc4 != 0:
        erros += 1
    print()

    # ── Coletar dados finais ──
    total_prod = 0
    total_grp = 0
    total_foto = 0

    data_prod, st_prod = api_get("/api/loja/produtos?pagina=1&busca=")
    if st_prod == 200 and isinstance(data_prod, dict):
        total_prod = data_prod.get("total", 0)
        prods = data_prod.get("produtos", [])
        total_foto = sum(1 for p in prods if p.get("foto"))

    data_grp, st_grp = api_get("/api/loja/grupos")
    if st_grp == 200 and isinstance(data_grp, list):
        total_grp = len(data_grp)

    # ── Resumo final ──
    print("=" * 60)
    print("  RESUMO FINAL")
    print("=" * 60)
    print(f"  Produtos no portal:  {total_prod}")
    print(f"  Grupos:              {total_grp}")
    print(f"  Produtos c/ foto:    {total_foto}")
    print()
    print(f"  Links:")
    print(f"    Loja:   {PORTAL_URL}/loja2")
    print(f"    Admin:  {PORTAL_URL}/admin")
    print()

    if erros == 0 and total_prod > 0:
        ok("Deploy completo finalizado com sucesso!")
    elif total_prod > 0:
        print("  [ATENCAO] Deploy concluido com alguns avisos (veja acima).")
        print("  A loja esta no ar com produtos.")
    else:
        print("  [FALHA] Nao foi possivel repovoar o portal.")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
