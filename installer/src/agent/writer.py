import datetime
import logging
from decimal import Decimal
from agent.db import query, execute, get_connection

log = logging.getLogger("writer")


def gerar_id(generator_name):
    cols, rows = query(f"SELECT GEN_ID({generator_name}, 1) FROM RDB$DATABASE")
    return rows[0][0]


def get_flag_serial_hd():
    cols, rows = query("SELECT FIRST 1 FLAG_SERIAL_HD FROM ORCAMENTO WHERE FLAG_SERIAL_HD IS NOT NULL")
    if rows and rows[0][0]:
        return rows[0][0].strip()
    cols, rows = query("SELECT FIRST 1 HASH_TRIPA FROM USUARIO WHERE HASH_TRIPA IS NOT NULL")
    if rows and rows[0][0]:
        return rows[0][0].strip()
    return "AGENTE-IFODPIRATA"


def validar_pedido(pedido):
    erros = []

    itens = pedido.get("itens", [])
    if not itens:
        erros.append("Pedido sem itens")
        return erros

    total_calculado = Decimal("0")
    for i, item in enumerate(itens):
        id_produto = item.get("id_produto")
        qtd = Decimal(str(item.get("quantidade", 0)))
        vlr_unit = Decimal(str(item.get("valor_unitario", 0)))
        vlr_total = Decimal(str(item.get("valor_total", 0)))

        if id_produto:
            cols, rows = query("SELECT ID_PRODUTO, STATUS, PRODUTO FROM PRODUTOS WHERE ID_PRODUTO = ?", [id_produto])
            if not rows:
                erros.append(f"Item {i+1}: produto ID {id_produto} nao encontrado no Firebird")
            elif rows[0][1] != "ATIVO":
                erros.append(f"Item {i+1}: produto ID {id_produto} ({rows[0][2]}) nao esta ATIVO (status={rows[0][1]})")
            else:
                nome_firebird = (rows[0][2] or "").strip()
                if not nome_firebird:
                    erros.append(f"Item {i+1}: produto ID {id_produto} esta ATIVO mas sem descricao no Firebird (PRODUTO vazio)")
                # Atualizar a descricao no pedido com a do Firebird
                item["produto"] = nome_firebird

        if vlr_unit <= 0:
            erros.append(f"Item {i+1}: preco unitario deve ser maior que zero (R$ {vlr_unit})")

        if qtd <= 0:
            erros.append(f"Item {i+1}: quantidade deve ser maior que zero")

        total_calculado += vlr_total

    valor_total_pedido = Decimal(str(pedido.get("valor_total", 0)))
    diferenca = abs(total_calculado - valor_total_pedido)
    if diferenca > Decimal("0.01"):
        erros.append(
            f"Total do pedido (R$ {valor_total_pedido:.2f}) difere da soma dos itens "
            f"(R$ {total_calculado:.2f}, diferenca R$ {diferenca:.2f})"
        )

    return erros


def resolver_cliente(pedido):
    id_cliente = pedido.get("id_cliente")
    if not id_cliente:
        log.info("  Cliente: consumidor padrao (sem ID informado)")
        return None

    cols, rows = query("SELECT ID_CLIENTE, CLIENTE FROM CLIENTES WHERE ID_CLIENTE = ?", [id_cliente])
    if not rows:
        log.warning(f"  Cliente ID {id_cliente} nao encontrado no Firebird, usando consumidor padrao (id_cliente=NULL)")
        return None

    log.info(f"  Cliente: {rows[0][1]} (ID={id_cliente})")
    return id_cliente


def criar_orcamento(pedido):
    conn = get_connection()
    cur = conn.cursor()

    try:
        erros = validar_pedido(pedido)
        if erros:
            for e in erros:
                log.error(f"  Validacao: {e}")
            return {"success": False, "erros": erros}

        orcamento_id = gerar_id("ORCAMENTO_GEN")
        hoje = datetime.date.today()
        agora = datetime.datetime.now().strftime("%H:%M:%S")
        flag_serial_hd = get_flag_serial_hd()

        id_cliente_final = resolver_cliente(pedido)

        valor_total = Decimal(str(pedido.get("valor_total", 0)))
        desconto = Decimal(str(pedido.get("desconto", 0)))
        total_produtos = Decimal("0")
        for item in pedido.get("itens", []):
            total_produtos += Decimal(str(item.get("valor_total", 0)))

        # Montar endereco completo para ENDERECO_CLIENTE
        endereco_parts = []
        logradouro = (pedido.get("logradouro") or "").strip()
        numero = (pedido.get("numero") or "").strip()
        bairro = (pedido.get("bairro") or "").strip()
        cidade = (pedido.get("cidade") or "").strip()
        complemento = (pedido.get("complemento") or "").strip()
        referencia = (pedido.get("referencia") or "").strip()

        if logradouro:
            addr = logradouro
            if numero:
                addr += f", N {numero}"
            endereco_parts.append(addr)
        if bairro:
            endereco_parts.append(bairro)
        if cidade:
            endereco_parts.append(cidade)
        if complemento:
            endereco_parts.append(f"({complemento})")
        endereco_completo = " - ".join(endereco_parts) if endereco_parts else ""

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
                ?, ?, 2, NULL,
                ?, ?,
                ?, 0, ?, ?,
                0, 0,
                'A', ?, ?, ?,
                ?, 'N', 'AGENTE-IFODPIRATA', 'AGENTE-IFODPIRATA',
                'ABERTO', ?, 'ONLINE',
                0, 'N', ?,
                'N',
                ?, ?
            )
        """, (
            orcamento_id,
            id_cliente_final,
            hoje, agora,
            desconto,
            valor_total,
            total_produtos,
            pedido.get("nome_cliente", ""),
            endereco_completo,
            pedido.get("fone_cliente", ""),
            pedido.get("cpf_cnpj", ""),
            pedido.get("observacao", ""),
            flag_serial_hd,
            bairro,
            complemento,
        ))

        qtd_itens = 0
        for idx, item in enumerate(pedido.get("itens", [])):
            item_id = gerar_id("ORCAMENTO_ITENS_GEN")
            qtd = Decimal(str(item.get("quantidade", 1)))
            vlr_unit = Decimal(str(item.get("valor_unitario", 0)))
            vlr_total = Decimal(str(item.get("valor_total", 0)))
            vlr_produtos = qtd * vlr_unit
            qtd_itens += 1

            now = datetime.datetime.now()

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
                    ?, ?, ?, ?,
                    ?, ?, 0,
                    ?, ?,
                    0, 0, 0, 0,
                    'N', 'N', '', 0,
                    0, 0, 0,
                    2, ?
                )
            """, (
                item_id,
                idx + 1,
                item.get("id_produto"),
                orcamento_id,
                qtd,
                vlr_unit,
                vlr_produtos,
                vlr_total,
                now,
            ))

        forma_pgto = pedido.get("forma_pagamento", "")
        if forma_pgto:
            pgto_id = gerar_id("ORCAMENTO_TOTAL_TIPO_PGTO_GEN")
            tipo_pgto_map = {
                "DINHEIRO": 1,
                "CARTAO DE CREDITO": 3,
                "CARTAO": 3,
                "CARTAO DE DEBITO": 4,
                "PIX": 4,
                "PRAZO": 5,
                "CHEQUE": 7,
            }
            id_tipo_pgto = tipo_pgto_map.get(forma_pgto.upper(), 1)
            cur.execute("""
                INSERT INTO ORCAMENTO_TOTAL_TIPO_PGTO (
                    ID, ID_VENDA_CABECALHO, ID_TIPO_PAGAMENTO,
                    NOME_COMPUTADOR, NOME_CAIXA, VALOR, ESTORNO
                ) VALUES (?, ?, ?, 'AGENTE-IFODPIRATA', 'AGENTE-IFODPIRATA', ?, 'N')
            """, (pgto_id, orcamento_id, id_tipo_pgto, valor_total))

        conn.commit()

        log.info(f"  ORCAMENTO #{orcamento_id} gravado com sucesso")
        log.info(f"    Itens: {qtd_itens}")
        log.info(f"    Total: R$ {valor_total:.2f}")
        log.info(f"    Situacao: ABERTO (Orcamento Livre)")
        log.info(f"    Tabelas: ORCAMENTO + ORCAMENTO_ITENS" +
                 (" + ORCAMENTO_TOTAL_TIPO_PGTO" if forma_pgto else ""))

        return {"success": True, "orcamento_id": orcamento_id, "id_externo": pedido.get("id_externo"), "itens": qtd_itens}

    except Exception as e:
        conn.rollback()
        log.error(f"  Erro ao gravar ORCAMENTO: {e}")
        raise e
    finally:
        cur.close()
