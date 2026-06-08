/* =============================================================================
 * Combo-Debug - Pannello variabili d'ambiente ROS (requisito 2).
 * ============================================================================= */

"use strict";

import { apiGet } from "./api.js";
import { escapeHtml } from "./utils.js";

/**
 * Aggiorna le variabili d'ambiente ROS (requisito 2).
 * @returns {Promise<void>}
 */
export async function refreshEnv() {
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
