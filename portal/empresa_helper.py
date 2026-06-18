"""
Helpers para resolucao de empresa (multi-tenant).
"""
import logging
from flask import session, request

from portal.models import get_db

log = logging.getLogger("empresa_helper")


def get_empresa_by_slug(slug):
    db = get_db()
    return db.execute(
        "SELECT * FROM empresas WHERE slug = ? AND ativo = 1", [slug]
    ).fetchone()


def get_empresa_by_api_key(api_key):
    db = get_db()
    return db.execute(
        "SELECT * FROM empresas WHERE api_key = ? AND ativo = 1", [api_key]
    ).fetchone()


def get_empresa_by_id(empresa_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM empresas WHERE id = ?", [empresa_id]
    ).fetchone()


def get_empresa_from_session():
    empresa_id = session.get("empresa_id")
    if not empresa_id:
        return None
    return get_empresa_by_id(empresa_id)


def set_empresa_session(empresa_id):
    session["empresa_id"] = empresa_id


def get_empresa_from_request():
    """Tenta obter empresa da request: session (loja) ou API key (sync)."""
    empresa = get_empresa_from_session()
    if empresa:
        return empresa
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        empresa = get_empresa_by_api_key(api_key)
        if empresa:
            return empresa
    # Master API key from env
    import os
    master_key = os.getenv("PORTAL_API_KEY", "")
    if api_key and api_key == master_key:
        master_empresa = get_empresa_by_slug("demo")
        if master_empresa:
            return master_empresa
    return None


def listar_empresas():
    db = get_db()
    rows = db.execute("SELECT * FROM empresas ORDER BY nome_fantasia").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        eid = d["id"]
        d["total_produtos"] = db.execute(
            "SELECT COUNT(*) FROM produtos WHERE empresa_id = ?", [eid]
        ).fetchone()[0]
        d["total_pedidos"] = db.execute(
            "SELECT COUNT(*) FROM pedidos WHERE empresa_id = ?", [eid]
        ).fetchone()[0]
        result.append(d)
    return result


def criar_empresa(nome_fantasia, razao_social="", cnpj="", telefone="",
                  cidade="", endereco="", slug=None):
    import uuid
    import re

    if not slug:
        slug = re.sub(r'[^a-z0-9]+', '-', nome_fantasia.lower()).strip('-')
        if not slug:
            slug = "empresa"
        # Ensure unique slug
        db = get_db()
        existing = db.execute("SELECT id FROM empresas WHERE slug = ?", [slug]).fetchone()
        if existing:
            slug = f"{slug}-{str(uuid.uuid4())[:8]}"
    else:
        db = get_db()

    api_key = str(uuid.uuid4())
    db = get_db()
    db.execute(
        """INSERT INTO empresas (nome_fantasia, razao_social, cnpj, telefone, cidade, endereco, slug, api_key, ativo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (nome_fantasia, razao_social, cnpj, telefone, cidade, endereco, slug, api_key),
    )
    db.commit()
    row = db.execute("SELECT * FROM empresas WHERE slug = ?", [slug]).fetchone()
    return dict(row) if row else None


def atualizar_empresa(empresa_id, dados):
    db = get_db()
    campos = []
    valores = []
    for chave in ("nome_fantasia", "razao_social", "cnpj", "telefone", "cidade", "endereco", "ativo"):
        if chave in dados:
            campos.append(f"{chave} = ?")
            valores.append(dados[chave])
    if not campos:
        return None
    valores.append(empresa_id)
    db.execute(f"UPDATE empresas SET {', '.join(campos)} WHERE id = ?", valores)
    db.commit()
    return dict(db.execute("SELECT * FROM empresas WHERE id = ?", [empresa_id]).fetchone())


def regenerar_api_key(empresa_id):
    import uuid
    nova_key = str(uuid.uuid4())
    db = get_db()
    db.execute("UPDATE empresas SET api_key = ? WHERE id = ?", [nova_key, empresa_id])
    db.commit()
    return nova_key
