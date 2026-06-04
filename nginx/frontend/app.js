/* =============================================================================
 * Combo-Debug - Logica del frontend (Vanilla JS).
 *
 * Recupera periodicamente i dati dal backend via REST (polling) e aggiorna la
 * dashboard. Nessun framework: solo fetch + manipolazione del DOM.
 * ============================================================================= */

"use strict";

/** Intervallo di polling in millisecondi. */
const POLL_INTERVAL_MS = 5000;

/** Base path delle API (Nginx fa da reverse proxy verso il backend). */
const API_BASE = "/api";

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
 * Aggiorna l'elenco dei nodi con il color-coding (requisito 1).
 * @returns {Promise<void>}
 */
async function refreshNodes() {
  const list = document.getElementById("nodes-list");
  const nodes = await apiGet("/nodes");
  if (nodes.length === 0) {
    list.innerHTML = '<li class="muted">Nessun nodo rilevato.</li>';
    return;
  }
  list.innerHTML = "";
  for (const node of nodes) {
    const li = document.createElement("li");
    li.innerHTML =
      `<span class="dot ${dotClass(node.status)}"></span>` +
      `<span class="node-name">${escapeHtml(node.name)}</span>` +
      `<span class="node-reason">${escapeHtml(node.reason)}</span>`;
    list.appendChild(li);
  }
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

  const pillClass = { green: "pill-ok", yellow: "pill-warn", red: "pill-bad" }[report.status];
  statusEl.innerHTML = `Stato sistema: <span class="pill ${pillClass}">${report.status}</span>`;

  tbody.innerHTML = "";
  for (const topic of report.topics) {
    const tr = document.createElement("tr");
    const measured = topic.measured_hz === null ? "—" : topic.measured_hz;
    const pill = topic.healthy ? "pill-ok" : "pill-bad";
    const label = topic.healthy ? "ok" : "sotto soglia";
    tr.innerHTML =
      `<td class="mono">${escapeHtml(topic.topic)}</td>` +
      `<td>${topic.expected_hz}</td>` +
      `<td>${measured}</td>` +
      `<td><span class="pill ${pill}">${label}</span></td>`;
    tbody.appendChild(tr);
  }
}

/**
 * Aggiorna l'elenco dei comandi rqt suggeriti (requisito 4).
 * @returns {Promise<void>}
 */
async function refreshRqt() {
  const list = document.getElementById("rqt-list");
  const tools = await apiGet("/rqt/tools");
  list.innerHTML = "";
  for (const tool of tools) {
    const li = document.createElement("li");
    li.innerHTML =
      `<strong>${escapeHtml(tool.label)}</strong>` +
      `<div class="muted">${escapeHtml(tool.description)}</div>` +
      `<code title="Clicca per copiare">${escapeHtml(tool.command)}</code>`;
    const code = li.querySelector("code");
    code.addEventListener("click", () => navigator.clipboard?.writeText(tool.command));
    list.appendChild(li);
  }
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
    badge.className = "pill pill-ok";
  } catch (_err) {
    badge.textContent = "backend: irraggiungibile";
    badge.className = "pill pill-bad";
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
    ["nodi", refreshNodes],
    ["env", refreshEnv],
    ["salute", refreshHealth],
    ["rqt", refreshRqt],
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

// ---- Bootstrap ---------------------------------------------------------------

let pollTimer = null;

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

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("poll-seconds").textContent = String(POLL_INTERVAL_MS / 1000);
  document.getElementById("autorefresh").addEventListener("change", setupPolling);
  document.getElementById("log-level").addEventListener("change", refreshLogs);
  refreshAll();
  setupPolling();
});
