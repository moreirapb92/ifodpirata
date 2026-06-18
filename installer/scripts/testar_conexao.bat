@echo off
title IfodPirata Agente - Testar Conexao
cd /d "C:\IfodPirataAgente"
agente.exe --testar
echo.
echo Pressione qualquer tecla para sair...
pause >nul
