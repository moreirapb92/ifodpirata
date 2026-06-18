# IfodPirata Agente - Instalador

## Pré-requisitos para BUILD

1. **Python 3.9+** com pip
2. **PyInstaller** (`pip install pyinstaller`)
3. **Inno Setup 6** (https://jrsoftware.org/isdl.php) - para gerar o .exe instalador

## Como buildar

### Opção 1: Script automático
Execute `build.bat` dentro da pasta `installer/`:
```
cd installer
build.bat
```

### Opção 2: Passo a passo
```bash
cd installer

# 1. Preparar source
mkdir build_src
copy src\agente.py build_src\
xcopy ..\agent build_src\agent\ /E /I
xcopy ..\config build_src\config\ /E /I
copy src\config.ini.example build_src\

# 2. Compilar com PyInstaller
cd build_src
py -m PyInstaller --onedir --name agente --hidden-import fdb ^
    --hidden-import config.settings --hidden-import agent.db ^
    --hidden-import agent.reader --hidden-import agent.writer ^
    --hidden-import agent.sync --hidden-import agent.importer_online ^
    --hidden-import agent.utils --collect-all fdb ^
    --noconfirm agente.py
cd ..
move build_src\dist\agente dist\agente

# 3. Compilar instalador (Inno Setup)
ISCC.exe agente.iss
```

O instalador será gerado em: `installer\output\IfodPirataAgente_v1.0.0_Setup.exe`

## Estrutura do instalador

```
C:\IfodPirataAgente\
├── agente.exe                    # Executavel principal
├── _internal/                    # Dependencias (PyInstaller)
├── config.ini                    # Configuracao do cliente
├── logs/                         # Logs do agente
│   └── agente.log
├── testar_conexao.bat            # Atalho: testar conexoes
├── sincronizar_agora.bat         # Atalho: sync una vez
├── importar_pedidos.bat          # Atalho: importar pedidos
├── instalar_servico.bat          # Atalho: instalar como servico
└── desinstalar.exe               # Desinstalador
```

## Comandos disponiveis

| Comando | Descricao |
|---------|-----------|
| `agente.exe --testar` | Testa conexoes com portal e Firebird |
| `agente.exe --sync-once` | Sincroniza produtos + importa pedidos |
| `agente.exe --importar-pedidos` | Importa apenas pedidos ACEITOS |
| `agente.exe --run` | Modo continuo (sync a cada N segundos) |
| `agente.exe --config` | Mostra configuracao atual |

## Configuracao do cliente

Cada cliente recebe:
- **API Key** unica (gerada em /admin/empresas)
- **Slug** da empresa (definido no admin)
- **config.ini** pre-preenchido

O instalador cria config.ini apenas se nao existir (preserva edicoes do cliente em atualizacoes).

## Servico do Windows

Durante a instalacao, o usuario pode optar por criar uma tarefa no Agendador do Windows
que inicia o agente automaticamente na inicializacao do sistema.

Para instalar manualmente depois:
```
schtasks /create /tn "IfodPirataAgente" /tr "C:\IfodPirataAgente\agente.exe --run" /sc onstart /delay 0000:30 /rl highest /f
```

Para remover:
```
schtasks /delete /tn "IfodPirataAgente" /f
```
