"""
Cria um ORCAMENTO de teste com dados completos de cliente/endereco.
O usuario deve importar manualmente como DAV no HOST para descobrir os campos.
"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent.db import query, get_connection


def main():
    conn = get_connection()
    cur = conn.cursor()

    gen_id = query("SELECT GEN_ID(ORCAMENTO_GEN, 0) FROM RDB$DATABASE")[1][0][0]
    print(f"ORCAMENTO_GEN atual = {gen_id}")

    novo_id = query("SELECT GEN_ID(ORCAMENTO_GEN, 1) FROM RDB$DATABASE")[1][0][0]
    print(f"Novo ORCAMENTO ID = {novo_id}")

    hoje = datetime.date.today()
    agora = datetime.datetime.now().strftime("%H:%M:%S")

    cur.execute("""
        INSERT INTO ORCAMENTO (
            ID, ID_CLIENTE, ID_USUARIO, ID_VENDEDOR,
            DATA_VENDA, HORA_VENDA,
            DESCONTO, ACRESCIMO, VALOR_FINAL, TOTAL_PRODUTOS,
            ACRESCIMO_ITENS, DESCONTO_ITENS,
            STATUS_VENDA, NOME_CLIENTE, ENDERECO_CLIENTE, FONE_CLIENTE,
            CPF_CNPJ_CLIENTE, CANCELADO, NOME_COMPUTADOR, NOME_CAIXA,
            SITUACAO, OBS, DESTINO,
            VALOR_FINAL_APRAZO, FLAG_USO, FLAG_SERIAL_HD,
            DELIVERY_SINCRONIZADO,
            BAIRRO, COMPLEMENTO
        ) VALUES (
            ?, NULL, 2, NULL,
            ?, ?,
            0, 0, 25.00, 25.00,
            0, 0,
            'A', ?, ?, ?,
            '', 'N', 'AGENTE-TESTE', 'AGENTE-TESTE',
            'ABERTO', ?, 'ONLINE',
            0, 'N', 'AEA753E9',
            'N',
            ?, ?
        )
    """, (
        novo_id,
        hoje, agora,
        "TESTE CLIENTE DELIVERY",
        "RUA TESTE DELIVERY, N 110 - CENTRO - PEDRA BRANCA",
        "88999999999",
        "PEDIDO ONLINE\nCliente: TESTE CLIENTE DELIVERY\nTelefone: 88999999999\nEndereco: RUA TESTE DELIVERY, N 110\nBairro: CENTRO\nCidade: PEDRA BRANCA\nComplemento: CASA AZUL\nPagamento: DINHEIRO (troco para R$ 30.00)",
        "CENTRO",
        "CASA AZUL",
    ))

    # Item 1
    item_id1 = query("SELECT GEN_ID(ORCAMENTO_ITENS_GEN, 1) FROM RDB$DATABASE")[1][0][0]
    cur.execute("""
        INSERT INTO ORCAMENTO_ITENS (
            ID, ITEM, ID_PRODUTO, ID_ORCAMENTO,
            QUANTIDADE, VALOR_UNITARIO, VALOR_CUSTO,
            VALOR_PRODUTOS, TOTAL_ITEM,
            DESCONTO, ACRESCIMO, ACRESCIMO_RATEIO, DESCONTO_RATEIO,
            CANCELADO, MOVIMENTA_ESTOQUE, DESC_ACRES, ID_GRADE_ITENS,
            TAXA_DESCONTO, VALOR_UNITARIO_APRAZO, TOTAL_ITEM_APRAZO,
            ID_USUARIO_INSERT, DTHR_INSERCAO
        ) VALUES (
            ?, 1, 6118, ?,
            2, 9.48, 0,
            18.96, 18.96,
            0, 0, 0, 0,
            'N', 'N', '', 0,
            0, 0, 0,
            2, ?
        )
    """, (item_id1, novo_id, datetime.datetime.now()))

    # Item 2
    item_id2 = query("SELECT GEN_ID(ORCAMENTO_ITENS_GEN, 1) FROM RDB$DATABASE")[1][0][0]
    cur.execute("""
        INSERT INTO ORCAMENTO_ITENS (
            ID, ITEM, ID_PRODUTO, ID_ORCAMENTO,
            QUANTIDADE, VALOR_UNITARIO, VALOR_CUSTO,
            VALOR_PRODUTOS, TOTAL_ITEM,
            DESCONTO, ACRESCIMO, ACRESCIMO_RATEIO, DESCONTO_RATEIO,
            CANCELADO, MOVIMENTA_ESTOQUE, DESC_ACRES, ID_GRADE_ITENS,
            TAXA_DESCONTO, VALOR_UNITARIO_APRAZO, TOTAL_ITEM_APRAZO,
            ID_USUARIO_INSERT, DTHR_INSERCAO
        ) VALUES (
            ?, 2, 4994, ?,
            1, 7.79, 0,
            7.79, 7.79,
            0, 0, 0, 0,
            'N', 'N', '', 0,
            0, 0, 0,
            2, ?
        )
    """, (item_id2, novo_id, datetime.datetime.now()))

    # Pagamento
    cols, rows = query("SELECT ID FROM ECF_TIPO_PAGAMENTO WHERE UPPER(DESCRICAO) LIKE '%DINHEIRO%'")
    pgto_tipo = rows[0][0] if rows else 1
    pgto_id = query("SELECT GEN_ID(ORCAMENTO_TOTAL_TIPO_PGTO_GEN, 1) FROM RDB$DATABASE")[1][0][0]
    cur.execute("""
        INSERT INTO ORCAMENTO_TOTAL_TIPO_PGTO (
            ID, ID_VENDA_CABECALHO, ID_TIPO_PAGAMENTO,
            NOME_COMPUTADOR, NOME_CAIXA, VALOR, ESTORNO
        ) VALUES (?, ?, ?, 'AGENTE-TESTE', 'AGENTE-TESTE', ?, 'N')
    """, (pgto_id, novo_id, pgto_tipo, 25.00))

    conn.commit()

    print(f"\nORCAMENTO #{novo_id} criado com sucesso!")
    print(f"  NOME_CLIENTE      = TESTE CLIENTE DELIVERY")
    print(f"  ENDERECO_CLIENTE  = RUA TESTE DELIVERY, N 110 - CENTRO - PEDRA BRANCA")
    print(f"  FONE_CLIENTE      = 88999999999")
    print(f"  BAIRRO            = CENTRO")
    print(f"  COMPLEMENTO       = CASA AZUL")
    print(f"  OBS               = (texto completo)")
    print(f"  DESTINO           = ONLINE")
    print()
    print(f">>> Abra o HOST > Orcamento Livre, veja o ORCAMENTO #{novo_id}")
    print(f">>> Depois IMPORTE como DAV manualmente no HOST")
    print(f">>> Avise quando terminar para eu comparar os snapshots")


if __name__ == "__main__":
    main()
