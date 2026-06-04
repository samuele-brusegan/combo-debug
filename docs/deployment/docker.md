# Deployment con Docker

Documento foglia: build, configurazione ed esecuzione dei container.

## Servizi

Definiti in `docker-compose.yml`:

- **`ros-backend`** — build da `backend/Dockerfile` (base `ros:humble-ros-base`).
  Espone la porta `8000` solo sulla rete interna. Avvia i nodi demo e il
  backend FastAPI tramite `backend/entrypoint.sh`.
- **`nginx`** — build da `nginx/Dockerfile`. Pubblica la dashboard su
  `http://localhost:8090` e inoltra `/api` al backend.

I due container condividono la rete bridge `combo-debug-net`; Nginx raggiunge il
backend tramite l'hostname di servizio `ros-backend`.

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

## Avvio dei tool grafici rqt

I tool `rqt` richiedono un server X. Di default il backend **non** li lancia: la
dashboard mostra solo i comandi da eseguire manualmente. Per abilitare il lancio
diretto via `POST /api/rqt/launch` occorre fornire un `DISPLAY` valido al
container (montaggio del socket X11), operazione fuori dallo scopo del setup di
base per ragioni di portabilita' e sicurezza.

## Collegarsi a un grafo ROS esterno

Per monitorare nodi su un'altra macchina/host, allinea `ROS_DOMAIN_ID` e la
configurazione di rete DDS, ed eventualmente avvia il container con
`network_mode: host` (Linux) cosi' che il discovery DDS funzioni.
```
