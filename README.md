# Combo-Debug

Web app di **debugging e monitoraggio** per un ecosistema misto, con focus sui
nodi **ROS 2**. Mostra in tempo reale lo stato dei nodi (color-coding
verde/rosso), le variabili d'ambiente ROS, i log classificati per severita' ed
alcune euristiche avanzate (rilevamento spin bloccato).

L'applicazione gira interamente in **Docker** ed e' composta da due container:

| Container     | Contenuto                                                        |
| ------------- | ---------------------------------------------------------------- |
| `ros-backend` | ROS 2 Humble + backend Python/FastAPI + nodi ROS 2 di esempio    |
| `nginx`       | Web server statico (frontend Vanilla JS) + reverse proxy `/api`  |

## Avvio rapido

```bash
docker compose up --build
```

Apri poi la dashboard su **http://localhost:8090**.

I nodi demo vengono avviati automaticamente e dimostrano tutti gli stati:

- `talker`, `listener` → **verde** (sani)
- `stuck_spinner` → **giallo** nel report di salute (spin bloccato simulato)
- `crasher` → **rosso** (crasha dopo pochi secondi e resta offline)

## Requisiti implementati

1. **Stato dei nodi (color-coding)** – elenco nodi con indicatore verde/rosso.
2. **Variabili d'ambiente ROS** – ispezione di `ROS_DOMAIN_ID`, `RMW_*`, ecc.
3. **Log parser centralizzato** – lettura di `~/.ros/log` con evidenziazione di
   errori e warning.
4. **Funzionalita' avanzate** – euristica di spin bloccato (frequenza topic).

## Collegamento a un ROS 2 reale

Per default vengono avviati nodi ROS 2 di esempio. Per agganciare la dashboard a
un robot/ecosistema ROS 2 reale (disattivare i nodi demo, condividere dominio e
rete DDS, configurare nodi/topic attesi e log) vedi
[`docs/ros/real-ros.md`](docs/ros/real-ros.md).

## Documentazione

La documentazione completa e organizzata ad albero si trova nella cartella
[`docs/`](docs/README.md), dal livello generale (radice) a quello di dettaglio
(foglie).

## Sviluppo

```bash
# Ambiente di sviluppo del backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt

# Qualita' del codice (equivalente Python di PSR-12)
cd backend
ruff check .
black --check .
mypy app
pytest
```
