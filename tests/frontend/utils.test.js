import { describe, expect, it } from "vitest";

import { dotClass, escapeHtml } from "../../nginx/frontend/js/utils.js";

describe("dotClass", () => {
  it("mappa gli stati noti alle classi del pallino", () => {
    expect(dotClass("green")).toBe("dot-green");
    expect(dotClass("red")).toBe("dot-red");
    expect(dotClass("yellow")).toBe("dot-yellow");
    expect(dotClass("zombie")).toBe("dot-zombie");
  });

  it("usa il giallo come fallback per stati sconosciuti", () => {
    expect(dotClass("boh")).toBe("dot-yellow");
  });
});

describe("escapeHtml", () => {
  it("effettua l'escape dei caratteri pericolosi", () => {
    expect(escapeHtml("<script>")).toBe("&lt;script&gt;");
    expect(escapeHtml("a & b")).toBe("a &amp; b");
  });

  it("gestisce null/undefined come stringa vuota", () => {
    expect(escapeHtml(null)).toBe("");
    expect(escapeHtml(undefined)).toBe("");
  });
});
