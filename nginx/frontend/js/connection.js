/* =============================================================================
 * Combo-Debug - Collegamento a un ROS 2 reale (riconfigurazione a caldo).
 *
 * Gestisce il badge in header (DEMO / ROS reale) e il modal di connessione:
 * lettura/scrittura della configurazione, scelta della RMW, verifica e
 * rilevamento (discovery) di nodi/topic dal grafo.
 * ============================================================================= */

"use strict";

import { apiGet, apiPost, API_BASE } from "./api.js";
import { escapeHtml } from "./utils.js";
import { refreshAll } from "./dashboard.js";

// `bootstrap` (bundle CDN) e' caricato come script globale prima di questo modulo.

/**
 * Aggiorna il badge in header che indica la sorgente dati corrente:
 * "Modalita' DEMO" quando si osservano i nodi di esempio, altrimenti "ROS reale".
 * @returns {Promise<void>}
 */
export async function refreshConnectionBadge() {
	const badge = document.getElementById("connection-badge");
	const config = await apiGet("/connection");
	badge.classList.remove("d-none", "text-bg-warning", "text-bg-success");
	if (config.demo_mode) {
		badge.classList.add("text-bg-warning");
		badge.textContent = "Modalità DEMO";
		badge.title = "Connesso ai nodi ROS 2 di esempio (demo). Usa 'Collega a ROS reale' per un robot vero.";
	} else {
		badge.classList.add("text-bg-success");
		badge.textContent = `ROS reale · dominio ${config.ros_domain_id}`;
		badge.title = "Connesso a un grafo ROS 2 reale (nodi demo non osservati).";
	}
}

/**
 * Carica la configurazione di connessione corrente dal backend e popola il form
 * del modal. Invocata all'apertura del modal.
 * @returns {Promise<void>}
 */
async function loadConnectionConfig() {
	const config = await apiGet("/connection");
	document.getElementById("conn-domain").value = config.ros_domain_id ?? "";
	document.getElementById("conn-discovery").value = config.ros_discovery_server ?? "";
	document.getElementById("conn-nodes").value = config.expected_nodes ?? "";
	document.getElementById("conn-topics").value = config.expected_topics ?? "";
	document.getElementById("conn-logdir").value = config.ros_log_dir ?? "";
	await loadRmwOptions(config.rmw_implementation ?? "");
}

/** Valore speciale che, nel menu RMW, attiva l'input testuale personalizzato. */
const RMW_CUSTOM = "__custom__";

/**
 * Popola il menu a tendina delle RMW con quelle installate nel container e
 * seleziona quella corrente. Aggiunge l'opzione "Altro…" per valori custom.
 * @param {string} current RMW attualmente configurata.
 * @returns {Promise<void>}
 */
async function loadRmwOptions(current) {
	const select = document.getElementById("conn-rmw");
	let options;
	try {
		options = await apiGet("/connection/rmw");
	} catch (_err) {
		options = { available: current ? [current] : [], current };
	}
	const available = options.available || [];
	// RMW corrente non nel catalogo (es. personalizzata gia' attiva): la includo.
	const list = current && !available.includes(current) ? [...available, current] : available;

	select.innerHTML = "";
	select.add(new Option("(default ROS)", ""));
	for (const rmw of list) {
		select.add(new Option(rmw, rmw));
	}
	select.add(new Option("Altro… (personalizzata)", RMW_CUSTOM));
	select.value = current && list.includes(current) ? current : "";
	updateRmwCustomVisibility();
}

/** Mostra/nasconde l'input RMW personalizzato in base alla selezione. */
function updateRmwCustomVisibility() {
	const select = document.getElementById("conn-rmw");
	const custom = document.getElementById("conn-rmw-custom");
	const isCustom = select.value === RMW_CUSTOM;
	custom.classList.toggle("d-none", !isCustom);
	if (isCustom) {
		custom.focus();
	}
}

/** Restituisce la RMW effettiva scelta (menu o valore personalizzato). */
function selectedRmw() {
	const select = document.getElementById("conn-rmw");
	if (select.value === RMW_CUSTOM) {
		return document.getElementById("conn-rmw-custom").value.trim();
	}
	return select.value.trim();
}

/**
 * Costruisce il corpo dell'aggiornamento di connessione dai campi del form.
 * @returns {Record<string, string>} Parametri di connessione da inviare.
 */
function buildConnectionUpdate() {
	return {
		ros_domain_id: document.getElementById("conn-domain").value.trim(),
		rmw_implementation: selectedRmw(),
		ros_discovery_server: document.getElementById("conn-discovery").value.trim(),
		expected_nodes: document.getElementById("conn-nodes").value.trim(),
		expected_topics: document.getElementById("conn-topics").value.trim(),
		ros_log_dir: document.getElementById("conn-logdir").value.trim(),
	};
}

/**
 * Applica a caldo i parametri di connessione correnti del form (PUT).
 * @returns {Promise<any>} La configurazione applicata restituita dal backend.
 */
async function applyConnectionConfig() {
	const url = new URL(API_BASE + "/connection", window.location.origin);
	const response = await fetch(url, {
		method: "PUT",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(buildConnectionUpdate()),
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status} applicando la connessione`);
	}
	return response.json();
}

/**
 * Mostra l'esito di una verifica/applicazione di connessione nel modal.
 * @param {string} type Tipo di alert Bootstrap ("success" | "danger" | "warning").
 * @param {string} html Contenuto HTML (gia' sanificato) del messaggio.
 * @returns {void}
 */
function showConnectionResult(type, html) {
	document.getElementById("connection-result").innerHTML =
		`<div class="alert alert-${type} mb-0">${html}</div>`;
}

/**
 * Applica i parametri e verifica la connessione, mostrando i nodi rilevati.
 * Il modal resta aperto per consentire correzioni.
 * @returns {Promise<void>}
 */
async function testConnection() {
	showConnectionResult("secondary", "Verifica in corso...");
	try {
		await applyConnectionConfig();
		const probe = await apiPost("/connection/test");
		if (!probe.available) {
			showConnectionResult("danger", `CLI ROS non disponibile: ${escapeHtml(probe.detail)}`);
			return;
		}
		const list = probe.nodes.map((n) => `<li class="font-monospace">${escapeHtml(n)}</li>`).join("");
		const type = probe.node_count > 0 ? "success" : "warning";
		showConnectionResult(
			type,
			`${escapeHtml(probe.detail)}${list ? `<ul class="mb-0 mt-2">${list}</ul>` : ""}`,
		);
	} catch (err) {
		showConnectionResult("danger", `Errore: ${escapeHtml(err.message)}`);
	}
}

/**
 * Applica i parametri, chiude il modal e aggiorna subito la dashboard.
 * Nessun riavvio: il refresh successivo riflette il grafo reale.
 * @returns {Promise<void>}
 */
async function applyAndRefresh() {
	try {
		await applyConnectionConfig();
		bootstrap.Modal.getInstance(document.getElementById("connection-modal"))?.hide();
		await refreshAll();
	} catch (err) {
		showConnectionResult("danger", `Errore: ${escapeHtml(err.message)}`);
	}
}

/**
 * Applica i parametri correnti e rileva nodi/topic dal grafo, mostrandoli come
 * elenco selezionabile. Cosi' i valori attesi si scelgono invece di digitarli.
 * @returns {Promise<void>}
 */
async function discoverGraph() {
	const container = document.getElementById("discovery-result");
	container.innerHTML = '<div class="text-info small">Rilevamento in corso...</div>';
	try {
		await applyConnectionConfig();
		renderDiscovery(await apiGet("/connection/discover"));
	} catch (err) {
		container.innerHTML = `<div class="alert alert-danger mb-0">Errore: ${escapeHtml(err.message)}</div>`;
	}
}

/**
 * Renderizza i nodi/topic rilevati come checkbox selezionabili.
 * @param {any} discovery Esito di GET /api/connection/discover.
 * @returns {void}
 */
function renderDiscovery(discovery) {
	const container = document.getElementById("discovery-result");
	if (!discovery.available) {
		container.innerHTML = `<div class="alert alert-danger mb-0">CLI ROS non disponibile: ${escapeHtml(discovery.detail)}</div>`;
		return;
	}
	if (discovery.nodes.length === 0 && discovery.topics.length === 0) {
		container.innerHTML = `<div class="alert alert-warning mb-0">${escapeHtml(discovery.detail)} Nessun nodo/topic da selezionare (controlla dominio e rete).</div>`;
		return;
	}
	const checkboxes = (items, cls) =>
		items
			.map((name, i) => {
				const id = `${cls}-${i}`;
				return (
					`<div class="form-check"><input class="form-check-input ${cls}" type="checkbox" value="${escapeHtml(name)}" id="${id}" checked />` +
					`<label class="form-check-label font-monospace small" for="${id}">${escapeHtml(name)}</label></div>`
				);
			})
			.join("") || '<span class="muted">nessuno</span>';
	container.innerHTML =
		`<div class="row g-3">` +
		`<div class="col-md-6"><div class="fw-semibold small mb-1">Nodi rilevati (${discovery.nodes.length})</div>` +
		`<div class="border rounded p-2 overflow-auto" style="max-height: 180px">${checkboxes(discovery.nodes, "discover-node")}</div></div>` +
		`<div class="col-md-6"><div class="fw-semibold small mb-1">Topic rilevati (${discovery.topics.length})</div>` +
		`<div class="border rounded p-2 overflow-auto" style="max-height: 180px">${checkboxes(discovery.topics, "discover-topic")}</div></div>` +
		`<div class="col-12"><button type="button" class="btn btn-info btn-sm" id="discovery-use">Usa selezionati</button>` +
		`<span class="muted ms-2">${escapeHtml(discovery.detail)}</span></div></div>`;
	document.getElementById("discovery-use").addEventListener("click", useDiscoverySelection);
}

/**
 * Popola i campi "nodi/topic attesi" con gli elementi rilevati selezionati.
 * Ai topic viene applicata la frequenza minima indicata in "freq. minima topic".
 * @returns {void}
 */
function useDiscoverySelection() {
	const hz = document.getElementById("discover-hz").value.trim() || "1.0";
	const nodes = [...document.querySelectorAll(".discover-node:checked")].map((c) => c.value);
	const topics = [...document.querySelectorAll(".discover-topic:checked")].map((c) => `${c.value}=${hz}`);
	document.getElementById("conn-nodes").value = nodes.join(",");
	document.getElementById("conn-topics").value = topics.join(",");
}

/**
 * Collega gli eventi del modal di connessione (apertura, scoperta, verifica, applica).
 * @returns {void}
 */
export function setupConnectionModal() {
	const modal = document.getElementById("connection-modal");
	modal.addEventListener("show.bs.modal", () => {
		document.getElementById("connection-result").innerHTML = "";
		document.getElementById("discovery-result").innerHTML = "";
		loadConnectionConfig().catch((err) =>
			showConnectionResult("danger", `Impossibile leggere la configurazione: ${escapeHtml(err.message)}`),
		);
	});
	document.getElementById("conn-rmw").addEventListener("change", updateRmwCustomVisibility);
	document.getElementById("connection-discover").addEventListener("click", discoverGraph);
	document.getElementById("connection-test").addEventListener("click", testConnection);
	document.getElementById("connection-apply").addEventListener("click", applyAndRefresh);
}
