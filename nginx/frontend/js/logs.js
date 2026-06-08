/* =============================================================================
 * Combo-Debug - Pannello Log (requisito 3).
 *
 * Scarica i log dal backend, li mette in cache e li filtra lato client tramite
 * il linguaggio di filtraggio (vedi filter.js, esposto come window.LogFilter).
 * L'AST `logFilterAst` e' l'unica sorgente di verita': testo e blocchi vengono
 * entrambi rigenerati da esso, quindi non possono mai divergere.
 * ============================================================================= */

"use strict";

import { apiGet } from "./api.js";
import { escapeHtml } from "./utils.js";
import { setPanelSeverity } from "./panels.js";

// `LogFilter` (filter.js) e `bootstrap` (bundle CDN) sono caricati come script
// globali prima di questo modulo: vi si accede tramite lo scope globale.

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
export function filterLogsByNode(nodeName) {
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
export function renderFilterBuilder() {
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
export function setupLogFilter() {
  document.getElementById("log-filter-text").addEventListener("input", onFilterTextInput);
  document.getElementById("log-filter-clear").addEventListener("click", clearLogFilter);
  document.getElementById("log-export-csv").addEventListener("click", exportFilteredLogsCsv);
  // Alla prima apertura del modal assicura che i blocchi siano renderizzati.
  document
    .getElementById("log-filter-modal")
    .addEventListener("show.bs.modal", syncFilterUiFromAst);
}

/**
 * Scarica i log, li mette in cache e renderizza la tabella applicando il filtro
 * corrente (requisito 3). Il filtraggio e' lato client.
 * @returns {Promise<void>}
 */
export async function refreshLogs() {
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
