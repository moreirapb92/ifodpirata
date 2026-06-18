"""
Reseta apenas o banco SQLite do portal.
NUNCA toca no Firebird.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from portal.models import DB_PATH, init_db

db_path = os.path.abspath(DB_PATH)

# Seguranca: se o caminho apontar para .FDB, aborta
if db_path.lower().endswith(".fdb"):
    print("ERRO: O caminho parece ser um arquivo Firebird (.FDB). Abortando.")
    sys.exit(1)

# Confirma se e SQLite
if not os.path.exists(db_path):
    print("Banco SQLite do portal nao encontrado. Um novo sera criado.")
else:
    with open(db_path, "rb") as f:
        header = f.read(16)
    if header[:6] != b"SQLite":
        print("ERRO: O arquivo nao parece ser um banco SQLite valido. Abortando.")
        sys.exit(1)

try:
    os.remove(db_path)
    print(f"Arquivo removido: {db_path}")
except Exception as e:
    print(f"ERRO ao remover: {e}")
    sys.exit(1)

init_db()
print("Banco do portal zerado com sucesso.")
print(f"Novo banco criado em: {db_path}")
