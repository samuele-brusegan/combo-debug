# Architettura

Documento di livello intermedio: descrive i componenti del sistema e come
interagiscono. Per i dettagli implementativi rimanda ai documenti di area.

## Vista dei container (deployment)

```mermaid
flowchart LR
    browser["Browser<br/>(frontend Vanilla JS)"]

    subgraph net["rete docker: combo-debug-net"]
        subgraph c2["Container 2: nginx"]
            nginx["Nginx<br/>static + reverse proxy"]
        end
        subgraph c1["Container 1: ros-backend (ROS 2 Humble)"]
            api["Backend FastAPI<br/>:8000"]
            adapter["Adapter ros2 CLI"]
            nodes["Nodi ROS 2 demo<br/>talker / listener /<br/>stuck_spinner / crasher"]
            logs[("~/.ros/log")]
        end
    end

    browser -- "HTTP :8090<br/>statici + /api/*" --> nginx
    nginx -- "proxy /api, /healthz" --> api
    api --> adapter
    adapter -- "SysCall: ros2 node/topic" --> nodes
    api -- "legge file di log" --> logs
    nodes -- "scrivono log" --> logs
```

## Componenti

### Container 1 — `ros-backend`

Immagine basata su **ROS 2 Humble** (`ros:humble-ros-base`). Contiene:

- **Backend FastAPI**: espone l'API REST consumata dal frontend.
- **Adapter ROS 2**: unico punto che esegue SysCall verso la CLI `ros2`
  (`ros2 node list`, `ros2 node info`, `ros2 topic hz`).
- **Nodi ROS 2 di esempio**: avviati automaticamente per popolare il grafo e
  permettere il test della dashboard.

Il backend deve risiedere **nello stesso container** dei nodi ROS perche':

1. condivide lo stesso `ROS_DOMAIN_ID` / dominio DDS, quindi "vede" lo stesso
   grafo dei nodi;
2. ha accesso diretto all'eseguibile `ros2` e alla cartella dei log
   (`~/.ros/log`).

### Container 2 — `nginx`

Immagine `nginx:alpine`. Svolge due ruoli:

- **web server statico** per il frontend (HTML/CSS/JS);
- **reverse proxy**: inoltra `/api/*` e `/healthz` verso `ros-backend:8000`.

Il browser parla quindi solo con Nginx (una sola origine), evitando problemi di
CORS in produzione.

## Flusso dei dati (polling)

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser (app.js)
    participant N as Nginx
    participant A as FastAPI (router)
    participant S as Service
    participant R as Adapter ros2
    participant ROS as Grafo ROS 2 / log

    loop ogni 5s (refreshAll)
        B->>N: GET /api/nodes
        N->>A: proxy /api/nodes
        A->>S: get_nodes()
        S->>R: run(["node","list"])
        R->>ROS: SysCall `ros2 node list`
        ROS-->>R: stdout
        R-->>S: CommandResult
        S-->>A: list[RosNode]
        A-->>N: JSON
        N-->>B: JSON
        B->>B: aggiorna DOM (color-coding)
    end
```

In sintesi:

1. Il browser carica il frontend statico da Nginx.
2. Il frontend esegue **polling** ogni 5s verso `/api/*`.
3. Nginx inoltra le richieste al backend FastAPI.
4. Il backend, tramite l'Adapter, esegue SysCall a `ros2` (o legge i log dal
   filesystem) e restituisce JSON.
5. Il frontend aggiorna il DOM (color-coding, tabelle, log).

## Scelte tecnologiche

| Ambito        | Scelta            | Motivazione                                        |
| ------------- | ----------------- | -------------------------------------------------- |
| Backend       | Python + FastAPI  | Type hints nativi, OpenAPI automatico, leggero.    |
| Interfaccia ROS | SysCall a `ros2` CLI | Nessuna dipendenza di build; isolata in un Adapter sostituibile con `rclpy`. |
| Frontend      | Vanilla JS        | Nessuna toolchain di build, facile da ereditare.   |
| Real-time     | Polling REST      | Semplicita' e robustezza di manutenzione.          |
| Orchestrazione | Docker Compose    | Due container con rete interna dedicata.           |

## Degrado controllato

Se la CLI `ros2` non e' disponibile o un comando va in timeout, l'Adapter non
solleva eccezioni: restituisce un risultato di errore. I service degradano di
conseguenza (es. nodi non rilevati), senza far cadere l'intera API.
