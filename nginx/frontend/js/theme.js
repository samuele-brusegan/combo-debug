/* =============================================================================
 * Combo-Debug - Tema chiaro/scuro e persistenza del layout.
 *
 * Il tema usa l'attributo nativo data-bs-theme di Bootstrap 5.3. La preferenza
 * e lo stato dei pannelli (visibilita', collasso, altezza massima) sono salvati
 * in localStorage e ripristinati all'avvio.
 * ============================================================================= */

"use strict";

const THEME_KEY = "combo_debug_theme";
const LAYOUT_KEY = "combo_debug_layout";

/**
 * Applica un tema all'elemento <html> e aggiorna l'etichetta del bottone.
 * @param {string} theme "dark" oppure "light".
 * @returns {void}
 */
function applyTheme(theme) {
  document.documentElement.setAttribute("data-bs-theme", theme);
  const button = document.getElementById("theme-toggle");
  if (button) {
    button.textContent = theme === "dark" ? "Tema chiaro" : "Tema scuro";
  }
}

/** Inizializza il tema dalla preferenza salvata (default: scuro). */
export function setupTheme() {
  applyTheme(localStorage.getItem(THEME_KEY) || "dark");
  const button = document.getElementById("theme-toggle");
  if (button) {
    button.addEventListener("click", () => {
      const next =
        document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  }
}

/**
 * Salva lo stato corrente del layout (toggle dei pannelli, altezza massima).
 * @returns {void}
 */
export function saveLayout() {
  const toggles = {};
  for (const toggle of document.querySelectorAll(".panel-toggle")) {
    toggles[toggle.id] = toggle.checked;
  }
  localStorage.setItem(LAYOUT_KEY, JSON.stringify(toggles));
}

/**
 * Ripristina lo stato del layout salvato applicando i toggle dei pannelli.
 * Va chiamato PRIMA del wiring degli eventi cosi' che lo stato iniziale sia
 * coerente; emette un change per applicare la visibilita'.
 * @returns {void}
 */
export function restoreLayout() {
  const raw = localStorage.getItem(LAYOUT_KEY);
  if (!raw) {
    return;
  }
  let toggles;
  try {
    toggles = JSON.parse(raw);
  } catch (_err) {
    return;
  }
  for (const [id, checked] of Object.entries(toggles)) {
    const toggle = document.getElementById(id);
    if (toggle && toggle.checked !== checked) {
      toggle.checked = checked;
      toggle.dispatchEvent(new Event("change"));
    }
  }
}
