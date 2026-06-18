import sqlite3
import os
import logging

log = logging.getLogger("models")

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
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_fantasia TEXT NOT NULL DEFAULT '',
            razao_social TEXT NOT NULL DEFAULT '',
            cnpj TEXT NOT NULL DEFAULT '',
            telefone TEXT NOT NULL DEFAULT '',
            cidade TEXT NOT NULL DEFAULT '',
            endereco TEXT NOT NULL DEFAULT '',
            slug TEXT UNIQUE NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS emitente (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL DEFAULT 1,
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
            empresa_id INTEGER NOT NULL DEFAULT 1,
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
            empresa_id INTEGER NOT NULL DEFAULT 1,
            id_grupo INTEGER,
            grupo TEXT,
            desconto REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS subgrupos (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL DEFAULT 1,
            id_subgrupo INTEGER,
            subgrupo TEXT,
            id_grupo INTEGER
        );

        CREATE TABLE IF NOT EXISTS marcas (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL DEFAULT 1,
            id_marca INTEGER,
            marca TEXT
        );

        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL DEFAULT 1,
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
            empresa_id INTEGER NOT NULL DEFAULT 1,
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
            empresa_id INTEGER NOT NULL DEFAULT 1,
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
            chave TEXT NOT NULL,
            empresa_id INTEGER NOT NULL DEFAULT 1,
            valor TEXT NOT NULL,
            PRIMARY KEY (chave, empresa_id)
        );
    """)

    # Migrations: add columns that might not exist
    migracoes_empresa = [
        ("empresa_id", "ALTER TABLE emitente ADD COLUMN empresa_id INTEGER NOT NULL DEFAULT 1"),
        ("empresa_id", "ALTER TABLE produtos ADD COLUMN empresa_id INTEGER NOT NULL DEFAULT 1"),
        ("empresa_id", "ALTER TABLE grupos ADD COLUMN empresa_id INTEGER NOT NULL DEFAULT 1"),
        ("empresa_id", "ALTER TABLE subgrupos ADD COLUMN empresa_id INTEGER NOT NULL DEFAULT 1"),
        ("empresa_id", "ALTER TABLE marcas ADD COLUMN empresa_id INTEGER NOT NULL DEFAULT 1"),
        ("empresa_id", "ALTER TABLE clientes ADD COLUMN empresa_id INTEGER NOT NULL DEFAULT 1"),
        ("empresa_id", "ALTER TABLE pedidos ADD COLUMN empresa_id INTEGER NOT NULL DEFAULT 1"),
        ("empresa_id", "ALTER TABLE pedido_itens ADD COLUMN empresa_id INTEGER NOT NULL DEFAULT 1"),
    ]
    # These need special handling because config has composite PK
    if not coluna_existe(conn, "config", "empresa_id"):
        try:
            conn.execute("DROP TABLE IF EXISTS config")
            conn.executescript("""
                CREATE TABLE config (
                    chave TEXT NOT NULL,
                    empresa_id INTEGER NOT NULL DEFAULT 1,
                    valor TEXT NOT NULL,
                    PRIMARY KEY (chave, empresa_id)
                );
            """)
        except Exception as e:
            log.warning(f"Could not migrate config table: {e}")

    for col, sql in migracoes_empresa:
        tabela = sql.split()[5]
        if not coluna_existe(conn, tabela, col):
            try:
                conn.execute(sql)
            except Exception as e:
                log.warning(f"Could not add {col} to {tabela}: {e}")

    # Create default empresa if none exists
    default_empresa = conn.execute("SELECT id FROM empresas WHERE slug = 'demo'").fetchone()
    if not default_empresa:
        import uuid
        conn.execute(
            "INSERT INTO empresas (nome_fantasia, razao_social, slug, api_key, ativo) VALUES (?, ?, ?, ?, 1)",
            ("Loja Demo", "Loja Demo Ltda", "demo", str(uuid.uuid4()))
        )
        conn.commit()
        default_empresa = conn.execute("SELECT id FROM empresas WHERE slug = 'demo'").fetchone()

    empresa_id = default_empresa["id"]

    # Migrate existing data to default empresa
    for tabela in ("emitente", "produtos", "grupos", "subgrupos", "marcas", "clientes", "pedidos", "pedido_itens"):
        if coluna_existe(conn, tabela, "empresa_id"):
            conn.execute(f"UPDATE {tabela} SET empresa_id = ? WHERE empresa_id IS NULL OR empresa_id = 0", [empresa_id])

    # Migrate config
    has_config_empresa = coluna_existe(conn, "config", "empresa_id")
    if has_config_empresa:
        conn.execute("UPDATE config SET empresa_id = ? WHERE empresa_id IS NULL OR empresa_id = 0", [empresa_id])

    # Config defaults per empresa
    config_defaults = {
        "dry_run": "true",
        "destino_pedido": "ORCAMENTO",
        "sync_interval": "60",
        "modo_teste": "true",
    }
    for chave, valor in config_defaults.items():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO config (chave, empresa_id, valor) VALUES (?, ?, ?)",
                (chave, empresa_id, valor),
            )
        except Exception:
            # Old format without empresa_id
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO config (chave, valor) VALUES (?, ?)",
                    (chave, valor),
                )
            except Exception:
                pass

    conn.commit()

    # Migra estrutura do banco (adiciona colunas faltantes)
    migrate_db(conn)

    conn.close()


def _migrar_colunas(conn, tabela, colunas):
    """Adiciona colunas faltantes em uma tabela de forma idempotente."""
    for coluna, definicao in colunas:
        if not coluna_existe(conn, tabela, coluna):
            try:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
                log.info(f"Migracao: coluna '{coluna}' adicionada em '{tabela}'")
            except Exception as e:
                log.warning(f"Migracao: erro ao adicionar '{coluna}' em '{tabela}': {e}")


def migrate_db(conn):
    """Migra estrutura do banco adicionando colunas faltantes sem apagar dados."""

    # Colunas da tabela pedidos
    _migrar_colunas(conn, "pedidos", [
        ("logradouro_entrega", "TEXT DEFAULT ''"),
        ("numero_entrega", "TEXT DEFAULT ''"),
        ("bairro_entrega", "TEXT DEFAULT ''"),
        ("complemento", "TEXT DEFAULT ''"),
        ("cidade", "TEXT DEFAULT ''"),
        ("referencia", "TEXT DEFAULT ''"),
        ("forma_pagamento_detalhe", "TEXT DEFAULT ''"),
        ("troco_para", "TEXT DEFAULT ''"),
        ("tipo_cartao", "TEXT DEFAULT ''"),
        ("precisa_troco", "INTEGER DEFAULT 0"),
        ("dados_pix", "TEXT"),
        ("status_importacao", "TEXT"),
        ("orcamento_id", "INTEGER"),
        ("numero_orcamento", "INTEGER"),
        ("id_orcamento_firebird", "INTEGER"),
        ("numero_dav", "INTEGER"),
        ("importado", "INTEGER DEFAULT 0"),
        ("importado_em", "TEXT"),
        ("erro_importacao", "TEXT"),
        ("data_importacao", "TEXT"),
    ])

    # Colunas da tabela pedido_itens
    _migrar_colunas(conn, "pedido_itens", [
        ("unidade", "TEXT DEFAULT 'UN'"),
    ])

    conn.commit()
