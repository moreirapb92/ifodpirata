import fdb

conn = fdb.connect(dsn=r'C:\TSD\Host\HOST.FDB', user='SYSDBA', password='masterkey', charset='WIN1252')
cur = conn.cursor()

# Check generators
cur.execute("""
    SELECT rdb$generator_name, rdb$system_flag
    FROM rdb$generators
    WHERE rdb$system_flag = 0
    ORDER BY 1
""")
print("=== GENERATORS (non-system) ===")
gen_names = [row[0].strip() for row in cur.fetchall()]
for name in gen_names:
    try:
        cur.execute(f"SELECT GEN_ID({name}, 0) FROM rdb$database")
        val = cur.fetchone()[0]
        print(f"  {name:35s} current={val}")
    except Exception as e:
        print(f"  {name:35s} error={e}")

print("\n=== SAMPLE DATA: PRODUTOS (5 rows) ===")
cur.execute("SELECT FIRST 5 ID_PRODUTO, PRODUTO, VALOR_VENDA/100, ESTOQUE/100, GRUPO, STATUS FROM PRODUTOS")
for row in cur.fetchall():
    print(f"  ID={row[0]}, Produto={row[1]}, Preco={row[2]:.2f}, Estoque={row[3]:.2f}, Grupo={row[4]}, Status={row[5]}")

print("\n=== SAMPLE DATA: CLIENTES (5 rows) ===")
cur.execute("SELECT FIRST 5 ID_CLIENTE, CLIENTE, CPF_CNPJ, STATUS, FONE, CELULAR FROM CLIENTES")
for row in cur.fetchall():
    print(f"  ID={row[0]}, Nome={row[1]}, CPF={row[2]}, Status={row[3]}, Fone={row[4]}, Cel={row[5]}")

print("\n=== SAMPLE DATA: PRVD (5 rows) ===")
cur.execute("SELECT FIRST 5 ID, ID_CLIENTE, DATA_VENDA, VALOR_FINAL/100, STATUS_VENDA, SITUACAO, MODO FROM PRVD")
for row in cur.fetchall():
    print(f"  ID={row[0]}, Cliente={row[1]}, Data={row[2]}, Valor={row[3]:.2f}, Status={row[4]}, Sit={row[5]}, Modo={row[6]}")

print("\n=== SAMPLE DATA: PRVD_ITENS (5 rows) ===")
cur.execute("SELECT FIRST 5 ID, ID_PRVD, ID_PRODUTO, ITEM, QUANTIDADE/1000, VALOR_UNITARIO/100 FROM PRVD_ITENS")
for row in cur.fetchall():
    print(f"  ID={row[0]}, ID_PRVD={row[1]}, ID_Prod={row[2]}, Item={row[3]}, Qtd={row[4]:.3f}, Vlr_Unit={row[5]:.2f}")

print("\n=== PRODUTOS_GRUPO ===")
cur.execute("SELECT * FROM PRODUTOS_GRUPO")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== PRODUTOS_SUBGRUPO ===")
cur.execute("SELECT * FROM PRODUTOS_SUBGRUPO")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== PRODUTOS_MARCA ===")
cur.execute("SELECT * FROM PRODUTOS_MARCA")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== VENDEDOR ===")
cur.execute("SELECT * FROM VENDEDOR")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== USUARIO ===")
cur.execute("SELECT * FROM USUARIO")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== NATUREZA_OPERACAO ===")
cur.execute("SELECT * FROM NATUREZA_OPERACAO")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== ECF_TIPO_PAGAMENTO ===")
cur.execute("SELECT * FROM ECF_TIPO_PAGAMENTO")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== WEB_CONTROL ===")
cur.execute("SELECT * FROM WEB_CONTROL")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== WEB_PONTEIROS ===")
cur.execute("SELECT * FROM WEB_PONTEIROS")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== MOVIMENTO (5 rows) ===")
cur.execute("SELECT FIRST 5 * FROM MOVIMENTO")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== CAIXA_USUARIO ===")
cur.execute("SELECT * FROM CAIXA_USUARIO")
cols = [d[0].strip() for d in cur.description]
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

print("\n=== FRENTE (5 rows) ===")
cur.execute("SELECT FIRST 5 ID, ID_CLIENTE, DATA_VENDA, VALOR_FINAL/100, STATUS_VENDA, SITUACAO FROM FRENTE")
for row in cur.fetchall():
    print(f"  ID={row[0]}, Cliente={row[1]}, Data={row[2]}, Valor={row[3]:.2f}, Status={row[4]}, Sit={row[5]}")

cur.close()
conn.close()
