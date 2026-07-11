@echo off
title LAN Remote Play - Installation
echo Lancement de l'installation automatique...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
pause
