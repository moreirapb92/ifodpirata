"""
Importa um pedido do portal como ORCAMENTO no Firebird.

Usa a MESMA funcao da tela web (/admin/pedidos-importacao).

Uso:
    # Simular (apenas validacao)
    python importar_pedido.py --id 1 --dry-run

    # Importar de verdade
    python importar_pedido.py --id 1 --confirmar
"""
import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(
        description="Importar pedido do portal como ORCAMENTO no Firebird"
    )
    parser.add_argument(
        "--id",
        type=int,
        required=True,
        help="ID do pedido no portal",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas simular (validar sem gravar)",
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Importar de fato o pedido para ORCAMENTO no Firebird",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.confirmar:
        print("ERRO: Use --dry-run para simular ou --confirmar para importar.")
        sys.exit(1)

    if args.dry_run:
        from portal.importer import diagnosticar_pedido
        diag = diagnosticar_pedido(args.id)
        if "erro" in diag:
            print(f"ERRO: {diag['erro']}")
            sys.exit(1)

        print(f"{'='*60}")
        print(f"DIAGNOSTICO - Pedido #{diag['id']}")
        print(f"{'='*60}")
        print(f"Cliente:     {diag.get('nome_cliente','')}")
        fone = diag.get('fone') or ''
        print(f"Telefone:    {fone}")
        print(f"Total:       R$ {diag.get('valor_total',0):.2f}")
        print(f"Itens:       {diag.get('total_itens',0)}")
        print(f"Status:      {diag.get('status','')}")
        print(f"Importado:   {'SIM' if diag.get('importado') else 'NAO'}")
        print(f"Apto:        {'SIM' if diag.get('apto_para_importar') else 'NAO'}")
        print()
        if diag.get("itens_validacao"):
            print(f"{'--- ITENS ---'}")
            for item in diag["itens_validacao"]:
                status_icon = "\u2713" if item["valido"] else "\u2717"
                print(f"  {item['item']}. [{status_icon}] ID={item['id_produto']} | {item.get('produto','')[:40]:40s} | R$ {item['valor_unitario']:.2f} | {item['motivo']}")
        if diag.get("motivos_bloqueio"):
            print(f"\nMOTIVOS DE BLOQUEIO:")
            for m in diag["motivos_bloqueio"]:
                print(f"  - {m}")
        if diag.get("apto_para_importar"):
            print(f"\nPedido APTO para importar. Use --confirmar para importar.")
        else:
            print(f"\nPedido NAO esta apto para importar. Corrija os problemas acima.")
        return

    if args.confirmar:
        from portal.importer import importar_pedido_para_orcamento
        result = importar_pedido_para_orcamento(args.id)
        if result.get("success"):
            print(f"\nORCAMENTO #{result['orcamento_id']} criado com sucesso!")
            print(f"  Abra o HOST > Orcamento Livre para conferir.")
            sys.exit(0)
        else:
            print(f"\nERRO ao importar pedido #{args.id}:")
            for e in result.get("erros", [result.get("mensagem", "Erro desconhecido")]):
                print(f"  - {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
