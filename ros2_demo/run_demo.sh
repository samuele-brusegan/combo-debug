#!/usr/bin/env bash
# =============================================================================
# Avvia i nodi ROS 2 di esempio usati per testare la dashboard.
#
# Stati dimostrati:
#   * talker / listener -> nodi sani (VERDE)
#   * stuck_spinner      -> spin bloccato, /heartbeat lento (GIALLO via euristica)
#   * crasher            -> crasha dopo pochi secondi e resta offline (ROSSO)
# =============================================================================
# NB: niente `set -u`: il source di setup.bash di ROS referenzia variabili
# opzionali non sempre impostate (es. AMENT_TRACE_SETUP_FILES).

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash

NODES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nodes"

python3 "${NODES_DIR}/talker.py" &
python3 "${NODES_DIR}/listener.py" &
python3 "${NODES_DIR}/stuck_spinner.py" &
# Il crasher viene avviato una sola volta: dopo il crash resta offline,
# cosi' la dashboard puo' mostrarlo stabilmente in ROSSO.
python3 "${NODES_DIR}/crasher.py" &

wait
