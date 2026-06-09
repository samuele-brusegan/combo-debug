/* =============================================================================
 * Combo-Debug - Autenticazione della dashboard (opt-in).
 *
 * Se il backend ha l'autenticazione abilitata, mostra una schermata di login,
 * memorizza il token e lo allega alle richieste (via api.js). Quando l'auth e'
 * disabilitata (default) questo modulo e' sostanzialmente un no-op.
 * ============================================================================= */

"use strict";

import { API_BASE, clearToken, getToken, setToken } from "./api.js";
import { escapeHtml } from "./utils.js";
import { refreshAll } from "./dashboard.js";

/** Restituisce l'istanza (singleton) del modal di login Bootstrap. */
function loginModal() {
  const el = document.getElementById("login-modal");
  return bootstrap.Modal.getOrCreateInstance(el, { backdrop: "static", keyboard: false });
}

/**
 * Interroga lo stato dell'autenticazione e mostra il login se necessario.
 * @returns {Promise<boolean>} `true` se si puo' procedere (autenticati o auth off).
 */
export async function ensureAuthenticated() {
  let status;
  try {
    const response = await fetch(new URL(API_BASE + "/auth/status", window.location.origin), {
      headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : undefined,
    });
    status = await response.json();
  } catch (_err) {
    // Se non riusciamo a contattare il backend, lasciamo procedere: il badge di
    // liveness segnalera' comunque il problema.
    return true;
  }
  updateAuthControls(Boolean(status.enabled));
  if (status.enabled && !status.authenticated) {
    showLogin();
    return false;
  }
  return true;
}

/** Mostra il modal di login. */
function showLogin() {
  document.getElementById("login-error").textContent = "";
  loginModal().show();
}

/**
 * Aggiorna i controlli di autenticazione in header (bottone "Esci").
 * @param {boolean} enabled Se l'auth e' abilitata lato backend.
 * @returns {void}
 */
function updateAuthControls(enabled) {
  const logout = document.getElementById("logout-button");
  if (logout) {
    logout.classList.toggle("d-none", !(enabled && Boolean(getToken())));
  }
}

/**
 * Esegue il login con le credenziali del form.
 * @returns {Promise<void>}
 */
async function submitLogin() {
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;
  const errorBox = document.getElementById("login-error");
  errorBox.textContent = "";
  try {
    const response = await fetch(new URL(API_BASE + "/auth/login", window.location.origin), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      errorBox.textContent =
        response.status === 401 ? "Credenziali non valide." : `Errore HTTP ${response.status}.`;
      return;
    }
    const data = await response.json();
    setToken(data.token);
    updateAuthControls(true);
    loginModal().hide();
    document.getElementById("login-password").value = "";
    await refreshAll();
  } catch (err) {
    errorBox.textContent = `Errore: ${escapeHtml(err.message)}`;
  }
}

/** Esegue il logout: rimuove il token e ripropone il login. */
function logout() {
  clearToken();
  updateAuthControls(true);
  showLogin();
}

/**
 * Collega gli eventi di autenticazione (login, logout, evento 401 globale).
 * @returns {void}
 */
export function setupAuth() {
  const form = document.getElementById("login-form");
  if (form) {
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      submitLogin();
    });
  }
  const logoutButton = document.getElementById("logout-button");
  if (logoutButton) {
    logoutButton.addEventListener("click", logout);
  }
  // Una qualsiasi chiamata API che riceve 401 ripropone il login.
  document.addEventListener("combo-debug:auth-required", () => showLogin());
}
