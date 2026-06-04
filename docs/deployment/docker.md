# Deployment con Docker

Documento foglia: build, configurazione ed esecuzione dei container.

## Servizi

Definiti in `docker-compose.yml`:

- **`ros-backend`** — build da `backend/Dockerfile` (base `ros:humble-ros-base`).
  Gira con `network_mode: host` e ascolta sulla porta `8000` dell'host. Avvia i
  nodi demo e il backend FastAPI tramite `backend/entrypoint.sh`.
- **`nginx`** — build da `nginx/Dockerfile`. Pubblica la dashboard su
  `http://localhost:8090` e inoltra `/api` al backend.

Il backend usa la rete dell'host (`network_mode: host`) e condivide l'IPC con
l'host (`ipc: host`, per il transport a memoria condivisa di FastDDS) cosi' che
il discovery DDS e lo scambio dati verso un ROS 2 reale funzionino **senza
modificare il compose**. Nginx resta su rete bridge e raggiunge il backend via
`host.docker.internal` (mappato con `extra_hosts: ["host.docker.internal:host-gateway"]`).

## Comandi

```bash
# Build + avvio
docker compose up --build

# In background
docker compose up -d --build

# Log
docker compose logs -f ros-backend

# Stop
docker compose down
```

## Variabili d'ambiente principali

Impostabili nel blocco `environment:` del servizio `ros-backend`:

| Variabile                  | Default                | Descrizione                              |
| -------------------------- | ---------------------- | ---------------------------------------- |
| `ROS_DOMAIN_ID`            | `0`                    | Dominio DDS condiviso backend/nodi.      |
| `RMW_IMPLEMENTATION`       | `rmw_fastrtps_cpp`     | Implementazione RMW.                     |
| `COMBO_DEBUG_START_DEMO`   | `1`                    | Avvia i nodi demo all'avvio.             |
| `COMBO_DEBUG_*`            | vedi `backend/README`  | Configurazione del backend.              |

## Collegarsi a un grafo ROS esterno

La rete e' gia' condivisa con l'host (`network_mode: host`): per monitorare nodi
su un'altra macchina/host basta allineare `ROS_DOMAIN_ID` (e l'eventuale
`RMW_IMPLEMENTATION`), anche a caldo dalla UI, senza modificare il compose.
Dettagli e casi particolari (Discovery Server, log) in
[`../ros/real-ros.md`](../ros/real-ros.md).
