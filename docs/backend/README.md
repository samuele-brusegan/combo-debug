# Backend (Python / FastAPI)

Panoramica del backend. Per il riferimento degli endpoint vedi
[`api.md`](api.md); per pattern e principi vedi [`design.md`](design.md).

## Struttura dei package

```
backend/
├── app/
│   ├── main.py            # Application factory FastAPI
│   ├── core/
│   │   └── config.py      # Configurazione centralizzata (Settings)
│   ├── models/
│   │   └── schemas.py     # DTO Pydantic (contratto API)
│   ├── adapters/
│   │   └── ros_cli.py     # Adapter verso la CLI ros2 (SysCall)
│   ├── services/          # Logica applicativa (un file per area)
│   │   ├── node_service.py
│   │   ├── env_service.py
│   │   ├── log_service.py
│   │   └── health_service.py
│   └── api/
│       ├── deps.py        # Dependency injection (composition root)
│       └── routes/        # Router REST (uno per area)
└── tests/                 # Test con runner ROS fittizio
```

## Responsabilita' dei layer

- **adapters** — unico punto che esegue SysCall; isola il "mondo esterno".
- **services** — logica di dominio; dipendono da astrazioni, non da dettagli.
- **api** — traduce HTTP ⇄ chiamate ai service; nessuna logica di dominio.
- **models** — schemi dati condivisi e serializzabili in JSON.
- **core** — configurazione e utilita' trasversali.

## Configurazione

Tutta la configurazione e' in `app/core/config.py` (classe `Settings`) e si
sovrascrive con variabili d'ambiente prefissate `COMBO_DEBUG_`:

| Variabile                       | Default                                   | Significato                                  |
| ------------------------------- | ----------------------------------------- | -------------------------------------------- |
| `COMBO_DEBUG_ROS_LOG_DIR`       | `~/.ros/log`                              | Cartella dei log analizzata dal parser.      |
| `COMBO_DEBUG_ROS_COMMAND_TIMEOUT` | `8.0`                                   | Timeout (s) delle SysCall a `ros2`.          |
| `COMBO_DEBUG_TOPIC_HZ_WINDOW`   | `4.0`                                     | Finestra (s) di misura di `ros2 topic hz`.   |
| `COMBO_DEBUG_EXPECTED_TOPICS`   | `/chatter=0.5,/heartbeat=1.0`             | Topic attesi `nome=freq_min_hz`.             |
| `COMBO_DEBUG_EXPECTED_NODES`    | `/talker,/listener,/stuck_spinner,/crasher` | Nodi attesi (assenti ⇒ rosso).            |

## Avvio locale (senza Docker)

Richiede un ambiente ROS 2 con `ros2` nel PATH per dati reali; senza ROS l'API
risponde comunque (degrado controllato).

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload
# Docs interattive: http://localhost:8000/docs
```

## Qualita' del codice

Lo stile segue l'equivalente Python di PSR-12 (vedi `pyproject.toml`):
`black` (formattazione), `ruff` (lint PEP 8 + docstring), `mypy` (type hints).
Ogni funzione ha la propria docstring stile Google (il "JavaDoc" Python).
