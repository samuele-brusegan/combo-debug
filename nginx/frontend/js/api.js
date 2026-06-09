/* =============================================================================
 * Combo-Debug - Accesso REST al backend.
 *
 * Wrapper minimi attorno a `fetch` per le chiamate JSON GET/POST. Nginx fa da
 * reverse proxy verso il backend, quindi tutte le rotte sono relative a API_BASE.
 *
 * Autenticazione: se presente un token in localStorage, viene inviato come
 * header `Authorization: Bearer <token>`. Una risposta 401 emette l'evento
 * `combo-debug:auth-required` cosi' che il modulo auth.js possa mostrare il
 * login (l'auth e' opt-in lato backend; senza di essa nulla cambia).
 * ============================================================================= */

"use strict";

/** Base path delle API (Nginx fa da reverse proxy verso il backend). */
export const API_BASE = "/api";

/** Chiave di localStorage in cui e' memorizzato il token di autenticazione. */
const TOKEN_KEY = "combo_debug_token";

/**
 * Restituisce il token di autenticazione memorizzato (stringa vuota se assente).
 * @returns {string} Il token bearer corrente.
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

/**
 * Memorizza il token di autenticazione.
 * @param {string} token Token bearer da salvare.
 * @returns {void}
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Rimuove il token di autenticazione memorizzato (logout).
 * @returns {void}
 */
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Costruisce gli header di richiesta aggiungendo il bearer token se presente.
 * @param {Record<string, string>} [extra] Header aggiuntivi.
 * @returns {Record<string, string>} Header completi.
 */
function authHeaders(extra) {
  const headers = { ...(extra || {}) };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Gestisce le risposte non autorizzate emettendo un evento globale.
 * @param {Response} response Risposta HTTP da ispezionare.
 * @returns {void}
 */
function handleUnauthorized(response) {
  if (response.status === 401) {
    document.dispatchEvent(new CustomEvent("combo-debug:auth-required"));
  }
}

/**
 * Esegue una GET JSON verso un endpoint dell'API.
 * @param {string} path Percorso relativo a API_BASE (es. "/nodes").
 * @param {URLSearchParams} [params] Eventuali query string.
 * @returns {Promise<any>} Il corpo JSON deserializzato.
 */
export async function apiGet(path, params) {
  const url = new URL(API_BASE + path, window.location.origin);
  if (params) {
    url.search = params.toString();
  }
  const response = await fetch(url, { headers: authHeaders() });
  if (!response.ok) {
    handleUnauthorized(response);
    throw new Error(`HTTP ${response.status} su ${path}`);
  }
  return response.json();
}

/**
 * Esegue una POST JSON verso un endpoint dell'API.
 * @param {string} path Percorso relativo a API_BASE (puo' includere query string).
 * @param {unknown} [body] Eventuale corpo JSON da inviare.
 * @returns {Promise<any>} Il corpo JSON deserializzato.
 */
export async function apiPost(path, body) {
  const url = new URL(API_BASE + path, window.location.origin);
  const response = await fetch(url, {
    method: "POST",
    headers: authHeaders(
      body !== undefined ? { "Content-Type": "application/json" } : undefined,
    ),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    handleUnauthorized(response);
    const error = new Error(`HTTP ${response.status} su ${path}`);
    /** @type {any} */ (error).status = response.status;
    throw error;
  }
  return response.json();
}
