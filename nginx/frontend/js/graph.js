/* =============================================================================
 * Combo-Debug - Pannelli Topics, Servizi e Azioni (grafo ROS 2).
 *
 * Renderizza le entita' del grafo evidenziando gli zombie (presenti nel grafo
 * ma senza nodi attivi).
 * ============================================================================= */

"use strict";

import { apiGet } from "./api.js";
import { dotClass, escapeHtml } from "./utils.js";
import { setPanelSeverity } from "./panels.js";
import { openTopicEcho } from "./topics.js";

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
    // Solo i topic offrono l'echo on-demand di un messaggio.
    const echoButton =
      entity.kind === "topic"
        ? '<button type="button" class="btn btn-sm btn-outline-info ms-2 py-0 echo-btn" title="Mostra l\'ultimo messaggio">echo</button>'
        : "";
    li.innerHTML =
      `<span class="dot ${dotClass(entity.status)}"></span>` +
      `<span class="node-name">${escapeHtml(entity.name)}</span>` +
      zombieBadge +
      typeText +
      echoButton;
    const echoEl = li.querySelector(".echo-btn");
    if (echoEl) {
      echoEl.addEventListener("click", () => openTopicEcho(entity.name));
    }
    list.appendChild(li);
  }
  setPanelSeverity(panelId, severity);
}

/**
 * Aggiorna i pannelli Topics, Servizi e Azioni con i dati del grafo ROS 2,
 * evidenziando le entita' zombie (presenti nel grafo ma senza nodi attivi).
 * @returns {Promise<void>}
 */
export async function refreshGraph() {
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
