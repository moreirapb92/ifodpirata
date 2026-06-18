import fdb
import sys

conn = fdb.connect(dsn=r'C:\TSD\Host\HOST.FDB', user='SYSDBA', password='masterkey', charset='WIN1252')
cur = conn.cursor()

tables = sys.argv[1:] if len(sys.argv) > 1 else [
    "PRODUTOS", "PRODUTOS_GRUPO", "PRODUTOS_SUBGRUPO",
    "PRODUTOS_MARCA", "PRODUTOS_BARRAS", "PRODUTOS_MOVIMENTACAO",
    "CLIENTES", "CLIENTES_GRUPO",
    "PRVD", "PRVD_ITENS", "PRVD_TOTAL_TIPO_PGTO",
    "PEDIDO", "PEDIDO_ITENS", "PEDIDO_FORMA_PAGAMENTO",
    "DAV", "DAV_ITENS",
    "FRENTE", "FRENTE_ITENS",
    "EMITENTE", "PARAMETROS",
    "WEB_CONTROL", "WEB_PONTEIROS",
    "NATUREZA_OPERACAO",
    "VENDEDOR", "USUARIO",
    "ECF_TIPO_PAGAMENTO", "ECF_VENDA_CABECALHO",
]

for table in tables:
    print(f"\n{'='*80}")
    print(f"TABLE: {table}")
    print(f"{'='*80}")

    # PK
    cur.execute("""
        SELECT s.rdb$field_name
        FROM rdb$relation_constraints rc
        JOIN rdb$index_segments s ON s.rdb$index_name = rc.rdb$index_name
        WHERE rc.rdb$relation_name = ? AND rc.rdb$constraint_type = 'PRIMARY KEY'
        ORDER BY s.rdb$field_position
    """, [table])
    pk = [r[0].strip() for r in cur.fetchall()]
    if pk:
        print(f"  PK: {', '.join(pk)}")

    # Columns
    cur.execute("""
        SELECT
            f.rdb$field_name,
            f.rdb$field_position,
            rf.rdb$null_flag,
            CAST(f.rdb$default_source AS VARCHAR(255)),
            rf.rdb$field_type
        FROM rdb$relation_fields f
        JOIN rdb$fields rf ON rf.rdb$field_name = f.rdb$field_source
        WHERE f.rdb$relation_name = ?
        ORDER BY f.rdb$field_position
    """, [table])
    type_names = {7: "SMALLINT", 8: "INTEGER", 10: "FLOAT", 12: "DATE", 13: "TIME",
                  14: "TEXT", 16: "BIGINT", 27: "DOUBLE", 35: "TIMESTAMP", 37: "VARYING",
                  40: "CSTRING", 45: "BLOB_ID", 261: "BLOB"}
    for row in cur.fetchall():
        name = row[0].strip()
        nullable = "NULL" if row[2] is None else "NOT NULL"
        default = f" DEFAULT {row[3].strip()}" if row[3] else ""
        tipo = type_names.get(row[4], f"TYPE{row[4]}")
        print(f"  {name:30s} {tipo:12s} {nullable}{default}")

    # FK
    cur.execute("""
        SELECT s.rdb$field_name, rc.rdb$relation_name, s2.rdb$field_name
        FROM rdb$relation_constraints rc
        JOIN rdb$index_segments s ON s.rdb$index_name = rc.rdb$index_name
        JOIN rdb$relation_constraints rc2 ON rc2.rdb$index_name = rc.rdb$foreign_key
        JOIN rdb$index_segments s2 ON s2.rdb$index_name = rc2.rdb$index_name
        WHERE rc.rdb$relation_name = ? AND rc.rdb$constraint_type = 'FOREIGN KEY'
        ORDER BY s.rdb$field_position
    """, [table])
    for row in cur.fetchall():
        print(f"  FK: {row[0].strip()} -> {row[1].strip()}.{row[2].strip()}")

cur.close()
conn.close()
