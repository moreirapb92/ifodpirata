# Deploy do Portal no Render

## Arquitetura

```
┌─────────────────────────────────────────────┐
│                RENDER.COM                    │
│                                              │
│  ┌──────────── Web Service ────────────┐     │
│  │  ifodpirata-portal                  │     │
│  │  Flask + Gunicorn + SQLite          │     │
│  │  /loja2  /admin  /api               │     │
│  └────────────────┬────────────────────┘     │
│                   │ HTTP                     │
│  ┌──────────── Worker ─────────────────┐     │
│  │  ifodpirata-agent                   │     │
│  │  (Firebird sync)                    │     │
│  └─────────────────────────────────────┘     │
└─────────────────────────────────────────────┘
         │
         ▼ Firebird (local ou VPN)
    ┌──────────────────┐
    │  C:\TSD\Host     │
    │  HOST.FDB        │
    └──────────────────┘
```

**Fluxo:**
1. Agente local (ou Worker no Render) conecta no Firebird e envia dados via `/api/sync/full`
2. Portal online recebe e armazena em SQLite
3. Cliente faz pedido em `/loja2`
4. Agente busca pedidos ACEITO via `/api/sync/pedidos-pendentes`
5. Agente importa pedido como ORCAMENTO/DAV no Firebird local

---

## Passo a passo

### 1. Criar repositório no GitHub

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create ifodpirata --public --push
```

### 2. Criar Web Service no Render

1. Acesse https://dashboard.render.com
2. **New +** → **Web Service**
3. Conecte seu repositório GitHub
4. Configuração:

| Campo | Valor |
|---|---|
| **Name** | `ifodpirata-portal` |
| **Environment** | `Python` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 30` |
| **Plan** | `Free` |

5. **Add Environment Variables**:

| Chave | Valor | Descrição |
|---|---|---|
| `PYTHON_VERSION` | `3.11.0` | Versão do Python |
| `PORTAL_SECRET_KEY` | _(Generate)_ | Chave secreta Flask |
| `PORTAL_API_KEY` | _(Generate)_ | Chave para o agente autenticar |
| `PORTAL_URL` | `https://ifodpirata-portal.onrender.com` | URL do próprio portal |
| `GUNICORN_CMD_ARGS` | `--access-logfile -` | Logs de acesso |

6. **Add Disk (persistente)**:

| Campo | Valor |
|---|---|
| **Name** | `portal-data` |
| **Mount Path** | `/data` |
| **Size** | `1 GB` |

7. Clique em **Deploy**

### 3. Verificar o deploy

Aguardar o build e deploy (1-2 minutos). Testar:

```
https://ifodpirata-portal.onrender.com/loja2
https://ifodpirata-portal.onrender.com/api/loja/produtos?pagina=1&busca=
https://ifodpirata-portal.onrender.com/api/loja/grupos
```

### Pontos importantes

#### Render online NÃO conecta no Firebird

O portal online é apenas o **site da loja** + **API REST**. Ele usa SQLite (em disco persistente) e nunca tenta conectar no Firebird. Toda a comunicação com o Firebird é feita exclusivamente pelo **agente local** rodando na máquina do mercado.

#### PORTAL_API_KEY precisa ser igual nos dois lados

O agente local autentica no portal usando o header `X-API-Key`. A chave `PORTAL_API_KEY` precisa ser **a mesma** no Web Service (Render) e no agente local:

1. No Render, ela é gerada automaticamente (`generateValue: true`)
2. Copie o valor gerado no painel do Render (Dashboard → Environment)
3. Use esse mesmo valor no agente local: `PORTAL_API_KEY=<copiado>`

#### SQLite e imagens usam disco persistente

Render **não mantém arquivos entre deploys** a menos que use um **Disk**. O Web Service já está configurado com:

| Campo | Valor |
|---|---|
| **Mount Path** | `/data` |
| **Size** | `1 GB` |

O banco SQLite será criado em `/data/portal.db` e as imagens podem ser copiadas para `/data/imgProdutos`. O Render mantém esses arquivos mesmo entre deploys.

#### Agente usa PORTAL_URL para apontar para onde enviar os dados

A mesma variável `PORTAL_URL` controla para qual servidor o agente envia:

| Ambiente | `PORTAL_URL` |
|---|---|
| Desenvolvimento (local) | `http://localhost:5000` |
| Produção (Render) | `https://ifodpirata-portal.onrender.com` |

Troque o valor no `.env` do agente local e reinicie o agente. Nenhuma outra alteração é necessária.

### 4. Configurar o agente local

No servidor Windows que tem acesso ao Firebird (`C:\TSD\Host\HOST.FDB`):

#### 4.1 Clonar/clonar o repositório

```bash
cd C:\Users\NONATO\Documents
git clone https://github.com/seu-usuario/ifodpirata.git ifodpirata-agent
cd ifodpirata-agent
pip install -r requirements.txt
```

#### 4.2 Configurar variáveis de ambiente

Crie um arquivo `.env` ou defina no sistema:

```
PORTAL_URL=https://ifodpirata-portal.onrender.com
PORTAL_API_KEY=<copiar do Render>
FB_HOST=
FB_DATABASE=C:\TSD\Host\HOST.FDB
FB_USER=SYSDBA
FB_PASSWORD=masterkey
DRY_RUN=true
DESTINO_PEDIDO=ORCAMENTO
SYNC_INTERVAL_SECONDS=60
```

#### 4.3 Executar o agente

```bash
python run_agent.py
```

O agente vai:
- Ler produtos, clientes, grupos do Firebird
- Enviar para o portal online via `/api/sync/full`
- A cada 60 segundos (configurável), repetir
- Pedidos que o cliente fizer no portal ficam com status `PENDENTE`
- No admin do portal, aceitar pedido → status `ACEITO`
- Agente detecta pedidos ACEITO e importa como ORCAMENTO no HOST

### 5. Modo produção (DRY_RUN=false)

Quando quiser que o agente realmente grave ORCAMENTO no HOST:

```
DRY_RUN=false
```

### 6. Configurar agente como Worker no Render (opcional)

Se o Firebird estiver acessível via IP/Hostname, o agente pode rodar direto no Render como Worker:

1. **New +** → **Worker**
2. Nome: `ifodpirata-agent`
3. Start Command: `python run_agent.py`
4. Env vars:
   - `FB_HOST=ip.do.seu.firebird`
   - `FB_DATABASE=C:\TSD\Host\HOST.FDB`
   - `FB_USER=SYSDBA`
   - `FB_PASSWORD=masterkey`
   - `PORTAL_URL=https://ifodpirata-portal.onrender.com`
   - `PORTAL_API_KEY=<copiar do web service>`

---

## Variáveis de Ambiente - Referência

### Portal (Web Service)

| Variável | Padrão | Obrigatório | Descrição |
|---|---|---|---|
| `PORTAL_SECRET_KEY` | `ifodpirata-dev-...` | Sim | Chave secreta Flask (gere uma forte) |
| `PORTAL_API_KEY` | `agent-api-key-change-me` | Sim | Chave para autenticação do agente |
| `PORTAL_URL` | `http://localhost:5000` | Sim | URL pública do portal |
| `IMAGENS_PRODUTOS_DIR` | `C:\TSD\Host\imgProdutos` | Não | Caminho das imagens (vazio = sem imagens) |
| `DATABASE_URL` | — | Não | Para PostgreSQL futuramente |
| `FLASK_DEBUG` | `false` | Não | Modo debug |

### Agente (Worker / Local)

| Variável | Padrão | Obrigatório | Descrição |
|---|---|---|---|
| `PORTAL_URL` | `http://localhost:5000` | Sim | URL do portal online |
| `PORTAL_API_KEY` | `agent-api-key-change-me` | Sim | Mesma chave configurada no portal |
| `FB_HOST` | `""` | Não | IP do servidor Firebird (vazio = local) |
| `FB_DATABASE` | `C:\TSD\Host\HOST.FDB` | Sim | Caminho do banco Firebird |
| `FB_USER` | `SYSDBA` | Sim | Usuário Firebird |
| `FB_PASSWORD` | `masterkey` | Sim | Senha Firebird |
| `FB_PORT` | `3050` | Não | Porta Firebird |
| `SYNC_INTERVAL_SECONDS` | `60` | Não | Intervalo entre sincronizações |
| `DESTINO_PEDIDO` | `ORCAMENTO` | Não | Tipo de documento no HOST |
| `DRY_RUN` | `true` | Não | `true` = não grava no HOST |

---

## Fotos dos Produtos

No Render (Linux), o diretório `C:\TSD\Host\imgProdutos` **não existe**.

**Solução 1 — Upload manual:** Copie as imagens para o disco persistente do Render:
```bash
# No Render, as imagens ficariam em /data/imgProdutos
```

**Solução 2 — Servir de outro lugar:** Configure `IMAGENS_PRODUTOS_DIR` para uma URL externa ou bucket S3.

**Solução 3 — Sem imagens (fallback):** Se o diretório não existir, a rota `/api/loja/produto/{id}/foto` retorna 404 e a loja mostra `"Sem imagem"`.

Para uma loja funcional sem imagens, o sistema já funciona perfeitamente — os produtos aparecem com placeholder "Sem imagem".

---

## Banco de Dados

### SQLite (padrao)

O banco fica em `/data/portal.db` (disco persistente configurado no Web Service).

**Importante:** Para que os dados sobrevivam a redeploys, o Render precisa de um **Persistent Disk** montado em `/data`.
Sem ele, a cada deploy o SQLite e criado vazio e voce precisa rodar `sincronizar_render.py` novamente.

**Cuidados:**
- SQLite não suporta concorrência pesada (várias requisições simultâneas podem dar `database is locked`)
- Para um volume baixo de pedidos (dezenas/dia), SQLite aguenta bem
- O Render Free tem 512 MB de RAM — limite de conexões SQLite não será problema

---

## Apos cada deploy: repovoar o portal

Render Free **nao mantem dados** entre deploys. Apos cada deploy, execute:

### Comando unico (recomendado)

```bash
cd C:\Users\NONATO\Documents\ifodpirata
```

**PowerShell:**
```powershell
$env:PORTAL_URL="https://ifodpirata.onrender.com"
$env:PORTAL_API_KEY="SUA_CHAVE"
python deploy_completo.py
```

**CMD:**
```cmd
set PORTAL_URL=https://ifodpirata.onrender.com
set PORTAL_API_KEY=SUA_CHAVE
python deploy_completo.py
```

O `deploy_completo.py` executa em sequencia:
1. Testa se o portal esta online
2. Sincroniza produtos, grupos e clientes do Firebird
3. Envia as fotos dos produtos (5553 arquivos)
4. Verifica o resultado final

### Comandos individuais

```bash
# Testar conexao
python testar_render.py

# Sincronizar dados
python sincronizar_render.py

# Sincronizar fotos (~20 min)
python sincronizar_fotos_render.py

# Diagnosticar imagens no Render
python diagnosticar_imagens_render.py

# Importar pedidos pendentes do portal para o HOST
python importar_pedidos_online.py

# Agente continuo (sync + import a cada 60s)
python run_agent.py
```

### PostgreSQL (futuro)

Para preparar, o `requirements.txt` já tem suporte. Basta:
1. Adicionar `psycopg2-binary` ao `requirements.txt`
2. Criar um banco PostgreSQL no Render
3. Alterar `portal/models.py` para usar `DATABASE_URL`
4. Configurar `DATABASE_URL` nas env vars

---

## Links úteis

- [Render Dashboard](https://dashboard.render.com)
- [Render Docs - Python](https://render.com/docs/deploy-flask)
- [Render Docs - Disks](https://render.com/docs/disks)
- [Render Docs - Workers](https://render.com/docs/background-workers)
