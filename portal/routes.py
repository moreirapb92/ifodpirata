import sqlite3
import json
import os
from flask import Blueprint, request, jsonify, g, render_template, redirect, url_for, flash

from portal.models import get_db, init_db

api = Blueprint("api", __name__, url_prefix="/api")

# API Key for agent authentication
AGENT_API_KEY = os.getenv("PORTAL_API_KEY", "agent-api-key-change-me")


# ----- Authentication -----
def check_api_key():
    auth = request.headers.get("X-API-Key", "")
    if auth != AGENT_API_KEY:
        return False
    return True


def require_api_key(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_api_key() and request.method != "GET":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ----- Agent: Sync data from Firebird -----
def _sanitizar_emitente(valor):
    if not valor:
        return None
    s = str(valor).strip()
    if s.lower() in ("null", "none", "undefined", ""):
        return None
    return s

@api.route("/sync/emitente", methods=["POST"])
@require_api_key
def sync_emitente():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    db = get_db()
    fantasia = _sanitizar_emitente(data.get("FANTASIA")) or _sanitizar_emitente(data.get("RAZ_SOCIAL")) or "Minha Loja"
    db.execute("DELETE FROM emitente")
    db.execute("""INSERT INTO emitente (id, fantasia, razao_social, cnpj, ie, municipio, uf, logradouro, bairro, telefone, email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (1, fantasia, data.get("RAZ_SOCIAL"), data.get("CNPJ"),
         data.get("INSC_EST"), data.get("MUNICIPIO"), data.get("UF"),
         data.get("ENDER"), data.get("BAIRRO"), data.get("TELEFONE"), data.get("EMAIL")))
    db.commit()
    return jsonify({"ok": True, "emitente": fantasia})


@api.route("/sync/produtos", methods=["POST"])
@require_api_key
def sync_produtos():
    data = request.json
    if not data or "produtos" not in data:
        return jsonify({"error": "No produtos"}), 400
    db = get_db()
    db.execute("DELETE FROM produtos")
    for p in data["produtos"]:
        db.execute("""INSERT INTO produtos (id_produto, produto, gtin, ncm, unidade,
            valor_venda, valor_atacado, valor_aprazo, estoque,
            grupo, subgrupo, marca, nome_grupo, nome_subgrupo, nome_marca,
            foto, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (p.get("ID_PRODUTO"), p.get("PRODUTO"), p.get("GTIN"), p.get("NCM"),
             p.get("UNIDADE"), p.get("VALOR_VENDA"), p.get("VALOR_ATACADO"),
             p.get("VALOR_APRAZO"), p.get("ESTOQUE"),
             p.get("GRUPO"), p.get("SUBGRUPO"), p.get("MARCA"),
             p.get("NOME_GRUPO"), p.get("NOME_SUBGRUPO"), p.get("NOME_MARCA"),
             p.get("FOTO"), p.get("STATUS")))
    db.commit()
    return jsonify({"ok": True, "count": len(data["produtos"])})


@api.route("/sync/grupos", methods=["POST"])
@require_api_key
def sync_grupos():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    db = get_db()
    db.execute("DELETE FROM grupos")
    db.execute("DELETE FROM subgrupos")
    for g in data.get("grupos", []):
        db.execute("INSERT INTO grupos (id_grupo, grupo, desconto) VALUES (?, ?, ?)",
                   (g.get("ID"), g.get("GRUPO"), g.get("DESCONTO")))
    for s in data.get("subgrupos", []):
        db.execute("INSERT INTO subgrupos (id_subgrupo, subgrupo, id_grupo) VALUES (?, ?, ?)",
                   (s.get("ID"), s.get("SUBGRUPO"), s.get("ID_GRUPO")))
    for m in data.get("marcas", []):
        db.execute("INSERT INTO marcas (id_marca, marca) VALUES (?, ?)",
                   (m.get("ID"), m.get("MARCA")))
    db.commit()
    return jsonify({"ok": True})


@api.route("/sync/clientes", methods=["POST"])
@require_api_key
def sync_clientes():
    data = request.json
    if not data or "clientes" not in data:
        return jsonify({"error": "No clientes"}), 400
    db = get_db()
    db.execute("DELETE FROM clientes")
    for c in data["clientes"]:
        db.execute("""INSERT INTO clientes (id_cliente, cliente, cpf_cnpj, ie_rg,
            logradouro, numero, bairro, municipio, uf, cep,
            fone, celular, email, status, limite_credito)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (c.get("ID_CLIENTE"), c.get("CLIENTE"), c.get("CPF_CNPJ"),
             c.get("IE_RG"), c.get("LOGRADOURO"), c.get("NUMERO"),
             c.get("BAIRRO"), c.get("MUNICIPIO"), c.get("UF"), c.get("CEP"),
             c.get("FONE"), c.get("CELULAR"), c.get("EMAIL"),
             c.get("STATUS"), c.get("LMTE_CREDITO")))
    db.commit()
    return jsonify({"ok": True, "count": len(data["clientes"])})


@api.route("/sync/full", methods=["POST"])
@require_api_key
def sync_full():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    db = get_db()
    # Emitente (sanitizado)
    emit = data.get("emitente")
    if emit:
        db.execute("DELETE FROM emitente")
        fantasia = _sanitizar_emitente(emit.get("FANTASIA")) or _sanitizar_emitente(emit.get("RAZ_SOCIAL")) or "Minha Loja"
        db.execute("""INSERT INTO emitente (id, fantasia, razao_social, cnpj, ie, municipio, uf, logradouro, bairro, telefone, email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, fantasia, emit.get("RAZ_SOCIAL"), emit.get("CNPJ"),
             emit.get("INSC_EST"), emit.get("MUNICIPIO"), emit.get("UF"),
             emit.get("ENDER"), emit.get("BAIRRO"), emit.get("TELEFONE"), emit.get("EMAIL")))
    # Produtos
    db.execute("DELETE FROM produtos")
    for p in data.get("produtos", []):
        db.execute("""INSERT INTO produtos (id_produto, produto, gtin, ncm, unidade,
            valor_venda, valor_atacado, valor_aprazo, estoque,
            grupo, subgrupo, marca, nome_grupo, nome_subgrupo, nome_marca, foto, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (p.get("ID_PRODUTO"), p.get("PRODUTO"), p.get("GTIN"), p.get("NCM"),
             p.get("UNIDADE"), p.get("VALOR_VENDA"), p.get("VALOR_ATACADO"),
             p.get("VALOR_APRAZO"), p.get("ESTOQUE"),
             p.get("GRUPO"), p.get("SUBGRUPO"), p.get("MARCA"),
             p.get("NOME_GRUPO"), p.get("NOME_SUBGRUPO"), p.get("NOME_MARCA"),
             p.get("FOTO"), p.get("STATUS")))
    # Grupos
    db.execute("DELETE FROM grupos")
    for g in data.get("grupos", []):
        db.execute("INSERT INTO grupos (id_grupo, grupo, desconto) VALUES (?, ?, ?)",
                   (g.get("ID"), g.get("GRUPO"), g.get("DESCONTO")))
    db.execute("DELETE FROM subgrupos")
    for s in data.get("subgrupos", []):
        db.execute("INSERT INTO subgrupos (id_subgrupo, subgrupo, id_grupo) VALUES (?, ?, ?)",
                   (s.get("ID"), s.get("SUBGRUPO"), s.get("ID_GRUPO")))
    db.execute("DELETE FROM marcas")
    for m in data.get("marcas", []):
        db.execute("INSERT INTO marcas (id_marca, marca) VALUES (?, ?)",
                   (m.get("ID"), m.get("MARCA")))
    # Clientes
    db.execute("DELETE FROM clientes")
    for c in data.get("clientes", []):
        db.execute("""INSERT INTO clientes (id_cliente, cliente, cpf_cnpj, ie_rg,
            logradouro, numero, bairro, municipio, uf, cep,
            fone, celular, email, status, limite_credito)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (c.get("ID_CLIENTE"), c.get("CLIENTE"), c.get("CPF_CNPJ"),
             c.get("IE_RG"), c.get("LOGRADOURO"), c.get("NUMERO"),
             c.get("BAIRRO"), c.get("MUNICIPIO"), c.get("UF"), c.get("CEP"),
             c.get("FONE"), c.get("CELULAR"), c.get("EMAIL"),
             c.get("STATUS"), c.get("LMTE_CREDITO")))
    db.commit()
    return jsonify({"ok": True, "produtos": len(data.get("produtos", [])), "clientes": len(data.get("clientes", []))})


# ----- Portal: Order management -----
@api.route("/pedidos", methods=["GET"])
def list_pedidos():
    db = get_db()
    status = request.args.get("status")
    if status:
        rows = db.execute("SELECT * FROM pedidos WHERE status = ? ORDER BY criado_em DESC", [status]).fetchall()
    else:
        rows = db.execute("SELECT * FROM pedidos ORDER BY criado_em DESC").fetchall()
    pedidos = []
    for r in rows:
        p = dict(r)
        itens = db.execute("SELECT * FROM pedido_itens WHERE id_pedido = ?", [p["id"]]).fetchall()
        p["itens"] = [dict(i) for i in itens]
        pedidos.append(p)
    return jsonify(pedidos)


@api.route("/pedidos", methods=["POST"])
def criar_pedido():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    db = get_db()

    # Generate a unique external ID
    import uuid
    id_externo = str(uuid.uuid4())

    cur = db.execute("""INSERT INTO pedidos (id_externo, id_cliente, nome_cliente, cpf_cnpj, fone,
        valor_total, desconto, observacao, forma_pagamento, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE')""",
        (id_externo, data.get("id_cliente"), data.get("nome_cliente"),
         data.get("cpf_cnpj"), data.get("fone_cliente", ""),
         data.get("valor_total", 0),
         data.get("desconto", 0), data.get("observacao"),
         data.get("forma_pagamento")))
    pedido_id = cur.lastrowid

    for item in data.get("itens", []):
        db.execute("""INSERT INTO pedido_itens (id_pedido, id_produto, produto, gtin,
            quantidade, valor_unitario, valor_total)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (pedido_id, item.get("id_produto"), item.get("produto"),
             item.get("gtin"), item.get("quantidade", 1),
             item.get("valor_unitario", 0), item.get("valor_total", 0)))

    db.commit()
    return jsonify({"ok": True, "id": pedido_id, "id_externo": id_externo}), 201


@api.route("/pedidos/<int:pedido_id>", methods=["GET"])
def get_pedido(pedido_id):
    db = get_db()
    row = db.execute("SELECT * FROM pedidos WHERE id = ?", [pedido_id]).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    p = dict(row)
    itens = db.execute("SELECT * FROM pedido_itens WHERE id_pedido = ?", [pedido_id]).fetchall()
    p["itens"] = [dict(i) for i in itens]
    return jsonify(p)


@api.route("/pedidos/<int:pedido_id>/aceitar", methods=["POST"])
def aceitar_pedido(pedido_id):
    """Aceita o pedido, marcando para sincronização com o Firebird."""
    db = get_db()
    row = db.execute("SELECT * FROM pedidos WHERE id = ?", [pedido_id]).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    if row["status"] != "PENDENTE":
        return jsonify({"error": f"Pedido já está {row['status']}"}), 400
    db.execute("UPDATE pedidos SET status = 'ACEITO', atualizado_em = CURRENT_TIMESTAMP WHERE id = ?", [pedido_id])
    db.commit()
    return jsonify({"ok": True, "status": "ACEITO"})


@api.route("/pedidos/<int:pedido_id>/recusar", methods=["POST"])
def recusar_pedido(pedido_id):
    db = get_db()
    row = db.execute("SELECT * FROM pedidos WHERE id = ?", [pedido_id]).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    db.execute("UPDATE pedidos SET status = 'RECUSADO', atualizado_em = CURRENT_TIMESTAMP WHERE id = ?", [pedido_id])
    db.commit()
    return jsonify({"ok": True, "status": "RECUSADO"})


# ----- Agent: Pull accepted orders -----
@api.route("/sync/pedidos-pendentes", methods=["GET"])
@require_api_key
def pedidos_pendentes():
    db = get_db()
    rows = db.execute("SELECT * FROM pedidos WHERE status = 'ACEITO' AND sincronizado = 0 ORDER BY criado_em").fetchall()
    pedidos = []
    for r in rows:
        p = dict(r)
        itens = db.execute("SELECT * FROM pedido_itens WHERE id_pedido = ?", [p["id"]]).fetchall()
        p["itens"] = [dict(i) for i in itens]
        pedidos.append(p)
    return jsonify(pedidos)


@api.route("/sync/pedidos/<pedido_id>/confirmar-sincronizacao", methods=["POST"])
@require_api_key
def confirmar_sincronizacao(pedido_id):
    db = get_db()
    db.execute("UPDATE pedidos SET sincronizado = 1, status = 'FINALIZADO', atualizado_em = CURRENT_TIMESTAMP WHERE id_externo = ?", [pedido_id])
    db.commit()
    return jsonify({"ok": True})


@api.route("/sync/pedidos/<pedido_id>/atualizar", methods=["POST"])
@require_api_key
def atualizar_pedido_agente(pedido_id):
    """
    O agente local chama este endpoint APOS importar um pedido no Firebird.
    Body:
      { "status": "IMPORTADO",
        "orcamento_id": 123,
        "numero_orcamento": 123,
        "erro_importacao": null }
    ou:
      { "status": "ERRO_IMPORTACAO",
        "erro_importacao": "Mensagem de erro" }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    db = get_db()
    row = db.execute("SELECT * FROM pedidos WHERE id_externo = ?", [pedido_id]).fetchone()
    if not row:
        return jsonify({"error": "Pedido nao encontrado"}), 404
    status = data.get("status", "IMPORTADO")
    orcamento_id = data.get("orcamento_id")
    numero_orcamento = data.get("numero_orcamento")
    erro = data.get("erro_importacao")
    now = __import__("datetime").datetime.now().isoformat()
    db.execute("""UPDATE pedidos SET
        status = ?, sincronizado = 1,
        orcamento_id = ?, id_orcamento_firebird = ?,
        numero_orcamento = ?,
        erro_importacao = ?, importado = ?,
        data_importacao = ?,
        atualizado_em = CURRENT_TIMESTAMP
        WHERE id_externo = ?""",
        (status,
         orcamento_id, orcamento_id, numero_orcamento,
         erro, 1 if status == "IMPORTADO" else 0,
         now if status == "IMPORTADO" else None,
         pedido_id))
    db.commit()
    return jsonify({"ok": True, "pedido_id": pedido_id, "status": status})


# ----- Portal: Public queries -----
@api.route("/produtos", methods=["GET"])
def list_produtos():
    db = get_db()
    search = request.args.get("search", "")
    grupo = request.args.get("grupo")
    if search:
        rows = db.execute("SELECT * FROM produtos WHERE produto LIKE ? ORDER BY produto LIMIT 100", [f"%{search}%"]).fetchall()
    elif grupo:
        rows = db.execute("SELECT * FROM produtos WHERE grupo = ? ORDER BY produto LIMIT 100", [grupo]).fetchall()
    else:
        rows = db.execute("SELECT * FROM produtos ORDER BY produto LIMIT 100").fetchall()
    return jsonify([dict(r) for r in rows])


@api.route("/clientes", methods=["GET"])
def list_clientes():
    db = get_db()
    search = request.args.get("search", "")
    if search:
        rows = db.execute("SELECT * FROM clientes WHERE cliente LIKE ? OR cpf_cnpj LIKE ? ORDER BY cliente LIMIT 50",
                          [f"%{search}%", f"%{search}%"]).fetchall()
    else:
        rows = db.execute("SELECT * FROM clientes ORDER BY cliente LIMIT 50").fetchall()
    return jsonify([dict(r) for r in rows])


@api.route("/grupos", methods=["GET"])
def list_grupos():
    db = get_db()
    rows = db.execute("SELECT * FROM grupos ORDER BY grupo").fetchall()
    result = [dict(r) for r in rows]
    sub = db.execute("SELECT * FROM subgrupos ORDER BY subgrupo").fetchall()
    mar = db.execute("SELECT * FROM marcas ORDER BY marca").fetchall()
    return jsonify({"grupos": result, "subgrupos": [dict(s) for s in sub], "marcas": [dict(m) for m in mar]})


@api.route("/emitente", methods=["GET"])
def get_emitente():
    db = get_db()
    row = db.execute("SELECT * FROM emitente WHERE id = 1").fetchone()
    if not row:
        return jsonify({"fantasia": "Minha Loja"})
    d = dict(row)
    fantasia = _sanitizar_emitente(d.get("fantasia")) or _sanitizar_emitente(d.get("razao_social")) or "Minha Loja"
    d["fantasia"] = fantasia
    return jsonify(d)


@api.route("/admin/reset", methods=["POST"])
def admin_reset():
    data = request.get_json(silent=True) or {}
    confirm = data.get("confirm", "")
    if confirm != "SIM":
        return jsonify({"error": 'Envie {"confirm": "SIM"} para confirmar'}), 400
    db = get_db()
    db.executescript("""
        DELETE FROM pedido_itens;
        DELETE FROM pedidos;
        DELETE FROM produtos;
        DELETE FROM clientes;
        DELETE FROM grupos;
        DELETE FROM subgrupos;
        DELETE FROM marcas;
        DELETE FROM emitente;
    """)
    db.commit()
    return jsonify({"ok": True, "message": "Dados locais do portal zerados. Firebird intacto."})
