/* =============================================================================
 * Combo-Debug - Accesso REST al backend.
 *
 * Wrapper minimi attorno a `fetch` per le chiamate JSON GET/POST. Nginx fa da
 * reverse proxy verso il backend, quindi tutte le rotte sono relative a API_BASE.
 * ============================================================================= */

"use strict";

/** Base path delle API (Nginx fa da reverse proxy verso il backend). */
export const API_BASE = "/api";

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
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} su ${path}`);
  }
  return response.json();
}

/**
 * Esegue una POST JSON verso un endpoint dell'API.
 * @param {string} path Percorso relativo a API_BASE (es. "/connection/test").
 * @param {unknown} [body] Eventuale corpo JSON da inviare.
 * @returns {Promise<any>} Il corpo JSON deserializzato.
 */
export async function apiPost(path, body) {
  const url = new URL(API_BASE + path, window.location.origin);
  const response = await fetch(url, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} su ${path}`);
  }
  return response.json();
}
