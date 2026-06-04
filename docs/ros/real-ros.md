# Aggancio a un ROS 2 reale

Documento foglia: spiega come collegare Combo-Debug a un **ecosistema ROS 2
reale** (un robot o una rete di nodi gia' esistente) al posto dei nodi demo.

Per default il container `ros-backend` avvia dei nodi `rclpy` di esempio (vedi
[`demo-nodes.md`](demo-nodes.md)). In produzione si disattivano i nodi demo e
si fa in modo che il backend "veda" lo stesso grafo ROS 2 del robot.

## Concetto chiave: condividere il grafo DDS

ROS 2 non usa un master centrale (a differenza di ROS 1): i nodi si scoprono a
vicenda tramite **DDS**, a condizione che condividano:

- lo stesso `ROS_DOMAIN_ID`;
- la stessa `RMW_IMPLEMENTATION` (es. `rmw_fastrtps_cpp`);
- una **rete raggiungibile** a livello DDS (multicast/UDP).

Il backend ispeziona il grafo eseguendo la CLI `ros2` (vedi
[`../backend/README.md`](../backend/README.md)); per ottenere dati reali deve
quindi trovarsi sullo stesso dominio e sulla stessa rete del robot.

## Passo 1 — Disattivare i nodi demo

Nel `docker-compose.yml`, servizio `ros-backend`:

```yaml
environment:
  COMBO_DEBUG_START_DEMO: "0"   # non avviare i nodi di esempio
```

## Passo 2 — Allineare dominio e RMW al robot

Imposta gli stessi valori usati dal robot reale:

```yaml
environment:
  COMBO_DEBUG_START_DEMO: "0"
  ROS_DOMAIN_ID: "0"                 # stesso valore del robot
  RMW_IMPLEMENTATION: rmw_fastrtps_cpp
```

> Verifica il dominio sul robot con `echo $ROS_DOMAIN_ID`. Se non e' impostato,
> il default e' `0`.

## Passo 3 — Rete: far scoprire i nodi via DDS

La discovery DDS usa multicast UDP, che la rete bridge di Docker non inoltra. Le
opzioni piu' comuni, dalla piu' semplice alla piu' isolata:

### Opzione A — `network_mode: host` (consigliata su host Linux)

Il container condivide direttamente lo stack di rete dell'host, quindi vede gli
stessi nodi DDS visibili dall'host.

```yaml
services:
  ros-backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    network_mode: host          # rimuovere allora la sezione networks/expose
    environment:
      COMBO_DEBUG_START_DEMO: "0"
      ROS_DOMAIN_ID: "0"
      RMW_IMPLEMENTATION: rmw_fastrtps_cpp
```

Con `network_mode: host` non si possono usare `networks:` ne' `expose:` per
questo servizio: il backend ascolta direttamente su `localhost:8000`. Nginx
allora deve raggiungere il backend su `host.docker.internal:8000` (o
sull'IP dell'host) invece che su `ros-backend:8000` — aggiornare di conseguenza
il `proxy_pass` in [`../../nginx/nginx.conf`](../../nginx/nginx.conf).

### Opzione B — Discovery Server di Fast DDS

Se il multicast non e' disponibile (es. reti cloud/Wi-Fi che lo bloccano), si
usa un **Discovery Server** e lo si comunica al container:

```yaml
environment:
  COMBO_DEBUG_START_DEMO: "0"
  ROS_DISCOVERY_SERVER: "192.168.1.10:11811"   # IP:porta del discovery server
```

## Passo 4 — Configurare nodi e topic attesi

Le euristiche (nodo assente = rosso, topic sotto soglia = giallo) si basano su
liste di valori attesi. Vanno adattate al robot reale (vedi tabella in
[`../backend/README.md`](../backend/README.md)):

```yaml
environment:
  COMBO_DEBUG_EXPECTED_NODES: "/robot_state_publisher,/controller_manager,/lidar"
  COMBO_DEBUG_EXPECTED_TOPICS: "/scan=10.0,/odom=20.0,/tf=30.0"
```

Formato di `COMBO_DEBUG_EXPECTED_TOPICS`: `nome=frequenza_minima_hz`, separati
da virgola. Ricavabili da `ros2 topic list` e `ros2 topic hz <topic>` sul robot.

## Passo 5 — Log dei nodi reali

Il log parser legge la cartella indicata da `COMBO_DEBUG_ROS_LOG_DIR` (default
`~/.ros/log`). Per analizzare i log del robot, montala come volume:

```yaml
volumes:
  - /percorso/host/ai/log/ros:/root/.ros/log:ro
environment:
  COMBO_DEBUG_ROS_LOG_DIR: /root/.ros/log
```

Su molti sistemi i log ROS 2 si trovano in `~/.ros/log` dell'utente che ha
lanciato i nodi.

## Passo 6 — Verifica

Dopo `docker compose up --build`:

```bash
# Dall'interno del container backend, i nodi reali devono comparire:
docker exec -it combo-debug-ros-backend ros2 node list
docker exec -it combo-debug-ros-backend ros2 topic list
```

Se `ros2 node list` mostra i nodi del robot, la dashboard
(http://localhost:8090) riflettera' lo stato reale: nodi attesi assenti in
rosso, topic sotto la frequenza minima in giallo nel report di salute.

## Risoluzione problemi

| Sintomo                                   | Causa probabile                          | Rimedio                                            |
| ----------------------------------------- | ---------------------------------------- | -------------------------------------------------- |
| Nessun nodo in `ros2 node list`           | Dominio o rete non condivisi             | Verifica `ROS_DOMAIN_ID` e usa `network_mode: host`|
| Nodi visibili ma tutti "rossi"            | `COMBO_DEBUG_EXPECTED_NODES` non allineato | Aggiorna la lista con i nomi reali (`ros2 node list`) |
| Topic sempre "sotto soglia"               | Soglie troppo alte o RMW diverso         | Misura con `ros2 topic hz` e correggi le soglie    |
| Pannello log vuoto                         | Volume dei log non montato               | Monta `~/.ros/log` e imposta `COMBO_DEBUG_ROS_LOG_DIR` |
| Multicast bloccato dalla rete             | Wi-Fi/cloud senza multicast              | Usa il Discovery Server (`ROS_DISCOVERY_SERVER`)   |
