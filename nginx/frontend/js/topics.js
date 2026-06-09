/* =============================================================================
 * Combo-Debug - Streaming on-demand dei messaggi di un topic.
 *
 * Sottoscrive il topic selezionato e mostra in tempo reale tutti i messaggi
 * pubblicati, in un modal. Lo stream (SSE) si interrompe alla chiusura del
 * modal; il buffer e' limitato agli ultimi MAX_MESSAGES messaggi.
 * ============================================================================= */

"use strict";

import { apiStream } from "./api.js";

/** Numero massimo di messaggi mantenuti nel modal (buffer circolare). */
const MAX_MESSAGES = 200;

/** Restituisce l'istanza (singleton) del modal Bootstrap di echo. */
function echoModal() {
  return bootstrap.Modal.getOrCreateInstance(document.getElementById("echo-modal"));
}

/**
 * Aggiorna la riga di stato del modal (indicatore live + testo).
 * @param {HTMLElement} statusEl Elemento della riga di stato.
 * @param {"live"|"end"|"error"} state Stato corrente dello stream.
 * @param {string} text Testo descrittivo da mostrare.
 * @returns {void}
 */
function setStatus(statusEl, state, text) {
  statusEl.className = `echo-status small echo-status-${state}`;
  statusEl.textContent = text;
}

/**
 * Aggiunge un messaggio al contenitore, mantenendo il buffer e l'auto-scroll.
 * @param {HTMLElement} output Contenitore dei messaggi.
 * @param {string} text Contenuto (YAML) del messaggio.
 * @returns {void}
 */
function appendMessage(output, text) {
  // Auto-scroll solo se l'utente sta gia' guardando il fondo (non disturba
  // chi e' scrollato in alto a leggere un messaggio precedente).
  const atBottom =
    output.scrollHeight - output.scrollTop - output.clientHeight < 32;
  const entry = document.createElement("pre");
  entry.className = "echo-msg";
  entry.textContent = text;
  output.appendChild(entry);
  while (output.childElementCount > MAX_MESSAGES) {
    output.removeChild(output.firstElementChild);
  }
  if (atBottom) {
    output.scrollTop = output.scrollHeight;
  }
}

/**
 * Estrae tipo di evento e dati da un blocco SSE grezzo (righe `event:`/`data:`).
 * @param {string} raw Blocco di evento (senza la riga vuota terminale).
 * @returns {{event: string, data: string}} Evento normalizzato.
 */
function parseSseEvent(raw) {
  let event = "message";
  const dataLines = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith(":")) {
      continue; // commento/keep-alive
    }
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  return { event, data: dataLines.join("\n") };
}

/**
 * Legge lo stream SSE e instrada gli eventi verso il modal.
 * @param {Response} response Risposta in streaming dell'API.
 * @param {HTMLElement} output Contenitore dei messaggi.
 * @param {HTMLElement} statusEl Riga di stato.
 * @param {() => number} count Funzione che restituisce il numero di messaggi.
 * @param {(n: number) => void} bump Incrementa il contatore dei messaggi.
 * @returns {Promise<void>}
 */
async function consumeStream(response, output, statusEl, count, bump) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const { event, data } = parseSseEvent(buffer.slice(0, sep));
      buffer = buffer.slice(sep + 2);
      if (event === "message") {
        appendMessage(output, data);
        bump(1);
        setStatus(statusEl, "live", `In ascolto · ${count()} messaggi`);
      } else if (event === "info") {
        setStatus(statusEl, "live", data);
      } else if (event === "end") {
        setStatus(statusEl, "end", `${data} (${count()} messaggi)`);
      } else if (event === "error") {
        setStatus(statusEl, "error", data);
      }
    }
  }
}

/**
 * Apre il modal di echo e avvia lo streaming dei messaggi dal topic indicato.
 * Lo stream viene interrotto automaticamente alla chiusura del modal.
 * @param {string} topic Nome del topic da ascoltare.
 * @returns {Promise<void>}
 */
export async function openTopicEcho(topic) {
  const modalEl = document.getElementById("echo-modal");
  const output = document.getElementById("echo-output");
  const statusEl = document.getElementById("echo-status");
  const clearBtn = document.getElementById("echo-clear");
  document.getElementById("echo-topic").textContent = topic;
  output.replaceChildren();

  let messages = 0;
  const count = () => messages;
  const bump = (n) => {
    messages += n;
  };

  // Interrompe lo stream (e quindi il processo ros2 lato server) alla chiusura.
  const controller = new AbortController();
  const onClear = () => {
    output.replaceChildren();
    messages = 0;
  };
  const onHide = () => {
    controller.abort();
    clearBtn.removeEventListener("click", onClear);
    modalEl.removeEventListener("hidden.bs.modal", onHide);
  };
  clearBtn.addEventListener("click", onClear);
  modalEl.addEventListener("hidden.bs.modal", onHide);

  echoModal().show();
  setStatus(statusEl, "live", "Connessione allo stream…");
  try {
    const params = new URLSearchParams({ topic });
    const response = await apiStream("/topics/echo/stream", params, controller.signal);
    await consumeStream(response, output, statusEl, count, bump);
  } catch (err) {
    if (err.name !== "AbortError") {
      setStatus(statusEl, "error", `Errore: ${err.message}`);
    }
  }
}
