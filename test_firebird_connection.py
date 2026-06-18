"""
Teste de conexão com o Firebird.

Uso:
    python test_firebird_connection.py

Apenas LEITURA - não altera nada no banco.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import FB_DATABASE, FB_USER, FB_PASSWORD, FB_HOST, FB_PORT
import fdb


def test():
    print("=" * 60)
    print("  TESTE DE CONEXÃO - FIREBIRD")
    print("=" * 60)

    # 1. Mostrar config
    dsn = FB_DATABASE
    if FB_HOST:
        dsn = f"{FB_HOST}/{FB_PORT}:{FB_DATABASE}"
    print(f"\n[1] Configuração:")
    print(f"    Database: {FB_DATABASE}")
    print(f"    Host:     {FB_HOST or '(local)'}")
    print(f"    Porta:    {FB_PORT}")
    print(f"    Usuário:  {FB_USER}")
    print(f"    DSN:      {dsn}")

    # 2. Conectar
    print(f"\n[2] Conectando ao Firebird...")
    try:
        conn = fdb.connect(
            dsn=dsn,
            user=FB_USER,
            password=FB_PASSWORD,
            charset="WIN1252",
        )
        print("    CONECTADO com sucesso!")
    except Exception as e:
        print(f"    ERRO: {e}")
        sys.exit(1)

    cur = conn.cursor()

    # 3. Listar tabelas
    print(f"\n[3] Listando tabelas do banco...")
    cur.execute("""
        SELECT r.rdb$relation_name
        FROM rdb$relations r
        WHERE r.rdb$relation_type = 0
          AND r.rdb$system_flag = 0
        ORDER BY 1
    """)
    tables = [row[0].strip() for row in cur.fetchall()]
    print(f"    Total de tabelas encontradas: {len(tables)}")
    for t in tables:
        cur2 = conn.cursor()
        cur2.execute("SELECT COUNT(*) FROM \"%s\"" % t)
        count = cur2.fetchone()[0]
        cur2.close()
        print(f"      {t:40s} {count:>6} registros")

    # 4. Procurar tabelas prováveis
    print(f"\n[4] Buscando tabelas por padrão de nome...")
    padroes = {
        "PRODUTOS": ["PRODUTO", "PROD", "ITEM", "ESTOQUE", "MERCADORIA"],
        "CLIENTES": ["CLIENTE", "PESSOA", "CADASTRO"],
        "GRUPOS": ["GRUPO"],
    }
    for alvo, keywords in padroes.items():
        encontradas = []
        for t in tables:
            for kw in keywords:
                if kw.upper() in t.upper():
                    encontradas.append(t)
                    break
        print(f"    Tabelas relacionadas a '{alvo}': {encontradas or 'NENHUMA ENCONTRADA'}")

    # 5. Contar registros nas tabelas principais
    print(f"\n[5] Contagem nas tabelas principais...")
    tabelas_principais = [
        "PRODUTOS", "CLIENTES", "PRODUTOS_GRUPO", "PRODUTOS_SUBGRUPO",
        "PRODUTOS_MARCA", "CLIENTES_GRUPO", "VENDEDOR",
        "PRVD", "PRVD_ITENS", "PEDIDO", "PEDIDO_ITENS",
        "ECF_TIPO_PAGAMENTO", "NATUREZA_OPERACAO",
        "EMITENTE", "MOVIMENTO", "FRENTE",
    ]
    for tabela in tabelas_principais:
        if tabela in tables:
            cur.execute("SELECT COUNT(*) FROM \"%s\"" % tabela)
            count = cur.fetchone()[0]
            print(f"    {tabela:35s} = {count:>8} registros")
        else:
            print(f"    {tabela:35s} = TABELA NÃO ENCONTRADA")

    # 6. Primeiros 5 produtos
    print(f"\n[6] Primeiros 5 produtos encontrados:")
    if "PRODUTOS" in tables:
        # Descobrir colunas
        cur.execute("""
            SELECT f.rdb$field_name
            FROM rdb$relation_fields f
            WHERE f.rdb$relation_name = 'PRODUTOS'
            ORDER BY f.rdb$field_position
        """)
        colunas = [row[0].strip() for row in cur.fetchall()]

        nome_col = "PRODUTO" if "PRODUTO" in colunas else (colunas[1] if len(colunas) > 1 else colunas[0])
        id_col = "ID_PRODUTO" if "ID_PRODUTO" in colunas else (colunas[0] if colunas else "ID")

        cur.execute('SELECT FIRST 5 "%s", "%s" FROM PRODUTOS ORDER BY "%s"' % (id_col, nome_col, id_col))
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"    ID={r[0]}  ->  '{r[1]}'")
        else:
            print("    NENHUM produto encontrado (tabela vazia)")
    else:
        print("    Tabela PRODUTOS não existe")

    cur.close()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"  TESTE CONCLUÍDO - Nenhuma alteração no banco")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    test()
