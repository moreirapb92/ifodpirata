"""
Blueprint com rotas administrativas: configuracao e importacao de pedidos.
"""
import datetime
import logging
from flask import Blueprint, request, jsonify, render_template

from portal.models import get_db
from config.settings import MODO_ONLINE

log = logging.getLogger("admin")

admin_bp = Blueprint("admin", __name__)


# ===== Paginas =====

@admin_bp.route("/admin/configuracao")
def pagina_configuracao():
    return render_template("admin_config.html")


@admin_bp.route("/admin/pedidos-importacao")
def pagina_importacao():
    return render_template("admin_importacao.html", MODO_ONLINE=str(MODO_ONLINE).lower())


# ===== API: Config =====

@admin_bp.route("/api/admin/config", methods=["GET"])
def get_config():
    db = get_db()
    rows = db.execute("SELECT chave, valor FROM config").fetchall()
    return jsonify({r["chave"]: r["valor"] for r in rows})


@admin_bp.route("/api/admin/config", methods=["POST"])
def set_config():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    db = get_db()
    permitidas = {"dry_run", "destino_pedido", "sync_interval", "modo_teste"}
    atualizadas = {}
    for chave, valor in data.items():
        if chave not in permitidas:
            continue
        db.execute(
            "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
            (chave, str(valor)),
        )
        atualizadas[chave] = str(valor)
    db.commit()
    log.info(f"Config atualizada: {atualizadas}")
    return jsonify({"ok": True, "atualizadas": atualizadas})


# ===== API: Pedidos para importacao =====

@admin_bp.route("/api/admin/pedidos-importacao", methods=["GET"])
def listar_pedidos_importacao():
    """Lista pedidos ACEITOS + IMPORTADOS + IGNORADOS com controle de importacao."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM pedidos
        WHERE status IN ('ACEITO', 'IMPORTADO', 'IGNORADO')
        ORDER BY criado_em DESC
    """).fetchall()
    result = []
    for r in rows:
        p = dict(r)
        itens = db.execute(
            "SELECT * FROM pedido_itens WHERE id_pedido = ?", [p["id"]]
        ).fetchall()
        p["itens"] = [dict(i) for i in itens]
        result.append(p)
    return jsonify(result)


def _modo_online_error():
    return jsonify({"error": "Importacao desativada no modo online. Use o agente local para importar pedidos."}), 400

@admin_bp.route("/api/admin/pedidos/<int:pedido_id>/simular", methods=["POST"])
def simular_importacao(pedido_id):
    """Simula a importacao (valida sem gravar) com detalhes por item."""
    if MODO_ONLINE:
        return _modo_online_error()
    from agent.writer import validar_pedido

    db = get_db()
    row = db.execute("SELECT * FROM pedidos WHERE id = ?", [pedido_id]).fetchone()
    if not row:
        return jsonify({"error": "Pedido nao encontrado"}), 404

    pedido = _montar_pedido_para_importacao(row)
    erros = validar_pedido(pedido)

    # Validar cada item no Firebird
    from agent.db import query
    itens_validacao = []
    for item in pedido.get("itens", []):
        info = {
            "id_produto": item.get("id_produto"),
            "produto": item.get("produto", ""),
            "quantidade": item.get("quantidade"),
            "valor_unitario": float(item.get("valor_unitario", 0)),
            "valor_total": float(item.get("valor_total", 0)),
            "existe_firebird": False,
            "status_firebird": None,
            "nome_firebird": None,
        }
        pid = item.get("id_produto")
        if pid:
            cols, rows = query("SELECT ID_PRODUTO, STATUS, PRODUTO FROM PRODUTOS WHERE ID_PRODUTO = ?", [pid])
            if rows:
                info["existe_firebird"] = True
                info["status_firebird"] = rows[0][1]
                info["nome_firebird"] = rows[0][2]
        itens_validacao.append(info)

    return jsonify({
        "ok": True,
        "simulacao": True,
        "pedido_id": pedido_id,
        "valido": len(erros) == 0,
        "erros": erros,
        "dados": {
            "cliente": pedido.get("nome_cliente"),
            "fone": pedido.get("fone_cliente", ""),
            "pagamento": pedido.get("forma_pagamento", ""),
            "itens": len(pedido.get("itens", [])),
            "total": float(pedido.get("valor_total", 0)),
            "tabela_destino": "ORCAMENTO + ORCAMENTO_ITENS" + (" + ORCAMENTO_TOTAL_TIPO_PGTO" if pedido.get("forma_pagamento") else ""),
            "status_orcamento": "ABERTO (Orcamento Livre)",
        },
        "itens_validacao": itens_validacao,
    })


@admin_bp.route("/api/admin/pedidos/<int:pedido_id>/importar", methods=["POST"])
def importar_pedido(pedido_id):
    """Importa o pedido como ORCAMENTO no Firebird. Usa o importador centralizado."""
    if MODO_ONLINE:
        return _modo_online_error()
    from portal.importer import importar_pedido_para_orcamento
    result = importar_pedido_para_orcamento(pedido_id)
    if result.get("success"):
        return jsonify({
            "ok": True,
            "pedido_id": pedido_id,
            "orcamento_id": result["orcamento_id"],
            "numero_orcamento": result.get("numero_orcamento"),
            "itens": result.get("itens", 0),
            "total": float(result.get("total", 0)),
        })
    else:
        status_code = 400
        if result.get("dry_run"):
            status_code = 400
        return jsonify({
            "ok": False,
            "erro": result.get("mensagem", "Erro desconhecido"),
            "erros": result.get("erros", []),
            "dry_run": result.get("dry_run", False),
            "detalhes": {
                "pedido_id": pedido_id,
            },
        }), status_code


@admin_bp.route("/api/admin/pedidos/<int:pedido_id>/diagnosticar", methods=["GET"])
def diagnosticar_pedido(pedido_id):
    """Retorna diagnostico completo do pedido + validacao por item no Firebird."""
    if MODO_ONLINE:
        return _modo_online_error()
    from portal.importer import diagnosticar_pedido
    diag = diagnosticar_pedido(pedido_id)
    if "erro" in diag:
        return jsonify({"error": diag["erro"]}), 404
    return jsonify(diag)


@admin_bp.route("/api/admin/pedidos/<int:pedido_id>/ignorar", methods=["POST"])
def ignorar_pedido(pedido_id):
    db = get_db()
    row = db.execute("SELECT * FROM pedidos WHERE id = ?", [pedido_id]).fetchone()
    if not row:
        return jsonify({"error": "Pedido nao encontrado"}), 404
    db.execute(
        "UPDATE pedidos SET status = 'IGNORADO', atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
        [pedido_id],
    )
    db.commit()
    return jsonify({"ok": True, "status": "IGNORADO"})


@admin_bp.route("/api/admin/pedidos/<int:pedido_id>/cancelar", methods=["POST"])
def cancelar_pedido(pedido_id):
    db = get_db()
    row = db.execute("SELECT * FROM pedidos WHERE id = ?", [pedido_id]).fetchone()
    if not row:
        return jsonify({"error": "Pedido nao encontrado"}), 404
    if row["importado"]:
        return jsonify({"error": "Pedido ja importado, nao pode ser cancelado"}), 400
    db.execute(
        "UPDATE pedidos SET status = 'CANCELADO', atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
        [pedido_id],
    )
    db.commit()
    return jsonify({"ok": True, "status": "CANCELADO"})


@admin_bp.route("/api/admin/pedidos/limpar", methods=["POST"])
def limpar_pedidos_antigos():
    """Cancela todos os pedidos ACEITOS nao importados de uma vez."""
    data = request.get_json(silent=True) or {}
    confirm = data.get("confirm", "")
    if confirm != "SIM":
        return jsonify({"error": 'Envie {"confirm": "SIM"} para confirmar'}), 400

    db = get_db()
    db.execute(
        """UPDATE pedidos SET status = 'CANCELADO', atualizado_em = CURRENT_TIMESTAMP
           WHERE status = 'ACEITO' AND (importado IS NULL OR importado = 0)"""
    )
    db.commit()
    afetados = db.total_changes
    return jsonify({"ok": True, "cancelados": afetados})


# ===== Helpers =====

def _montar_pedido_para_importacao(row):
    """Converte uma linha do banco portal no formato esperado por criar_orcamento.
    Monta uma observacao completa com dados de cliente, endereco e pagamento."""
    db = get_db()
    p = dict(row)
    itens_rows = db.execute(
        "SELECT * FROM pedido_itens WHERE id_pedido = ?", [p["id"]]
    ).fetchall()
    itens = []
    for i in itens_rows:
        i = dict(i)
        itens.append({
            "id_produto": i.get("id_produto"),
            "produto": i.get("produto", ""),
            "gtin": i.get("gtin", ""),
            "quantidade": float(i.get("quantidade", 1)),
            "valor_unitario": float(i.get("valor_unitario", 0)),
            "valor_total": float(i.get("valor_total", 0)),
        })

    # Enriquecer itens com dados do Firebird
    from agent.db import query as fb_query
    for item in itens:
        pid = item.get("id_produto")
        if pid:
            cols, rows = fb_query(
                "SELECT ID_PRODUTO, PRODUTO, UNIDADE_COMECIAL, VALOR_VENDA FROM PRODUTOS WHERE ID_PRODUTO = ?",
                [pid],
            )
            if rows:
                nome_fb = (rows[0][1] or "").strip()
                if nome_fb:
                    item["produto"] = nome_fb
                unidade_fb = (rows[0][2] or "UN").strip()
                item["unidade"] = unidade_fb

    # Compor observacao completa
    obs = "PEDIDO ONLINE"
    obs += f"\nCliente: {p.get('nome_cliente', '')}"
    obs += f"\nTelefone: {p.get('fone', '')}"
    cpf = p.get("cpf_cnpj", "") or ""
    if cpf.strip():
        obs += f"\nCPF/CNPJ: {cpf}"
    endereco_parts = []
    if p.get("logradouro_entrega"):
        endereco_parts.append(p["logradouro_entrega"])
    if p.get("numero_entrega"):
        endereco_parts.append(f"N {p['numero_entrega']}")
    if endereco_parts:
        obs += f"\nEndereco: {', '.join(endereco_parts)}"
    if p.get("bairro_entrega"):
        obs += f"\nBairro: {p['bairro_entrega']}"
    if p.get("cidade"):
        obs += f"\nCidade: {p['cidade']}"
    if p.get("referencia"):
        obs += f"\nReferencia: {p['referencia']}"
    if p.get("complemento"):
        obs += f"\nComplemento: {p['complemento']}"

    pgto = p.get("forma_pagamento", "")
    if pgto:
        if pgto == "DINHEIRO":
            troco = p.get("troco_para")
            obs += f"\nPagamento: DINHEIRO"
            if troco:
                obs += f" (troco para R$ {float(troco):.2f})"
        elif pgto == "CARTAO":
            tipo = p.get("tipo_cartao", "")
            obs += f"\nPagamento: CARTAO"
            if tipo:
                obs += f" ({tipo})"
            obs += " (maquininha na entrega)"
        elif pgto == "PIX":
            obs += f"\nPagamento: PIX"
    obs_extra = p.get("observacao", "") or ""
    if obs_extra.strip():
        obs += f"\nObservacao: {obs_extra.strip()}"

    log.info(f"--- OBS composta para ORCAMENTO.OBS ---")
    log.info(f"{obs}")
    log.info(f"--- Serah gravada no campo OBS da tabela ORCAMENTO ---")

    return {
        "id_externo": p.get("id_externo"),
        "id_cliente": p.get("id_cliente"),
        "nome_cliente": p.get("nome_cliente", ""),
        "cpf_cnpj": p.get("cpf_cnpj", ""),
        "fone_cliente": p.get("fone", ""),
        "logradouro": (p.get("logradouro_entrega") or "").strip(),
        "numero": (p.get("numero_entrega") or "").strip(),
        "bairro": (p.get("bairro_entrega") or "").strip(),
        "cidade": (p.get("cidade") or "").strip(),
        "complemento": (p.get("complemento") or "").strip(),
        "referencia": (p.get("referencia") or "").strip(),
        "observacao": obs,
        "valor_total": float(p.get("valor_total", 0)),
        "desconto": float(p.get("desconto", 0)),
        "forma_pagamento": p.get("forma_pagamento", ""),
        "itens": itens,
    }
