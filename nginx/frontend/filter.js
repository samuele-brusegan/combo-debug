/* =============================================================================
 * Combo-Debug - Linguaggio di filtraggio dei log + query builder a blocchi.
 *
 * Una sola sorgente di verita': un AST (Abstract Syntax Tree). Da esso si
 * genera sia il testo (serialize) sia i blocchi grafici (renderBuilder); il
 * testo si ri-converte in AST (parse). Cosi' testo e blocchi non possono mai
 * divergere: quando uno cambia, l'altro viene rigenerato dall'AST.
 *
 * Grammatica (precedenza: OR < AND, con parentesi):
 *   expr      := orExpr
 *   orExpr    := andExpr ( "OR"  andExpr )*
 *   andExpr   := primary ( "AND" primary )*
 *   primary   := condition | "(" orExpr ")"
 *   condition := field op value
 *   field     := node | level | message
 *   op        := == | != | ~ | !~ | >= | <= | > | <
 *   value     := bareword | "stringa quotata"
 *
 * Esempi:
 *   node == /talker
 *   level >= warn AND message ~ "timeout"
 *   node == /talker AND (level == error OR message ~ boom)
 * ========================================================================== */

"use strict";

(function (global) {
  /** Ordine dei livelli di log (per i confronti <, <=, >, >=). */
  const LEVELS = ["debug", "info", "warn", "error", "fatal"];
  const LEVEL_ORDER = { debug: 0, info: 1, warn: 2, error: 3, fatal: 4 };

  /**
   * Definizione dei campi filtrabili: etichetta, classe colore (blocchi),
   * operatori ammessi e tipo del valore.
   */
  const FIELDS = {
    node: {
      label: "nodo",
      ops: ["==", "!=", "~", "!~", "=~", "!=~"],
      valueType: "text",
    },
    level: {
      label: "livello",
      ops: ["==", "!=", ">", ">=", "<", "<="],
      valueType: "level",
    },
    message: {
      label: "messaggio",
      ops: ["~", "!~", "=~", "!=~", "==", "!="],
      valueType: "text",
    },
  };

  /** Operatori di matching tramite espressione regolare (case-insensitive). */
  const REGEX_OPS = new Set(["=~", "!=~"]);

  /** Etichette leggibili degli operatori per i blocchi. */
  const OP_LABELS = {
    "==": "uguale a",
    "!=": "diverso da",
    "~": "contiene",
    "!~": "non contiene",
    "=~": "regex",
    "!=~": "non regex",
    ">": "maggiore di",
    ">=": "maggiore/uguale",
    "<": "minore di",
    "<=": "minore/uguale",
  };

  // Operatori in ordine di lunghezza decrescente (il tokenizer deve provare
  // prima i multi-carattere, es. "!=~" prima di "!=", "!=" prima di "!~").
  const OP_TOKENS = ["!=~", "=~", "==", "!=", "!~", ">=", "<=", "~", ">", "<"];

  /** Errore di parsing del filtro (messaggio leggibile per la UI). */
  class FilterError extends Error {}

  // -- Tokenizer -------------------------------------------------------------

  /**
   * Suddivide la stringa di filtro in token.
   * @param {string} input Testo del filtro.
   * @returns {Array<object>} Lista di token.
   */
  function tokenize(input) {
    const tokens = [];
    let i = 0;
    const n = input.length;
    while (i < n) {
      const c = input[i];
      if (/\s/.test(c)) {
        i++;
        continue;
      }
      if (c === "(") {
        tokens.push({ t: "lparen" });
        i++;
        continue;
      }
      if (c === ")") {
        tokens.push({ t: "rparen" });
        i++;
        continue;
      }
      if (c === '"' || c === "'") {
        const quote = c;
        let j = i + 1;
        let s = "";
        // Dentro le virgolette si escapa SOLO la virgoletta (``\"``): ogni altro
        // backslash e' preservato letteralmente, cosi' i pattern regex come
        // ``\d`` restano intatti senza richiedere doppio escaping.
        while (j < n && input[j] !== quote) {
          if (input[j] === "\\" && j + 1 < n && input[j + 1] === quote) {
            s += quote;
            j += 2;
          } else {
            s += input[j];
            j++;
          }
        }
        if (j >= n) {
          throw new FilterError("Stringa tra virgolette non terminata.");
        }
        tokens.push({ t: "string", v: s });
        i = j + 1;
        continue;
      }
      let op = null;
      for (const candidate of OP_TOKENS) {
        if (input.startsWith(candidate, i)) {
          op = candidate;
          break;
        }
      }
      if (op) {
        tokens.push({ t: "op", v: op });
        i += op.length;
        continue;
      }
      const m = /^[A-Za-z0-9_/.\-:]+/.exec(input.slice(i));
      if (m) {
        const w = m[0];
        const up = w.toUpperCase();
        if (up === "AND") {
          tokens.push({ t: "and" });
        } else if (up === "OR") {
          tokens.push({ t: "or" });
        } else {
          tokens.push({ t: "word", v: w });
        }
        i += w.length;
        continue;
      }
      throw new FilterError(`Carattere inatteso: '${c}'.`);
    }
    return tokens;
  }

  // -- Parser ----------------------------------------------------------------

  /**
   * Crea una condizione AST.
   * @param {string} field Campo (node/level/message).
   * @param {string} op Operatore.
   * @param {string} value Valore.
   * @returns {object} Nodo condizione.
   */
  function cond(field, op, value) {
    return { type: "cond", field, op, value };
  }

  /**
   * Crea un gruppo AST.
   * @param {string} conn Connettore logico ("AND"|"OR").
   * @param {Array<object>} children Figli del gruppo.
   * @returns {object} Nodo gruppo.
   */
  function group(conn, children) {
    return { type: "group", conn, children };
  }

  /** @returns {object} Un filtro vuoto (corrisponde a "tutto"). */
  function emptyRoot() {
    return group("AND", []);
  }

  /**
   * Combina due nodi con un connettore, appiattendo i gruppi con stesso
   * connettore (associativita' a sinistra).
   */
  function combine(conn, left, right) {
    if (left.type === "group" && left.conn === conn) {
      left.children.push(right);
      return left;
    }
    return group(conn, [left, right]);
  }

  /** Garantisce che la radice dell'AST sia sempre un gruppo. */
  function toRootGroup(node) {
    return node.type === "group" ? node : group("AND", [node]);
  }

  /**
   * Converte il testo del filtro in AST. Lancia `FilterError` se non valido.
   * @param {string} input Testo del filtro.
   * @returns {object} AST radice (sempre un gruppo).
   */
  function parse(input) {
    if (!input || !input.trim()) {
      return emptyRoot();
    }
    const tokens = tokenize(input);
    let pos = 0;
    const peek = () => tokens[pos];
    const next = () => tokens[pos++];

    function parseOr() {
      let left = parseAnd();
      while (peek() && peek().t === "or") {
        next();
        left = combine("OR", left, parseAnd());
      }
      return left;
    }
    function parseAnd() {
      let left = parsePrimary();
      while (peek() && peek().t === "and") {
        next();
        left = combine("AND", left, parsePrimary());
      }
      return left;
    }
    function parsePrimary() {
      const tk = peek();
      if (!tk) {
        throw new FilterError("Espressione incompleta.");
      }
      if (tk.t === "lparen") {
        next();
        const e = parseOr();
        if (!peek() || peek().t !== "rparen") {
          throw new FilterError("Manca la parentesi di chiusura ')'.");
        }
        next();
        return e;
      }
      return parseCondition();
    }
    function parseCondition() {
      const f = next();
      if (!f || f.t !== "word") {
        throw new FilterError("Atteso un campo (node, level o message).");
      }
      const field = f.v.toLowerCase();
      if (!FIELDS[field]) {
        throw new FilterError(
          `Campo sconosciuto: '${f.v}' (ammessi: node, level, message).`,
        );
      }
      const o = next();
      if (!o || o.t !== "op") {
        throw new FilterError(`Atteso un operatore dopo '${field}'.`);
      }
      if (!FIELDS[field].ops.includes(o.v)) {
        throw new FilterError(
          `Operatore '${o.v}' non valido per '${field}'.`,
        );
      }
      const val = next();
      if (!val || (val.t !== "word" && val.t !== "string")) {
        throw new FilterError(`Atteso un valore dopo '${field} ${o.v}'.`);
      }
      let value = val.v;
      if (FIELDS[field].valueType === "level") {
        value = value.toLowerCase();
        if (!(value in LEVEL_ORDER)) {
          throw new FilterError(
            `Livello non valido: '${val.v}' (usa ${LEVELS.join(", ")}).`,
          );
        }
      }
      if (REGEX_OPS.has(o.v)) {
        // Validiamo subito la regex: cosi' un pattern non valido rende il filtro
        // non valido (segnalato dalla UI) invece di fallire silenziosamente.
        try {
          new RegExp(value);
        } catch (err) {
          throw new FilterError(`Espressione regolare non valida: ${err.message}`);
        }
      }
      return cond(field, o.v, value);
    }

    const ast = parseOr();
    if (pos < tokens.length) {
      throw new FilterError("Token in eccesso dopo l'espressione.");
    }
    return toRootGroup(ast);
  }

  // -- Serializzazione (AST -> testo) ----------------------------------------

  /** Formatta il valore di una condizione (bareword o stringa quotata). */
  function formatValue(node) {
    if (FIELDS[node.field].valueType === "level") {
      return node.value;
    }
    const v = String(node.value);
    if (v !== "" && /^[A-Za-z0-9_/.\-:]+$/.test(v) && !["and", "or"].includes(v.toLowerCase())) {
      return v;
    }
    // Escapiamo solo le virgolette: i backslash (regex) restano letterali, cosi'
    // il testo mostrato coincide con quanto digitato (nessun doppio escaping).
    return '"' + v.replace(/"/g, '\\"') + '"';
  }

  /**
   * Converte l'AST in testo canonico.
   * @param {object} node Nodo AST.
   * @returns {string} Testo del filtro.
   */
  function serialize(node) {
    if (node.type === "cond") {
      return `${node.field} ${node.op} ${formatValue(node)}`;
    }
    if (node.children.length === 0) {
      return "";
    }
    const parts = node.children.map((child) => {
      const s = serialize(child);
      if (child.type === "group" && child.children.length > 1 && child.conn !== node.conn) {
        return `(${s})`;
      }
      return s;
    });
    return parts.join(` ${node.conn} `);
  }

  // -- Valutazione -----------------------------------------------------------

  /** Normalizza un nome di nodo per il confronto (no slash, minuscolo). */
  function normNode(s) {
    return String(s).trim().replace(/^\//, "").toLowerCase();
  }

  // Cache delle regex compilate (case-insensitive). Valore ``null`` se il
  // pattern non e' compilabile (non dovrebbe accadere: validato nel parser).
  const _regexCache = new Map();

  /** Compila (con cache) una regex case-insensitive, o ``null`` se invalida. */
  function compileRegex(pattern) {
    if (_regexCache.has(pattern)) {
      return _regexCache.get(pattern);
    }
    let re = null;
    try {
      re = new RegExp(pattern, "i");
    } catch (_err) {
      re = null;
    }
    _regexCache.set(pattern, re);
    return re;
  }

  /** Valuta una singola condizione su una riga di log. */
  function matchCond(c, entry) {
    if (c.field === "level") {
      const a = LEVEL_ORDER[entry.level];
      const b = LEVEL_ORDER[c.value];
      if (a === undefined || b === undefined) {
        return false;
      }
      switch (c.op) {
        case "==":
          return a === b;
        case "!=":
          return a !== b;
        case ">":
          return a > b;
        case ">=":
          return a >= b;
        case "<":
          return a < b;
        case "<=":
          return a <= b;
        default:
          return false;
      }
    }
    const raw = String(c.field === "node" ? entry.source : entry.message);
    // I match regex usano il testo grezzo (case-insensitive via flag "i"),
    // cosi' si possono usare ancore/classi senza normalizzazioni a sorpresa.
    if (c.op === "=~" || c.op === "!=~") {
      const re = compileRegex(c.value);
      const ok = re ? re.test(raw) : false;
      return c.op === "=~" ? ok : !ok;
    }
    const field = c.field === "node" ? normNode(raw) : raw.toLowerCase();
    const target = c.field === "node" ? normNode(c.value) : String(c.value).toLowerCase();
    switch (c.op) {
      case "==":
        return field === target;
      case "!=":
        return field !== target;
      case "~":
        return field.includes(target);
      case "!~":
        return !field.includes(target);
      default:
        return false;
    }
  }

  /**
   * Valuta l'AST su una riga di log.
   * @param {object} ast AST radice.
   * @param {{level:string, source:string, message:string}} entry Riga di log.
   * @returns {boolean} ``true`` se la riga supera il filtro.
   */
  function matches(ast, entry) {
    if (ast.type === "group") {
      if (ast.children.length === 0) {
        return true;
      }
      return ast.conn === "AND"
        ? ast.children.every((child) => matches(child, entry))
        : ast.children.some((child) => matches(child, entry));
    }
    return matchCond(ast, entry);
  }

  // -- Helper: imposta la parte "nodo" del filtro ----------------------------

  /** Cerca ricorsivamente la prima condizione ``node == ...``. */
  function findNodeEqCond(node) {
    if (node.type === "cond") {
      return node.field === "node" && node.op === "==" ? node : null;
    }
    for (const child of node.children) {
      const found = findNodeEqCond(child);
      if (found) {
        return found;
      }
    }
    return null;
  }

  /**
   * Imposta la condizione ``node == <nodeName>`` nel filtro, preservando il
   * resto: se esiste gia' una condizione ``node ==`` ne aggiorna il valore,
   * altrimenti la aggiunge in AND con il filtro esistente.
   * @param {object} root AST radice corrente.
   * @param {string} nodeName Nome del nodo (es. "/talker").
   * @returns {object} Nuovo AST radice.
   */
  function setNodeInFilter(root, nodeName) {
    const existing = findNodeEqCond(root);
    if (existing) {
      existing.value = nodeName;
      return root;
    }
    const nodeCond = cond("node", "==", nodeName);
    if (root.children.length === 0) {
      return group("AND", [nodeCond]);
    }
    if (root.conn === "AND") {
      root.children.unshift(nodeCond);
      return root;
    }
    return group("AND", [nodeCond, root]);
  }

  // -- Query builder a blocchi -----------------------------------------------

  /** Crea un elemento con classe e (opzionale) testo. */
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  /** Valore di default per un campo appena selezionato. */
  function defaultValue(field) {
    return FIELDS[field].valueType === "level" ? "warn" : "";
  }

  /**
   * Renderizza il query builder a blocchi dentro ``container``, sincronizzato
   * con l'AST ``root``. Ogni modifica strutturale ridisegna i blocchi; ogni
   * modifica chiama ``onChange`` (per aggiornare testo e tabella).
   *
   * @param {HTMLElement} container Contenitore dei blocchi.
   * @param {object} root AST radice (mutato in place dalle interazioni).
   * @param {function():void} onChange Callback invocata ad ogni modifica.
   * @returns {void}
   */
  function renderBuilder(container, root, onChange) {
    function rerender() {
      container.innerHTML = "";
      container.appendChild(renderGroup(root, null));
    }

    function renderCondition(c, parent) {
      const row = el("div", "filter-cond");

      const fieldSel = el("select", `form-select form-select-sm filter-field filter-field-${c.field}`);
      for (const key of Object.keys(FIELDS)) {
        const opt = el("option", null, FIELDS[key].label);
        opt.value = key;
        if (key === c.field) {
          opt.selected = true;
        }
        fieldSel.appendChild(opt);
      }
      fieldSel.addEventListener("change", () => {
        c.field = fieldSel.value;
        if (!FIELDS[c.field].ops.includes(c.op)) {
          c.op = FIELDS[c.field].ops[0];
        }
        c.value = defaultValue(c.field);
        rerender();
        onChange();
      });
      row.appendChild(fieldSel);

      const opSel = el("select", "form-select form-select-sm filter-op");
      for (const op of FIELDS[c.field].ops) {
        const opt = el("option", null, `${op}  (${OP_LABELS[op]})`);
        opt.value = op;
        if (op === c.op) {
          opt.selected = true;
        }
        opSel.appendChild(opt);
      }
      opSel.addEventListener("change", () => {
        c.op = opSel.value;
        onChange();
      });
      row.appendChild(opSel);

      if (FIELDS[c.field].valueType === "level") {
        const valSel = el("select", "form-select form-select-sm filter-value");
        for (const lvl of LEVELS) {
          const opt = el("option", null, lvl);
          opt.value = lvl;
          if (lvl === c.value) {
            opt.selected = true;
          }
          valSel.appendChild(opt);
        }
        valSel.addEventListener("change", () => {
          c.value = valSel.value;
          onChange();
        });
        row.appendChild(valSel);
      } else {
        const valInput = el("input", "form-control form-control-sm filter-value");
        valInput.type = "text";
        valInput.value = c.value;
        valInput.placeholder = c.field === "node" ? "/talker" : "testo...";
        // Solo onChange (niente rerender) per non perdere il focus mentre si scrive.
        valInput.addEventListener("input", () => {
          c.value = valInput.value;
          onChange();
        });
        row.appendChild(valInput);
      }

      const del = el("button", "btn btn-sm btn-outline-danger filter-del", "×");
      del.type = "button";
      del.title = "Rimuovi condizione";
      del.addEventListener("click", () => {
        const idx = parent.children.indexOf(c);
        if (idx >= 0) {
          parent.children.splice(idx, 1);
        }
        rerender();
        onChange();
      });
      row.appendChild(del);

      return row;
    }

    function renderGroup(g, parent) {
      const box = el("div", "filter-group");

      const head = el("div", "filter-group-head");

      // Selettore connettore (AND/OR) applicato tra i figli del gruppo.
      const connWrap = el("div", "btn-group btn-group-sm filter-conn");
      for (const conn of ["AND", "OR"]) {
        const btn = el("button", "btn btn-sm", conn);
        btn.type = "button";
        btn.classList.add(
          g.conn === conn ? (conn === "AND" ? "btn-success" : "btn-warning") : "btn-outline-secondary",
        );
        btn.addEventListener("click", () => {
          if (g.conn !== conn) {
            g.conn = conn;
            rerender();
            onChange();
          }
        });
        connWrap.appendChild(btn);
      }
      head.appendChild(connWrap);

      const addCond = el("button", "btn btn-sm btn-outline-info", "+ condizione");
      addCond.type = "button";
      addCond.addEventListener("click", () => {
        g.children.push(cond("message", "~", ""));
        rerender();
        onChange();
      });
      head.appendChild(addCond);

      const addGroup = el("button", "btn btn-sm btn-outline-secondary", "+ gruppo");
      addGroup.type = "button";
      addGroup.addEventListener("click", () => {
        g.children.push(group(g.conn === "AND" ? "OR" : "AND", [cond("message", "~", "")]));
        rerender();
        onChange();
      });
      head.appendChild(addGroup);

      if (parent) {
        const del = el("button", "btn btn-sm btn-outline-danger ms-auto", "× gruppo");
        del.type = "button";
        del.addEventListener("click", () => {
          const idx = parent.children.indexOf(g);
          if (idx >= 0) {
            parent.children.splice(idx, 1);
          }
          rerender();
          onChange();
        });
        head.appendChild(del);
      }

      box.appendChild(head);

      const childrenWrap = el("div", "filter-children");
      if (g.children.length === 0) {
        childrenWrap.appendChild(el("div", "filter-empty muted", "Nessuna condizione: il filtro mostra tutto."));
      }
      g.children.forEach((child, index) => {
        if (index > 0) {
          childrenWrap.appendChild(
            el("div", `filter-connector filter-connector-${g.conn.toLowerCase()}`, g.conn),
          );
        }
        childrenWrap.appendChild(
          child.type === "group" ? renderGroup(child, g) : renderCondition(child, g),
        );
      });
      box.appendChild(childrenWrap);

      return box;
    }

    rerender();
  }

  const api = {
    LEVELS,
    LEVEL_ORDER,
    FIELDS,
    FilterError,
    parse,
    serialize,
    matches,
    emptyRoot,
    setNodeInFilter,
    renderBuilder,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  if (global) {
    global.LogFilter = api;
  }
})(typeof window !== "undefined" ? window : null);
