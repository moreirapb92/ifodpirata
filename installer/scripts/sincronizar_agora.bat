@echo off
title IfodPirata Agente - Sincronizar Agora
cd /d "C:\IfodPirataAgente"
agente.exe --sync-once
echo.
echo Pressione qualquer tecla para sair...
pause >nul
