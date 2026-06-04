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

## UI: Bootstrap 5

Il layout e i componenti (grid, card, tabelle, badge, form, offcanvas, collapse)
sono forniti da **Bootstrap 5** caricato via **CDN** (jsDelivr) in `index.html`,
con Subresource Integrity (`integrity`). Il tema scuro e' attivato da
`data-bs-theme="dark"` sull'elemento `<html>`.

> Nota: essendo via CDN, il browser deve avere accesso a internet. Per un
> deployment offline, scaricare i file di Bootstrap in `nginx/frontend/` e
> aggiornare i tag `<link>`/`<script>` con percorsi relativi.

In `styles.css` restano solo gli stili custom non coperti da Bootstrap:
variabili di color-coding, pallini di stato (con animazione di lampeggio) e
formattazione dei log.

## Pannelli della dashboard

| Pannello                    | Requisito | Endpoint usato                 |
| --------------------------- | --------- | ------------------------------ |
| Nodi ROS 2                  | 1         | `GET /api/nodes`               |
| Salute & spin bloccato      | 4         | `GET /api/health`              |
| Variabili d'ambiente ROS    | 2         | `GET /api/env`                 |
| Log dei nodi                | 3         | `GET /api/logs`, `/api/logs/summary` |

## Funzionamento

- All'avvio (`DOMContentLoaded`) viene eseguito un primo `refreshAll()` e poi
  impostato un `setInterval` di **polling** ogni 5 secondi.
- `refreshAll()` aggiorna ogni pannello in parallelo; l'errore di un singolo
  pannello non blocca gli altri (catch isolato).
- Il color-coding (`green`/`red`/`yellow`) e' mappato a classi CSS dei pallini e
  dei badge.
- Il filtro dei log e' una `<select>` che ricarica solo il pannello log.
- L'aggiornamento automatico puo' essere disattivato dalla checkbox nel pannello
  Impostazioni.

## Impostazioni, collasso e pallino lampeggiante

- **Pannello Impostazioni** (offcanvas, apribile dal bottone "Impostazioni"):
  contiene l'interruttore dell'aggiornamento automatico e una checkbox per ogni
  pannello che ne controlla la **visibilita'** (classe `d-none`).
- **Collasso**: ogni card ha un toggle (Bootstrap `collapse`) per nascondere il
  corpo mantenendo l'header. I bottoni "Collassa tutti" / "Espandi tutti" agiscono
  su tutti i pannelli insieme.
- **Pallino di stato lampeggiante**: quando un pannello e' **collassato**, nel suo
  header compare un pallino che lampeggia per segnalare problemi:
  - **rosso**: presenza di errori (nodo rosso, stato salute rosso, log con
    errori/fatal);
  - **giallo**: presenza di warning (nodo giallo, stato salute giallo, log con
    warning).
  - Quando il pannello e' espanso il pallino e' **nascosto** (i problemi sono gia'
    visibili nel contenuto); il pannello `env` non ha una semantica di problema,
    quindi non mostra mai il pallino.
- La severita' per pannello e' ricalcolata ad ogni `refreshAll()` da
  `setPanelSeverity()`; `updatePanelDot()` mostra/nasconde il pallino in base allo
  stato di collasso. Le impostazioni sono **solo di sessione** (nessuna persistenza
  in `localStorage`): si ripristinano ai default al ricaricamento della pagina.

## Sicurezza

Tutti i valori provenienti dal backend passano per `escapeHtml()` prima di
essere inseriti nel DOM, per prevenire XSS (es. da messaggi di log arbitrari).

## Configurazione

- `POLL_INTERVAL_MS` in `app.js` controlla la frequenza di polling.
- `API_BASE` (`/api`) e' relativo: Nginx fa da reverse proxy, quindi non serve
  configurare host/porta del backend nel frontend.
