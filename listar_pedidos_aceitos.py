"""
Lista pedidos do portal com status de importacao.

Uso:
    python listar_pedidos_aceitos.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from portal.models import get_db

db = get_db()

# Estatisticas
total = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
total_aceitos = db.execute(
    "SELECT COUNT(*) FROM pedidos WHERE status = 'ACEITO'"
).fetchone()[0]
total_pendentes = db.execute(
    "SELECT COUNT(*) FROM pedidos WHERE status = 'PENDENTE'"
).fetchone()[0]
total_importados = db.execute(
    "SELECT COUNT(*) FROM pedidos WHERE importado = 1"
).fetchone()[0]
total_ignorados = db.execute(
    "SELECT COUNT(*) FROM pedidos WHERE status = 'IGNORADO'"
).fetchone()[0]

print("=" * 70)
print("  RESUMO DE PEDIDOS NO PORTAL")
print("=" * 70)
print(f"  Total de pedidos:        {total}")
print(f"  Pendentes (aprovacao):   {total_pendentes}")
print(f"  Aceitos (a importar):    {total_aceitos}")
print(f"  Importados:              {total_importados}")
print(f"  Ignorados:               {total_ignorados}")
print()

rows = db.execute("""
    SELECT p.*, COALESCE(p.importado, 0) as importado_flag
    FROM pedidos p
    WHERE p.status IN ('ACEITO', 'IMPORTADO', 'IGNORADO')
    ORDER BY p.criado_em DESC
""").fetchall()

if not rows:
    print("  Nenhum pedido ACEITO/IMPORTADO/IGNORADO encontrado.")
    sys.exit(0)

for r in rows:
    p = dict(r)
    itens = db.execute(
        "SELECT COUNT(*) FROM pedido_itens WHERE id_pedido = ?", [p["id"]]
    ).fetchone()[0]

    status_str = p["status"]
    if p.get("importado_flag"):
        status_str = "IMPORTADO"

    orc_info = f"  ORCAMENTO #{p['orcamento_id']}" if p.get("orcamento_id") else ""
    fone = p.get("fone") or ""
    cpf = p.get("cpf_cnpj") or ""

    print(f"  Pedido #{p['id']:<4d} | {status_str:12s} | {p['nome_cliente'] or 'N/A':35s} | "
          f"R$ {float(p['valor_total'] or 0):>8.2f} | {itens} itens"
          + (f" | {orc_info}" if orc_info else "")
    )
    if fone or cpf:
        print(f"          Fone: {fone}  CPF: {cpf}")
    print()

db.close()
