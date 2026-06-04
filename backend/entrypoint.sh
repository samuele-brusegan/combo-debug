#!/usr/bin/env bash
# =============================================================================
# Entrypoint del container ros-backend.
#
# 1. Carica l'ambiente ROS 2 Humble (cosi' sia i nodi demo sia il backend
#    vedono lo stesso grafo / ROS_DOMAIN_ID).
# 2. Avvia (opzionalmente) i nodi ROS 2 di esempio.
# 3. Avvia il server FastAPI con uvicorn in foreground (PID 1 del container).
# =============================================================================
set -e

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash

# Cartella di log ROS analizzata dal log parser.
export ROS_LOG_DIR="${ROS_LOG_DIR:-/root/.ros/log}"
mkdir -p "${ROS_LOG_DIR}"

# Avvio dei nodi demo (abilitato di default tramite docker-compose).
if [ "${COMBO_DEBUG_START_DEMO:-0}" = "1" ]; then
    echo "[entrypoint] Avvio dei nodi ROS 2 di esempio..."
    /app/ros2_demo/run_demo.sh &
fi

echo "[entrypoint] Avvio del backend FastAPI su :8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
