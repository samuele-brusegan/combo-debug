# Aggancio a un ROS 2 reale

Documento foglia: spiega come collegare Combo-Debug a un **ecosistema ROS 2
reale** (un robot o una rete di nodi gia' esistente) al posto dei nodi demo.

Per default il container `ros-backend` avvia dei nodi `rclpy` di esempio (vedi
[`demo-nodes.md`](demo-nodes.md)). In produzione si disattivano i nodi demo e
si fa in modo che il backend "veda" lo stesso grafo ROS 2 del robot.

## Via rapida: dalla UI, a caldo (senza riavvio)

La dashboard include il pulsante **"Collega a ROS reale"** (in alto a destra) che
apre un modal con istruzioni passo passo e un form per impostare **a caldo**:
`ROS_DOMAIN_ID`, `RMW_IMPLEMENTATION`, `ROS_DISCOVERY_SERVER`, nodi e topic
attesi e la cartella dei log.

- **Scopri nodi e topic**: applica i parametri e rileva dal grafo i nodi e i
  topic realmente presenti, mostrandoli come elenco selezionabile. Con "Usa
  selezionati" i campi "nodi/topic attesi" vengono compilati automaticamente
  (ai topic si applica la frequenza minima indicata), senza digitarli a mano.
- **Verifica**: applica i parametri e interroga subito il grafo, mostrando i nodi
  rilevati (utile per capire se la rete/dominio sono corretti).
- **Applica e aggiorna**: applica i parametri e ricarica la dashboard sui dati
  reali. Nessun riavvio del container: i nuovi valori sono scritti in
  `os.environ` e usati dalle invocazioni `ros2` successive (vedi
  `ConnectionService` e gli endpoint `*/api/connection*` in
  [`../backend/api.md`](../backend/api.md)).

> La rete DDS e' gia' condivisa con l'host: il servizio `ros-backend` gira con
> `network_mode: host` **di default** (vedi `docker-compose.yml`), quindi il
> backend vede lo stesso grafo ROS 2 visibile dall'host. Cambiare dominio/RMW
> dalla UI fa quindi comparire i nodi reali **senza modificare il compose**.
> Unica eccezione: la cartella dei log impostata dalla UI deve essere
> effettivamente montata nel container (passo 5).

I passi seguenti descrivono invece la configurazione **persistente** via
`docker-compose.yml` (consigliata in produzione, es. per disattivare la demo o
montare i log).

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

```env
COMBO_DEBUG_START_DEMO = "0"
ROS_DOMAIN_ID = "0"                     # stesso valore del robot
RMW_IMPLEMENTATION = rmw_fastrtps_cpp   # oppure rmw_cyclonedds_cpp
```

> Verifica il dominio sul robot con `echo $ROS_DOMAIN_ID`. Se non e' impostato,
> il default e' `0`.

> **RMW**: due nodi ROS 2 comunicano solo se usano la **stessa**
> `RMW_IMPLEMENTATION`. L'immagine include sia **Fast DDS**
> (`rmw_fastrtps_cpp`, default) sia **Cyclone DDS** (`rmw_cyclonedds_cpp`),
> quindi puoi allinearti al robot scegliendo l'una o l'altra dalla UI o via
> variabile d'ambiente, **senza ricostruire l'immagine ne' modificare il
> compose**. Se imposti una RMW non installata, la CLI `ros2` fallisce con un
> errore tipo `failed to load shared library 'librmw_*.so'`.

### Aggiungere una nuova `RMW_IMPLEMENTATION`

Il menu a tendina **RMW_IMPLEMENTATION** del modal "Collega a ROS reale" elenca
solo le RMW **realmente installate** nel container: il backend le rileva con
`ros2 pkg list` (endpoint `GET /api/connection/rmw`, vedi
[`../backend/api.md`](../backend/api.md)). Per renderne disponibile una nuova:

1. **Installa il pacchetto** nel [`../../backend/Dockerfile`](../../backend/Dockerfile),
   nello stesso blocco `apt-get install` delle altre RMW. Esempi:

   ```dockerfile
   RUN apt-get update \
       && apt-get install -y --no-install-recommends \
           python3-pip \
           ros-humble-std-msgs \
           ros-humble-rmw-fastrtps-cpp \
           ros-humble-rmw-cyclonedds-cpp \
           ros-humble-rmw-connextdds \
       && rm -rf /var/lib/apt/lists/*
   ```

   > RTI Connext DDS (`rmw_connextdds`) richiede l'accettazione della licenza e
   > non e' sempre disponibile via apt: segui la documentazione ufficiale RTI.

2. Se la RMW non e' nel catalogo di rilevamento, aggiungine il nome al tuple
   `_KNOWN_RMW` in
   [`../../backend/app/services/connection_service.py`](../../backend/app/services/connection_service.py).
3. **Ricostruisci** l'immagine: `docker compose up --build`.
4. La nuova RMW comparira' automaticamente nel menu a tendina.

In alternativa, dalla UI puoi scegliere **"Altro… (personalizzata)"** e digitare
il nome della RMW: deve comunque essere **gia' installata** nel container,
altrimenti la CLI `ros2` fallira' con `failed to load shared library 'librmw_*.so'`.

## Passo 3 — Rete: far scoprire i nodi via DDS

La discovery DDS usa multicast UDP, che la rete bridge di Docker non inoltra.

### Default — `network_mode: host` (gia' configurato)

Il `docker-compose.yml` fornito usa **gia'** `network_mode: host` per
`ros-backend`: il container condivide direttamente lo stack di rete dell'host e
vede quindi gli stessi nodi DDS visibili dall'host. **Non serve modificare
nulla** per agganciare un robot reale sulla rete dell'host: e' sufficiente
allineare dominio/RMW (passo 2) o farlo a caldo dalla UI.

Dettagli di funzionamento (gia' impostati nel repo):

- con `network_mode: host` il backend ascolta direttamente su `localhost:8000`
  dell'host, quindi non si usano `networks:` ne' `expose:` per questo servizio;
- con `ipc: host` il backend condivide `/dev/shm` con l'host. FastDDS usa di
  default il transport a **memoria condivisa (SHM)** tra partecipanti sullo
  stesso host: senza un `/dev/shm` comune il backend non vedrebbe i nodi ROS
  reali in esecuzione sull'host (o in altri container) pur essendo sulla stessa
  rete. Per questo `ipc: host` e' essenziale tanto quanto `network_mode: host`;
- nginx (su rete bridge) raggiunge il backend tramite `host.docker.internal`,
  mappato con `extra_hosts: ["host.docker.internal:host-gateway"]`; il
  `proxy_pass` in [`../../nginx/nginx.conf`](../../nginx/nginx.conf) punta gia'
  a `http://host.docker.internal:8000`.

> Nota: `network_mode: host` condivide lo stack di rete dell'host ed e'
> pienamente supportato su host **Linux** (lo scenario tipico per ROS 2).

### Alternativa — Discovery Server di Fast DDS

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
| Nessun nodo in `ros2 node list`           | Dominio non allineato (rete gia' host)   | Verifica `ROS_DOMAIN_ID` (host vs robot); se host non Linux usa il Discovery Server |
| Nodi reali visti solo "a meta'" o assenti | `/dev/shm` non condiviso (SHM FastDDS)   | Verifica che `ros-backend` abbia `ipc: host` nel compose       |
| `failed to load shared library 'librmw_*.so'` / `ros2` esce con 1 | `RMW_IMPLEMENTATION` non installata | Usa una RMW inclusa (`rmw_fastrtps_cpp` o `rmw_cyclonedds_cpp`) allineata al robot |
| Nodi visibili ma tutti "rossi"            | `COMBO_DEBUG_EXPECTED_NODES` non allineato | Aggiorna la lista con i nomi reali (`ros2 node list`) |
| Topic sempre "sotto soglia"               | Soglie troppo alte o RMW diverso         | Misura con `ros2 topic hz` e correggi le soglie    |
| Pannello log vuoto                         | Volume dei log non montato               | Monta `~/.ros/log` e imposta `COMBO_DEBUG_ROS_LOG_DIR` |
| Multicast bloccato dalla rete             | Wi-Fi/cloud senza multicast              | Usa il Discovery Server (`ROS_DISCOVERY_SERVER`)   |
