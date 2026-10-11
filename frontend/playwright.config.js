import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";
import { ADMIN, API_PORT, WEB_PORT } from "./e2e/constants.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(here, "../backend");
const tmpDir = path.join(here, "e2e", ".tmp");
const siteDir = path.join("e2e", ".tmp", "site");

// Start every run with an empty database (workers re-read this file, so only the main process cleans up).
if (!process.env.TEST_WORKER_INDEX) {
  fs.rmSync(tmpDir, { recursive: true, force: true });
  fs.mkdirSync(tmpDir, { recursive: true });
}

const venvPython = path.join(backendDir, ".venv", "bin", "python");
const python = process.env.E2E_PYTHON ?? (fs.existsSync(venvPython) ? venvPython : "python3");

export default defineConfig({
  testDir: "./e2e",
  // One shared database: run tests one at a time, each creating its own uniquely named data.
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  // Generous limits: slow laptops and CI machines need them, and a passing test never waits this long.
  timeout: 90_000,
  expect: { timeout: 12_000 },
  reporter: [["list"], ["html", { open: "never" }], ["./e2e/failure-reporter.js"]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    actionTimeout: 20_000,
    navigationTimeout: 40_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Throwaway backend: empty database, fixed admin account, no demo data.
      command: `${python} app.py`,
      cwd: backendDir,
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        ...process.env,
        PORT: String(API_PORT),
        FLASK_DEBUG: "0",
        DATABASE: path.join(tmpDir, "e2e.db"),
        SECRET_KEY: "e2e-secret-key-not-for-real-use",
        ADMIN_USERNAME: ADMIN.username,
        ADMIN_PASSWORD: ADMIN.password,
        SEED_DEMO_DATA: "0",
        LOGIN_MAX_FAILS: "50",
      },
    },
    {
      // By default the tests run against a production build of the site (fast and stable, like the real thing).
      // E2E_DEV=1 uses the Vite dev server instead, which is handy while debugging but much slower.
      command: process.env.E2E_DEV
        ? `npm run dev -- --port ${WEB_PORT} --strictPort`
        : `npm run build -- --outDir ${siteDir} --emptyOutDir && npm run preview -- --outDir ${siteDir} --port ${WEB_PORT} --strictPort`,
      cwd: here,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: { ...process.env, VITE_API_BASE_URL: `http://127.0.0.1:${API_PORT}` },
    },
  ],
});
