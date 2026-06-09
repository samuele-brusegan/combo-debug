/* =============================================================================
 * Combo-Debug - Echo on-demand di un topic.
 *
 * Cattura e mostra un singolo messaggio dal topic selezionato, in un modal.
 * ============================================================================= */

"use strict";

import { apiGet } from "./api.js";
import { escapeHtml } from "./utils.js";

/** Restituisce l'istanza (singleton) del modal Bootstrap di echo. */
function echoModal() {
  return bootstrap.Modal.getOrCreateInstance(document.getElementById("echo-modal"));
}

/**
 * Apre il modal di echo e cattura un messaggio dal topic indicato.
 * @param {string} topic Nome del topic da ispezionare.
 * @returns {Promise<void>}
 */
export async function openTopicEcho(topic) {
  document.getElementById("echo-topic").textContent = topic;
  const output = document.getElementById("echo-output");
  output.textContent = "Cattura del prossimo messaggio in corso...";
  echoModal().show();
  try {
    const params = new URLSearchParams({ topic });
    const result = await apiGet("/topics/echo", params);
    output.textContent = result.available
      ? result.message
      : result.detail || "Nessun messaggio disponibile.";
  } catch (err) {
    output.textContent = `Errore: ${escapeHtml(err.message)}`;
  }
}
