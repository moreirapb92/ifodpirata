import datetime
from decimal import Decimal
from agent.db import query


def ler_produtos(apenas_ativos=True, apenas_com_estoque=False):
    sql = """
        SELECT
            p.ID_PRODUTO,
            p.PRODUTO,
            p.DESCRICAO_COMPRA,
            p.GTIN,
            p.BARRAS,
            p.NCM,
            p.CEST,
            p.UNIDADE_COMECIAL AS UNIDADE,
            p.VALOR_VENDA,
            p.VALOR_ATACADO,
            p.VALOR_APRAZO,
            p.ESTOQUE,
            p.ESTOQUE_ANT,
            p.CUSTO,
            p.MARGEM,
            p.PESO_LIQUIDO,
            p.PESO_BRUTO,
            p.REFERENCIA,
            p.MARCA,
            p.GRUPO,
            p.SUBGRUPO,
            p.CFOP,
            p.CST,
            p.CSOSN,
            p.ICMS,
            p.STATUS,
            p.DT_CADASTRO,
            p.DT_ULTIMO_MOVIMENTO,
            p.FOTO,
            p.OBS,
            p.LOCALIZACAO,
            p.SECAO,
            g.GRUPO AS NOME_GRUPO,
            s.SUBGRUPO AS NOME_SUBGRUPO,
            m.MARCA AS NOME_MARCA
        FROM PRODUTOS p
        LEFT JOIN PRODUTOS_GRUPO g ON g.ID = p.GRUPO
        LEFT JOIN PRODUTOS_SUBGRUPO s ON s.ID = p.SUBGRUPO
        LEFT JOIN PRODUTOS_MARCA m ON m.ID = p.MARCA
        WHERE 1=1
    """
    params = []
    if apenas_ativos:
        sql += " AND p.STATUS = 'ATIVO'"
    if apenas_com_estoque:
        sql += " AND p.ESTOQUE > 0"

    sql += " ORDER BY p.PRODUTO"

    cols, rows = query(sql, params)
    produtos = []
    for row in rows:
        r = dict(zip(cols, row))
        descricao = (r.get("PRODUTO") or "").strip()
        if not descricao:
            continue
        r["VALOR_VENDA"] = _fmt_decimal(r.get("VALOR_VENDA"), 100)
        r["VALOR_ATACADO"] = _fmt_decimal(r.get("VALOR_ATACADO"), 100)
        r["VALOR_APRAZO"] = _fmt_decimal(r.get("VALOR_APRAZO"), 100)
        r["ESTOQUE"] = _fmt_decimal(r.get("ESTOQUE"), 100)
        r["ESTOQUE_ANT"] = _fmt_decimal(r.get("ESTOQUE_ANT"), 100)
        r["CUSTO"] = _fmt_decimal(r.get("CUSTO"), 100)
        r["MARGEM"] = _fmt_decimal(r.get("MARGEM"), 100)
        r["PESO_LIQUIDO"] = _fmt_decimal(r.get("PESO_LIQUIDO"), 1000)
        r["PESO_BRUTO"] = _fmt_decimal(r.get("PESO_BRUTO"), 1000)
        produtos.append(r)
    return produtos


def ler_grupos():
    cols, rows = query("SELECT * FROM PRODUTOS_GRUPO ORDER BY GRUPO")
    return [dict(zip(cols, row)) for row in rows]


def ler_subgrupos():
    cols, rows = query("SELECT * FROM PRODUTOS_SUBGRUPO ORDER BY SUBGRUPO")
    return [dict(zip(cols, row)) for row in rows]


def ler_marcas():
    cols, rows = query("SELECT * FROM PRODUTOS_MARCA ORDER BY MARCA")
    return [dict(zip(cols, row)) for row in rows]


def ler_barras():
    cols, rows = query("SELECT * FROM PRODUTOS_BARRAS ORDER BY ID_PRODUTO")
    return [dict(zip(cols, row)) for row in rows]


def ler_clientes(apenas_ativos=True):
    sql = """
        SELECT
            c.ID_CLIENTE,
            c.CLIENTE,
            c.RAZ_SOCIAL,
            c.CPF_CNPJ,
            c.IE_RG,
            c.LOGRADOURO,
            c.NUMERO,
            c.COMPLEMENTO,
            c.BAIRRO,
            c.MUNICIPIO,
            c.UF,
            c.CEP,
            c.FONE,
            c.CELULAR,
            c.EMAIL,
            c.DT_NASC,
            c.DT_CADASTRO,
            c.STATUS,
            c.LMTE_CREDITO,
            c.VENDE_APRAZO,
            c.BLOQUEADO,
            c.CRT,
            c.PONTO_REFERENCIA,
            c.CONTATO,
            c.ID_GRUPO,
            cg.GRUPO AS NOME_GRUPO
        FROM CLIENTES c
        LEFT JOIN CLIENTES_GRUPO cg ON cg.ID = c.ID_GRUPO
        WHERE 1=1
    """
    params = []
    if apenas_ativos:
        sql += " AND c.STATUS = 'ATIVO'"
    sql += " ORDER BY c.CLIENTE"

    cols, rows = query(sql, params)
    clientes = []
    for row in rows:
        r = dict(zip(cols, row))
        r["LMTE_CREDITO"] = _fmt_decimal(r.get("LMTE_CREDITO"))
        clientes.append(r)
    return clientes


def ler_vendedores():
    cols, rows = query("SELECT * FROM VENDEDOR ORDER BY DESCRICAO")
    return [dict(zip(cols, row)) for row in rows]


def ler_tipos_pagamento():
    cols, rows = query("SELECT * FROM ECF_TIPO_PAGAMENTO ORDER BY ID")
    return [dict(zip(cols, row)) for row in rows]


def ler_naturezas_operacao(tipo="SAIDA"):
    cols, rows = query(
        "SELECT * FROM NATUREZA_OPERACAO WHERE TIPO = ? ORDER BY NATUREZA_OPERACAO",
        [tipo],
    )
    return [dict(zip(cols, row)) for row in rows]


def _sanitizar_nome(valor):
    if not valor:
        return None
    s = str(valor).strip()
    if s.lower() in ("null", "none", "undefined", ""):
        return None
    return s

def ler_emitente():
    cols, rows = query("SELECT * FROM EMITENTE WHERE ID = 1")
    if rows:
        d = dict(zip(cols, rows[0]))
        fantasia = _sanitizar_nome(d.get("FANTASIA"))
        razao = _sanitizar_nome(d.get("RAZ_SOCIAL"))
        d["FANTASIA"] = fantasia or razao or "Minha Loja"
        return d
    return None


def _fmt_decimal(val, divisor=1):
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val) / divisor


def exportar_tudo():
    return {
        "emitente": ler_emitente(),
        "produtos": ler_produtos(),
        "grupos": ler_grupos(),
        "subgrupos": ler_subgrupos(),
        "marcas": ler_marcas(),
        "barras": ler_barras(),
        "clientes": ler_clientes(),
        "vendedores": ler_vendedores(),
        "tipos_pagamento": ler_tipos_pagamento(),
        "naturezas_operacao": ler_naturezas_operacao(),
        "exportado_em": datetime.datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import json
    data = exportar_tudo()
    print(f"Produtos: {len(data['produtos'])}")
    print(f"Grupos: {len(data['grupos'])}")
    print(f"Clientes: {len(data['clientes'])}")
    print(f"Vendedores: {len(data['vendedores'])}")
