import fdb

conn = fdb.connect(dsn=r'C:\TSD\Host\HOST.FDB', user='SYSDBA', password='masterkey', charset='WIN1252')
cur = conn.cursor()

cur.execute("""
    SELECT rdb$relation_name
    FROM rdb$relations
    WHERE rdb$relation_type = 0 AND rdb$system_flag = 0
    ORDER BY 1
""")
print("All user tables:")
for row in cur.fetchall():
    name = row[0].strip()
    # count columns
    cur2 = conn.cursor()
    cur2.execute("SELECT COUNT(*) FROM rdb$relation_fields WHERE rdb$relation_name = ?", [name])
    count = cur2.fetchone()[0]
    cur2.close()
    print(f"  {name} ({count} cols)")

cur.close()
conn.close()
