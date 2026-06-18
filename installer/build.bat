@echo off
chcp 65001 >nul
title Build IfodPirata Agente - Instalador

echo ============================================
echo  Build do IfodPirata Agente
echo ============================================
echo.

:: ===== Verificar dependencias =====
echo [1/4] Verificando dependencias...

where py >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python (py) nao encontrado. Instale Python 3.9+.
    exit /b 1
)

py -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    py -m pip install pyinstaller
)

py -c "import fdb" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando fdb...
    py -m pip install fdb
)

:: ===== Preparar diretorio de build =====
echo [2/4] Preparando diretorio de build...

set BUILD_DIR=build_src
if exist %BUILD_DIR% rmdir /s /q %BUILD_DIR%
mkdir %BUILD_DIR%

:: Copiar entry point
copy src\agente.py %BUILD_DIR%\agente.py >nul

:: Copiar pacotes agent e config do projeto principal
xcopy ..\agent %BUILD_DIR%\agent\ /E /I /Q >nul
xcopy ..\config %BUILD_DIR%\config\ /E /I /Q >nul

:: Copiar config.ini.example
copy src\config.ini.example %BUILD_DIR%\config.ini.example >nul

:: ===== Compilar com PyInstaller =====
echo [3/4] Compilando com PyInstaller (onedir)...

cd %BUILD_DIR%

py -m PyInstaller ^
    --onedir ^
    --name agente ^
    --hidden-import fdb ^
    --hidden-import config.settings ^
    --hidden-import agent.db ^
    --hidden-import agent.reader ^
    --hidden-import agent.writer ^
    --hidden-import agent.sync ^
    --hidden-import agent.importer_online ^
    --hidden-import agent.utils ^
    --collect-all fdb ^
    --add-data "config.ini.example;." ^
    --noconfirm ^
    agente.py

if %errorlevel% neq 0 (
    echo.
    echo ERRO: PyInstaller falhou.
    cd ..
    exit /b 1
)

cd ..

:: Mover para dist/
if exist dist\agente rmdir /s /q dist\agente
move %BUILD_DIR%\dist\agente dist\agente >nul

:: ===== Compilar instalador com Inno Setup =====
echo [4/4] Compilando instalador Inno Setup...

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC% (
    echo AVISO: Inno Setup nao encontrado em %ISCC%
    echo O executavel foi compilado em: .\dist\agente\
    echo Para criar o instalador, instale Inno Setup e execute:
    echo   ISCC.exe agente.iss
    echo.
    echo Build parcial concluido.
    pause
    exit /b 0
)

%ISCC% agente.iss

if %errorlevel% neq 0 (
    echo ERRO: Inno Setup falhou.
    pause
    exit /b 1
)

:: ===== Limpeza =====
echo Limpando diretorio temporario...
if exist %BUILD_DIR% rmdir /s /q %BUILD_DIR%

echo.
echo ============================================
echo  BUILD CONCLUIDO COM SUCESSO!
echo ============================================
echo.
echo Instalador gerado em:
echo   .\output\IfodPirataAgente_v1.0.0_Setup.exe
echo.
echo Executavel standalone em:
echo   .\dist\agente\agente.exe
echo.
pause
