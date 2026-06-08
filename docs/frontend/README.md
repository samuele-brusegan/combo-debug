# Frontend (Vanilla JS)

Documento foglia: descrive il frontend statico servito da Nginx.

## File

```
nginx/frontend/
├── index.html       # struttura della dashboard
├── styles.css       # stili (tema scuro, color-coding)
├── filter.js        # linguaggio di filtraggio log + query builder (window.LogFilter)
├── vendor/          # asset di terze parti per l'offline (gitignored, vedi sotto)
│   └── bootstrap/     # popolato da ./download-vendor.sh
└── js/              # logica della dashboard, suddivisa in ES modules
    ├── main.js        # punto di ingresso: init, polling, orologio (DOMContentLoaded)
    ├── api.js         # wrapper REST GET/POST + API_BASE
    ├── utils.js       # utility condivise (escapeHtml, dotClass)
    ├── panels.js      # severita' pannelli, pallini, toggle, collasso
    ├── nodes.js       # pannello Nodi
    ├── graph.js       # pannelli Topics/Servizi/Azioni
    ├── env.js         # pannello variabili d'ambiente
    ├── logs.js        # pannello Log: filtro, tabella, export CSV
    ├── connection.js  # badge sorgente dati + modal di connessione
    └── dashboard.js   # ciclo refreshAll() + liveness backend
```

Nessuna toolchain di build: i file sono serviti cosi' come sono, per
massimizzare la manutenibilita' da parte di chi eredita il progetto. La logica
e' suddivisa in **ES modules** (`<script type="module" src="js/main.js">`);
`filter.js` resta uno script classico che espone `window.LogFilter`, caricato
prima del modulo.

## UI: Bootstrap 5 (servito in locale, offline)

Il layout e i componenti (grid, card, tabelle, badge, form, offcanvas, collapse)
sono forniti da **Bootstrap 5**, servito **localmente** da `vendor/bootstrap/`
(nessuna dipendenza da CDN/internet a runtime). Il tema scuro e' attivato da
`data-bs-theme="dark"` sull'elemento `<html>`.

Gli asset di Bootstrap non sono versionati in git (sono terze parti): vanno
scaricati una volta con lo script alla radice del repo, **prima della build**:

```bash
./download-vendor.sh
```

Lo script scarica CSS, JS bundle e i relativi source map in
`nginx/frontend/vendor/bootstrap/`, verificando l'integrita' dei file principali
contro gli hash **SRI (sha384)**. Per aggiornare la versione di Bootstrap si
modificano la variabile `BOOTSTRAP_VERSION` e gli hash SRI nello script (gli
URL `vendor/bootstrap/...` in `index.html` restano invariati). Dettagli sul
deployment: [`../deployment/docker.md`](../deployment/docker.md).

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

- Il punto di ingresso e' `js/main.js`: all'avvio (`DOMContentLoaded`) collega
  gli handler (`setupPanelToggles`, `setupCollapse`, `setupConnectionModal`,
  `setupLogFilter`), esegue un primo `refreshAll()` e avvia il polling.
- Il **polling** e' *concatenato* (`scheduleNextPoll` in `js/main.js`): il ciclo
  successivo viene pianificato con `setTimeout` **dopo** il completamento di
  quello corrente, cosi' un giro lento non fa accumulare richieste sovrapposte.
  L'intervallo e' `POLL_INTERVAL_MS` (5 s).
- `refreshAll()` (in `js/dashboard.js`) aggiorna ogni pannello in parallelo
  invocando le rispettive funzioni `refresh*` dei moduli; l'errore di un singolo
  pannello non blocca gli altri (catch isolato). Una guardia `isRefreshing`
  evita che due cicli si accavallino.
- Il color-coding (`green`/`red`/`yellow`) e' mappato a classi CSS dei pallini e
  dei badge da `dotClass()` (`js/utils.js`).
- Il filtro dei log (`js/logs.js` + `filter.js`) e' lato client: un piccolo
  linguaggio con AST come unica sorgente di verita', sincronizzato tra input
  testuale e query builder a blocchi (vedi sotto).
- L'aggiornamento automatico puo' essere disattivato dalla checkbox nel pannello
  Impostazioni.

### Organizzazione del codice (ES modules)

La logica e' divisa per responsabilita' in `js/` (vedi l'albero in [File](#file)).
Le dipendenze sono esplicite via `import`/`export`: ad esempio `js/dashboard.js`
importa le funzioni `refresh*` dei singoli pannelli, mentre `js/nodes.js`
importa `filterLogsByNode` da `js/logs.js` per il click su un nodo. `filter.js`
non e' un modulo: resta uno script classico che espone l'API `window.LogFilter`,
usata da `js/logs.js`.

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

- `POLL_INTERVAL_MS` in `js/main.js` controlla la frequenza di polling.
- `API_BASE` (`/api`) e' relativo: Nginx fa da reverse proxy, quindi non serve
  configurare host/porta del backend nel frontend.
