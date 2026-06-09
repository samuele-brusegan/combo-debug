/* =============================================================================
 * Combo-Debug - Ispezione e modifica dei parametri dei nodi.
 *
 * Modal che permette di scegliere un nodo, elencarne i parametri, leggerne il
 * valore e modificarli. La modifica e' protetta da uno switch di sicurezza: i
 * controlli di scrittura restano disabilitati finche' non viene attivato, e la
 * richiesta include `confirm: true` solo a switch acceso (il backend rifiuta
 * comunque qualsiasi scrittura non confermata).
 * ============================================================================= */

"use strict";

import { apiGet, apiPost } from "./api.js";
import { escapeHtml } from "./utils.js";

/** Nodo attualmente selezionato nel modal. */
let currentNode = "";
/** Parametro attualmente selezionato per la modifica. */
let currentParam = "";

/** Restituisce l'istanza (singleton) del modal Bootstrap dei parametri. */
function paramsModal() {
  return bootstrap.Modal.getOrCreateInstance(document.getElementById("params-modal"));
}

/**
 * Popola il menu a tendina dei nodi con quelli attualmente nel grafo.
 * @returns {Promise<void>}
 */
async function loadNodes() {
  const select = document.getElementById("params-node");
  const nodes = await apiGet("/nodes");
  select.innerHTML = "";
  select.add(new Option("(scegli un nodo)", ""));
  for (const node of nodes) {
    select.add(new Option(node.name, node.name));
  }
}

/**
 * Carica l'elenco dei parametri del nodo selezionato.
 * @returns {Promise<void>}
 */
async function loadParams() {
  const list = document.getElementById("params-list");
  currentNode = document.getElementById("params-node").value;
  resetEditor();
  if (!currentNode) {
    list.innerHTML = '<li class="muted">Seleziona un nodo.</li>';
    return;
  }
  list.innerHTML = '<li class="muted">Caricamento...</li>';
  const params = new URLSearchParams({ node: currentNode });
  const result = await apiGet("/params", params);
  if (!result.available) {
    list.innerHTML = `<li class="text-danger">${escapeHtml(result.detail || "Errore.")}</li>`;
    return;
  }
  if (result.params.length === 0) {
    list.innerHTML = '<li class="muted">Nessun parametro dichiarato.</li>';
    return;
  }
  list.innerHTML = "";
  for (const name of result.params) {
    const li = document.createElement("li");
    li.className = "node-item";
    li.tabIndex = 0;
    li.innerHTML = `<span class="node-name">${escapeHtml(name)}</span>`;
    li.addEventListener("click", () => selectParam(name));
    li.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        selectParam(name);
      }
    });
    list.appendChild(li);
  }
}

/**
 * Seleziona un parametro e ne carica il valore corrente nell'editor.
 * @param {string} name Nome del parametro.
 * @returns {Promise<void>}
 */
async function selectParam(name) {
  currentParam = name;
  document.getElementById("param-name").textContent = `${currentNode} → ${name}`;
  document.getElementById("param-editor").classList.remove("d-none");
  const valueInput = document.getElementById("param-value");
  valueInput.value = "Caricamento...";
  setEditEnabled(document.getElementById("param-write-switch").checked);
  showSetResult("", "");
  const params = new URLSearchParams({ node: currentNode, name });
  const result = await apiGet("/params/value", params);
  valueInput.value = result.available ? result.value : "";
  if (!result.available) {
    showSetResult("danger", result.detail || "Impossibile leggere il valore.");
  }
}

/** Nasconde l'editor e azzera la selezione del parametro. */
function resetEditor() {
  currentParam = "";
  document.getElementById("param-editor").classList.add("d-none");
  showSetResult("", "");
}

/**
 * Abilita/disabilita i controlli di scrittura in base allo switch di sicurezza.
 * @param {boolean} enabled Se la scrittura e' abilitata.
 * @returns {void}
 */
function setEditEnabled(enabled) {
  document.getElementById("param-value").disabled = !enabled;
  document.getElementById("param-save").disabled = !enabled;
}

/**
 * Mostra l'esito di una modifica nell'editor.
 * @param {string} type Tipo di alert ("success" | "danger" | "").
 * @param {string} message Messaggio da mostrare (sara' sanificato).
 * @returns {void}
 */
function showSetResult(type, message) {
  const box = document.getElementById("param-set-result");
  box.innerHTML = type
    ? `<div class="alert alert-${type} py-1 px-2 mb-0 small">${escapeHtml(message)}</div>`
    : "";
}

/**
 * Salva il valore del parametro corrente (con conferma di sicurezza).
 * @returns {Promise<void>}
 */
async function saveParam() {
  if (!document.getElementById("param-write-switch").checked) {
    showSetResult("warning", "Abilita prima lo switch di modifica.");
    return;
  }
  const value = document.getElementById("param-value").value;
  const params = new URLSearchParams({ node: currentNode, name: currentParam });
  try {
    const result = await apiPost(`/params/value?${params.toString()}`, {
      value,
      confirm: true,
    });
    showSetResult(result.success ? "success" : "danger", result.detail);
  } catch (err) {
    const status = /** @type {any} */ (err).status;
    showSetResult(
      "danger",
      status === 409 ? "Modifica rifiutata: conferma mancante." : err.message,
    );
  }
}

/**
 * Collega gli eventi del modal dei parametri.
 * @returns {void}
 */
export function setupParamsModal() {
  const modal = document.getElementById("params-modal");
  if (!modal) {
    return;
  }
  modal.addEventListener("show.bs.modal", () => {
    document.getElementById("param-write-switch").checked = false;
    document.getElementById("params-list").innerHTML =
      '<li class="muted">Seleziona un nodo e premi "Carica".</li>';
    resetEditor();
    loadNodes().catch((err) => {
      document.getElementById("params-list").innerHTML =
        `<li class="text-danger">${escapeHtml(err.message)}</li>`;
    });
  });
  document.getElementById("params-load").addEventListener("click", () => {
    loadParams().catch((err) => {
      document.getElementById("params-list").innerHTML =
        `<li class="text-danger">${escapeHtml(err.message)}</li>`;
    });
  });
  document.getElementById("param-write-switch").addEventListener("change", (ev) => {
    setEditEnabled(/** @type {HTMLInputElement} */ (ev.target).checked);
  });
  document.getElementById("param-save").addEventListener("click", saveParam);
}
