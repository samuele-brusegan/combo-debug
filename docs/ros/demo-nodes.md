# Nodi ROS 2 di esempio

Documento foglia: descrive i nodi demo usati per testare la dashboard senza un
robot reale. Sono semplici script `rclpy` in `ros2_demo/nodes/`, avviati dallo
start del container tramite `ros2_demo/run_demo.sh`.

| Nodo            | Topic         | Comportamento                                  | Stato atteso in dashboard |
| --------------- | ------------- | ---------------------------------------------- | ------------------------- |
| `talker`        | pub `/chatter`   | Pubblica a 1 Hz.                            | **Verde**                 |
| `listener`      | sub `/chatter`   | Ascolta `/chatter`.                         | **Verde**                 |
| `stuck_spinner` | pub `/heartbeat` | Spin "bloccato": pubblica ~0.2 Hz (sleep 4s nella callback). | Nodo verde, ma `/heartbeat` **giallo** nel report di salute |
| `crasher`       | —             | Solleva un'eccezione dopo ~15s e termina.      | **Rosso** (atteso ma assente) |

## Perche' script invece di un package colcon

I nodi sono semplici nodi `rclpy`: eseguirli con `python3 nodo.py` (dopo aver
fatto il source dell'ambiente ROS) evita la complessita' e i punti di rottura
di un build `colcon`, mantenendo la demo riproducibile. Per un progetto reale e'
consigliabile convertirli in un package `ament_python` con `entry_points`.

## Come si collegano agli stati della dashboard

- **Verde/Rosso (requisito 1)**: i nodi presenti nel grafo e responsivi sono
  verdi; `crasher`, essendo tra i nodi attesi ma assente dopo il crash, e'
  rosso. Vedi `COMBO_DEBUG_EXPECTED_NODES`.
- **Giallo / spin bloccato (requisito 4)**: `stuck_spinner` non rispetta la
  frequenza minima attesa su `/heartbeat` (`COMBO_DEBUG_EXPECTED_TOPICS`),
  quindi il report di salute lo segnala.

## Disattivare i nodi demo

Imposta `COMBO_DEBUG_START_DEMO=0` nel servizio `ros-backend` del
`docker-compose.yml`. In tal caso la dashboard mostrera' i nodi reali presenti
nel grafo ROS al quale il container e' collegato.
