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
| Topics                      | —         | `GET /api/graph`               |
| Servizi                     | —         | `GET /api/graph`               |
| Azioni                      | —         | `GET /api/graph`               |
| Variabili d'ambiente ROS    | 2         | `GET /api/env`                 |
| Log dei nodi                | 3         | `GET /api/logs`, `/api/logs/summary` |

I pannelli **Topics**, **Servizi** e **Azioni** sono popolati da un'unica
chiamata a `GET /api/graph` (`refreshGraph()`) e mostrano lo stato di ogni
entita': verde (produttore attivo), giallo (solo consumatori) e **zombie**
(nel grafo ma senza nodi attivi associati). Lo zombie ha un color-coding
distinto (viola, pallino quadrato lampeggiante, badge `ZOMBIE` e riga
evidenziata) per distinguerlo da un semplice errore rosso.

### Log: timestamp ed export CSV

La tabella dei log ha una colonna **Timestamp** (dallo `stamp` di `/rosout`).
Il pulsante **Esporta CSV** nell'header del pannello scarica le righe
**attualmente filtrate** (stesso insieme mostrato in tabella) in un file
`combo-debug-logs-<istante>.csv` con colonne `timestamp,livello,nodo,messaggio`.

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
  - **rosso**: presenza di errori (nodo rosso, entita' **zombie** in
    topic/servizi/azioni, log con errori/fatal);
  - **giallo**: presenza di warning (nodo giallo, entita' gialla — produttore
    mancante — in topic/servizi/azioni, log con warning).
  - Quando il pannello e' espanso il pallino e' **nascosto** (i problemi sono gia'
    visibili nel contenuto); il pannello `env` non ha una semantica di problema,
    quindi non mostra mai il pallino.
- La severita' per pannello e' ricalcolata ad ogni `refreshAll()` da
  `setPanelSeverity()`; `updatePanelDot()` mostra/nasconde il pallino in base allo
  stato di collasso. Le impostazioni sono **solo di sessione** (nessuna persistenza
  in `localStorage`): si ripristinano ai default al ricaricamento della pagina.

## Collegamento a un ROS 2 reale (a caldo)

- Il pulsante **"Collega a ROS reale"** apre un modal con istruzioni passo passo e
  un form (dominio, RMW, discovery server, nodi/topic attesi, cartella log).
- All'apertura il form viene popolato da `GET /api/connection`. **Scopri nodi e
  topic** applica i valori e chiama `GET /api/connection/discover`, mostrando
  nodi/topic del grafo come checkbox: "Usa selezionati" compila i campi attesi
  (niente digitazione manuale). **Verifica** applica i valori
  (`PUT /api/connection`) e interroga il grafo (`POST /api/connection/test`)
  mostrando i nodi rilevati. **Applica e aggiorna** applica i valori, chiude il
  modal e lancia subito `refreshAll()`.
- Tutto avviene **senza ricaricare la pagina ne' riavviare i container**:
  sfrutta la dinamicita' del DOM e la riconfigurazione a caldo del backend. Vedi
  [`../ros/real-ros.md`](../ros/real-ros.md).
- In header un badge indica la sorgente dati: **"Modalità DEMO"** (giallo) quando
  si stanno osservando i nodi di esempio, **"ROS reale · dominio N"** (verde)
  altrimenti. E' aggiornato ad ogni `refreshAll()` da `refreshConnectionBadge()`
  in base a `demo_mode` restituito da `GET /api/connection`.

## Nodi demo

In modalita' DEMO, il backend avvia i nodi demo descritti in
[`../ros/demo-nodes.md`](../ros/demo-nodes.md). Questi includono:
- **Topic**: `talker`, `listener`, `stuck_spinner`, `crasher`
- **Servizi**: `add_two_ints` (sano + zombie), `reset_counter` (sano + zombie)
- **Azioni**: `fibonacci` (sana + zombie), `navigate_to_pose` (sana + zombie)

Ogni tipo di entita' ha almeno un esempio sano (VERDE) e due zombie (VIOLA):
uno per assenza di publisher/server e uno per assenza di subscriber/client.

## Sicurezza

Tutti i valori provenienti dal backend passano per `escapeHtml()` prima di
essere inseriti nel DOM, per prevenire XSS (es. da messaggi di log arbitrari).

## Configurazione

- `POLL_INTERVAL_MS` in `app.js` controlla la frequenza di polling.
- `API_BASE` (`/api`) e' relativo: Nginx fa da reverse proxy, quindi non serve
  configurare host/porta del backend nel frontend.
