/* =============================================================================
 * Combo-Debug - Visualizzazione grafica del grafo ROS 2 (Cytoscape.js).
 *
 * Costruisce un grafo node-link (stile rqt_graph) a partire dai dati gia'
 * esposti dal backend (/nodes e /graph): i nodi ROS e i topic sono vertici, gli
 * archi rappresentano publish/subscribe. Il colore segue lo stato (verde/giallo
 * /rosso/zombie). Cytoscape e' caricato come script globale (vedi index.html).
 * ============================================================================= */

"use strict";

import { apiGet } from "./api.js";

/** Colori degli stati, coerenti con le variabili CSS della dashboard. */
const STATUS_COLOR = {
  green: "#2ea043",
  red: "#f85149",
  yellow: "#d29922",
  zombie: "#a371f7",
  none: "#6e7681",
};

let cy = null;

/** Normalizza un nome di nodo rimuovendo lo slash iniziale. */
function norm(name) {
  return String(name || "").replace(/^\//, "");
}

/**
 * Costruisce gli elementi Cytoscape (nodi/topic + archi) dai dati del backend.
 * @param {Array<object>} nodes Nodi da /api/nodes.
 * @param {object} graph Snapshot da /api/graph.
 * @returns {Array<object>} Elementi per Cytoscape.
 */
export function buildElements(nodes, graph) {
  const elements = [];
  const seen = new Set();

  for (const node of nodes) {
    const id = `n:${norm(node.name)}`;
    seen.add(id);
    elements.push({
      data: { id, label: norm(node.name), color: STATUS_COLOR[node.status] || STATUS_COLOR.none, shape: "ellipse" },
    });
  }

  for (const topic of graph.topics || []) {
    const topicId = `t:${topic.name}`;
    elements.push({
      data: {
        id: topicId,
        label: topic.name,
        color: STATUS_COLOR[topic.status] || STATUS_COLOR.none,
        shape: "round-rectangle",
      },
    });
    const ensureNode = (name) => {
      const id = `n:${norm(name)}`;
      if (!seen.has(id)) {
        seen.add(id);
        elements.push({
          data: { id, label: norm(name), color: STATUS_COLOR.none, shape: "ellipse" },
        });
      }
      return id;
    };
    for (const producer of topic.producers || []) {
      elements.push({ data: { source: ensureNode(producer), target: topicId } });
    }
    for (const consumer of topic.consumers || []) {
      elements.push({ data: { source: topicId, target: ensureNode(consumer) } });
    }
  }
  return elements;
}

/**
 * Carica i dati e (ri)disegna il grafo nel container del modal.
 * @returns {Promise<void>}
 */
async function renderGraphView() {
  const container = document.getElementById("graph-view-canvas");
  const status = document.getElementById("graph-view-status");
  if (typeof cytoscape === "undefined") {
    status.textContent =
      "Cytoscape non caricato: esegui ./download-vendor.sh e ricostruisci l'immagine.";
    return;
  }
  status.textContent = "Caricamento del grafo...";
  const [nodes, graph] = await Promise.all([apiGet("/nodes"), apiGet("/graph")]);
  const elements = buildElements(nodes, graph);

  if (cy) {
    cy.destroy();
  }
  // eslint-disable-next-line no-undef
  cy = cytoscape({
    container,
    elements,
    style: [
      {
        selector: "node",
        style: {
          "background-color": "data(color)",
          shape: "data(shape)",
          label: "data(label)",
          color: "#e6edf3",
          "font-size": "9px",
          "text-valign": "center",
          "text-halign": "center",
          "text-outline-color": "#0d1117",
          "text-outline-width": 2,
          width: "label",
          height: "24px",
          padding: "6px",
        },
      },
      {
        selector: "edge",
        style: {
          width: 1.5,
          "line-color": "#484f58",
          "target-arrow-color": "#484f58",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
        },
      },
    ],
    layout: { name: "breadthfirst", directed: true, padding: 10, spacingFactor: 1.1 },
  });
  status.textContent = `${nodes.length} nodi · ${(graph.topics || []).length} topic`;
}

/**
 * Collega gli eventi del modal della vista grafica.
 * @returns {void}
 */
export function setupGraphView() {
  const modal = document.getElementById("graph-view-modal");
  if (!modal) {
    return;
  }
  modal.addEventListener("shown.bs.modal", () => {
    renderGraphView().catch((err) => {
      document.getElementById("graph-view-status").textContent = `Errore: ${err.message}`;
    });
  });
  document.getElementById("graph-view-refresh").addEventListener("click", () => {
    renderGraphView().catch((err) => {
      document.getElementById("graph-view-status").textContent = `Errore: ${err.message}`;
    });
  });
}
