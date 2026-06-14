@echo off
:: AeroTherm Windows Launcher
title AeroTherm - Surveillance Thermique
echo 🚀 Demarrage de AeroTherm...
cd /d "%~dp0"

:: Install dependencies if not present
if not exist node_modules (
    echo 📦 Installation des dependances npm...
    call npm install
)

:: Launch browser in default system browser
echo 🌐 Ouverture du tableau de bord...
start http://localhost:3000

:: Start express server
echo 🔥 Lancement du serveur de surveillance...
node server.js

pause
