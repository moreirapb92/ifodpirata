import sqlite3
import os

DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "portal.db"))


def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def coluna_existe(conn, tabela, coluna):
    cursor = conn.execute(f"PRAGMA table_info({tabela})")
    for row in cursor.fetchall():
        if row["name"] == coluna:
            return True
    return False


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS emitente (
            id INTEGER PRIMARY KEY,
            fantasia TEXT,
            razao_social TEXT,
            cnpj TEXT,
            ie TEXT,
            municipio TEXT,
            uf TEXT,
            logradouro TEXT,
            bairro TEXT,
            telefone TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY,
            id_produto INTEGER,
            produto TEXT,
            gtin TEXT,
            ncm TEXT,
            unidade TEXT,
            valor_venda REAL DEFAULT 0,
            valor_atacado REAL DEFAULT 0,
            valor_aprazo REAL DEFAULT 0,
            estoque REAL DEFAULT 0,
            grupo INTEGER DEFAULT 0,
            subgrupo INTEGER DEFAULT 0,
            marca INTEGER DEFAULT 0,
            nome_grupo TEXT,
            nome_subgrupo TEXT,
            nome_marca TEXT,
            foto TEXT,
            status TEXT DEFAULT '0',
            sincronizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS grupos (
            id INTEGER PRIMARY KEY,
            id_grupo INTEGER,
            grupo TEXT,
            desconto REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS subgrupos (
            id INTEGER PRIMARY KEY,
            id_subgrupo INTEGER,
            subgrupo TEXT,
            id_grupo INTEGER
        );

        CREATE TABLE IF NOT EXISTS marcas (
            id INTEGER PRIMARY KEY,
            id_marca INTEGER,
            marca TEXT
        );

        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY,
            id_cliente INTEGER,
            cliente TEXT,
            cpf_cnpj TEXT,
            ie_rg TEXT,
            logradouro TEXT,
            numero TEXT,
            bairro TEXT,
            municipio TEXT,
            uf TEXT,
            cep TEXT,
            fone TEXT,
            celular TEXT,
            email TEXT,
            status TEXT DEFAULT 'ATIVO',
            limite_credito REAL DEFAULT 0,
            sincronizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_externo TEXT UNIQUE,
            numero INTEGER,
            id_cliente INTEGER,
            nome_cliente TEXT,
            cpf_cnpj TEXT,
            fone TEXT,
            data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            valor_total REAL DEFAULT 0,
            desconto REAL DEFAULT 0,
            status TEXT DEFAULT 'PENDENTE',
            observacao TEXT,
            forma_pagamento TEXT,
            sincronizado INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pedido_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pedido INTEGER NOT NULL,
            id_produto INTEGER,
            produto TEXT,
            gtin TEXT,
            quantidade REAL DEFAULT 1,
            valor_unitario REAL DEFAULT 0,
            valor_total REAL DEFAULT 0,
            FOREIGN KEY (id_pedido) REFERENCES pedidos(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS config (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );
    """)

    # Migrations: add columns that might not exist
    migracoes_pedidos = [
        ("fone", "ALTER TABLE pedidos ADD COLUMN fone TEXT"),
        ("importado", "ALTER TABLE pedidos ADD COLUMN importado INTEGER DEFAULT 0"),
        ("orcamento_id", "ALTER TABLE pedidos ADD COLUMN orcamento_id INTEGER"),
        ("data_importacao", "ALTER TABLE pedidos ADD COLUMN data_importacao TIMESTAMP"),
        ("troco_para", "ALTER TABLE pedidos ADD COLUMN troco_para REAL"),
        ("tipo_cartao", "ALTER TABLE pedidos ADD COLUMN tipo_cartao TEXT"),
        ("forma_pagamento_detalhe", "ALTER TABLE pedidos ADD COLUMN forma_pagamento_detalhe TEXT"),
        ("logradouro_entrega", "ALTER TABLE pedidos ADD COLUMN logradouro_entrega TEXT"),
        ("numero_entrega", "ALTER TABLE pedidos ADD COLUMN numero_entrega TEXT"),
        ("bairro_entrega", "ALTER TABLE pedidos ADD COLUMN bairro_entrega TEXT"),
        ("complemento", "ALTER TABLE pedidos ADD COLUMN complemento TEXT"),
        ("id_orcamento_firebird", "ALTER TABLE pedidos ADD COLUMN id_orcamento_firebird INTEGER"),
        ("numero_orcamento", "ALTER TABLE pedidos ADD COLUMN numero_orcamento INTEGER"),
        ("cidade", "ALTER TABLE pedidos ADD COLUMN cidade TEXT"),
        ("referencia", "ALTER TABLE pedidos ADD COLUMN referencia TEXT"),
        ("erro_importacao", "ALTER TABLE pedidos ADD COLUMN erro_importacao TEXT"),
        ("unidade", "ALTER TABLE pedido_itens ADD COLUMN unidade TEXT DEFAULT 'UN'"),
    ]
    for col, sql in migracoes_pedidos:
        try:
            if not coluna_existe(conn, "pedidos", col):
                conn.execute(sql)
        except Exception:
            pass

    # Migrations: emitente
    migracoes_emitente = [
        ("chave_pix", "ALTER TABLE emitente ADD COLUMN chave_pix TEXT"),
        ("nome_recebedor_pix", "ALTER TABLE emitente ADD COLUMN nome_recebedor_pix TEXT"),
        ("whatsapp", "ALTER TABLE emitente ADD COLUMN whatsapp TEXT"),
        ("obs_pagamento_pix", "ALTER TABLE emitente ADD COLUMN obs_pagamento_pix TEXT"),
    ]
    for col, sql in migracoes_emitente:
        try:
            if not coluna_existe(conn, "emitente", col):
                conn.execute(sql)
        except Exception:
            pass

    # Config defaults
    config_defaults = {
        "dry_run": "true",
        "destino_pedido": "ORCAMENTO",
        "sync_interval": "60",
        "modo_teste": "true",
    }
    for chave, valor in config_defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO config (chave, valor) VALUES (?, ?)",
            (chave, valor),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized with migrations.")
