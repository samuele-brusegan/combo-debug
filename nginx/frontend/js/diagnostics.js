/* =============================================================================
 * Combo-Debug - Pannello Diagnostica (/diagnostics).
 *
 * Mostra l'ultimo stato diagnostico di ogni componente hardware/software
 * pubblicato su /diagnostics, con color-coding OK/WARN/ERROR/STALE.
 * ============================================================================= */

"use strict";

import { apiGet } from "./api.js";
import { escapeHtml } from "./utils.js";
import { setPanelSeverity } from "./panels.js";

/** Mappa il livello diagnostico alla classe del pallino. */
const LEVEL_DOT = {
  ok: "dot-green",
  warn: "dot-yellow",
  error: "dot-red",
  stale: "dot-zombie",
};

/**
 * Aggiorna il pannello Diagnostica con l'ultimo stato di ogni componente.
 * @returns {Promise<void>}
 */
export async function refreshDiagnostics() {
  const list = document.getElementById("diagnostics-list");
  if (!list) {
    return;
  }
  const snapshot = await apiGet("/diagnostics");
  if (!snapshot.available && snapshot.statuses.length === 0) {
    list.innerHTML = `<li class="muted">${escapeHtml(snapshot.detail || "Diagnostica non disponibile.")}</li>`;
    setPanelSeverity("panel-diagnostics", "none");
    return;
  }
  if (snapshot.statuses.length === 0) {
    list.innerHTML = '<li class="muted">Nessuna entrata diagnostica.</li>';
    setPanelSeverity("panel-diagnostics", "none");
    return;
  }
  list.innerHTML = "";
  let severity = "none";
  for (const status of snapshot.statuses) {
    if (status.level === "error" || status.level === "stale") {
      severity = "red";
    } else if (status.level === "warn" && severity !== "red") {
      severity = "yellow";
    }
    const values = (status.values || [])
      .map((v) => `${escapeHtml(v.key)}=${escapeHtml(v.value)}`)
      .join(", ");
    const li = document.createElement("li");
    li.className = "node-item";
    li.title = values || status.message || "";
    li.innerHTML =
      `<span class="dot ${LEVEL_DOT[status.level] || "dot-yellow"}"></span>` +
      `<span class="node-name">${escapeHtml(status.name)}</span>` +
      `<span class="node-reason">${escapeHtml(status.message || status.level)}</span>`;
    list.appendChild(li);
  }
  setPanelSeverity("panel-diagnostics", severity);
}
