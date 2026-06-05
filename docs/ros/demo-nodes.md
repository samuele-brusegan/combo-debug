# Nodi ROS 2 di esempio

Documento foglia: descrive i nodi demo usati per testare la dashboard senza un
robot reale. Sono semplici script `rclpy` in `ros2_demo/nodes/`, avviati dallo
start del container tramite `ros2_demo/run_demo.sh`.

| Nodo            | Topic/Servizio/Azione | Comportamento                                  | Stato atteso in dashboard |
| --------------- | --------------------- | ---------------------------------------------- | ------------------------- |
| `talker`        | pub `/chatter`       | Pubblica a 1 Hz.                            | **Verde**                 |
| `listener`      | sub `/chatter`       | Ascolta `/chatter`.                         | **Verde**                 |
| `stuck_spinner` | pub `/heartbeat`      | Spin "bloccato": pubblica ~0.2 Hz (sleep 4s nella callback). | Nodo **verde**; `/heartbeat` verde nel pannello Topics |
| `crasher`       | —                     | Solleva un'eccezione dopo ~15s e termina.      | **Rosso** (atteso ma assente) |
| `publisher_only` | pub `/chatter_no_sub` | Pubblica a 1 Hz senza subscriber.             | **Giallo** (nessun subscriber) |
| `subscriber_only` | sub `/chatter_no_pub` | Ascolta senza publisher.                       | **Giallo** (nessun publisher) |
| `add_two_ints_server` | srv `/add_two_ints`   | Server sano (client attivo).                   | **Verde**                 |
| `add_two_ints_client` | srv `/add_two_ints`   | Client sano (server attivo).                   | **Verde**                 |
| `add_two_ints_server_only` | srv `/add_two_ints_no_sub` | Server senza client (zombie per assenza di subscriber). | **Zombie** (viola) |
| `add_two_ints_client_only` | srv `/add_two_ints_no_pub` | Client senza server (zombie per assenza di publisher). | **Zombie** (viola) |
| `reset_counter_server` | srv `/reset_counter`  | Server sano (client attivo).                   | **Verde**                 |
| `reset_counter_client` | srv `/reset_counter`  | Client sano (server attivo).                   | **Verde**                 |
| `reset_counter_server_only` | srv `/reset_counter_no_sub` | Server senza client (zombie per assenza di subscriber). | **Zombie** (viola) |
| `reset_counter_client_only` | srv `/reset_counter_no_pub` | Client senza server (zombie per assenza di publisher). | **Zombie** (viola) |
| `fibonacci_server` | act `/fibonacci`      | Server azione sano (client attivo).            | **Verde**                 |
| `fibonacci_client` | act `/fibonacci`      | Client azione sano (server attivo).            | **Verde**                 |
| `fibonacci_server_only` | act `/fibonacci_no_sub` | Server azione senza client (zombie per assenza di subscriber). | **Zombie** (viola) |
| `fibonacci_client_only` | act `/fibonacci_no_pub` | Client azione senza server (zombie per assenza di publisher). | **Zombie** (viola) |
| `navigate_server` | act `/navigate_to_pose` | Server azione sano (client attivo).            | **Verde**                 |
| `navigate_client` | act `/navigate_to_pose` | Client azione sano (server attivo).            | **Verde**                 |
| `navigate_server_only` | act `/navigate_no_sub` | Server azione senza client (zombie per assenza di subscriber). | **Zombie** (viola) |
| `navigate_client_only` | act `/navigate_no_pub` | Client azione senza server (zombie per assenza di publisher). | **Zombie** (viola) |

## Perche' script invece di un package colcon

I nodi sono semplici nodi `rclpy`: eseguirli con `python3 nodo.py` (dopo aver
fatto il source dell'ambiente ROS) evita la complessita' e i punti di rottura
di un build `colcon`, mantenendo la demo riproducibile. Per un progetto reale e'
consigliabile convertirli in un package `ament_python` con `entry_points`.

## Come si collegano agli stati della dashboard

- **Verde/Rosso (requisito 1)**: i nodi presenti nel grafo e responsivi sono
  verdi; `crasher`, essendo tra i nodi attesi ma assente dopo il crash, e'
  rosso. Vedi `COMBO_DEBUG_EXPECTED_NODES`.
- **Topics / Servizi / Azioni con zombie**: i pannelli del grafo elencano le
  entita' rilevate e ne mostrano lo stato. Un'entita' diventa **zombie** quando
  resta nel grafo ma nessun nodo attivo la usa piu' (es. tutti i suoi publisher
  sono crashati): in tal caso e' evidenziata in viola con il badge `ZOMBIE`.
  Lo stato **giallo** indica invece un'entita' con soli consumatori attivi e
  nessun produttore (produttore mancante/crashato).

## Disattivare i nodi demo

Imposta `COMBO_DEBUG_START_DEMO=0` nel servizio `ros-backend` del
`docker-compose.yml`. In tal caso la dashboard mostrera' i nodi reali presenti
nel grafo ROS al quale il container e' collegato.
