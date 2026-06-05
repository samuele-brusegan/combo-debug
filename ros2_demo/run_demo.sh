#!/usr/bin/env bash
# =============================================================================
# Avvia i nodi ROS 2 di esempio usati per testare la dashboard.
#
# Stati dimostrati:
#   * talker / listener -> nodi sani (VERDE)
#   * stuck_spinner      -> spin bloccato, /heartbeat lento (GIALLO via euristica)
#   * crasher            -> crasha dopo pochi secondi e resta offline (ROSSO)
#   * Servizi (add_two_ints, reset_counter) -> sani (VERDE), zombie (VIOLA)
#   * Azioni (fibonacci, navigate_to_pose) -> sane (VERDE), zombie (VIOLA)
# =============================================================================
# NB: niente `set -u`: il source di setup.bash di ROS referenzia variabili
# opzionali non sempre impostate (es. AMENT_TRACE_SETUP_FILES).

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash

NODES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nodes"

# Topic demo
python3 "${NODES_DIR}/talker.py" &
python3 "${NODES_DIR}/listener.py" &
python3 "${NODES_DIR}/stuck_spinner.py" &
python3 "${NODES_DIR}/publisher_only.py" &
python3 "${NODES_DIR}/subscriber_only.py" &
# Il crasher viene avviato una sola volta: dopo il crash resta offline,
# cosi' la dashboard puo' mostrarlo stabilmente in ROSSO.
python3 "${NODES_DIR}/crasher.py" &

# Servizi demo (sani e zombie)
python3 "${NODES_DIR}/add_two_ints_server.py" &
python3 "${NODES_DIR}/add_two_ints_client.py" &
python3 "${NODES_DIR}/add_two_ints_server_only.py" &
python3 "${NODES_DIR}/add_two_ints_client_only.py" &
python3 "${NODES_DIR}/reset_counter_server.py" &
python3 "${NODES_DIR}/reset_counter_client.py" &
python3 "${NODES_DIR}/reset_counter_server_only.py" &
python3 "${NODES_DIR}/reset_counter_client_only.py" &

# Azioni demo (sane e zombie)
python3 "${NODES_DIR}/fibonacci_server.py" &
python3 "${NODES_DIR}/fibonacci_client.py" &
python3 "${NODES_DIR}/fibonacci_server_only.py" &
python3 "${NODES_DIR}/fibonacci_client_only.py" &
python3 "${NODES_DIR}/navigate_server.py" &
python3 "${NODES_DIR}/navigate_client.py" &
python3 "${NODES_DIR}/navigate_server_only.py" &
python3 "${NODES_DIR}/navigate_client_only.py" &

wait
