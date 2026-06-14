#!/bin/bash

# AeroTherm Linux Launcher
echo "🚀 Démarrage de AeroTherm..."
cd "$(dirname "$0")"

# Install dependencies if not present
if [ ! -d "node_modules" ]; then
    echo "📦 Installation des dépendances npm..."
    npm install
fi

# Run the node server in background
echo "🔥 Lancement du serveur de surveillance..."
node server.js &
SERVER_PID=$!

# Ensure the background server is terminated when the script exits
trap "kill $SERVER_PID" EXIT

# Wait for server startup
sleep 1.5

# Open default web browser
echo "🌐 Ouverture du tableau de bord..."
if command -v xdg-open > /dev/null; then
    xdg-open "http://localhost:3000"
elif command -v sensible-browser > /dev/null; then
    sensible-browser "http://localhost:3000"
elif command -v x-www-browser > /dev/null; then
    x-www-browser "http://localhost:3000"
else
    echo "⚠️ Impossible d'ouvrir le navigateur automatiquement. Ouvrez http://localhost:3000 manuellement."
fi

# Wait for background process to finish (keep terminal open)
wait $SERVER_PID
