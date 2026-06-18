"""
Ferramenta de Snapshot/Comparação para mapear tabelas do Firebird.
Descobre quais tabelas o sistema HOST altera ao criar um ORÇAMENTO ou PRÉ-VENDA.

Uso:
    # Snapshots para ORCAMENTO
    python tools\snapshot_compare.py --orcamento --save data\antes.json
    # (criar orcamento manual no HOST)
    python tools\snapshot_compare.py --orcamento --save data\depois.json --compare data\antes.json --summary

    # Snapshots para PRVD
    python tools\snapshot_compare.py --save data\prvd_antes.json
    # (criar pre-venda manual no HOST)
    python tools\snapshot_compare.py --save data\prvd_depois.json --compare data\prvd_antes.json --summary
"""
import json
import argparse
import datetime
from decimal import Decimal
from agent.db import query

# --- Listas de tabelas ---

TABELAS_ORCAMENTO = [
    "ORCAMENTO", "ORCAMENTO_ITENS", "ORCAMENTO_FORMAS_PAGAMENTO",
    "ORCAMENTO_TOTAL_TIPO_PGTO",
    "DAV", "DAV_ITENS", "DAV_FORMAS_PAGAMENTO",
    "MOVIMENTO", "PRODUTOS_MOVIMENTACAO",
    "CONTAS_RECEBER", "WEB_CONTROL",
]

TABELAS_PRVD = [
    "PRVD", "PRVD_ITENS", "PRVD_TOTAL_TIPO_PGTO",
    "DAV", "DAV_ITENS", "DAV_FORMAS_PAGAMENTO",
    "FRENTE", "FRENTE_ITENS",
    "ECF_VENDA_CABECALHO", "ECF_VENDA_DETALHE",
    "MOVIMENTO", "PRODUTOS_MOVIMENTACAO",
    "CONTAS_RECEBER", "WEB_CONTROL", "WEB_PONTEIROS",
]

TABELAS_IMPORTANTES = [
    "DAV", "DAV_ITENS", "DAV_FORMAS_PAGAMENTO",
    "PRVD", "PRVD_ITENS", "PRVD_TOTAL_TIPO_PGTO",
    "FRENTE", "FRENTE_ITENS",
    "ORCAMENTO", "ORCAMENTO_ITENS", "ORCAMENTO_FORMAS_PAGAMENTO",
    "ORCAMENTO_TOTAL_TIPO_PGTO",
    "MOVIMENTO", "PRODUTOS_MOVIMENTACAO", "WEB_CONTROL",
]


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, datetime.time):
            return obj.strftime("%H:%M:%S")
        return super().default(obj)


def snap_table(table):
    cols, rows = query(f"SELECT * FROM {table}")
    data = []
    for row in rows:
        data.append(dict(zip(cols, row)))
    return {"columns": cols, "rows": data, "count": len(data)}


def make_snapshot(tables):
    snapshot = {}
    for t in tables:
        try:
            snapshot[t] = snap_table(t)
        except Exception as e:
            snapshot[t] = {"error": str(e), "columns": [], "rows": [], "count": 0}
    return snapshot


def compare_snapshots(before, after):
    diffs = {}
    for table in after:
        if table.startswith("_"):
            continue
        b = before.get(table, {"rows": [], "count": 0})
        a = after[table]
        if "error" in a:
            continue

        b_rows = {json.dumps(r, cls=DecimalEncoder, sort_keys=True): r for r in b["rows"]}
        a_rows = {json.dumps(r, cls=DecimalEncoder, sort_keys=True): r for r in a["rows"]}

        added = [r for k, r in a_rows.items() if k not in b_rows]
        removed = [r for k, r in b_rows.items() if k not in a_rows]
        changed = []

        for k, r_a in a_rows.items():
            r_b = b_rows.get(k)
            if r_b and r_a != r_b:
                changed.append({"before": r_b, "after": r_a})

        if added or removed or changed:
            diffs[table] = {
                "added": added,
                "removed": removed,
                "changed": changed,
                "total_before": b["count"],
                "total_after": a["count"],
            }
    return diffs


def _fmt_registro(r):
    """Formata um registro para exibicao legivel, omitindo campos nulos/vazios."""
    partes = []
    for k, v in r.items():
        if v is None or v == "" or v == 0 or v == "0":
            continue
        k_curto = k[:25]
        if isinstance(v, float):
            partes.append(f"{k_curto}={v:.2f}")
        elif isinstance(v, datetime.date):
            partes.append(f"{k_curto}={v.isoformat()}")
        elif isinstance(v, Decimal):
            partes.append(f"{k_curto}={float(v):.4f}")
        else:
            partes.append(f"{k_curto}={v}")
    return " | ".join(partes)


def _fmt_detalhado(r, colunas_importantes=None):
    """Formata um registro mostrando todas as colunas, uma por linha."""
    lines = []
    for k, v in r.items():
        if colunas_importantes and k not in colunas_importantes:
            continue
        if v is None:
            continue
        label = k[:25]
        if isinstance(v, float):
            lines.append(f"    {label:25s} = {v:.2f}")
        elif isinstance(v, Decimal):
            lines.append(f"    {label:25s} = {float(v):.4f}")
        elif isinstance(v, datetime.date):
            lines.append(f"    {label:25s} = {v.isoformat()}")
        else:
            lines.append(f"    {label:25s} = {v}")
    return "\n".join(lines)


def print_summary(diffs, only_important=False):
    """Exibe modo resumido focado em descobrir o destino do orcamento."""
    print("\n" + "=" * 70)
    print("  RESUMO DA COMPARACAO")
    print("=" * 70)

    if not diffs:
        print("\n  NENHUMA DIFERENCA ENCONTRADA entre os snapshots.")
        print("  As tabelas monitoradas nao foram alteradas.")
        return

    # Separar tabelas importantes e secundarias
    imp = {}
    sec = {}
    for table, diff in diffs.items():
        if table in TABELAS_IMPORTANTES:
            imp[table] = diff
        else:
            sec[table] = diff

    # 1. Tabelas com adicoes
    print("\n--- TABELAS COM REGISTROS ADICIONADOS ---")
    achou_adicao = False
    for table, diff in sorted(imp.items()):
        qtd = len(diff["added"])
        if qtd > 0:
            achou_adicao = True
            destaque = " <<<<" if table in ("DAV", "DAV_ITENS", "PRVD", "PRVD_ITENS", "ORCAMENTO", "ORCAMENTO_ITENS") else ""
            print(f"  [+] {table:30s} +{qtd:3d} registro(s)  (antes: {diff['total_before']}, depois: {diff['total_after']}){destaque}")
    if not achou_adicao:
        print("  (nenhuma)")
    if not only_important and sec:
        for table, diff in sorted(sec.items()):
            qtd = len(diff["added"])
            if qtd > 0:
                print(f"  [+] {table:30s} +{qtd:3d} registro(s)  (antes: {diff['total_before']}, depois: {diff['total_after']})")

    # 2. Tabelas com alteracoes
    print("\n--- TABELAS COM REGISTROS ALTERADOS ---")
    achou_alt = False
    for table, diff in sorted(imp.items()):
        qtd = len(diff["changed"])
        if qtd > 0:
            achou_alt = True
            print(f"  [~] {table:30s} {qtd:3d} registro(s) alterado(s)")
    if not achou_alt:
        print("  (nenhuma)")
    if not only_important and sec:
        for table, diff in sorted(sec.items()):
            qtd = len(diff["changed"])
            if qtd > 0:
                print(f"  [~] {table:30s} {qtd:3d} registro(s) alterado(s)")

    # 3. Registros removidos (menos comum)
    qtd_rem = sum(len(d["removed"]) for d in diffs.values())
    if qtd_rem > 0:
        print(f"\n--- REGISTROS REMOVIDOS: {qtd_rem} no total ---")

    # 4. Detalhes das tabelas DAV, DAV_ITENS, PRVD, PRVD_ITENS
    print("\n--- DETALHES DOS NOVOS REGISTROS ---")
    for tabela_alvo in ("DAV", "DAV_ITENS", "PRVD", "PRVD_ITENS", "ORCAMENTO", "ORCAMENTO_ITENS"):
        if tabela_alvo not in imp:
            continue
        diff = imp[tabela_alvo]
        if diff["added"]:
            print(f"\n  >> {tabela_alvo} ({len(diff['added'])} novo(s)):")
            for r in diff["added"]:
                print(f"  {_fmt_detalhado(r)}")
                print()
        elif tabela_alvo in imp:
            print(f"\n  >> {tabela_alvo}: sem alteracao")

    # 5. Conclusao
    print("\n" + "-" * 70)
    print("  CONCLUSAO")
    print("-" * 70)

    tem_dav = "DAV" in imp and len(imp["DAV"]["added"]) > 0
    tem_dav_itens = "DAV_ITENS" in imp and len(imp["DAV_ITENS"]["added"]) > 0
    tem_prvd = "PRVD" in imp and len(imp["PRVD"]["added"]) > 0
    tem_prvd_itens = "PRVD_ITENS" in imp and len(imp["PRVD_ITENS"]["added"]) > 0
    tem_orc = "ORCAMENTO" in imp and len(imp["ORCAMENTO"]["added"]) > 0
    tem_orc_itens = "ORCAMENTO_ITENS" in imp and len(imp["ORCAMENTO_ITENS"]["added"]) > 0
    tem_frente = "FRENTE" in imp and len(imp["FRENTE"]["added"]) > 0

    if tem_orc and tem_orc_itens:
        print("  PROVIDENCIA: ORCAMENTO/Orcamento Livre")
        print("  Tabelas envolvidas: ORCAMENTO + ORCAMENTO_ITENS")
    elif tem_dav and tem_dav_itens:
        print("  PROVIDENCIA: DAV/Documento Auxiliar de Venda")
        print("  Tabelas envolvidas: DAV + DAV_ITENS + DAV_FORMAS_PAGAMENTO")
    elif tem_prvd and tem_prvd_itens:
        print("  PROVIDENCIA: PRVD/Pre-Venda")
        print("  Tabelas envolvidas: PRVD + PRVD_ITENS + PRVD_TOTAL_TIPO_PGTO")
    elif tem_frente:
        print("  PROVIDENCIA: FRENTE/Venda no PDV")
        print("  Tabelas envolvidas: FRENTE + FRENTE_ITENS")
    elif tem_dav:
        print("  PROVIDENCIA: DAV (apenas cabecalho, sem itens)")
    elif tem_prvd:
        print("  PROVIDENCIA: PRVD (apenas cabecalho, sem itens)")
    else:
        print("  NAO FOI POSSIVEL IDENTIFICAR o destino.")
        print("  Verifique as tabelas com alteracoes manualmente.")

    # Listar todas as tabelas envolvidas
    print(f"\n  Tabelas afetadas ({len(diffs)}):")
    for t in sorted(diffs.keys()):
        d = diffs[t]
        resumo = []
        if len(d["added"]):
            resumo.append(f"+{len(d['added'])}")
        if len(d["changed"]):
            resumo.append(f"~{len(d['changed'])}")
        if len(d["removed"]):
            resumo.append(f"-{len(d['removed'])}")
        print(f"    {t:35s} {', '.join(resumo)}")

    print()


def print_detalhado(diffs):
    """Exibe modo detalhado original."""
    for table, diff in sorted(diffs.items()):
        print(f"\n{'='*60}")
        print(f"TABELA: {table}")
        print(f"  Antes: {diff['total_before']} registros")
        print(f"  Depois: {diff['total_after']} registros")
        if diff["added"]:
            print(f"\n  --- ADICIONADOS ({len(diff['added'])}) ---")
            for r in diff["added"]:
                print(f"    {json.dumps(r, cls=DecimalEncoder, ensure_ascii=False)}")
        if diff["removed"]:
            print(f"\n  --- REMOVIDOS ({len(diff['removed'])}) ---")
            for r in diff["removed"]:
                print(f"    {json.dumps(r, cls=DecimalEncoder, ensure_ascii=False)}")
        if diff["changed"]:
            print(f"\n  --- ALTERADOS ({len(diff['changed'])}) ---")
            for c in diff["changed"]:
                print(f"    BEFORE: {json.dumps(c['before'], cls=DecimalEncoder, ensure_ascii=False)}")
                print(f"    AFTER:  {json.dumps(c['after'], cls=DecimalEncoder, ensure_ascii=False)}")


def main():
    parser = argparse.ArgumentParser(
        description="Snapshot/Comparacao de tabelas do Firebird",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Capturar snapshot antes de criar orcamento
  %(prog)s --orcamento --save data/antes.json

  # Comparar depois de criar orcamento (modo resumido)
  %(prog)s --orcamento --save data/depois.json --compare data/antes.json --summary

  # Comparar focando apenas em tabelas relevantes
  %(prog)s --orcamento --compare data/antes.json --save data/depois.json --summary --only-important
        """,
    )
    parser.add_argument("--save", help="Salvar snapshot em arquivo JSON")
    parser.add_argument("--compare", help="Comparar com snapshot anterior (arquivo JSON)")
    parser.add_argument("--tables", nargs="*", default=None, help="Tabelas especificas para monitorar")
    parser.add_argument("--orcamento", action="store_true", help="Usar tabelas de ORCAMENTO")
    parser.add_argument("--prvd", action="store_true", help="Usar tabelas de PRVD (padrao)")
    parser.add_argument("--todas", action="store_true", help="Monitorar TODAS as tabelas do banco")
    parser.add_argument("--summary", action="store_true", help="Modo resumido (focado em orcamento/DAV/PRVD)")
    parser.add_argument("--only-important", action="store_true", help="Ignorar tabelas secundarias na comparacao")
    args = parser.parse_args()

    # --- definir lista de tabelas ---
    tables = args.tables
    if args.orcamento:
        tables = TABELAS_ORCAMENTO
        modo = "ORCAMENTO"
    elif args.prvd:
        tables = TABELAS_PRVD
        modo = "PRVD"
    elif args.todas:
        from agent.db import query as q2
        cols, rows = q2("""
            SELECT r.rdb$relation_name FROM rdb$relations r
            WHERE r.rdb$relation_type = 0 AND r.rdb$system_flag = 0 ORDER BY 1
        """)
        tables = [r[0].strip() for r in rows]
        modo = f"TODAS ({len(tables)})"
    elif tables is None:
        tables = TABELAS_PRVD
        modo = "PRVD (padrao)"

    print(f"\nModo: {modo}")
    if args.only_important:
        print(f"Apenas tabelas importantes: ativado")

    # --- capturar snapshot ---
    if not args.compare:
        print("Capturando snapshot...")
        snap = make_snapshot(tables)
        if args.save:
            with open(args.save, "w", encoding="utf-8") as f:
                json.dump(snap, f, cls=DecimalEncoder, indent=2, ensure_ascii=False)
            print(f"Snapshot salvo em: {args.save}")
            print(f"Tabelas capturadas: {len(snap)}")
            for t, data in snap.items():
                status = ""
                if "error" in data:
                    status = " [ERRO]"
                print(f"  {t:35s} = {data['count']:>8} registros{status}")
        else:
            print("Use --save <arquivo.json> para salvar o snapshot")
        return

    # --- comparar snapshots ---
    print(f"Carregando snapshot anterior: {args.compare}")
    with open(args.compare, "r", encoding="utf-8") as f:
        before = json.load(f)

    print("Capturando snapshot ATUAL...")
    after = make_snapshot(tables)
    diffs = compare_snapshots(before, after)

    if args.summary:
        print_summary(diffs, only_important=args.only_important)
    else:
        if not diffs:
            print("\nNENHUMA DIFERENCA ENCONTRADA!")
            print("As tabelas monitoradas nao foram alteradas.")
        else:
            print_detalhado(diffs)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(after, f, cls=DecimalEncoder, indent=2, ensure_ascii=False)
        print(f"\nSnapshot atual salvo em: {args.save}")


if __name__ == "__main__":
    main()
