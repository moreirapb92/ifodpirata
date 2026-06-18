"""
Importador de pedidos do portal online para o Firebird local (HOST).
Usado pelo CLI (importar_pedidos_online.py) e pelo run_agent.py.
"""
import json
import logging
import urllib.request
import urllib.error

from agent.writer import criar_orcamento

log = logging.getLogger("importer_online")

# Usa as mesmas configuracoes do sync
from config.settings import PORTAL_URL, PORTAL_API_KEY


class PortalAPI:
    """Cliente HTTP para o portal online."""

    def __init__(self):
        self.base_url = PORTAL_URL.rstrip("/")
        self.api_key = PORTAL_API_KEY

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }

    def _get(self, path):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")[:500]
            log.error(f"HTTP {e.code} GET {path}: {body}")
            return None
        except Exception as e:
            log.error(f"GET {path}: {e}")
            return None

    def _post(self, path, data):
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers=self._headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")[:500]
            log.error(f"HTTP {e.code} POST {path}: {body}")
            return None
        except Exception as e:
            log.error(f"POST {path}: {e}")
            return None

    def get_pedidos_aceitos(self):
        """Retorna lista de pedidos ACEITOS que ainda nao foram importados."""
        return self._get("/api/sync/pedidos-pendentes") or []

    def atualizar_pedido(self, id_externo, status, orcamento_id=None,
                         numero_orcamento=None, erro_importacao=None):
        """Atualiza o status do pedido no portal apos importacao local."""
        data = {
            "status": status,
            "orcamento_id": orcamento_id,
            "numero_orcamento": numero_orcamento,
            "erro_importacao": erro_importacao,
        }
        return self._post(f"/api/sync/pedidos/{id_externo}/atualizar", data)

    def testar_conexao(self):
        """Testa se a API key funciona."""
        result = self._get("/api/sync/pedidos-pendentes")
        return result is not None


def pedido_portal_para_dict(pedido_portal):
    """Converte um pedido do formato do portal para o formato esperado por criar_orcamento()."""
    itens = []
    for i in pedido_portal.get("itens", []):
        itens.append({
            "id_produto": i.get("id_produto") or i.get("codigo"),
            "produto": i.get("produto", i.get("descricao", "")),
            "gtin": i.get("gtin", ""),
            "quantidade": float(i.get("quantidade", 1)),
            "valor_unitario": float(i.get("valor_unitario", 0)),
            "valor_total": float(i.get("valor_total", 0)),
        })

    obs = "PEDIDO ONLINE"
    obs += f"\nCliente: {pedido_portal.get('nome_cliente', '')}"
    fone = pedido_portal.get("fone") or pedido_portal.get("fone_cliente", "")
    if fone:
        obs += f"\nTelefone: {fone}"
    cpf = pedido_portal.get("cpf_cnpj", "")
    if cpf:
        obs += f"\nCPF/CNPJ: {cpf}"
    ender = pedido_portal.get("logradouro_entrega", "")
    if ender:
        num = pedido_portal.get("numero_entrega", "")
        obs += f"\nEndereco: {ender}{', N ' + num if num else ''}"
    bairro = pedido_portal.get("bairro_entrega", "")
    if bairro:
        obs += f"\nBairro: {bairro}"
    cidade = pedido_portal.get("cidade", "")
    if cidade:
        obs += f"\nCidade: {cidade}"
    ref = pedido_portal.get("referencia", "")
    if ref:
        obs += f"\nReferencia: {ref}"
    comp = pedido_portal.get("complemento", "")
    if comp:
        obs += f"\nComplemento: {comp}"
    pgto = pedido_portal.get("forma_pagamento", "")
    if pgto:
        obs += f"\nPagamento: {pgto}"
    obs_extra = pedido_portal.get("observacao", "") or ""
    if obs_extra.strip():
        obs += f"\nObservacao: {obs_extra.strip()}"

    return {
        "id_externo": pedido_portal.get("id_externo"),
        "id_cliente": pedido_portal.get("id_cliente"),
        "nome_cliente": pedido_portal.get("nome_cliente", ""),
        "cpf_cnpj": pedido_portal.get("cpf_cnpj", ""),
        "fone_cliente": fone,
        "logradouro": (pedido_portal.get("logradouro_entrega") or "").strip(),
        "numero": (pedido_portal.get("numero_entrega") or "").strip(),
        "bairro": (pedido_portal.get("bairro_entrega") or "").strip(),
        "cidade": (pedido_portal.get("cidade") or "").strip(),
        "complemento": (pedido_portal.get("complemento") or "").strip(),
        "referencia": (pedido_portal.get("referencia") or "").strip(),
        "observacao": obs,
        "valor_total": float(pedido_portal.get("valor_total", 0)),
        "desconto": float(pedido_portal.get("desconto", 0)),
        "forma_pagamento": pgto,
        "itens": itens,
    }


def importar_pedido_unico(api, pedido_portal):
    """Importa um unico pedido no Firebird local e atualiza o portal.

    Retorna dict com {success, pedido_id, orcamento_id, mensagem}
    """
    id_externo = pedido_portal.get("id_externo")
    pedido_id = pedido_portal.get("id")
    nome = pedido_portal.get("nome_cliente", "?")

    log.info(f"--- Importando pedido #{pedido_id} ({nome}) ---")

    pedido = pedido_portal_para_dict(pedido_portal)

    log.info(f"  Itens: {len(pedido['itens'])} | Total: R$ {pedido['valor_total']:.2f}")

    try:
        result = criar_orcamento(pedido)
    except Exception as e:
        import traceback
        erro = f"{e}\n{traceback.format_exc()}"
        log.error(f"  ERRO ao criar ORCAMENTO: {e}")
        log.error(traceback.format_exc())
        api.atualizar_pedido(id_externo, "ERRO_IMPORTACAO",
                             erro_importacao=str(e)[:1000])
        return {"success": False, "mensagem": str(e), "pedido_id": pedido_id}

    if not result.get("success"):
        erros = result.get("erros", ["Erro desconhecido"])
        log.error(f"  ERRO do writer: {erros}")
        api.atualizar_pedido(id_externo, "ERRO_IMPORTACAO",
                             erro_importacao="; ".join(erros)[:1000])
        return {"success": False, "mensagem": "; ".join(erros), "pedido_id": pedido_id}

    orcamento_id = result["orcamento_id"]
    log.info(f"  ORCAMENTO #{orcamento_id} criado com sucesso!")

    update_ok = api.atualizar_pedido(id_externo, "IMPORTADO",
                                      orcamento_id=orcamento_id,
                                      numero_orcamento=orcamento_id)
    if update_ok:
        log.info(f"  Portal atualizado: pedido #{pedido_id} -> IMPORTADO")
    else:
        log.warning(f"  Nao foi possivel atualizar o portal para pedido #{pedido_id}")
    log.info(f"  --- Concluido: pedido #{pedido_id} -> ORCAMENTO #{orcamento_id} ---")

    return {
        "success": True,
        "orcamento_id": orcamento_id,
        "pedido_id": pedido_id,
        "mensagem": f"ORCAMENTO #{orcamento_id}",
    }


def importar_todos_pedidos(api=None):
    """Busca todos os pedidos ACEITOS no portal e importa no Firebird local.

    Retorna (importados, erros, pulados)
    """
    if api is None:
        api = PortalAPI()

    pedidos = api.get_pedidos_aceitos()

    if not pedidos:
        log.info("Nenhum pedido pendente para importar.")
        return 0, 0, 0

    log.info(f"Pedidos pendentes encontrados: {len(pedidos)}")

    importados = 0
    erros = 0
    pulados = 0

    for p in pedidos:
        result = importar_pedido_unico(api, p)
        if result["success"]:
            importados += 1
        else:
            erros += 1

    log.info(f"Total: {importados} importados, {erros} com erro")
    return importados, erros, pulados
