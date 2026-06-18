import fdb
import sys

conn = fdb.connect(dsn=r'C:\TSD\Host\HOST.FDB', user='SYSDBA', password='masterkey', charset='WIN1252')
cur = conn.cursor()

tables = sys.argv[1:] if len(sys.argv) > 1 else [
    "CLIENTES", "PRVD", "PRVD_ITENS", "PRVD_TOTAL_TIPO_PGTO",
    "PEDIDO", "PEDIDO_ITENS", "PEDIDO_FORMA_PAGAMENTO",
    "DAV", "DAV_ITENS", "WEB_CONTROL", "WEB_PONTEIROS",
    "EMITENTE", "PARAMETROS", "NATUREZA_OPERACAO",
]

type_names = {7: "SMALLINT", 8: "INTEGER", 10: "FLOAT", 12: "DATE", 13: "TIME",
              14: "TEXT", 16: "BIGINT", 27: "DOUBLE", 35: "TIMESTAMP", 37: "VARYING",
              40: "CSTRING", 45: "BLOB_ID", 261: "BLOB"}

for table in tables:
    print(f"\n{'='*80}")
    print(f"TABLE: {table}")
    print(f"{'='*80}")

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

    cur.execute("""
        SELECT
            f.rdb$field_name,
            f.rdb$field_position,
            rf.rdb$null_flag,
            CAST(f.rdb$default_source AS VARCHAR(500)),
            rf.rdb$field_type,
            rf.rdb$field_length,
            rf.rdb$field_scale,
            rf.rdb$field_precision
        FROM rdb$relation_fields f
        JOIN rdb$fields rf ON rf.rdb$field_name = f.rdb$field_source
        WHERE f.rdb$relation_name = ?
        ORDER BY f.rdb$field_position
    """, [table])
    for row in cur.fetchall():
        name = row[0].strip()
        nullable = "NULL" if row[2] is None else "NOT NULL"
        default = f" DEF={row[3].strip()}" if row[3] else ""
        ft = row[4]
        flen = row[5]
        scale = row[6]
        tipo = type_names.get(ft, f"TYPE{ft}")
        if ft in (8, 16) and scale and scale < 0:
            tipo = f"NUMERIC(?, {-scale})".replace("?", str(row[7] or 10))
        elif ft == 37 and flen:
            tipo = f"VARCHAR({flen})"
        elif ft == 14 and flen:
            tipo = f"TEXT({flen})"
        print(f"  {name:35s} {tipo:25s} {nullable}{default}")

cur.close()
conn.close()
