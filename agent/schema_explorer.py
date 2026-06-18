"""
Schema Explorer - Mapeia todas as tabelas, colunas, chaves e triggers do Firebird.
Útil para descobrir a estrutura do sistema comercial desconhecido.
"""
from agent.db import query


def get_all_tables():
    sql = """
        SELECT r.rdb$relation_name
        FROM rdb$relations r
        WHERE r.rdb$relation_type = 0
          AND r.rdb$system_flag = 0
        ORDER BY 1
    """
    cols, rows = query(sql)
    return [row[0].strip() for row in rows]


def get_table_columns(table_name):
    sql = """
        SELECT
            f.rdb$field_name,
            f.rdb$field_position,
            rf.rdb$null_flag,
            CAST(f.rdb$default_source AS VARCHAR(255)),
            CASE
                WHEN t.rdb$type_name = 'VARYING' THEN 'VARCHAR(' || rf.rdb$field_length || ')'
                WHEN t.rdb$type_name = 'SHORT' THEN 'SMALLINT'
                WHEN t.rdb$type_name = 'LONG' THEN 'INTEGER'
                WHEN t.rdb$type_name = 'FLOAT' THEN 'FLOAT'
                WHEN t.rdb$type_name = 'DOUBLE' THEN 'DOUBLE PRECISION'
                WHEN t.rdb$type_name = 'TIMESTAMP' THEN 'TIMESTAMP'
                WHEN t.rdb$type_name = 'DATE' THEN 'DATE'
                WHEN t.rdb$type_name = 'TIME' THEN 'TIME'
                WHEN t.rdb$type_name = 'BLOB' THEN 'BLOB'
                WHEN t.rdb$type_name = 'D_FLOAT' THEN 'DOUBLE PRECISION'
                WHEN t.rdb$type_name = 'NUMERIC' THEN 'NUMERIC(' || rf.rdb$field_precision || ',' || (0 - rf.rdb$field_scale) || ')'
                WHEN t.rdb$type_name = 'DECIMAL' THEN 'DECIMAL(' || rf.rdb$field_precision || ',' || (0 - rf.rdb$field_scale) || ')'
                WHEN t.rdb$type_name = 'INT64' THEN 'BIGINT'
                WHEN t.rdb$type_name = 'BOOLEAN' THEN 'BOOLEAN'
                ELSE t.rdb$type_name || '?'
            END AS field_type
        FROM rdb$relation_fields f
        JOIN rdb$fields rf ON rf.rdb$field_name = f.rdb$field_source
        LEFT JOIN rdb$types t ON t.rdb$type = rf.rdb$field_type AND t.rdb$field_name = 'RDB$FIELD_TYPE'
        WHERE f.rdb$relation_name = ?
        ORDER BY f.rdb$field_position
    """
    cols, rows = query(sql, [table_name])
    return [
        {
            "name": row[0].strip(),
            "pos": row[1],
            "nullable": row[2] is None,
            "default": row[3].strip() if row[3] else None,
            "type": row[4],
        }
        for row in rows
    ]


def get_primary_key(table_name):
    sql = """
        SELECT s.rdb$field_name
        FROM rdb$relation_constraints rc
        JOIN rdb$index_segments s ON s.rdb$index_name = rc.rdb$index_name
        WHERE rc.rdb$relation_name = ?
          AND rc.rdb$constraint_type = 'PRIMARY KEY'
        ORDER BY s.rdb$field_position
    """
    cols, rows = query(sql, [table_name])
    return [row[0].strip() for row in rows]


def get_foreign_keys(table_name):
    sql = """
        SELECT
            s.rdb$field_name,
            rc.rdb$relation_name,
            s2.rdb$field_name
        FROM rdb$relation_constraints rc
        JOIN rdb$index_segments s ON s.rdb$index_name = rc.rdb$index_name
        JOIN rdb$relation_constraints rc2 ON rc2.rdb$index_name = rc.rdb$foreign_key
        JOIN rdb$index_segments s2 ON s2.rdb$index_name = rc2.rdb$index_name
        WHERE rc.rdb$relation_name = ?
          AND rc.rdb$constraint_type = 'FOREIGN KEY'
        ORDER BY s.rdb$field_position
    """
    cols, rows = query(sql, [table_name])
    return [
        {"column": row[0].strip(), "ref_table": row[1].strip(), "ref_column": row[2].strip()}
        for row in rows
    ]


def get_generators():
    sql = """
        SELECT rdb$generator_name, rdb$generator_increment
        FROM rdb$generators
        WHERE rdb$system_flag = 0
        ORDER BY 1
    """
    cols, rows = query(sql)
    return [{"name": row[0].strip(), "increment": row[1]} for row in rows]


def get_triggers(table_name=None):
    if table_name:
        sql = """
            SELECT rdb$trigger_name, rdb$relation_name, rdb$trigger_type,
                   rdb$trigger_sequence, rdb$trigger_source
            FROM rdb$triggers
            WHERE rdb$system_flag = 0 AND rdb$relation_name = ?
            ORDER BY rdb$trigger_sequence
        """
        cols, rows = query(sql, [table_name])
    else:
        sql = """
            SELECT rdb$trigger_name, rdb$relation_name, rdb$trigger_type,
                   rdb$trigger_sequence, rdb$trigger_source
            FROM rdb$triggers
            WHERE rdb$system_flag = 0
            ORDER BY rdb$relation_name, rdb$trigger_sequence
        """
        cols, rows = query(sql)
    return [
        {
            "name": row[0].strip(),
            "table": row[1].strip(),
            "type": row[2],
            "sequence": row[3],
            "source": row[4].strip() if row[4] else None,
        }
        for row in rows
    ]


def get_indices(table_name):
    sql = """
        SELECT i.rdb$index_name, i.rdb$unique_flag, i.rdb$index_type,
               s.rdb$field_name, s.rdb$field_position
        FROM rdb$indices i
        JOIN rdb$index_segments s ON s.rdb$index_name = i.rdb$index_name
        WHERE i.rdb$relation_name = ?
        ORDER BY i.rdb$index_name, s.rdb$field_position
    """
    cols, rows = query(sql, [table_name])
    indices = {}
    for row in rows:
        name = row[0].strip()
        if name not in indices:
            indices[name] = {
                "name": name,
                "unique": row[1] == 1,
                "type": "ASC" if row[2] == 0 else "DESC",
                "columns": [],
            }
        indices[name]["columns"].append(row[3].strip())
    return list(indices.values())


def explore_database():
    tables = get_all_tables()
    result = {}
    for table in tables:
        result[table] = {
            "columns": get_table_columns(table),
            "primary_key": get_primary_key(table),
            "foreign_keys": get_foreign_keys(table),
            "indices": get_indices(table),
        }
    result["_generators"] = get_generators()
    result["_triggers"] = get_triggers()
    return result


def export_schema_to_txt(filepath="data/schema.txt"):
    tables = get_all_tables()
    lines = []
    lines.append(f"=== TABLES ({len(tables)}) ===\n")
    for t in tables:
        lines.append(f"\n--- {t} ---")
        pk = get_primary_key(t)
        if pk:
            lines.append(f"  PK: {', '.join(pk)}")
        cols = get_table_columns(t)
        for c in cols:
            nullable = "NULL" if c["nullable"] else "NOT NULL"
            default = f" DEFAULT {c['default']}" if c["default"] else ""
            lines.append(f"  {c['name']:30s} {c['type']:25s} {nullable}{default}")
        fks = get_foreign_keys(t)
        for fk in fks:
            lines.append(f"  FK: {fk['column']} -> {fk['ref_table']}({fk['ref_column']})")
        idxs = get_indices(t)
        for idx in idxs:
            cols_str = ", ".join(idx["columns"])
            lines.append(f"  INDEX {'UNIQUE ' if idx['unique'] else ''}[{', '.join(idx['columns'])}]")
    lines.append(f"\n\n=== GENERATORS ===\n")
    for g in get_generators():
        lines.append(f"  {g['name']}")
    lines.append(f"\n=== TRIGGERS ===\n")
    for tr in get_triggers():
        lines.append(f"  {tr['name']} ON {tr['table']} (type={tr['type']})")

    content = "\n".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Schema exported to {filepath}")
    return content


if __name__ == "__main__":
    export_schema_to_txt()
