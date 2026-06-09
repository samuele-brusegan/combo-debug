# Riferimento API REST

Tutti gli endpoint sono montati sotto il prefisso `/api`. La documentazione
interattiva (OpenAPI/Swagger) e' disponibile su `/docs` quando il backend e' in
esecuzione.

## Meta

### `GET /healthz`
Liveness probe del backend.
```json
{ "status": "ok", "version": "0.1.0" }
```

## Nodi — requisito 1

### `GET /api/nodes`
Elenco dei nodi con stato color-coded.
```json
[
  { "name": "/talker", "status": "green", "reason": "Nodo attivo e responsivo." },
  { "name": "/crasher", "status": "red", "reason": "Nodo atteso ma assente dal grafo (crashato/offline)." }
]
```
`status` ∈ `green` | `red` | `yellow`.

## Variabili d'ambiente — requisito 2

### `GET /api/env`
Variabili d'ambiente pertinenti a ROS (prefissi `ROS`, `RMW`, `AMENT`, ...).
```json
[ { "key": "ROS_DOMAIN_ID", "value": "0" } ]
```

## Log — requisito 3

### `GET /api/logs`
Righe di log classificate per severita'.

| Query param   | Tipo            | Default | Descrizione                                  |
| ------------- | --------------- | ------- | -------------------------------------------- |
| `level`       | ripetibile      | —       | Filtra per livello (`error`, `warn`, ...).   |
| `max_entries` | int (1..10000)  | 500     | Numero massimo di righe.                     |

```json
[ { "level": "error", "message": "[ERROR] ...", "source": "talker", "line_number": 12, "timestamp": "2026-06-05T14:23:01.123" } ]
```
Il campo `timestamp` (ISO 8601) proviene dallo `stamp` del messaggio `/rosout`
quando i log sono live; e' `null` per i log letti dai file locali. Il frontend
lo mostra in una colonna dedicata e lo include nell'export CSV.

### `GET /api/logs/summary`
Conteggio righe per livello: `{ "info": 10, "warn": 2, "error": 1 }`.

## Grafo: topic, servizi e azioni (con rilevamento zombie)

### `GET /api/graph`
Restituisce topic, servizi e azioni del grafo con il loro stato. Lo stato e'
derivato incrociando `ros2 <topic|service|action> list` con l'aggregazione di
`ros2 node info` sui nodi attivi:

- `green`  — produttore attivo (publisher per i topic, server per servizi/azioni);
- `yellow` — solo consumatori attivi (subscriber/client), produttore mancante;
- `zombie` — entita' ancora nel grafo ma **nessun** nodo attivo associato
  (tutti i publisher/server, o client, sono crashati lasciando endpoint
  fantasma nella discovery DDS).

I servizi parametro standard di ogni nodo (`*/get_parameters`, `*/set_parameters`, ...)
vengono filtrati per ridurre il rumore.
```json
{
  "topics": [
    { "name": "/chatter", "kind": "topic", "status": "green", "entity_type": "std_msgs/msg/String", "producers": ["talker"], "consumers": ["listener"], "reason": "1 publisher attivo/i: talker." },
    { "name": "/ghost", "kind": "topic", "status": "zombie", "entity_type": "", "producers": [], "consumers": [], "reason": "Zombie: presente nel grafo ma nessun publisher/subscriber attivo ..." }
  ],
  "services": [ { "name": "/add_two_ints", "kind": "service", "status": "green", "producers": ["talker"], "consumers": ["listener"], "reason": "..." } ],
  "actions":  [ { "name": "/fibonacci", "kind": "action", "status": "green", "producers": ["talker"], "consumers": [], "reason": "..." } ]
}
```

## Connessione runtime al grafo ROS 2

Permette di ricollegare il backend a un grafo ROS reale **a caldo**, senza
riavviare il container: i parametri DDS vengono scritti in `os.environ` (quindi
ereditati dalle SysCall `ros2` successive) e i nodi/topic attesi aggiornati
sulle `Settings` condivise. Vedi [`../ros/real-ros.md`](../ros/real-ros.md).

### `GET /api/connection`
Configurazione di connessione attualmente attiva.
```json
{
  "ros_domain_id": "0",
  "rmw_implementation": "rmw_fastrtps_cpp",
  "ros_discovery_server": "",
  "expected_nodes": "/talker,/listener",
  "expected_topics": "/chatter=0.5",
  "ros_log_dir": "/root/.ros/log"
}
```

### `PUT /api/connection`
Applica a caldo i parametri (tutti opzionali; `ros_discovery_server` vuoto =
discovery via multicast). Restituisce la configurazione risultante.
```json
// request (sottoinsieme dei campi)
{ "ros_domain_id": "5", "expected_nodes": "/robot_state_publisher,/lidar" }
```

### `POST /api/connection/test`
Verifica la connessione interrogando il grafo con la config corrente.
```json
{ "available": true, "node_count": 3, "nodes": ["/lidar", "/robot_state_publisher", "/tf"], "detail": "Rilevati 3 nodi nel grafo." }
```

### `GET /api/connection/discover`
Rileva nodi e topic presenti nel grafo con la config corrente, per popolare i
valori attesi dalla UI senza digitarli a mano.
```json
{ "available": true, "nodes": ["/lidar", "/robot_state_publisher"], "topics": ["/scan", "/tf"], "detail": "Rilevati 2 nodi e 2 topic nel grafo." }
```

### `GET /api/connection/rmw`
Implementazioni RMW installate nel container (rilevate via `ros2 pkg list`) e
quella attiva, per popolare il menu a tendina `RMW_IMPLEMENTATION` della UI.
```json
{ "available": ["rmw_cyclonedds_cpp", "rmw_fastrtps_cpp"], "current": "rmw_fastrtps_cpp", "detail": "2 implementazioni RMW installate. ..." }
```

## Parametri dei nodi

### `GET /api/params?node=/talker`
Elenca i parametri dichiarati da un nodo.
```json
{ "node": "/talker", "params": ["use_sim_time"], "available": true, "detail": "" }
```

### `GET /api/params/value?node=/talker&name=use_sim_time`
Legge il valore corrente di un parametro.
```json
{ "node": "/talker", "name": "use_sim_time", "value": "false", "available": true, "detail": "" }
```

### `POST /api/params/value?node=/talker&name=use_sim_time`
Modifica un parametro. **La scrittura puo' alterare lo stato del robot**: il
campo `confirm` deve essere `true`, altrimenti la richiesta e' rifiutata con
**HTTP 409** e nessuna modifica viene applicata (controparte server-side dello
switch di sicurezza della UI).
```json
// request
{ "value": "true", "confirm": true }
// response
{ "node": "/talker", "name": "use_sim_time", "value": "true", "success": true, "detail": "Set parameter successful" }
```

## Echo dei topic

### `GET /api/topics/echo/stream?topic=/chatter`
Sottoscrive il topic (`ros2 topic echo --full-length`) e trasmette **tutti** i
messaggi in tempo reale come stream SSE (`text/event-stream`). La risposta resta
aperta finche' il client non chiude la connessione (chiusura del modal), che
termina il processo `ros2` lato server.

Eventi emessi:
- `info` — messaggio iniziale (in ascolto sul topic);
- `message` — un evento per ogni messaggio catturato (YAML);
- `end` — chiusura dello stream (con nota se il topic era silente).

```text
event: info
data: In ascolto su /chatter — in attesa di messaggi…

event: message
data: data: hello world 42

event: message
data: data: hello world 43
```

## Diagnostica

### `GET /api/diagnostics`
Ultimo stato di ogni componente pubblicato su `/diagnostics`. `available` e'
`false` se il monitor non e' attivo (ROS assente) o nessun messaggio e' arrivato.
```json
{
  "available": true,
  "statuses": [
    { "name": "motore", "level": "warn", "message": "temperatura alta", "hardware_id": "", "values": [ { "key": "temp", "value": "80" } ] }
  ],
  "detail": ""
}
```
`level` ∈ `ok` | `warn` | `error` | `stale`.

## Albero TF

### `GET /api/tf`
Albero delle trasformate rilevato da `/tf` e `/tf_static`. Piu' di una `roots`
indica alberi scollegati.
```json
{
  "available": true,
  "frames": [
    { "frame_id": "odom", "parent": null, "is_static": false },
    { "frame_id": "base_link", "parent": "odom", "is_static": false }
  ],
  "roots": ["odom"],
  "detail": ""
}
```

## Autenticazione (opt-in)

Disabilitata di default (`COMBO_DEBUG_AUTH_ENABLED=false`). Quando abilitata,
tutte le route sotto `/api` (eccetto `/api/auth/*` e `/healthz`) richiedono
l'header `Authorization: Bearer <token>`.

### `GET /api/auth/status`
Indica se l'auth e' abilitata e se la richiesta corrente e' autenticata.
```json
{ "enabled": true, "authenticated": false }
```

### `POST /api/auth/login`
Verifica le credenziali e rilascia un token firmato a tempo. Restituisce
**401** se le credenziali non sono valide, **403** se l'auth e' disabilitata.
```json
// request
{ "username": "admin", "password": "..." }
// response
{ "token": "<token firmato>", "token_type": "bearer" }
```
