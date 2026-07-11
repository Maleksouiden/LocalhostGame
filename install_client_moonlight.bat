@echo off
title Installation de Moonlight (client)
echo Lancement de l'installation de Moonlight...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_client_moonlight.ps1"
pause
