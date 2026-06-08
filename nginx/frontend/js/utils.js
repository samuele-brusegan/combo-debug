/* =============================================================================
 * Combo-Debug - Utility condivise tra i moduli del frontend.
 * ============================================================================= */

"use strict";

/**
 * Effettua l'escape dei caratteri HTML per prevenire XSS dai dati del backend.
 * @param {unknown} value Valore da convertire in testo sicuro.
 * @returns {string} Stringa con i caratteri speciali HTML codificati.
 */
export function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

/**
 * Mappa uno stato (green/red/yellow) alla classe CSS del pallino.
 * @param {string} status Stato del nodo.
 * @returns {string} Nome della classe CSS.
 */
export function dotClass(status) {
  return (
    { green: "dot-green", red: "dot-red", yellow: "dot-yellow", zombie: "dot-zombie" }[status] ||
    "dot-yellow"
  );
}
