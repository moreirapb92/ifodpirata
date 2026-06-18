"""Inicia o Agente de Sincronizacao IfodPirata.
Sincroniza dados do Firebird local com o portal online.
Importa pedidos ACEITOS do portal para ORCAMENTO no HOST local.
"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from agent.sync import run_forever

if __name__ == "__main__":
    run_forever()
