"""
Blueprint da Loja Delivery: catalogo, carrinho e checkout.
"""
import logging
import uuid
import json
import os
from flask import Blueprint, request, jsonify, render_template, redirect, send_from_directory
from werkzeug.exceptions import HTTPException

from portal.models import get_db

log = logging.getLogger("loja")

loja_bp = Blueprint("loja", __name__)


@loja_bp.errorhandler(Exception)
def handle_loja_error(e):
    if isinstance(e, HTTPException):
        return jsonify({"success": False, "error": e.description}), e.code
    log.error("Erro na rota loja: %s", e)
    return jsonify({"success": False, "error": "Erro interno do servidor"}), 500


@loja_bp.route("/loja")
def pagina_loja():
    return render_template("loja_nova.html")

@loja_bp.route("/loja2")
def pagina_loja2():
    return render_template("loja2.html")


def _sanitizar(valor, fallback=""):
    if not valor:
        return fallback
    s = str(valor).strip()
    if s.lower() in ("null", "none", "undefined", ""):
        return fallback
    return s


@loja_bp.route("/api/loja/emitente")
def api_emitente():
    db = get_db()
    row = db.execute("SELECT * FROM emitente WHERE id = 1").fetchone()
    if not row:
        return jsonify({"fantasia": "Minha Loja", "whatsapp": "", "chave_pix": "", "nome_recebedor_pix": "", "obs_pagamento_pix": ""})
    d = dict(row)
    return jsonify({
        "fantasia": _sanitizar(d.get("fantasia")) or _sanitizar(d.get("razao_social")) or "Minha Loja",
        "whatsapp": _sanitizar(d.get("whatsapp")),
        "chave_pix": _sanitizar(d.get("chave_pix")),
        "nome_recebedor_pix": _sanitizar(d.get("nome_recebedor_pix")),
        "obs_pagamento_pix": _sanitizar(d.get("obs_pagamento_pix")),
        "telefone": _sanitizar(d.get("telefone")),
        "bairro": _sanitizar(d.get("bairro")),
        "logradouro": _sanitizar(d.get("logradouro")),
    })


@loja_bp.route("/api/loja/grupos")
def api_grupos():
    db = get_db()
    rows = db.execute("""
        SELECT g.*, COUNT(p.id) as total_produtos
        FROM grupos g
        LEFT JOIN produtos p ON p.grupo = g.id_grupo AND p.status = 'ATIVO'
        GROUP BY g.id
        ORDER BY g.grupo
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@loja_bp.route("/api/loja/produtos")
def api_produtos():
    db = get_db()
    grupo = request.args.get("grupo", type=int)
    busca = request.args.get("busca", "").strip()
    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = 30
    offset = (pagina - 1) * por_pagina

    sql = "SELECT * FROM produtos WHERE status = 'ATIVO' AND valor_venda > 0 AND produto IS NOT NULL AND produto != ''"
    params = []

    if grupo:
        sql += " AND grupo = ?"
        params.append(grupo)
    if busca:
        sql += " AND (produto LIKE ? OR gtin LIKE ?)"
        params.append(f"%{busca}%")
        params.append(f"%{busca}%")

    # Total
    total = db.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]

    sql += " ORDER BY produto LIMIT ? OFFSET ?"
    params.append(por_pagina)
    params.append(offset)

    rows = db.execute(sql, params).fetchall()
    produtos = []
    for r in rows:
        d = dict(r)
        produtos.append({
            "id": d.get("id_produto"),
            "id_produto": d.get("id_produto"),
            "produto": d.get("produto"),
            "gtin": d.get("gtin"),
            "valor_venda": d.get("valor_venda", 0),
            "estoque": d.get("estoque", 0),
            "grupo": d.get("grupo", 0),
            "nome_grupo": d.get("nome_grupo") or "",
            "foto": d.get("foto") or "",
            "unidade": d.get("unidade") or "UN",
        })

    return jsonify({
        "produtos": produtos,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_paginas": (total + por_pagina - 1) // por_pagina,
    })


@loja_bp.route("/api/loja/checkout", methods=["POST"])
def api_checkout():
    try:
        data = request.json
        log.info("PEDIDO RECEBIDO: %s", json.dumps(data, ensure_ascii=False, indent=2))
        if not data:
            return jsonify({"success": False, "error": "Dados do pedido obrigatorios"}), 400

        itens = data.get("itens", [])
        if not itens:
            return jsonify({"success": False, "error": "Pedido sem itens"}), 400

        total_cliente = float(data.get("total", 0))
        log.info("DADOS CLIENTE: nome=%s fone=%s cpf=%s forma_pgto=%s",
                 data.get("nome_cliente"), data.get("fone"), data.get("cpf_cnpj"), data.get("forma_pagamento"))

        for item in itens:
            desc = (item.get("produto") or "").strip()
            if not desc:
                return jsonify({"success": False, "error": "Produto sem descricao nao pode ser adicionado ao pedido"}), 400

        nome_cliente = (data.get("nome_cliente") or "").strip()
        if not nome_cliente:
            return jsonify({"success": False, "error": "Nome do cliente obrigatorio"}), 400

        fone = (data.get("fone") or "").strip()
        if not fone:
            return jsonify({"success": False, "error": "Telefone para contato obrigatorio"}), 400

        forma_pagamento = data.get("forma_pagamento", "").upper()
        if forma_pagamento not in ("DINHEIRO", "CARTAO", "PIX"):
            return jsonify({"success": False, "error": "Forma de pagamento invalida"}), 400

        # Calcular total
        total = 0
        for item in itens:
            qtd = float(item.get("quantidade", 1))
            vlr = float(item.get("valor_unitario", 0))
            total += qtd * vlr

        log.info("ITENS: %d itens, total calculado R$ %.2f", len(itens), total)

        # Montar detalhe do pagamento
        detalhe_pgto = forma_pagamento
        if forma_pagamento == "DINHEIRO":
            troco_para = data.get("troco_para")
            if troco_para:
                detalhe_pgto = f"DINHEIRO (troco para R$ {float(troco_para):.2f})"
        elif forma_pagamento == "CARTAO":
            tipo_cartao = data.get("tipo_cartao", "").upper()
            tipos_validos = {"DEBITO", "CREDITO", "VOUCHER"}
            if tipo_cartao not in tipos_validos:
                tipo_cartao = "DEBITO"
            detalhe_pgto = f"CARTAO {tipo_cartao} (maquininha na entrega)"
        elif forma_pagamento == "PIX":
            detalhe_pgto = "PIX"

        observacao = data.get("observacao", "").strip()
        endereco = f"{data.get('logradouro','')}, {data.get('numero','')}"
        bairro = data.get("bairro", "")
        comp = data.get("complemento", "")
        if comp:
            endereco += f" - {comp}"
        if bairro:
            endereco += f" - {bairro}"

        db = get_db()
        id_externo = str(uuid.uuid4())

        cur = db.execute("""
            INSERT INTO pedidos (
                id_externo, nome_cliente, fone, cpf_cnpj,
                logradouro_entrega, numero_entrega, bairro_entrega, complemento,
                cidade, referencia,
                valor_total, forma_pagamento, forma_pagamento_detalhe,
                troco_para, tipo_cartao, observacao, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE')
        """, (
            id_externo,
            nome_cliente,
            fone,
            data.get("cpf_cnpj", ""),
            data.get("logradouro", ""),
            data.get("numero", ""),
            data.get("bairro", ""),
            data.get("complemento", ""),
            data.get("cidade", ""),
            data.get("referencia", ""),
            total,
            forma_pagamento,
            detalhe_pgto,
            data.get("troco_para"),
            data.get("tipo_cartao", ""),
            observacao,
        ))
        pedido_id = cur.lastrowid

        for item in itens:
            qtd = float(item.get("quantidade", 1))
            vlr = float(item.get("valor_unitario", 0))
            db.execute("""
                INSERT INTO pedido_itens (id_pedido, id_produto, produto, gtin, unidade, quantidade, valor_unitario, valor_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pedido_id,
                item.get("id_produto"),
                item.get("produto", ""),
                item.get("gtin", ""),
                item.get("unidade", "UN"),
                qtd,
                vlr,
                qtd * vlr,
            ))

        db.commit()

        log.info("Pedido #%d criado na loja: %s - R$ %.2f (%s)", pedido_id, nome_cliente, total, detalhe_pgto)

        return jsonify({
            "success": True,
            "ok": True,
            "id": pedido_id,
            "pedido_id": pedido_id,
            "id_externo": id_externo,
            "total": total,
            "message": "Pedido enviado com sucesso",
        }), 201

    except Exception as e:
        log.error("ERRO ao criar pedido: %s", e)
        import traceback
        log.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Erro interno ao processar pedido: {str(e)}",
        }), 500


@loja_bp.route("/api/loja/produto/<int:produto_id>/foto")
def api_foto_produto(produto_id):
    """Redireciona para a foto real do produto. Se não existir, retorna 404."""
    db = get_db()
    row = db.execute("SELECT foto FROM produtos WHERE id_produto = ?", [produto_id]).fetchone()
    if not row or not row["foto"]:
        return "", 404
    return redirect(f"/api/loja/produto-imagem/{row['foto']}")


@loja_bp.route("/api/loja/produto-imagem/<path:filename>")
def servir_imagem_produto(filename):
    """Serve a imagem real do produto do disco local."""
    import os
    safe_name = os.path.basename(filename)
    caminho = os.path.join(IMAGENS_PRODUTOS_DIR, safe_name)
    if not os.path.isfile(caminho):
        return "", 404
    return send_from_directory(IMAGENS_PRODUTOS_DIR, safe_name)


CATEGORIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "img", "categorias")
IMAGENS_PRODUTOS_DIR = os.getenv("IMAGENS_PRODUTOS_DIR", "").strip() or r"C:\TSD\Host\imgProdutos"


@loja_bp.route("/static/img/categorias/<path:filename>")
def servir_fallback_categoria(filename):
    return send_from_directory(CATEGORIA_DIR, filename)


def _grupo_para_slug(grupo_nome):
    mapping = {
        "acougue": "acougue",
        "hortifruti": "hortifruti",
        "bebidas": "bebidas",
        "limpeza": "limpeza",
        "mercearia": "mercearia",
        "padaria": "padaria",
        "frios": "frios",
        "laticinios": "frios",
        "higiene": "higiene",
    }
    for key, slug in mapping.items():
        if key in grupo_nome:
            return slug
    return "sem-imagem"
