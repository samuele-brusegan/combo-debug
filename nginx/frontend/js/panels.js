/* =============================================================================
 * Combo-Debug - Gestione dei pannelli della dashboard.
 *
 * Severita' dei pannelli (pallino lampeggiante quando collassati), toggle di
 * visibilita' e collasso/espansione globale.
 * ============================================================================= */

"use strict";

import { saveLayout } from "./theme.js";

/**
 * Severita' corrente di ciascun pannello, usata per il pallino lampeggiante
 * mostrato quando il pannello e' collassato. Valori: "none" | "yellow" | "red".
 * @type {Record<string, string>}
 */
const panelSeverity = {
  "panel-nodes": "none",
  "panel-topics": "none",
  "panel-services": "none",
  "panel-actions": "none",
  "panel-env": "none",
  "panel-logs": "none",
  "panel-diagnostics": "none",
  "panel-tf": "none",
};

/**
 * Registra la severita' di un pannello e aggiorna il relativo pallino di stato.
 * @param {string} panelId Id della sezione del pannello (es. "panel-nodes").
 * @param {string} severity Severita' calcolata: "none" | "yellow" | "red".
 * @returns {void}
 */
export function setPanelSeverity(panelId, severity) {
  panelSeverity[panelId] = severity;
  updatePanelDot(panelId);
}

/**
 * Aggiorna il pallino di stato di un pannello: lampeggia (giallo/rosso) solo se
 * il pannello e' collassato e contiene problemi; altrimenti resta nascosto.
 * @param {string} panelId Id della sezione del pannello (es. "panel-nodes").
 * @returns {void}
 */
export function updatePanelDot(panelId) {
  const section = document.getElementById(panelId);
  if (!section) {
    return;
  }
  const dot = section.querySelector("[data-status-dot]");
  const body = section.querySelector(".collapse");
  const collapsed = body ? !body.classList.contains("show") : false;
  const severity = panelSeverity[panelId];

  dot.classList.remove("blink-yellow", "blink-red");
  if (collapsed && severity === "red") {
    dot.classList.add("blink-red");
  } else if (collapsed && severity === "yellow") {
    dot.classList.add("blink-yellow");
  }
}

/**
 * Collega le checkbox delle impostazioni alla visibilita' dei pannelli.
 * @returns {void}
 */
export function setupPanelToggles() {
  for (const toggle of document.querySelectorAll(".panel-toggle")) {
    toggle.addEventListener("change", () => {
      const section = document.getElementById(toggle.dataset.panel);
      if (section) {
        section.classList.toggle("d-none", !toggle.checked);
      }
      saveLayout();
    });
  }
}

/**
 * Collega gli eventi di collasso dei pannelli per aggiornare il pallino di
 * stato (visibile solo quando collassato) e i bottoni "Collassa/Espandi tutti".
 * @returns {void}
 */
export function setupCollapse() {
  for (const body of document.querySelectorAll("main .collapse")) {
    const panelId = body.id.replace("body-", "panel-");
    body.addEventListener("shown.bs.collapse", () => updatePanelDot(panelId));
    body.addEventListener("hidden.bs.collapse", () => updatePanelDot(panelId));
  }

  const applyToAll = (show) => {
    for (const body of document.querySelectorAll("main .collapse")) {
      const instance = bootstrap.Collapse.getOrCreateInstance(body, { toggle: false });
      show ? instance.show() : instance.hide();
    }
  };
  document.getElementById("collapse-all").addEventListener("click", () => applyToAll(false));
  document.getElementById("expand-all").addEventListener("click", () => applyToAll(true));
}
