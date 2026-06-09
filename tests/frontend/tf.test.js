import { describe, expect, it } from "vitest";

import { renderSubtree } from "../../nginx/frontend/js/tf.js";

describe("renderSubtree", () => {
  it("renderizza ricorsivamente i frame figli", () => {
    const childrenOf = new Map([
      ["odom", [{ frame_id: "base_link" }]],
      ["base_link", [{ frame_id: "laser" }]],
    ]);
    const html = renderSubtree("odom", childrenOf);
    expect(html).toContain("odom");
    expect(html).toContain("base_link");
    expect(html).toContain("laser");
    // L'annidamento produce liste <ul> figlie.
    expect(html).toContain("tf-children");
  });

  it("una foglia non ha lista figli", () => {
    const html = renderSubtree("solo", new Map());
    expect(html).toContain("solo");
    expect(html).not.toContain("tf-children");
  });
});
