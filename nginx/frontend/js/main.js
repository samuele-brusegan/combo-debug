/* =============================================================================
 * Combo-Debug - Punto di ingresso del frontend (ES module).
 *
 * Recupera periodicamente i dati dal backend via REST (polling) e aggiorna la
 * dashboard. L'impaginazione e i componenti sono di Bootstrap 5; qui si collega
 * il tutto: avvio dell'orologio, polling concatenato e wiring dei pannelli.
 *
 * Dipendenze globali caricate come script classici PRIMA di questo modulo:
 *   - bootstrap (bundle CDN)
 *   - LogFilter (filter.js)
 * ============================================================================= */

"use strict";

import { setupPanelToggles, setupCollapse } from "./panels.js";
import { setupLogFilter, renderFilterBuilder } from "./logs.js";
import { setupConnectionModal } from "./connection.js";
import { refreshAll } from "./dashboard.js";

/** Intervallo di polling in millisecondi. */
const POLL_INTERVAL_MS = 5000;

let pollTimer = null;
let pollingActive = false;

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
