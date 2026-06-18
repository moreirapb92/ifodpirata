"""
Importador centralizado de pedidos para ORCAMENTO no Firebird.

Usado tanto pela interface web (/admin/pedidos-importacao) quanto pelo CLI
(importar_pedido.py). Nao duplica logica.
"""
import datetime
import logging

from portal.models import get_db

log = logging.getLogger("importer")


def carregar_pedido(pedido_id):
    db = get_db()
    row = db.execute("SELECT * FROM pedidos WHERE id = ?", [pedido_id]).fetchone()
    if not row:
        return None, "Pedido nao encontrado"
    p = dict(row)
    itens_rows = db.execute(
        "SELECT * FROM pedido_itens WHERE id_pedido = ?", [pedido_id]
    ).fetchall()
    p["itens"] = [dict(i) for i in itens_rows]
    return p, None


def diagnosticar_pedido(pedido_id):
    """Retorna diagnostico completo do pedido: dados + validacao por item no Firebird."""
    from agent.db import query as fb_query

    p, erro = carregar_pedido(pedido_id)
    if erro:
        return {"erro": erro}

    result = {
        "id": p["id"],
        "id_externo": p.get("id_externo"),
        "status": p["status"],
        "importado": bool(p.get("importado")),
        "nome_cliente": p.get("nome_cliente"),
        "fone": p.get("fone"),
        "valor_total": float(p.get("valor_total", 0)),
        "total_itens": len(p.get("itens", [])),
        "numero_orcamento": p.get("numero_orcamento"),
        "id_orcamento_firebird": p.get("id_orcamento_firebird"),
        "erro_importacao": p.get("erro_importacao"),
        "data_importacao": p.get("data_importacao"),
        "criado_em": p.get("criado_em"),
        "forma_pagamento": p.get("forma_pagamento"),
        "itens_validacao": [],
        "apto_para_importar": False,
        "motivos_bloqueio": [],
    }

    itens = p.get("itens", [])
    if not itens:
        result["motivos_bloqueio"].append("Pedido sem itens")
        result["itens_validacao"] = []
        return result

    # Batch: carregar todos os produtos do Firebird em 1 consulta
    ids_itens = [str(item.get("id_produto")) for item in itens if item.get("id_produto")]
    fb_map = {}
    if ids_itens:
        cols, rows = fb_query(
            f"SELECT ID_PRODUTO, STATUS, PRODUTO FROM PRODUTOS WHERE ID_PRODUTO IN ({','.join('?'*len(ids_itens))})",
            ids_itens,
        )
        for r in rows:
            fb_map[r[0]] = r

    todos_ok = True
    for idx, item in enumerate(itens):
        info = {
            "item": idx + 1,
            "id_produto": item.get("id_produto"),
            "produto": item.get("produto", ""),
            "quantidade": float(item.get("quantidade", 0)),
            "valor_unitario": float(item.get("valor_unitario", 0)),
            "valor_total": float(item.get("valor_total", 0)),
            "existe_firebird": False,
            "descricao_preenchida": bool((item.get("produto") or "").strip()),
            "status_firebird": None,
            "nome_firebird": None,
            "preco_valido": float(item.get("valor_unitario", 0)) > 0,
            "valido": False,
            "motivo": None,
        }

        pid = item.get("id_produto")
        if pid and pid in fb_map:
            fb_row = fb_map[pid]
            info["existe_firebird"] = True
            info["status_firebird"] = fb_row[1]
            nome_fb = (fb_row[2] or "").strip()
            info["nome_firebird"] = nome_fb if nome_fb else None
            if not nome_fb:
                info["descricao_preenchida"] = False
        elif pid:
            info["motivo"] = "Produto nao encontrado no Firebird"

        if not info["existe_firebird"]:
            info["valido"] = False
            if not info["motivo"]:
                info["motivo"] = "Produto nao existe no Firebird"
            todos_ok = False
        elif info["status_firebird"] != "ATIVO":
            info["valido"] = False
            info["motivo"] = f"Status Firebird: {info['status_firebird']} (deveria ser ATIVO)"
            todos_ok = False
        elif not info["descricao_preenchida"]:
            info["valido"] = False
            info["motivo"] = "Descricao vazia no Firebird"
            todos_ok = False
        elif not info["preco_valido"]:
            info["valido"] = False
            info["motivo"] = "Preco unitario zero ou negativo"
            todos_ok = False
        else:
            info["valido"] = True
            info["motivo"] = "OK"

        result["itens_validacao"].append(info)

    result["apto_para_importar"] = todos_ok and len(itens) > 0
    return result


def importar_pedido_para_orcamento(pedido_id):
    """Funcao unica de importacao. Usada pela web e pelo CLI.

    Retorna dict com:
        success (bool), orcamento_id (int|None),
        erros (list[str]), mensagem (str)
    """
    log.info(f"=== CLICOU IMPORTAR PEDIDO {pedido_id} ===")

    p, erro = carregar_pedido(pedido_id)
    if erro:
        log.error(f"  ERRO: {erro}")
        _salvar_erro(pedido_id, erro)
        return {"success": False, "erros": [erro], "mensagem": erro}

    log.info(f"  Pedido carregado: #{p['id']} {p.get('nome_cliente','')}")

    if p.get("importado"):
        msg = f"Pedido #{pedido_id} ja foi importado anteriormente"
        log.error(f"  ERRO: {msg}")
        return {"success": False, "erros": [msg], "mensagem": msg}

    if p["status"] not in ("ACEITO", "PENDENTE"):
        msg = f"Pedido com status '{p['status']}' nao pode ser importado"
        log.error(f"  ERRO: {msg}")
        _salvar_erro(pedido_id, msg)
        return {"success": False, "erros": [msg], "mensagem": msg}

    itens = p.get("itens", [])
    log.info(f"  Itens encontrados: {len(itens)}")
    if not itens:
        msg = "Pedido sem itens"
        log.error(f"  ERRO: {msg}")
        _salvar_erro(pedido_id, msg)
        return {"success": False, "erros": [msg], "mensagem": msg}

    # Ler config do portal
    db = get_db()
    row_config = db.execute(
        "SELECT valor FROM config WHERE chave = 'dry_run'"
    ).fetchone()
    dry_run = row_config and row_config["valor"].lower() in ("true", "1", "sim")
    row_dest = db.execute(
        "SELECT valor FROM config WHERE chave = 'destino_pedido'"
    ).fetchone()
    destino = row_dest["valor"] if row_dest else "ORCAMENTO"

    if dry_run:
        msg = "DRY_RUN=True no portal. Altere em /admin/configuracao ou use --confirmar no CLI."
        log.warning(f"  BLOQUEADO: {msg}")
        return {
            "success": False,
            "dry_run": True,
            "erros": [msg],
            "mensagem": msg,
        }

    # Montar pedido no formato do writer (enriquecido com Firebird)
    from portal.admin import _montar_pedido_para_importacao

    p_row = db.execute(
        "SELECT * FROM pedidos WHERE id = ?", [pedido_id]
    ).fetchone()
    pedido = _montar_pedido_para_importacao(p_row)
    log.info(f"  Pedido montado: {len(pedido.get('itens',[]))} itens, R$ {float(pedido.get('valor_total',0)):.2f}")

    # Validacao dos itens no Firebird (batch: unica consulta)
    from agent.db import query as fb_query
    from agent.writer import criar_orcamento

    ids_itens = [str(item.get("id_produto")) for item in pedido.get("itens", []) if item.get("id_produto")]
    fb_map = {}
    if ids_itens:
        cols, rows = fb_query(
            f"SELECT ID_PRODUTO, STATUS, PRODUTO, VALOR_VENDA FROM PRODUTOS WHERE ID_PRODUTO IN ({','.join('?'*len(ids_itens))})",
            ids_itens,
        )
        for r in rows:
            fb_map[r[0]] = r
        log.info(f"  Firebird batch: {len(rows)} produtos carregados em 1 consulta")

    erros_validacao = []
    for idx, item in enumerate(pedido.get("itens", [])):
        pid = item.get("id_produto")
        log.info(f"  Validando item {idx+1}: ID_PRODUTO={pid}")

        if not pid:
            erros_validacao.append(f"Item {idx+1}: sem ID do produto")
            continue

        fb_row = fb_map.get(pid)
        if not fb_row:
            erros_validacao.append(f"Item {idx+1}: produto ID {pid} nao encontrado no Firebird")
            continue

        fb_status = fb_row[1]
        fb_produto = (fb_row[2] or "").strip()
        fb_preco = float(fb_row[3] or 0) / 100

        log.info(
            f"    Firebird: produto={fb_produto!r} status={fb_status} preco=R$ {fb_preco:.2f}"
        )

        if fb_status != "ATIVO":
            erros_validacao.append(
                f"Item {idx+1}: produto ID {pid} ({fb_produto}) nao esta ATIVO (status={fb_status})"
            )
            continue

        if not fb_produto:
            erros_validacao.append(
                f"Item {idx+1}: produto ID {pid} esta ATIVO mas sem descricao no Firebird (PRODUTO vazio)"
            )
            continue

        item["produto"] = fb_produto

    if erros_validacao:
        msg = "Validacao de itens falhou"
        for e in erros_validacao:
            log.error(f"  {e}")
        _salvar_erro(pedido_id, "; ".join(erros_validacao))
        return {"success": False, "erros": erros_validacao, "mensagem": msg}

    # Log dos itens que serao enviados
    log.info(f"  DESTINO={destino} | DRY_RUN={dry_run}")
    for idx, item in enumerate(pedido.get("itens", [])):
        log.info(
            f"  Item {idx+1}: id_produto={item.get('id_produto')} | "
            f"produto={item.get('produto','')} | "
            f"qtd={item.get('quantidade')} | "
            f"preco=R${float(item.get('valor_unitario',0)):.2f} | "
            f"total=R${float(item.get('valor_total',0)):.2f}"
        )

    # Criar ORCAMENTO no Firebird
    log.info("  Conectando Firebird...")
    log.info("  Criando orcamento...")
    try:
        result = criar_orcamento(pedido)
    except Exception as e:
        import traceback
        erro_str = f"{e}\n{traceback.format_exc()}"
        log.error(f"  ERRO ao criar orcamento: {e}")
        log.error(traceback.format_exc())
        _salvar_erro(pedido_id, str(e))
        return {
            "success": False,
            "erros": [str(e)],
            "mensagem": f"Erro ao criar ORCAMENTO: {e}",
            "traceback": erro_str,
        }

    if not result.get("success"):
        erros = result.get("erros", ["Erro desconhecido no writer"])
        log.error(f"  ERRO do writer: {erros}")
        _salvar_erro(pedido_id, "; ".join(erros))
        return {"success": False, "erros": erros, "mensagem": "Falha na criacao do ORCAMENTO"}

    log.info("  Commit Firebird OK")
    orcamento_id = result["orcamento_id"]
    log.info(f"  ORCAMENTO #{orcamento_id} criado com sucesso")

    # Atualizar pedido no SQLite
    log.info("  Atualizando pedido no SQLite...")
    agora = datetime.datetime.now().isoformat()
    db.execute(
        """UPDATE pedidos
           SET importado = 1, orcamento_id = ?, id_orcamento_firebird = ?,
               numero_orcamento = ?, status = 'IMPORTADO',
               data_importacao = ?, erro_importacao = NULL,
               atualizado_em = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (orcamento_id, orcamento_id, orcamento_id, agora, pedido_id),
    )
    db.commit()
    log.info("  Commit SQLite OK")
    log.info(f"=== IMPORTACAO CONCLUIDA: Pedido #{pedido_id} -> ORCAMENTO #{orcamento_id} ===")

    return {
        "success": True,
        "orcamento_id": orcamento_id,
        "numero_orcamento": orcamento_id,
        "id_orcamento_firebird": orcamento_id,
        "mensagem": f"ORCAMENTO #{orcamento_id} criado com sucesso",
        "itens": result.get("itens", 0),
    }


def _salvar_erro(pedido_id, erro):
    """Salva mensagem de erro na coluna erro_importacao do pedido."""
    try:
        db = get_db()
        db.execute(
            "UPDATE pedidos SET erro_importacao = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
            [str(erro)[:1000], pedido_id],
        )
        db.commit()
    except Exception as e:
        log.error(f"  Nao foi possivel salvar erro_importacao: {e}")
