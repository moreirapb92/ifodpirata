"""
Verifica os dados completos de um pedido no portal antes da importacao.

Uso:
    python verificar_pedido_dados.py --id 1
    python verificar_pedido_dados.py --id 1 --raw    # mostra o row cru
    python verificar_pedido_dados.py --id 1 --obs    # mostra a observacao que vai pro ORCAMENTO
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from portal.models import get_db
from portal.admin import _montar_pedido_para_importacao


def main():
    parser = argparse.ArgumentParser(description="Verificar dados do pedido no portal")
    parser.add_argument("--id", type=int, required=True, help="ID do pedido")
    parser.add_argument("--raw", action="store_true", help="Mostrar todos os campos crus do banco")
    parser.add_argument("--obs", action="store_true", help="Mostrar apenas a observacao composta")
    args = parser.parse_args()

    db = get_db()

    # Buscar pedido
    row = db.execute("SELECT * FROM pedidos WHERE id = ?", [args.id]).fetchone()
    if not row:
        print(f"ERRO: Pedido #{args.id} nao encontrado.")
        sys.exit(1)

    p = dict(row)

    print(f"{'='*60}")
    print(f"PEDIDO #{p['id']}")
    print(f"{'='*60}")
    print(f"Status:        {p['status']}")
    print(f"Importado:     {'SIM' if p.get('importado') else 'NAO'}")
    print(f"Data criacao:  {p.get('criado_em', '')}")
    print(f"Valor total:   R$ {float(p.get('valor_total', 0)):.2f}")
    print(f"ID Externo:    {p.get('id_externo', '')}")
    print()

    # Cliente
    print(f"{'--- CLIENTE ---'}")
    print(f"Nome:       {p.get('nome_cliente', '')}")
    print(f"Telefone:   {p.get('fone', '')}")
    print(f"CPF/CNPJ:   {p.get('cpf_cnpj', '') or '(vazio)'}")
    print()

    # Endereco
    print(f"{'--- ENDERECO ---'}")
    print(f"Logradouro: {p.get('logradouro_entrega', '') or '(vazio)'}")
    print(f"Numero:     {p.get('numero_entrega', '') or '(vazio)'}")
    print(f"Bairro:     {p.get('bairro_entrega', '') or '(vazio)'}")
    print(f"Cidade:     {p.get('cidade', '') or '(vazio)'}")
    print(f"Referencia: {p.get('referencia', '') or '(vazio)'}")
    print(f"Complemento:{p.get('complemento', '') or '(vazio)'}")
    print()

    # Pagamento
    print(f"{'--- PAGAMENTO ---'}")
    print(f"Forma:      {p.get('forma_pagamento', '') or '(vazio)'}")
    print(f"Detalhe:    {p.get('forma_pagamento_detalhe', '') or '(vazio)'}")
    print(f"Troco para: {p.get('troco_para', '') or '(vazio)'}")
    print(f"Tipo cartao:{p.get('tipo_cartao', '') or '(vazio)'}")
    print()

    # Observacao
    obs = p.get("observacao", "") or "(vazio)"
    print(f"{'--- OBSERVACAO (salva no portal) ---'}")
    print(obs)
    print()

    # Itens
    from agent.db import query as fb_query
    itens = db.execute("SELECT * FROM pedido_itens WHERE id_pedido = ?", [args.id]).fetchall()
    print(f"{'--- ITENS (' + str(len(itens)) + ' itens) ---'}")
    for idx, item in enumerate(itens):
        d = dict(item)
        item_num = idx + 1
        pid = d.get("id_produto")
        fb_status = "?"
        fb_nome = ""
        if pid:
            cols, rows = fb_query(
                "SELECT ID_PRODUTO, PRODUTO, STATUS, UNIDADE_COMECIAL FROM PRODUTOS WHERE ID_PRODUTO = ?",
                [pid],
            )
            if rows:
                fb_nome = (rows[0][1] or "").strip()
                fb_status = rows[0][2]
                fb_unid = (rows[0][3] or "UN").strip()
            else:
                fb_status = "NAO_ENCONTRADO"
        ok = "OK" if (fb_nome and fb_status == "ATIVO") else "INVALIDO"
        print(f"  {item_num}. [{pid}] Firebird: {fb_nome!r} status={fb_status} [{ok}]")
        print(f"         Portal: {d.get('produto','')!r} | qtd={d.get('quantidade')} "
              f"x R$ {float(d.get('valor_unitario',0)):.2f} "
              f"= R$ {float(d.get('valor_total',0)):.2f}")

    # OBS composta (como vai pro ORCAMENTO)
    if args.obs or not args.raw:
        print()
        print(f"{'='*60}")
        print(f"OBS COMPOSTA (vai para ORCAMENTO.OBS)")
        print(f"{'='*60}")
        try:
            pedido = _montar_pedido_para_importacao(row)
            print(pedido.get("observacao", ""))
        except Exception as e:
            print(f"(Erro ao montar: {e})")

    # Raw dump
    if args.raw:
        print()
        print(f"{'--- RAW (todos os campos) ---'}")
        for k, v in p.items():
            print(f"  {k}: {v!r}")

    db.close()


if __name__ == "__main__":
    main()
