"""
TESTE: Criar um ORCAMENTO real no Firebird para conferir no HOST.

Cria um orcamento com 1 produto e 1 forma de pagamento.
O registro fica no banco - va no HOST > Orcamento Livre para conferir.

Uso:
    python test_criar_orcamento.py
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from agent.writer import criar_orcamento
from agent.writer import validar_pedido
from agent.db import query

# --- Escolher um produto existente ---
cols, rows = query("SELECT FIRST 10 ID_PRODUTO, PRODUTO, VALOR_VENDA, GTIN FROM PRODUTOS WHERE VALOR_VENDA > 0 ORDER BY ID_PRODUTO")
print("\nProdutos disponiveis:")
print(f"  {'ID':>5s}  {'PRODUTO':45s}  {'PRECO':>8s}  {'GTIN':>14s}")
print(f"  {'-----':>5s}  {'-'*45:45s}  {'--------':>8s}  {'-'*14:>14s}")
for r in rows:
    print(f"  {r[0]:>5d}  {r[1][:45]:45s}  R$ {float(r[2]):>6.2f}  {r[3] or '':14s}")

# Usar o primeiro produto da lista
prod = rows[0]
id_produto = prod[0]
nome_produto = prod[1]
preco = float(prod[2])
gtin = prod[3] or ""

print(f"\nProduto escolhido: ID={id_produto} - {nome_produto[:40]} - R$ {preco:.2f}")

# --- Montar pedido de teste ---
pedido_teste = {
    "id_externo": "teste-manual-002",
    "id_cliente": None,
    "nome_cliente": "CONSUMIDOR TESTE",
    "cpf_cnpj": "000.000.000-00",
    "fone_cliente": "88999999999",
    "observacao": "Orcamento de teste criado pelo agente em " + str(__import__('datetime').datetime.now().strftime("%d/%m/%Y %H:%M")),
    "valor_total": preco,
    "desconto": 0,
    "forma_pagamento": "DINHEIRO",
    "itens": [
        {
            "id_produto": id_produto,
            "produto": nome_produto,
            "gtin": gtin,
            "quantidade": 1.0,
            "valor_unitario": preco,
            "valor_total": preco,
        },
    ],
}

# --- Validar ---
print("\n--- VALIDACAO ---")
erros = validar_pedido(pedido_teste)
if erros:
    print("ERROS de validacao:")
    for e in erros:
        print(f"  - {e}")
    print("\nCorrija os erros e tente novamente.")
    sys.exit(1)
else:
    print("Validacao OK!")

# --- Gravar ---
print("\n--- GRAVANDO ORCAMENTO ---")
result = criar_orcamento(pedido_teste)

if result.get("success"):
    orc_id = result["orcamento_id"]
    print(f"\nSUCESSO! ORCAMENTO #{orc_id} criado!")
    print(f"  Produto: {nome_produto[:40]} (ID={id_produto})")
    print(f"  Quantidade: 1")
    print(f"  Total: R$ {preco:.2f}")
    print(f"  Forma pagamento: DINHEIRO")
    print(f"  Situacao: ABERTO (Orcamento Livre)")
    print(f"  Tabelas: ORCAMENTO + ORCAMENTO_ITENS + ORCAMENTO_TOTAL_TIPO_PGTO")
    print()
    print("=" * 60)
    print("  Para conferir, abra o HOST e va em:")
    print("    ORCAMENTO > Orcamento Livre")
    print(f"  Procure pelo ID #{orc_id} ou cliente 'CONSUMIDOR TESTE'")
    print("=" * 60)
else:
    print(f"\nERRO: {result.get('erros', result)}")
    sys.exit(1)
