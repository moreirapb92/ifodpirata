"""
Diagnóstico completo de leitura do Firebird.
Apenas LEITURA - não altera nada no banco.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import FB_DATABASE, FB_USER, FB_PASSWORD, FB_HOST, FB_PORT
import fdb

print("=" * 70)
print("  DIAGNÓSTICO - LEITURA FIREBIRD")
print("=" * 70)

# 1/2/3 — Dados da conexão
dsn = FB_DATABASE
if FB_HOST:
    dsn = f"{FB_HOST}/{FB_PORT}:{FB_DATABASE}"
print(f"\n[1/3] Configuração de conexão:")
print(f"  Caminho DB:  {FB_DATABASE}")
print(f"  Host:        {FB_HOST or '(local)'}")
print(f"  Porta:       {FB_PORT}")
print(f"  Usuário:     {FB_USER}")
print(f"  Charset:     WIN1252")
print(f"  DSN final:   {dsn}")

if not os.path.exists(FB_DATABASE):
    print(f"\n  ERRO: Arquivo não existe em: {FB_DATABASE}")
    sys.exit(1)

import os
tam_mb = os.path.getsize(FB_DATABASE) / (1024 * 1024)
print(f"  Arquivo existe: sim ({tam_mb:.1f} MB)")
print(f"  Última modificação: {os.path.getmtime(FB_DATABASE)}")

# Conectar
print(f"\n[4] Conectando...")
try:
    conn = fdb.connect(dsn=dsn, user=FB_USER, password=FB_PASSWORD, charset="WIN1252")
    print("  CONECTADO")
except Exception as e:
    print(f"  ERRO: {e}")
    sys.exit(1)

cur = conn.cursor()

# 4/5/6 — Contagens brutas
print(f"\n[5] Contagem bruta das tabelas:")
tabelas_para_contar = [
    "PRODUTOS", "PRODUTOS_GRUPO", "PRODUTOS_SUBGRUPO", "PRODUTOS_MARCA",
    "PRODUTOS_BARRAS", "PRODUTOS_MOVIMENTACAO",
    "CLIENTES", "CLIENTES_GRUPO",
    "EMITENTE", "VENDEDOR", "USUARIO",
    "ECF_TIPO_PAGAMENTO",
]
for t in tabelas_para_contar:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        c = cur.fetchone()[0]
        print(f"  {t:35s} = {c}")
    except Exception as e:
        print(f"  {t:35s} = ERRO: {e}")

# 7 — SQL exata usada no agente
print(f"\n[6] SQL exata usada pelo agente para buscar produtos:")
sql_produtos = """
        SELECT
            p.ID_PRODUTO,
            p.PRODUTO,
            p.DESCRICAO_COMPRA,
            p.GTIN,
            p.BARRAS,
            p.NCM,
            p.CEST,
            p.UNIDADE_COMECIAL AS UNIDADE,
            p.VALOR_VENDA,
            p.VALOR_ATACADO,
            p.VALOR_APRAZO,
            p.ESTOQUE,
            p.ESTOQUE_ANT,
            p.CUSTO,
            p.MARGEM,
            p.PESO_LIQUIDO,
            p.PESO_BRUTO,
            p.REFERENCIA,
            p.MARCA,
            p.GRUPO,
            p.SUBGRUPO,
            p.CFOP,
            p.CST,
            p.CSOSN,
            p.ICMS,
            p.STATUS,
            p.DT_CADASTRO,
            p.DT_ULTIMO_MOVIMENTO,
            p.FOTO,
            p.OBS,
            p.LOCALIZACAO,
            p.SECAO,
            g.GRUPO AS NOME_GRUPO,
            s.SUBGRUPO AS NOME_SUBGRUPO,
            m.MARCA AS NOME_MARCA
        FROM PRODUTOS p
        LEFT JOIN PRODUTOS_GRUPO g ON g.ID = p.GRUPO
        LEFT JOIN PRODUTOS_SUBGRUPO s ON s.ID = p.SUBGRUPO
        LEFT JOIN PRODUTOS_MARCA m ON m.ID = p.MARCA
        WHERE 1=1
"""
print(sql_produtos)

# 8 — SQL sem filtros (apenas WHERE 1=1)
print(f"\n[7] Executando SQL SEM filtros (WHERE 1=1)...")
try:
    cur.execute(sql_produtos)
    rows = cur.fetchall()
    cols = [d[0].strip() for d in cur.description]
    print(f"  Total sem filtros: {len(rows)} produtos")
    if rows:
        print(f"  Primeiro produto: ID={rows[0][0]} -> '{rows[0][1]}'")
except Exception as e:
    print(f"  ERRO na SQL: {e}")

# 9 — Aplicando filtro STATUS = '0'
print(f"\n[8] Aplicando filtro STATUS = '0'...")
sql_filtrada = sql_produtos + " AND p.STATUS = '0'"
try:
    cur.execute(sql_filtrada)
    rows_f = cur.fetchall()
    print(f"  Total com STATUS='0': {len(rows_f)} produtos")
except Exception as e:
    print(f"  ERRO: {e}")

# Verificar valores de STATUS
print(f"\n[9] Valores distintos de STATUS em PRODUTOS:")
cur.execute("SELECT DISTINCT STATUS, COUNT(*) FROM PRODUTOS GROUP BY STATUS")
for row in cur.fetchall():
    print(f"  STATUS = '{row[0]}' -> {row[1]} produtos")

# Verificar dados do EMITENTE
print(f"\n[10] Dados do EMITENTE:")
try:
    cur.execute("SELECT * FROM EMITENTE")
    cols_e = [d[0].strip() for d in cur.description]
    rows_e = cur.fetchall()
    print(f"  Colunas: {cols_e}")
    print(f"  Registros: {len(rows_e)}")
    if rows_e:
        for r in rows_e:
            for i, c in enumerate(cols_e):
                print(f"    {c:25s} = {r[i]}")
    else:
        print("  NENHUM registro encontrado!")
except Exception as e:
    print(f"  ERRO: {e}")

# 10 — Primeiros 10 produtos com detalhes
print(f"\n[11] Primeiros 10 produtos (SQL sem filtro de STATUS):")
try:
    cur.execute(sql_produtos + " ORDER BY p.ID_PRODUTO")
    rows = cur.fetchall()
    cols = [d[0].strip() for d in cur.description]
    for r in rows[:10]:
        idx = {c: i for i, c in enumerate(cols)}
        id_prod = r[idx["ID_PRODUTO"]]
        nome = r[idx["PRODUTO"]]
        preco = float(r[idx["VALOR_VENDA"]] or 0) / 100
        estoque = float(r[idx["ESTOQUE"]] or 0) / 100
        status = r[idx["STATUS"]]
        print(f"  ID={id_prod:5d} | '{nome[:50]:50s}' | R$ {preco:>8.2f} | Est: {estoque:>8.2f} | St={status}")
except Exception as e:
    print(f"  ERRO: {e}")

# Verificar CLIENTES
print(f"\n[12] Diagnóstico CLIENTES:")
cur.execute("SELECT DISTINCT STATUS, COUNT(*) FROM CLIENTES GROUP BY STATUS")
for row in cur.fetchall():
    print(f"  STATUS = '{row[0]}' -> {row[1]} clientes")
cur.execute("SELECT COUNT(*) FROM CLIENTES")
print(f"  Total clientes na tabela: {cur.fetchone()[0]}")

cur.close()
conn.close()
print(f"\n{'=' * 70}")
print("  DIAGNÓSTICO CONCLUÍDO")
print("=" * 70)
