@echo off
title IfodPirata Agente - Instalar como Servico
echo ============================================
echo  IfodPirata Agente - Instalar como Servico
echo ============================================
echo.
echo Este script instala o agente como um servico do Windows
echo usando o Agendador de Tarefas (mais simples, sem dependencias externas).
echo.
echo O servico rodara o agente em modo continuo a cada inicializacao do Windows.
echo.
set /p INSTALAR="Deseja instalar o servico? (S/N): "
if /i not "%INSTALAR%"=="S" goto :sair

echo.
echo Criando tarefa no Agendador do Windows...
schtasks /create /tn "IfodPirataAgente" /tr "C:\IfodPirataAgente\agente.exe --run" /sc onstart /delay 0000:30 /rl highest /f

if %errorlevel% equ 0 (
    echo.
    echo [OK] Servico instalado com sucesso!
    echo O agente rodara automaticamente na inicializacao do Windows.
    echo Para iniciar agora, execute manualmente: agente.exe --run
) else (
    echo.
    echo [ERRO] Nao foi possivel instalar o servico.
    echo Tente executar como Administrador.
)

:sair
echo.
echo Pressione qualquer tecla para sair...
pause >nul
