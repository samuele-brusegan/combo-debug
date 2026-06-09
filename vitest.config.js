import { defineConfig } from "vitest/config";

// I moduli del frontend usano API del DOM (document, localStorage): l'ambiente
// jsdom le fornisce nei test. I test vivono in tests/frontend/ e importano i
// moduli ES da nginx/frontend/js.
export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["tests/frontend/**/*.test.js"],
  },
});
