/* =============================================================================
 * Combo-Debug - Logica del frontend (Vanilla JS).
 *
 * Recupera periodicamente i dati dal backend via REST (polling) e aggiorna la
 * dashboard. L'impaginazione e i componenti sono di Bootstrap 5; qui si gestisce
 * il fetch dei dati, la visibilita'/collasso dei pannelli e i pallini di stato.
 * ============================================================================= */

"use strict";

/** Intervallo di polling in millisecondi. */
const POLL_INTERVAL_MS = 5000;

/** Base path delle API (Nginx fa da reverse proxy verso il backend). */
const API_BASE = "/api";

/**
 * Severita' corrente di ciascun pannello, usata per il pallino lampeggiante
 * mostrato quando il pannello e' collassato. Valori: "none" | "yellow" | "red".
 * @type {Record<string, string>}
 */
const panelSeverity = {
  "panel-nodes": "none",
  "panel-topics": "none",
  "panel-services": "none",
  "panel-actions": "none",
  "panel-env": "none",
  "panel-logs": "none",
};

/**
 * Esegue una GET JSON verso un endpoint dell'API.
 * @param {string} path Percorso relativo a API_BASE (es. "/nodes").
 * @param {URLSearchParams} [params] Eventuali query string.
 * @returns {Promise<any>} Il corpo JSON deserializzato.
 */
async function apiGet(path, params) {
  const url = new URL(API_BASE + path, window.location.origin);
  if (params) {
    url.search = params.toString();
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} su ${path}`);
  }
  return response.json();
}

/**
 * Esegue una POST JSON verso un endpoint dell'API.
 * @param {string} path Percorso relativo a API_BASE (es. "/connection/test").
 * @param {unknown} [body] Eventuale corpo JSON da inviare.
 * @returns {Promise<any>} Il corpo JSON deserializzato.
 */
async function apiPost(path, body) {
  const url = new URL(API_BASE + path, window.location.origin);
  const response = await fetch(url, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} su ${path}`);
  }
  return response.json();
}

/**
 * Mappa uno stato (green/red/yellow) alla classe CSS del pallino.
 * @param {string} status Stato del nodo.
 * @returns {string} Nome della classe CSS.
 */
function dotClass(status) {
  return (
    { green: "dot-green", red: "dot-red", yellow: "dot-yellow", zombie: "dot-zombie" }[status] ||
    "dot-yellow"
  );
}

/**
 * Registra la severita' di un pannello e aggiorna il relativo pallino di stato.
 * @param {string} panelId Id della sezione del pannello (es. "panel-nodes").
 * @param {string} severity Severita' calcolata: "none" | "yellow" | "red".
 * @returns {void}
 */
function setPanelSeverity(panelId, severity) {
  panelSeverity[panelId] = severity;
  updatePanelDot(panelId);
}

/**
 * Aggiorna il pallino di stato di un pannello: lampeggia (giallo/rosso) solo se
 * il pannello e' collassato e contiene problemi; altrimenti resta nascosto.
 * @param {string} panelId Id della sezione del pannello (es. "panel-nodes").
 * @returns {void}
 */
function updatePanelDot(panelId) {
  const section = document.getElementById(panelId);
  if (!section) {
    return;
  }
  const dot = section.querySelector("[data-status-dot]");
  const body = section.querySelector(".collapse");
  const collapsed = body ? !body.classList.contains("show") : false;
  const severity = panelSeverity[panelId];

  dot.classList.remove("blink-yellow", "blink-red");
  if (collapsed && severity === "red") {
    dot.classList.add("blink-red");
  } else if (collapsed && severity === "yellow") {
    dot.classList.add("blink-yellow");
  }
}

/**
 * Aggiorna l'elenco dei nodi con il color-coding (requisito 1).
 * @returns {Promise<void>}
 */
async function refreshNodes() {
  const list = document.getElementById("nodes-list");
  const nodes = await apiGet("/nodes");
  if (nodes.length === 0) {
    list.innerHTML = '<li class="muted">Nessun nodo rilevato.</li>';
    setPanelSeverity("panel-nodes", "none");
    return;
  }
  list.innerHTML = "";
  let severity = "none";
  for (const node of nodes) {
    if (node.status === "red") {
      severity = "red";
    } else if (node.status === "yellow" && severity !== "red") {
      severity = "yellow";
    }
    const li = document.createElement("li");
    li.className = "node-item";
    li.tabIndex = 0;
    li.title = "Clicca per filtrare i log su questo nodo";
    li.innerHTML =
      `<span class="dot ${dotClass(node.status)}"></span>` +
      `<span class="node-name">${escapeHtml(node.name)}</span>` +
      `<span class="node-reason">${escapeHtml(node.reason)}</span>`;
    li.addEventListener("click", () => filterLogsByNode(node.name));
    li.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        filterLogsByNode(node.name);
      }
    });
    list.appendChild(li);
  }
  setPanelSeverity("panel-nodes", severity);
}

/* ---- Filtro dei log (tabella + query builder) -------------------------------
 * L'AST `logFilterAst` e' l'unica sorgente di verita': testo e blocchi vengono
 * entrambi rigenerati da esso, quindi non possono mai divergere. */

/** AST radice del filtro corrente (gruppo vuoto = mostra tutto). */
let logFilterAst = LogFilter.emptyRoot();

/** Ultimo batch di log scaricato dal backend (per ri-filtrare senza refetch). */
let logEntriesCache = [];

/** Classe del badge Bootstrap per il livello di log. */
function logLevelBadge(level) {
  return (
    {
      fatal: "text-bg-danger",
      error: "text-bg-danger",
      warn: "text-bg-warning",
      info: "text-bg-secondary",
      debug: "text-bg-dark",
    }[level] || "text-bg-secondary"
  );
}

/** Indica se il filtro corrente e' "vuoto" (mostra tutto). */
function isFilterEmpty() {
  return logFilterAst.type === "group" && logFilterAst.children.length === 0;
}

/**
 * Formatta un timestamp ISO 8601 per la colonna della tabella (solo orario con
 * millisecondi). Restituisce un trattino se il timestamp non e' disponibile.
 * @param {string|null|undefined} iso Timestamp ISO 8601 (o assente).
 * @returns {string} Orario compatto (es. "14:23:01.123") oppure "—".
 */
function formatLogTime(iso) {
  if (!iso) {
    return "—";
  }
  const t = String(iso).split("T")[1];
  return t ? t.replace(/[+-]\d{2}:\d{2}$/, "") : String(iso);
}

/** Restituisce le voci di log correnti dopo l'applicazione del filtro attivo. */
function currentFilteredEntries() {
  return logEntriesCache.filter((entry) => LogFilter.matches(logFilterAst, entry));
}

/**
 * Renderizza la tabella dei log applicando il filtro corrente alla cache.
 * @returns {void}
 */
function renderLogTable() {
  const tbody = document.querySelector("#logs-table tbody");
  const filtered = currentFilteredEntries();

  // Riepilogo del filtro attivo accanto alla tabella.
  const activeEl = document.getElementById("log-active-filter");
  const filterText = LogFilter.serialize(logFilterAst);
  activeEl.textContent = filterText ? `filtro: ${filterText}` : "nessun filtro";
  const badge = document.getElementById("log-filter-badge");
  badge.classList.toggle("d-none", isFilterEmpty());

  if (filtered.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="4" class="muted">Nessuna riga di log corrisponde al filtro.</td></tr>';
    return;
  }
  tbody.innerHTML = "";
  for (const entry of filtered) {
    const tr = document.createElement("tr");
    tr.className = `log-row log-${entry.level}`;
    tr.innerHTML =
      `<td class="mono log-time-cell" title="${escapeHtml(entry.timestamp || "")}">${escapeHtml(formatLogTime(entry.timestamp))}</td>` +
      `<td><span class="badge ${logLevelBadge(entry.level)}">${escapeHtml(entry.level)}</span></td>` +
      `<td class="mono log-node-cell" title="Filtra su questo nodo">${escapeHtml(entry.source)}</td>` +
      `<td class="mono log-msg-cell">${escapeHtml(entry.message)}</td>`;
    // Click sul nodo nella tabella: stessa azione del click nel pannello nodi.
    tr.querySelector(".log-node-cell").addEventListener("click", () =>
      filterLogsByNode(entry.source),
    );
    tbody.appendChild(tr);
  }
}

/**
 * Imposta la parte "nodo" del filtro a ``node == <nodeName>`` e aggiorna tutto
 * (tabella, testo e blocchi se la finestra e' aperta), mantenendo il resto del
 * filtro. Espande il pannello log per dare feedback.
 * @param {string} nodeName Nome del nodo (es. "/talker").
 * @returns {void}
 */
function filterLogsByNode(nodeName) {
  logFilterAst = LogFilter.setNodeInFilter(logFilterAst, nodeName);
  syncFilterUiFromAst();
  renderLogTable();
  // Assicura che il pannello log sia visibile/espanso.
  const body = document.getElementById("body-logs");
  if (body) {
    bootstrap.Collapse.getOrCreateInstance(body, { toggle: false }).show();
  }
}

/**
 * Rigenera testo e blocchi a partire dall'AST corrente (mantiene la sincronia).
 * @returns {void}
 */
function syncFilterUiFromAst() {
  const textInput = document.getElementById("log-filter-text");
  if (textInput) {
    textInput.value = LogFilter.serialize(logFilterAst);
    textInput.classList.remove("is-invalid");
    document.getElementById("log-filter-error").textContent = "";
  }
  renderFilterBuilder();
}

/** Renderizza il query builder a blocchi (sincronizzato con l'AST). */
function renderFilterBuilder() {
  const builder = document.getElementById("log-filter-builder");
  if (!builder) {
    return;
  }
  LogFilter.renderBuilder(builder, logFilterAst, () => {
    // Modifica proveniente dai blocchi: aggiorna testo + tabella, mantenendo
    // testo e blocchi sempre allineati. Se un valore (es. una regex) non e'
    // valido lo segnaliamo, senza mai far divergere testo e blocchi.
    const textInput = document.getElementById("log-filter-text");
    const errorEl = document.getElementById("log-filter-error");
    textInput.value = LogFilter.serialize(logFilterAst);
    try {
      LogFilter.parse(textInput.value);
      textInput.classList.remove("is-invalid");
      errorEl.textContent = "";
    } catch (err) {
      textInput.classList.add("is-invalid");
      errorEl.textContent = err.message;
    }
    renderLogTable();
  });
}

/**
 * Gestisce la digitazione nell'input testuale: se valido aggiorna AST + blocchi
 * + tabella; se invalido segnala l'errore senza toccare lo stato (cosi' testo e
 * blocchi non divergono mai: i blocchi restano all'ultimo stato valido).
 * @returns {void}
 */
function onFilterTextInput() {
  const textInput = document.getElementById("log-filter-text");
  const errorEl = document.getElementById("log-filter-error");
  try {
    const ast = LogFilter.parse(textInput.value);
    logFilterAst = ast;
    textInput.classList.remove("is-invalid");
    errorEl.textContent = "";
    renderFilterBuilder();
    renderLogTable();
  } catch (err) {
    textInput.classList.add("is-invalid");
    errorEl.textContent = err.message;
  }
}

/** Azzera il filtro (mostra tutto) e sincronizza UI e tabella. */
function clearLogFilter() {
  logFilterAst = LogFilter.emptyRoot();
  syncFilterUiFromAst();
  renderLogTable();
}

/**
 * Codifica un singolo campo per il formato CSV (RFC 4180): racchiude tra
 * virgolette e raddoppia le virgolette interne.
 * @param {unknown} value Valore da codificare.
 * @returns {string} Campo CSV sicuro.
 */
function csvField(value) {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

/**
 * Esporta in un file CSV i log attualmente filtrati (stesso insieme mostrato in
 * tabella). Le colonne sono: timestamp, livello, nodo, messaggio.
 * @returns {void}
 */
function exportFilteredLogsCsv() {
  const entries = currentFilteredEntries();
  const header = ["timestamp", "livello", "nodo", "messaggio"];
  const rows = entries.map((entry) =>
    [entry.timestamp || "", entry.level, entry.source, entry.message]
      .map(csvField)
      .join(","),
  );
  // BOM iniziale: aiuta Excel a riconoscere la codifica UTF-8.
  const csv = "\uFEFF" + [header.map(csvField).join(","), ...rows].join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const link = document.createElement("a");
  link.href = url;
  link.download = `combo-debug-logs-${stamp}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** Collega gli eventi della finestra di filtro e dell'export. */
function setupLogFilter() {
  document.getElementById("log-filter-text").addEventListener("input", onFilterTextInput);
  document.getElementById("log-filter-clear").addEventListener("click", clearLogFilter);
  document.getElementById("log-export-csv").addEventListener("click", exportFilteredLogsCsv);
  // Alla prima apertura del modal assicura che i blocchi siano renderizzati.
  document
    .getElementById("log-filter-modal")
    .addEventListener("show.bs.modal", syncFilterUiFromAst);
}

/**
 * Aggiorna le variabili d'ambiente ROS (requisito 2).
 * @returns {Promise<void>}
 */
async function refreshEnv() {
  const tbody = document.querySelector("#env-table tbody");
  const variables = await apiGet("/env");
  if (variables.length === 0) {
    tbody.innerHTML = '<tr><td colspan="2" class="muted">Nessuna variabile ROS.</td></tr>';
    return;
  }
  tbody.innerHTML = "";
  for (const item of variables) {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td class="mono">${escapeHtml(item.key)}</td>` +
      `<td class="mono">${escapeHtml(item.value)}</td>`;
    tbody.appendChild(tr);
  }
}

/**
 * Renderizza un elenco di entita' del grafo (topic/servizi/azioni) con il
 * color-coding dello stato ed evidenziando gli zombie in modo distinto.
 * @param {string} listId Id della lista <ul> da popolare.
 * @param {string} panelId Id del pannello (per il pallino di severita').
 * @param {Array<object>} entities Entita' restituite da /graph.
 * @param {string} emptyText Testo mostrato quando non ci sono entita'.
 * @returns {void}
 */
function renderGraphEntities(listId, panelId, entities, emptyText) {
  const list = document.getElementById(listId);
  if (!entities || entities.length === 0) {
    list.innerHTML = `<li class="muted">${escapeHtml(emptyText)}</li>`;
    setPanelSeverity(panelId, "none");
    return;
  }
  list.innerHTML = "";
  let severity = "none";
  for (const entity of entities) {
    // Lo zombie e' un problema "rosso" per il pallino del pannello; il giallo
    // (produttore mancante) e' un'attenzione minore.
    if (entity.status === "zombie") {
      severity = "red";
    } else if (entity.status === "yellow" && severity !== "red") {
      severity = "yellow";
    }
    const li = document.createElement("li");
    li.className = entity.status === "zombie" ? "graph-item entity-zombie" : "graph-item";
    li.title = entity.reason || "";
    const zombieBadge =
      entity.status === "zombie"
        ? '<span class="badge text-bg-dark zombie-badge">ZOMBIE</span>'
        : "";
    const typeText = entity.entity_type
      ? `<span class="entity-type mono">${escapeHtml(entity.entity_type)}</span>`
      : "";
    li.innerHTML =
      `<span class="dot ${dotClass(entity.status)}"></span>` +
      `<span class="node-name">${escapeHtml(entity.name)}</span>` +
      zombieBadge +
      typeText;
    list.appendChild(li);
  }
  setPanelSeverity(panelId, severity);
}

/**
 * Aggiorna i pannelli Topics, Servizi e Azioni con i dati del grafo ROS 2,
 * evidenziando le entita' zombie (presenti nel grafo ma senza nodi attivi).
 * @returns {Promise<void>}
 */
async function refreshGraph() {
  const graph = await apiGet("/graph");
  renderGraphEntities("topics-list", "panel-topics", graph.topics, "Nessun topic rilevato.");
  renderGraphEntities(
    "services-list",
    "panel-services",
    graph.services,
    "Nessun servizio rilevato.",
  );
  renderGraphEntities("actions-list", "panel-actions", graph.actions, "Nessuna azione rilevata.");
}

/**
 * Scarica i log, li mette in cache e renderizza la tabella applicando il filtro
 * corrente (requisito 3). Il filtraggio e' lato client.
 * @returns {Promise<void>}
 */
async function refreshLogs() {
  const params = new URLSearchParams();
  // Scarichiamo un batch ampio senza filtri server-side: il filtraggio (anche
  // con condizioni logiche complesse) avviene lato client sulla cache, cosi' il
  // filtro si riapplica istantaneamente senza rifare richieste.
  params.append("max_entries", "1000");

  const [entries, summary] = await Promise.all([
    apiGet("/logs", params),
    apiGet("/logs/summary"),
  ]);

  logEntriesCache = entries;

  document.getElementById("log-summary").textContent =
    `errori: ${summary.error || 0} · warning: ${summary.warn || 0} · ` +
    `fatal: ${summary.fatal || 0} · info: ${summary.info || 0}`;

  // La severita' del pannello log riflette il riepilogo, non il filtro corrente.
  if ((summary.error || 0) > 0 || (summary.fatal || 0) > 0) {
    setPanelSeverity("panel-logs", "red");
  } else if ((summary.warn || 0) > 0) {
    setPanelSeverity("panel-logs", "yellow");
  } else {
    setPanelSeverity("panel-logs", "none");
  }

  renderLogTable();
}

/**
 * Verifica la liveness del backend e aggiorna il badge di stato.
 * @returns {Promise<void>}
 */
async function refreshBackendStatus() {
  const badge = document.getElementById("backend-status");
  try {
    const data = await (await fetch("/healthz")).json();
    badge.textContent = `backend: ok (v${data.version})`;
    badge.className = "badge text-bg-success";
  } catch (_err) {
    badge.textContent = "backend: irraggiungibile";
    badge.className = "badge text-bg-danger";
  }
}

/**
 * Aggiorna il badge in header che indica la sorgente dati corrente:
 * "Modalita' DEMO" quando si osservano i nodi di esempio, altrimenti "ROS reale".
 * @returns {Promise<void>}
 */
async function refreshConnectionBadge() {
  const badge = document.getElementById("connection-badge");
  const config = await apiGet("/connection");
  badge.classList.remove("d-none", "text-bg-warning", "text-bg-success");
  if (config.demo_mode) {
    badge.classList.add("text-bg-warning");
    badge.textContent = "Modalità DEMO";
    badge.title = "Connesso ai nodi ROS 2 di esempio (demo). Usa 'Collega a ROS reale' per un robot vero.";
  } else {
    badge.classList.add("text-bg-success");
    badge.textContent = `ROS reale · dominio ${config.ros_domain_id}`;
    badge.title = "Connesso a un grafo ROS 2 reale (nodi demo non osservati).";
  }
}

/**
 * Esegue un ciclo completo di aggiornamento di tutti i pannelli.
 * Gli errori dei singoli pannelli non bloccano gli altri.
 * @returns {Promise<void>}
 */
let isRefreshing = false;

async function refreshAll() {
  // Evita che cicli di refresh si accavallino (es. se un giro e' piu' lento
  // dell'intervallo di polling): senza questo guardia le richieste si
  // accumulerebbero e potrebbero saturare il backend.
  if (isRefreshing) {
    return;
  }
  isRefreshing = true;
  try {
    await refreshBackendStatus();
    const tasks = [
      ["connessione", refreshConnectionBadge],
      ["nodi", refreshNodes],
      ["grafo", refreshGraph],
      ["env", refreshEnv],
      ["log", refreshLogs],
    ];
    await Promise.all(
      tasks.map(([name, fn]) =>
        fn().catch((err) => console.error(`Aggiornamento ${name} fallito:`, err)),
      ),
    );
    document.getElementById("last-update").textContent =
      "ultimo aggiornamento: " + new Date().toLocaleTimeString();
  } finally {
    isRefreshing = false;
  }
}

/**
 * Effettua l'escape dei caratteri HTML per prevenire XSS dai dati del backend.
 * @param {unknown} value Valore da convertire in testo sicuro.
 * @returns {string} Stringa con i caratteri speciali HTML codificati.
 */
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

// ---- Collegamento a un ROS 2 reale (riconfigurazione a caldo) ----------------

/**
 * Carica la configurazione di connessione corrente dal backend e popola il form
 * del modal. Invocata all'apertura del modal.
 * @returns {Promise<void>}
 */
async function loadConnectionConfig() {
  const config = await apiGet("/connection");
  document.getElementById("conn-domain").value = config.ros_domain_id ?? "";
  document.getElementById("conn-discovery").value = config.ros_discovery_server ?? "";
  document.getElementById("conn-nodes").value = config.expected_nodes ?? "";
  document.getElementById("conn-topics").value = config.expected_topics ?? "";
  document.getElementById("conn-logdir").value = config.ros_log_dir ?? "";
  await loadRmwOptions(config.rmw_implementation ?? "");
}

/** Valore speciale che, nel menu RMW, attiva l'input testuale personalizzato. */
const RMW_CUSTOM = "__custom__";

/**
 * Popola il menu a tendina delle RMW con quelle installate nel container e
 * seleziona quella corrente. Aggiunge l'opzione "Altro…" per valori custom.
 * @param {string} current RMW attualmente configurata.
 * @returns {Promise<void>}
 */
async function loadRmwOptions(current) {
  const select = document.getElementById("conn-rmw");
  let options;
  try {
    options = await apiGet("/connection/rmw");
  } catch (_err) {
    options = { available: current ? [current] : [], current };
  }
  const available = options.available || [];
  // RMW corrente non nel catalogo (es. personalizzata gia' attiva): la includo.
  const list = current && !available.includes(current) ? [...available, current] : available;

  select.innerHTML = "";
  select.add(new Option("(default ROS)", ""));
  for (const rmw of list) {
    select.add(new Option(rmw, rmw));
  }
  select.add(new Option("Altro… (personalizzata)", RMW_CUSTOM));
  select.value = current && list.includes(current) ? current : "";
  updateRmwCustomVisibility();
}

/** Mostra/nasconde l'input RMW personalizzato in base alla selezione. */
function updateRmwCustomVisibility() {
  const select = document.getElementById("conn-rmw");
  const custom = document.getElementById("conn-rmw-custom");
  const isCustom = select.value === RMW_CUSTOM;
  custom.classList.toggle("d-none", !isCustom);
  if (isCustom) {
    custom.focus();
  }
}

/** Restituisce la RMW effettiva scelta (menu o valore personalizzato). */
function selectedRmw() {
  const select = document.getElementById("conn-rmw");
  if (select.value === RMW_CUSTOM) {
    return document.getElementById("conn-rmw-custom").value.trim();
  }
  return select.value.trim();
}

/**
 * Costruisce il corpo dell'aggiornamento di connessione dai campi del form.
 * @returns {Record<string, string>} Parametri di connessione da inviare.
 */
function buildConnectionUpdate() {
  return {
    ros_domain_id: document.getElementById("conn-domain").value.trim(),
    rmw_implementation: selectedRmw(),
    ros_discovery_server: document.getElementById("conn-discovery").value.trim(),
    expected_nodes: document.getElementById("conn-nodes").value.trim(),
    expected_topics: document.getElementById("conn-topics").value.trim(),
    ros_log_dir: document.getElementById("conn-logdir").value.trim(),
  };
}

/**
 * Applica a caldo i parametri di connessione correnti del form (PUT).
 * @returns {Promise<any>} La configurazione applicata restituita dal backend.
 */
async function applyConnectionConfig() {
  const url = new URL(API_BASE + "/connection", window.location.origin);
  const response = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildConnectionUpdate()),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} applicando la connessione`);
  }
  return response.json();
}

/**
 * Mostra l'esito di una verifica/applicazione di connessione nel modal.
 * @param {string} type Tipo di alert Bootstrap ("success" | "danger" | "warning").
 * @param {string} html Contenuto HTML (gia' sanificato) del messaggio.
 * @returns {void}
 */
function showConnectionResult(type, html) {
  document.getElementById("connection-result").innerHTML =
    `<div class="alert alert-${type} mb-0">${html}</div>`;
}

/**
 * Applica i parametri e verifica la connessione, mostrando i nodi rilevati.
 * Il modal resta aperto per consentire correzioni.
 * @returns {Promise<void>}
 */
async function testConnection() {
  showConnectionResult("secondary", "Verifica in corso...");
  try {
    await applyConnectionConfig();
    const probe = await apiPost("/connection/test");
    if (!probe.available) {
      showConnectionResult("danger", `CLI ROS non disponibile: ${escapeHtml(probe.detail)}`);
      return;
    }
    const list = probe.nodes.map((n) => `<li class="font-monospace">${escapeHtml(n)}</li>`).join("");
    const type = probe.node_count > 0 ? "success" : "warning";
    showConnectionResult(
      type,
      `${escapeHtml(probe.detail)}${list ? `<ul class="mb-0 mt-2">${list}</ul>` : ""}`,
    );
  } catch (err) {
    showConnectionResult("danger", `Errore: ${escapeHtml(err.message)}`);
  }
}

/**
 * Applica i parametri, chiude il modal e aggiorna subito la dashboard.
 * Nessun riavvio: il refresh successivo riflette il grafo reale.
 * @returns {Promise<void>}
 */
async function applyAndRefresh() {
  try {
    await applyConnectionConfig();
    bootstrap.Modal.getInstance(document.getElementById("connection-modal"))?.hide();
    await refreshAll();
  } catch (err) {
    showConnectionResult("danger", `Errore: ${escapeHtml(err.message)}`);
  }
}

/**
 * Applica i parametri correnti e rileva nodi/topic dal grafo, mostrandoli come
 * elenco selezionabile. Cosi' i valori attesi si scelgono invece di digitarli.
 * @returns {Promise<void>}
 */
async function discoverGraph() {
  const container = document.getElementById("discovery-result");
  container.innerHTML = '<div class="text-info small">Rilevamento in corso...</div>';
  try {
    await applyConnectionConfig();
    renderDiscovery(await apiGet("/connection/discover"));
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger mb-0">Errore: ${escapeHtml(err.message)}</div>`;
  }
}

/**
 * Renderizza i nodi/topic rilevati come checkbox selezionabili.
 * @param {any} discovery Esito di GET /api/connection/discover.
 * @returns {void}
 */
function renderDiscovery(discovery) {
  const container = document.getElementById("discovery-result");
  if (!discovery.available) {
    container.innerHTML = `<div class="alert alert-danger mb-0">CLI ROS non disponibile: ${escapeHtml(discovery.detail)}</div>`;
    return;
  }
  if (discovery.nodes.length === 0 && discovery.topics.length === 0) {
    container.innerHTML = `<div class="alert alert-warning mb-0">${escapeHtml(discovery.detail)} Nessun nodo/topic da selezionare (controlla dominio e rete).</div>`;
    return;
  }
  const checkboxes = (items, cls) =>
    items
      .map((name, i) => {
        const id = `${cls}-${i}`;
        return (
          `<div class="form-check"><input class="form-check-input ${cls}" type="checkbox" value="${escapeHtml(name)}" id="${id}" checked />` +
          `<label class="form-check-label font-monospace small" for="${id}">${escapeHtml(name)}</label></div>`
        );
      })
      .join("") || '<span class="muted">nessuno</span>';
  container.innerHTML =
    `<div class="row g-3">` +
    `<div class="col-md-6"><div class="fw-semibold small mb-1">Nodi rilevati (${discovery.nodes.length})</div>` +
    `<div class="border rounded p-2 overflow-auto" style="max-height: 180px">${checkboxes(discovery.nodes, "discover-node")}</div></div>` +
    `<div class="col-md-6"><div class="fw-semibold small mb-1">Topic rilevati (${discovery.topics.length})</div>` +
    `<div class="border rounded p-2 overflow-auto" style="max-height: 180px">${checkboxes(discovery.topics, "discover-topic")}</div></div>` +
    `<div class="col-12"><button type="button" class="btn btn-info btn-sm" id="discovery-use">Usa selezionati</button>` +
    `<span class="muted ms-2">${escapeHtml(discovery.detail)}</span></div></div>`;
  document.getElementById("discovery-use").addEventListener("click", useDiscoverySelection);
}

/**
 * Popola i campi "nodi/topic attesi" con gli elementi rilevati selezionati.
 * Ai topic viene applicata la frequenza minima indicata in "freq. minima topic".
 * @returns {void}
 */
function useDiscoverySelection() {
  const hz = document.getElementById("discover-hz").value.trim() || "1.0";
  const nodes = [...document.querySelectorAll(".discover-node:checked")].map((c) => c.value);
  const topics = [...document.querySelectorAll(".discover-topic:checked")].map((c) => `${c.value}=${hz}`);
  document.getElementById("conn-nodes").value = nodes.join(",");
  document.getElementById("conn-topics").value = topics.join(",");
}

/**
 * Collega gli eventi del modal di connessione (apertura, scoperta, verifica, applica).
 * @returns {void}
 */
function setupConnectionModal() {
  const modal = document.getElementById("connection-modal");
  modal.addEventListener("show.bs.modal", () => {
    document.getElementById("connection-result").innerHTML = "";
    document.getElementById("discovery-result").innerHTML = "";
    loadConnectionConfig().catch((err) =>
      showConnectionResult("danger", `Impossibile leggere la configurazione: ${escapeHtml(err.message)}`),
    );
  });
  document.getElementById("conn-rmw").addEventListener("change", updateRmwCustomVisibility);
  document.getElementById("connection-discover").addEventListener("click", discoverGraph);
  document.getElementById("connection-test").addEventListener("click", testConnection);
  document.getElementById("connection-apply").addEventListener("click", applyAndRefresh);
}

// ---- Bootstrap (avvio) -------------------------------------------------------

let pollTimer = null;

/** Avvia l'orologio in header che mostra l'ora esatta corrente (aggiornata al secondo). */
function startClock() {
  const clock = document.getElementById("clock");
  const tick = () => {
    clock.textContent = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };
  tick();
  setInterval(tick, 1000);
}

let pollingActive = false;

/**
 * Pianifica il prossimo ciclo di refresh DOPO il completamento di quello
 * corrente (polling concatenato): cosi' un ciclo lento non fa accumulare
 * richieste sovrapposte sul backend.
 * @returns {void}
 */
function scheduleNextPoll() {
  if (!pollingActive) {
    return;
  }
  pollTimer = setTimeout(async () => {
    await refreshAll();
    scheduleNextPoll();
  }, POLL_INTERVAL_MS);
}

/** Avvia o riavvia il polling concatenato in base alla checkbox. */
function setupPolling() {
  const checkbox = document.getElementById("autorefresh");
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  pollingActive = checkbox.checked;
  if (pollingActive) {
    scheduleNextPoll();
  }
}

/**
 * Collega le checkbox delle impostazioni alla visibilita' dei pannelli.
 * @returns {void}
 */
function setupPanelToggles() {
  for (const toggle of document.querySelectorAll(".panel-toggle")) {
    toggle.addEventListener("change", () => {
      const section = document.getElementById(toggle.dataset.panel);
      if (section) {
        section.classList.toggle("d-none", !toggle.checked);
      }
    });
  }
}

/**
 * Collega gli eventi di collasso dei pannelli per aggiornare il pallino di
 * stato (visibile solo quando collassato) e i bottoni "Collassa/Espandi tutti".
 * @returns {void}
 */
function setupCollapse() {
  for (const body of document.querySelectorAll("main .collapse")) {
    const panelId = body.id.replace("body-", "panel-");
    body.addEventListener("shown.bs.collapse", () => updatePanelDot(panelId));
    body.addEventListener("hidden.bs.collapse", () => updatePanelDot(panelId));
  }

  const applyToAll = (show) => {
    for (const body of document.querySelectorAll("main .collapse")) {
      const instance = bootstrap.Collapse.getOrCreateInstance(body, { toggle: false });
      show ? instance.show() : instance.hide();
    }
  };
  document.getElementById("collapse-all").addEventListener("click", () => applyToAll(false));
  document.getElementById("expand-all").addEventListener("click", () => applyToAll(true));
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("poll-seconds").textContent = String(POLL_INTERVAL_MS / 1000);
  document.getElementById("autorefresh").addEventListener("change", setupPolling);
  setupPanelToggles();
  setupCollapse();
  setupConnectionModal();
  setupLogFilter();
  renderFilterBuilder();
  startClock();
  refreshAll();
  setupPolling();
});
