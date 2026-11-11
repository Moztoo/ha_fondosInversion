#!/bin/sh
set -e

echo "[INFO] Iniciando BBVA Fondos de Inversión App..."

# Set database location in persistent storage if inside Home Assistant
if [ -d "/data" ]; then
    export DATABASE_PATH="/data/bbva_fondos.db"
    echo "[INFO] Base de datos persistente configurada en /data/bbva_fondos.db"
fi

export HOST="0.0.0.0"
export PORT="8088"

# Ejecutar servidor FastAPI / Uvicorn
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8088
