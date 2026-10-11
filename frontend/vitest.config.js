import { defineConfig } from "vitest/config";

// Unit tests live next to the code as src/**/*.test.js. The browser tests in e2e/ are run by Playwright
// (npm run test:e2e); without this, Vitest would also pick up e2e/*.spec.js and fail on them.
export default defineConfig({
  test: {
    include: ["src/**/*.test.{js,jsx}"],
    exclude: ["node_modules/**", "e2e/**", "dist/**"],
  },
});
