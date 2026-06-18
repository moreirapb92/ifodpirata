@echo off
title IfodPirata Agente - Importar Pedidos
cd /d "C:\IfodPirataAgente"
agente.exe --importar-pedidos
echo.
echo Pressione qualquer tecla para sair...
pause >nul
