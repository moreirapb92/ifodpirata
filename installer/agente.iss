; Inno Setup Script - IfodPirata Agente Local
; Gera instalador para o agente de sincronizacao local.
; Compilar com: ISCC.exe agente.iss

#define MyAppName "IfodPirata Agente"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "IfodPirata"
#define MyAppURL "https://ifodpirata.onrender.com"

[Setup]
AppId={{B8E3C9A1-4D2F-4A6E-9F0C-1D3E5A7B9C0D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\IfodPirataAgente
DefaultGroupName=IfodPirata Agente
AllowNoIcons=yes
OutputDir=.\output
OutputBaseFilename=IfodPirataAgente_v{#MyAppVersion}_Setup
Compression=lzma2/ultra64
SolidCompression=yes
UninstallDisplayIcon={app}\agente.exe
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=no
DisableWelcomePage=no
DisableReadyPage=no
SetupIconFile=.\assets\icon.ico

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na &Area de Trabalho"; GroupDescription: "Atalhos adicionais:"
Name: "service"; Description: "Instalar como servico do Windows (inicia automaticamente)"; GroupDescription: "Configuracao adicional:"

[Files]
; Executavel principal e dependencias (PyInstaller onedir output)
Source: "..\dist\agente\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: not IsWin64
Source: "..\dist\agente\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: IsWin64
; Configuracao (so cria se nao existir - preserva config do cliente)
Source: "src\config.ini.example"; DestDir: "{app}"; DestName: "config.ini"; Flags: onlyifdoesntexist
; Scripts auxiliares
Source: "scripts\testar_conexao.bat"; DestDir: "{app}"
Source: "scripts\sincronizar_agora.bat"; DestDir: "{app}"
Source: "scripts\importar_pedidos.bat"; DestDir: "{app}"
Source: "scripts\instalar_servico.bat"; DestDir: "{app}"

[Dirs]
Name: "{app}\logs"; Permissions: users-full

[Icons]
Name: "{group}\IfodPirata Agente (Modo Continuo)"; Filename: "{app}\agente.exe"; Parameters: "--run"; WorkingDir: "{app}"; Comment: "Iniciar agente em modo continuo"
Name: "{group}\Testar Conexao"; Filename: "{app}\agente.exe"; Parameters: "--testar"; WorkingDir: "{app}"; Comment: "Testar conexoes com portal e Firebird"
Name: "{group}\Sincronizar Agora"; Filename: "{app}\agente.exe"; Parameters: "--sync-once"; WorkingDir: "{app}"; Comment: "Executar sincronizacao una vez"
Name: "{group}\Importar Pedidos"; Filename: "{app}\agente.exe"; Parameters: "--importar-pedidos"; WorkingDir: "{app}"; Comment: "Importar pedidos ACEITOS do portal"
Name: "{group}\Editar Configuracao"; Filename: "notepad.exe"; Parameters: "{app}\config.ini"; Comment: "Abrir config.ini para edicao"
Name: "{group}\Abrir Pasta do Agente"; Filename: "{app}\"; Comment: "Abrir pasta de instalacao"
Name: "{group}\Desinstalar o Agente"; Filename: "{uninstallexe}"; Comment: "Remover o agente do computador"
; Atalho na Area de Trabalho
Name: "{commondesktop}\IfodPirata Agente"; Filename: "{app}\agente.exe"; Parameters: "--run"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "Iniciar agente em modo continuo"

[Run]
; Testar conexao apos instalacao
Filename: "{app}\agente.exe"; Parameters: "--testar"; Description: "Testar conexao apos instalacao"; Flags: postinstall nowait skipifsilent runascurrentuser
; Mostrar config.ini para edicao
Filename: "notepad.exe"; Parameters: "{app}\config.ini"; Description: "Editar configuracao do agente"; Flags: postinstall nowait skipifsilent shellexec

[UninstallDelete]
Type: files; Name: "{app}\logs\agente.log"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('service') then
    begin
      Log('Installing Windows Scheduled Task...');
      if Exec('schtasks', '/create /tn "IfodPirataAgente" /tr "' + ExpandConstant('{app}') + '\agente.exe --run" /sc onstart /delay 0000:30 /rl highest /f', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        if ResultCode = 0 then
          Log('Scheduled task installed successfully')
        else
          Log('Scheduled task installation failed with code: ' + IntToStr(ResultCode));
      end;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Log('Removing Windows Scheduled Task...');
    Exec('schtasks', '/delete /tn "IfodPirataAgente" /f', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
