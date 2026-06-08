/* =============================================================================
 * Combo-Debug - Pannello Nodi.
 *
 * Elenco dei nodi ROS con color-coding dello stato; il click su un nodo filtra
 * i log su quel nodo (requisito 1).
 * ============================================================================= */

"use strict";

import { apiGet } from "./api.js";
import { dotClass, escapeHtml } from "./utils.js";
import { setPanelSeverity } from "./panels.js";
import { filterLogsByNode } from "./logs.js";

/**
 * Aggiorna l'elenco dei nodi con il color-coding (requisito 1).
 * @returns {Promise<void>}
 */
export async function refreshNodes() {
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
