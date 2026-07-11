@echo off
title Installation de Sunshine (serveur)
echo Lancement de l'installation de Sunshine...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_server_sunshine.ps1"
pause
