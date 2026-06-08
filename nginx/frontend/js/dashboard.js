/* =============================================================================
 * Combo-Debug - Ciclo di aggiornamento della dashboard.
 *
 * Coordina il refresh di tutti i pannelli (polling) e verifica la liveness del
 * backend.
 * ============================================================================= */

"use strict";

import { refreshNodes } from "./nodes.js";
import { refreshGraph } from "./graph.js";
import { refreshEnv } from "./env.js";
import { refreshLogs } from "./logs.js";
import { refreshConnectionBadge } from "./connection.js";

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

let isRefreshing = false;

/**
 * Esegue un ciclo completo di aggiornamento di tutti i pannelli.
 * Gli errori dei singoli pannelli non bloccano gli altri.
 * @returns {Promise<void>}
 */
export async function refreshAll() {
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
