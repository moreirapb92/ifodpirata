"""
Snapshot e comparador de tabelas do DAV/ORCAMENTO no Firebird.

Uso:
    # Criar snapshot antes
    python snapshot_dav_cliente.py --save data/antes_dav_cliente.json

    # [Criar DAV manualmente no HOST]

    # Criar snapshot depois e comparar
    python snapshot_dav_cliente.py --save data/depois_dav_cliente.json \\
        --compare data/antes_dav_cliente.json
"""
import sys
import os
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent.db import query


TABELAS = [
    "ORCAMENTO",
    "ORCAMENTO_ITENS",
    "ORCAMENTO_TOTAL_TIPO_PGTO",
    "DAV",
    "DAV_ITENS",
    "DAV_FORMAS_PAGAMENTO",
    "CLIENTES",
    "FRENTE",
    "FRENTE_ITENS",
    "WEB_CONTROL",
]


def _fmt_val(v):
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def snap_tabela(nome):
    """Retorna lista de dicts com todos os registros da tabela."""
    try:
        cols, rows = query(f"SELECT * FROM {nome}")
        registros = []
        for row in rows:
            r = {}
            for i, col in enumerate(cols):
                r[col] = _fmt_val(row[i])
            registros.append(r)
        return registros
    except Exception as e:
        return {"erro": str(e)}


def fazer_snapshot():
    snap = {
        "_metadata": {
            "criado_em": datetime.now().isoformat(),
            "tabelas": TABELAS,
        },
        "tabelas": {},
    }
    for nome in TABELAS:
        print(f"  Snapshot: {nome}...")
        snap["tabelas"][nome] = snap_tabela(nome)
    return snap


def comparar_snapshots(antes, depois):
    """Compara dois snapshots e retorna as diferencas."""
    diffs = {}
    for nome in TABELAS:
        antes_tabela = antes.get("tabelas", {}).get(nome, [])
        depois_tabela = depois.get("tabelas", {}).get(nome, [])

        if not isinstance(antes_tabela, list) or not isinstance(depois_tabela, list):
            continue

        antes_ids = {}
        depois_ids = {}

        # Tenta achar chave primaria
        for reg in antes_tabela:
            for pk_candidate in ("ID", "ID_VENDA_CABECALHO", "ID_ORCAMENTO", "ID_CLIENTE"):
                if pk_candidate in reg:
                    antes_ids.setdefault(pk_candidate, {})
                    antes_ids[pk_candidate][reg[pk_candidate]] = reg
                    break

        for reg in depois_tabela:
            for pk_candidate in ("ID", "ID_VENDA_CABECALHO", "ID_ORCAMENTO", "ID_CLIENTE"):
                if pk_candidate in reg:
                    depois_ids.setdefault(pk_candidate, {})
                    depois_ids[pk_candidate][reg[pk_candidate]] = reg
                    break

        diff_list = []

        # Registros novos
        pk = next(iter(depois_ids.keys()), None) if depois_ids else None
        if pk:
            for key, reg in depois_ids[pk].items():
                if key not in antes_ids.get(pk, {}):
                    diff_list.append({"tipo": "NOVO", "chave": {pk: key}, "dados": reg})

        # Registros modificados
        if pk:
            for key, reg in depois_ids[pk].items():
                if key in antes_ids.get(pk, {}):
                    antes_reg = antes_ids[pk][key]
                    campos_alterados = {}
                    for k, v in reg.items():
                        v_antes = antes_reg.get(k)
                        if str(v) != str(v_antes):
                            campos_alterados[k] = {"antes": v_antes, "depois": v}
                    if campos_alterados:
                        diff_list.append({
                            "tipo": "ALTERADO",
                            "chave": {pk: key},
                            "campos": campos_alterados,
                        })

        if diff_list:
            diffs[nome] = diff_list

    return diffs


def main():
    parser = argparse.ArgumentParser(
        description="Snapshot e comparacao de tabelas DAV/ORCAMENTO"
    )
    parser.add_argument("--save", required=True, help="Arquivo JSON para salvar o snapshot")
    parser.add_argument("--compare", help="Arquivo JSON anterior para comparar")
    args = parser.parse_args()

    print(f"Snapshooting tabelas DAV/ORCAMENTO...")
    snap = fazer_snapshot()
    total = sum(
        len(v) if isinstance(v, list) else 0
        for v in snap["tabelas"].values()
    )
    print(f"\nTotal de registros capturados: {total}")

    os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
    with open(args.save, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    print(f"Snapshot salvo em: {args.save}")

    if args.compare:
        print(f"\nComparando com: {args.compare}")
        with open(args.compare, "r", encoding="utf-8") as f:
            antes = json.load(f)
        diffs = comparar_snapshots(antes, snap)

        if not diffs:
            print("Nenhuma diferenca encontrada entre os snapshots.")
        else:
            print(f"\n{'='*70}")
            print(f"DIFERENCAS ENCONTRADAS")
            print(f"{'='*70}")
            for nome_tabela, alterations in diffs.items():
                print(f"\n--- {nome_tabela} ({len(alterations)} alteracoes) ---")
                for alt in alterations:
                    chave_str = ", ".join(f"{k}={v}" for k, v in alt["chave"].items())
                    if alt["tipo"] == "NOVO":
                        print(f"  [+] NOVO {chave_str}")
                        dados = alt["dados"]
                        for k, v in dados.items():
                            if v is not None and v != "":
                                print(f"      {k:30s} = {v}")
                    elif alt["tipo"] == "ALTERADO":
                        print(f"  [~] ALTERADO {chave_str}")
                        for campo, vals in alt["campos"].items():
                            print(f"      {campo:30s}: {vals['antes']!r} -> {vals['depois']!r}")

    print("\nConcluido.")


if __name__ == "__main__":
    main()
