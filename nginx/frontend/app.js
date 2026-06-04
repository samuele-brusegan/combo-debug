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
  "panel-health": "none",
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
 * Mappa uno stato (green/red/yellow) alla classe CSS del pallino.
 * @param {string} status Stato del nodo.
 * @returns {string} Nome della classe CSS.
 */
function dotClass(status) {
  return { green: "dot-green", red: "dot-red", yellow: "dot-yellow" }[status] || "dot-yellow";
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
    li.innerHTML =
      `<span class="dot ${dotClass(node.status)}"></span>` +
      `<span class="node-name">${escapeHtml(node.name)}</span>` +
      `<span class="node-reason">${escapeHtml(node.reason)}</span>`;
    list.appendChild(li);
  }
  setPanelSeverity("panel-nodes", severity);
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
 * Aggiorna il report di salute / spin bloccato (requisito 4).
 * @returns {Promise<void>}
 */
async function refreshHealth() {
  const statusEl = document.getElementById("health-status");
  const tbody = document.querySelector("#health-table tbody");
  const report = await apiGet("/health");

  const badgeClass = {
    green: "text-bg-success",
    yellow: "text-bg-warning",
    red: "text-bg-danger",
  }[report.status] || "text-bg-secondary";
  statusEl.innerHTML = `Stato sistema: <span class="badge ${badgeClass}">${report.status}</span>`;

  tbody.innerHTML = "";
  for (const topic of report.topics) {
    const tr = document.createElement("tr");
    const measured = topic.measured_hz === null ? "—" : topic.measured_hz;
    const badge = topic.healthy ? "text-bg-success" : "text-bg-danger";
    const label = topic.healthy ? "ok" : "sotto soglia";
    tr.innerHTML =
      `<td class="mono">${escapeHtml(topic.topic)}</td>` +
      `<td>${topic.expected_hz}</td>` +
      `<td>${measured}</td>` +
      `<td><span class="badge ${badge}">${label}</span></td>`;
    tbody.appendChild(tr);
  }

  const severity = { red: "red", yellow: "yellow", green: "none" }[report.status] || "none";
  setPanelSeverity("panel-health", severity);
}

/**
 * Aggiorna il pannello dei log con il filtro di livello selezionato (requisito 3).
 * @returns {Promise<void>}
 */
async function refreshLogs() {
  const container = document.getElementById("logs-container");
  const select = document.getElementById("log-level");
  const params = new URLSearchParams();
  for (const level of select.value.split(",").filter(Boolean)) {
    params.append("level", level);
  }
  params.append("max_entries", "300");

  const [entries, summary] = await Promise.all([
    apiGet("/logs", params),
    apiGet("/logs/summary"),
  ]);

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

  if (entries.length === 0) {
    container.innerHTML = '<p class="muted">Nessuna riga di log per il filtro selezionato.</p>';
    return;
  }
  container.innerHTML = "";
  for (const entry of entries) {
    const div = document.createElement("div");
    div.className = `log-line log-${entry.level}`;
    div.innerHTML =
      `<span class="log-source">[${escapeHtml(entry.source)}:${entry.line_number}]</span> ` +
      escapeHtml(entry.message);
    container.appendChild(div);
  }
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
async function refreshAll() {
  await refreshBackendStatus();
  const tasks = [
    ["connessione", refreshConnectionBadge],
    ["nodi", refreshNodes],
    ["env", refreshEnv],
    ["salute", refreshHealth],
    ["log", refreshLogs],
  ];
  await Promise.all(
    tasks.map(([name, fn]) =>
      fn().catch((err) => console.error(`Aggiornamento ${name} fallito:`, err)),
    ),
  );
  document.getElementById("last-update").textContent =
    "ultimo aggiornamento: " + new Date().toLocaleTimeString();
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
  document.getElementById("conn-rmw").value = config.rmw_implementation ?? "";
  document.getElementById("conn-discovery").value = config.ros_discovery_server ?? "";
  document.getElementById("conn-nodes").value = config.expected_nodes ?? "";
  document.getElementById("conn-topics").value = config.expected_topics ?? "";
  document.getElementById("conn-logdir").value = config.ros_log_dir ?? "";
}

/**
 * Costruisce il corpo dell'aggiornamento di connessione dai campi del form.
 * @returns {Record<string, string>} Parametri di connessione da inviare.
 */
function buildConnectionUpdate() {
  return {
    ros_domain_id: document.getElementById("conn-domain").value.trim(),
    rmw_implementation: document.getElementById("conn-rmw").value.trim(),
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
    const probe = await apiGet("/connection/test");
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

/** Avvia o riavvia il timer di polling in base alla checkbox. */
function setupPolling() {
  const checkbox = document.getElementById("autorefresh");
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (checkbox.checked) {
    pollTimer = setInterval(refreshAll, POLL_INTERVAL_MS);
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
  document.getElementById("log-level").addEventListener("change", refreshLogs);
  setupPanelToggles();
  setupCollapse();
  setupConnectionModal();
  startClock();
  refreshAll();
  setupPolling();
});
