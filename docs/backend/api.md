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
