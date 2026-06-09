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
# 1. Scarica una volta gli asset frontend (Bootstrap) per il funzionamento
#    100% offline. Richiede connessione solo in questo passaggio.
./download-vendor.sh

# 2. Build e avvio dei container.
docker compose up --build
```

Apri poi la dashboard su **http://localhost:8090**.

> La dashboard non dipende da CDN a runtime: gli asset di terze parti sono
> serviti in locale. `./download-vendor.sh` va eseguito prima della prima build
> (gli asset non sono versionati in git). Dettagli:
> [`docs/deployment/docker.md`](docs/deployment/docker.md).

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

## Funzionalita' aggiuntive

- **Diagnostica** – pannello con l'ultimo stato di `/diagnostics`
  (OK/WARN/ERROR/STALE) per componente.
- **Albero TF** – ricostruzione di `/tf` e `/tf_static` con evidenziazione dei
  frame scollegati (piu' radici).
- **Parametri dei nodi** – ispezione e modifica a caldo (`ros2 param`), con uno
  **switch di sicurezza**: la scrittura e' disabilitata finche' non viene
  abilitata esplicitamente e il backend rifiuta ogni modifica non confermata.
- **Echo dei topic** – cattura on-demand di un messaggio (`ros2 topic echo`)
  direttamente dal pannello dei topic.
- **Vista grafica del grafo** – diagramma node-link (Cytoscape.js) di nodi e
  topic con color-coding dello stato.
- **Tema chiaro/scuro** e **layout salvabile** (preferenze in `localStorage`).
- **Autenticazione opt-in** – login con token bearer, attivabile via `.env`
  (`COMBO_DEBUG_AUTH_ENABLED=true`); disabilitata di default.

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

### Test del frontend

I moduli Vanilla JS hanno test unitari con [Vitest](https://vitest.dev) (jsdom),
eseguiti anche in CI. Le dipendenze Node servono **solo** allo sviluppo/CI e non
vengono incluse nell'immagine nginx.

```bash
npm install
npm test
```

### CI

La pipeline GitHub Actions (`.github/workflows/ci.yml`) esegue su ogni push/PR il
linting, il type checking e i test del backend (`ruff`, `black`, `mypy`,
`pytest`) e i test del frontend (`vitest`).
