# Frontend (Vanilla JS)

Documento foglia: descrive il frontend statico servito da Nginx.

## File

```
nginx/frontend/
├── index.html   # struttura della dashboard
├── styles.css   # stili (tema scuro, color-coding)
└── app.js       # logica: polling REST + aggiornamento DOM
```

Nessuna toolchain di build: i file sono serviti cosi' come sono, per
massimizzare la manutenibilita' da parte di chi eredita il progetto.

## Pannelli della dashboard

| Pannello                    | Requisito | Endpoint usato                 |
| --------------------------- | --------- | ------------------------------ |
| Nodi ROS 2                  | 1         | `GET /api/nodes`               |
| Salute & spin bloccato      | 4         | `GET /api/health`              |
| Variabili d'ambiente ROS    | 2         | `GET /api/env`                 |
| Tool diagnostici (rqt)      | 4         | `GET /api/rqt/tools`           |
| Log dei nodi                | 3         | `GET /api/logs`, `/api/logs/summary` |

## Funzionamento

- All'avvio (`DOMContentLoaded`) viene eseguito un primo `refreshAll()` e poi
  impostato un `setInterval` di **polling** ogni 5 secondi.
- `refreshAll()` aggiorna ogni pannello in parallelo; l'errore di un singolo
  pannello non blocca gli altri (catch isolato).
- Il color-coding (`green`/`red`/`yellow`) e' mappato a classi CSS dei pallini e
  dei badge.
- Il filtro dei log e' una `<select>` che ricarica solo il pannello log.
- L'aggiornamento automatico puo' essere disattivato dalla checkbox in header.

## Sicurezza

Tutti i valori provenienti dal backend passano per `escapeHtml()` prima di
essere inseriti nel DOM, per prevenire XSS (es. da messaggi di log arbitrari).

## Configurazione

- `POLL_INTERVAL_MS` in `app.js` controlla la frequenza di polling.
- `API_BASE` (`/api`) e' relativo: Nginx fa da reverse proxy, quindi non serve
  configurare host/porta del backend nel frontend.
