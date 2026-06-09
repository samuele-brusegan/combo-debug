import { describe, expect, it } from "vitest";

import { buildElements } from "../../nginx/frontend/js/graph-view.js";

describe("buildElements", () => {
  it("crea vertici per nodi e topic e archi publish/subscribe", () => {
    const nodes = [
      { name: "/talker", status: "green" },
      { name: "/listener", status: "green" },
    ];
    const graph = {
      topics: [
        {
          name: "/chatter",
          status: "green",
          producers: ["talker"],
          consumers: ["listener"],
        },
      ],
    };
    const elements = buildElements(nodes, graph);
    const ids = elements.filter((e) => e.data.id).map((e) => e.data.id);
    expect(ids).toContain("n:talker");
    expect(ids).toContain("n:listener");
    expect(ids).toContain("t:/chatter");

    const edges = elements.filter((e) => e.data.source);
    expect(edges).toContainEqual({ data: { source: "n:talker", target: "t:/chatter" } });
    expect(edges).toContainEqual({ data: { source: "t:/chatter", target: "n:listener" } });
  });

  it("crea i nodi mancanti referenziati solo dai topic", () => {
    const elements = buildElements([], {
      topics: [{ name: "/x", status: "yellow", producers: ["ghost"], consumers: [] }],
    });
    const ids = elements.filter((e) => e.data.id).map((e) => e.data.id);
    expect(ids).toContain("n:ghost");
    expect(ids).toContain("t:/x");
  });
});
