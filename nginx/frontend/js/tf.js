/* =============================================================================
 * Combo-Debug - Pannello albero TF (/tf, /tf_static).
 *
 * Ricostruisce e mostra l'albero dei frame di riferimento. Piu' radici
 * indicano alberi TF scollegati: la condizione viene evidenziata.
 * ============================================================================= */

"use strict";

import { apiGet } from "./api.js";
import { escapeHtml } from "./utils.js";
import { setPanelSeverity } from "./panels.js";

/**
 * Costruisce ricorsivamente l'HTML (lista annidata) dell'albero TF.
 * @param {string} frame Frame radice da cui partire.
 * @param {Map<string, Array<object>>} childrenOf Mappa genitore -> figli.
 * @returns {string} Markup HTML dell'albero a partire da `frame`.
 */
export function renderSubtree(frame, childrenOf) {
  const children = childrenOf.get(frame) || [];
  const childrenHtml = children
    .map((child) => renderSubtree(child.frame_id, childrenOf))
    .join("");
  const staticBadge = childrenOf.has(frame)
    ? ""
    : '<span class="badge text-bg-secondary tf-static-badge">foglia</span>';
  return (
    `<li><span class="node-name">${escapeHtml(frame)}</span>${staticBadge}` +
    (childrenHtml ? `<ul class="tf-children">${childrenHtml}</ul>` : "") +
    `</li>`
  );
}

/**
 * Aggiorna il pannello TF con l'albero corrente delle trasformate.
 * @returns {Promise<void>}
 */
export async function refreshTf() {
  const container = document.getElementById("tf-tree");
  if (!container) {
    return;
  }
  const tree = await apiGet("/tf");
  if (!tree.available && tree.frames.length === 0) {
    container.innerHTML = `<p class="muted mb-0">${escapeHtml(tree.detail || "TF non disponibile.")}</p>`;
    setPanelSeverity("panel-tf", "none");
    return;
  }
  if (tree.frames.length === 0) {
    container.innerHTML = '<p class="muted mb-0">Nessuna trasformata TF rilevata.</p>';
    setPanelSeverity("panel-tf", "none");
    return;
  }

  const childrenOf = new Map();
  for (const frame of tree.frames) {
    if (frame.parent) {
      if (!childrenOf.has(frame.parent)) {
        childrenOf.set(frame.parent, []);
      }
      childrenOf.get(frame.parent).push(frame);
    }
  }

  const roots = tree.roots.length ? tree.roots : tree.frames.map((f) => f.frame_id);
  const disconnected = roots.length > 1;
  const warning = disconnected
    ? `<div class="alert alert-warning py-1 px-2 mb-2 small">Albero TF scollegato: ${roots.length} radici (${roots.map(escapeHtml).join(", ")}).</div>`
    : "";
  const trees = roots.map((root) => renderSubtree(root, childrenOf)).join("");
  container.innerHTML = `${warning}<ul class="tf-tree-root">${trees}</ul>`;
  setPanelSeverity("panel-tf", disconnected ? "yellow" : "none");
}
