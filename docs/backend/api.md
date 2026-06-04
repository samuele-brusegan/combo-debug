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
[ { "level": "error", "message": "[ERROR] ...", "source": "node.log", "line_number": 12 } ]
```

### `GET /api/logs/summary`
Conteggio righe per livello: `{ "info": 10, "warn": 2, "error": 1 }`.

## Salute / spin bloccato — requisito 4

### `GET /api/health`
Report euristico basato sulla frequenza dei topic attesi.
```json
{
  "node": "system",
  "status": "yellow",
  "topics": [
    { "topic": "/heartbeat", "expected_hz": 1.0, "measured_hz": null, "healthy": false, "detail": "..." }
  ],
  "notes": ["Topic '/heartbeat' sotto soglia: ..."]
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
