"""
Diagnostico completo de um pedido para importacao.

Mostra dados do pedido, itens, validacao no Firebird,
e se o pedido esta apto para importar.

Uso:
    python diagnosticar_importacao.py --id 1
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description="Diagnosticar pedido para importacao no Firebird"
    )
    parser.add_argument(
        "--id",
        type=int,
        required=True,
        help="ID do pedido no portal",
    )
    args = parser.parse_args()

    from portal.importer import diagnosticar_pedido
    diag = diagnosticar_pedido(args.id)

    if "erro" in diag:
        print(f"ERRO: {diag['erro']}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"DIAGNOSTICO DE IMPORTACAO - Pedido #{diag['id']}")
    print(f"{'='*60}")
    print()
    print(f"{'--- DADOS DO PEDIDO ---'}")
    print(f"  ID:               {diag['id']}")
    print(f"  ID Externo:       {diag.get('id_externo','')}")
    print(f"  Cliente:          {diag.get('nome_cliente','')}")
    fone = diag.get('fone') or ''
    print(f"  Telefone:         {fone}")
    print(f"  Status:           {diag.get('status','')}")
    print(f"  Importado:        {'SIM' if diag.get('importado') else 'NAO'}")
    print(f"  Total:            R$ {diag.get('valor_total',0):.2f}")
    print(f"  Itens:            {diag.get('total_itens',0)}")
    print(f"  Pagamento:        {diag.get('forma_pagamento','')}")
    if diag.get('numero_orcamento'):
        print(f"  Orcamento HOST:   #{diag.get('numero_orcamento')}")
    if diag.get('id_orcamento_firebird'):
        print(f"  ID Firebird:      {diag.get('id_orcamento_firebird')}")
    if diag.get('data_importacao'):
        print(f"  Data importacao:  {diag.get('data_importacao')}")
    if diag.get('erro_importacao'):
        print(f"  Erro importacao:  {diag.get('erro_importacao')}")
    print()

    print(f"{'--- ITENS ---'}")
    if not diag.get("itens_validacao"):
        print("  (nenhum item)")
    else:
        print(f"  {'#':>2s} | {'Status':6s} | {'ID':>6s} | {'Produto':40s} | {'Qtd':>4s} | {'Preco':>8s} | {'Motivo'}")
        print(f"  {'-'*2} | {'-'*6} | {'-'*6} | {'-'*40} | {'-'*4} | {'-'*8} | {'-'*30}")
        for item in diag["itens_validacao"]:
            status = "\u2713 OK" if item["valido"] else "\u2717 INV"
            pid = str(item.get("id_produto") or "-")
            produto = (item.get("produto") or pid)[:40]
            qtd = float(item.get("quantidade") or 0)
            preco = float(item.get("valor_unitario") or 0)
            print(f"  {item['item']:2d} | {status:6s} | {pid:>6s} | {produto:40s} | {qtd:>4.0f} | R${preco:>6.2f} | {item['motivo']}")

    print()
    if diag.get("motivos_bloqueio"):
        print(f"--- MOTIVOS DE BLOQUEIO ---")
        for m in diag["motivos_bloqueio"]:
            print(f"  \u2717 {m}")
        print()

    if diag.get("apto_para_importar"):
        print(f"\u2713 PEDIDO APTO PARA IMPORTAR")
        print(f"  Use: python importar_pedido.py --id {args.id} --confirmar")
    else:
        print(f"\u2717 PEDIDO NAO ESTA APTO PARA IMPORTAR")
        print(f"  Corrija os problemas acima antes de importar.")


if __name__ == "__main__":
    main()
