import path from "node:path";

import { defineConfig } from "@playwright/test";

/**
 * E2E config. Runs against REAL servers:
 * - Flask backend on http://127.0.0.1:5001 with an ephemeral SQLite DB
 *   (DATABASE_URL env set by webServer command — never the dev Postgres).
 * - Next.js dev server on http://127.0.0.1:3100 proxying /api/* to Flask.
 * Both are started and torn down by Playwright itself.
 */

const FLASK_PORT = 5001;
// 3100 sits inside Windows' dynamic port-exclusion ranges (which move
// between reboots), producing EACCES on next start — 3900 is outside them.
const APP_PORT = 3900;
// Absolute so Flask-SQLAlchemy passes it through unchanged (relative sqlite
// URIs get app.instance_path prepended) and so the delete below matches the
// file the server actually opens, regardless of process CWD.
const REPO_ROOT = path.resolve(__dirname, "..");
const DB_FILE = path.join(REPO_ROOT, "instance", "e2e-school.db");

export default defineConfig({
  testDir: "./e2e",
  // Generous: next dev compiles routes on first request (multi-second,
  // occasionally flaky with Turbopack SSR races that need one reload).
  timeout: 180_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${APP_PORT}`,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    locale: "en-US",
  },
  webServer: [
    {
      // Fresh DB every run — delete the sqlite file, migrate, seed, serve.
      // Never reuse: a lingering Flask process would hold the OLD database
      // and serve stale fixture data.
      command: `python -c "import os; os.path.exists('${DB_FILE.replace(/\\/g, "\\\\")}') and os.remove('${DB_FILE.replace(/\\/g, "\\\\")}')" && python -m flask --app app db upgrade && python -m flask --app app seed-e2e && python -m flask --app app run --port ${FLASK_PORT}`,
      url: `http://127.0.0.1:${FLASK_PORT}/healthz`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        DATABASE_URL: `sqlite:///${DB_FILE.replace(/\\/g, "/")}`,
        SECRET_KEY: "e2e-secret-key-not-for-prod",
        FLASK_DEBUG: "0",
        // The auth limiter (5/min, shared across refresh+login) would trip
        // during test retries — every page mount fires /api/auth/refresh.
        RATELIMIT_ENABLED: "False",
        PYTHONPATH: "..",
      },
      cwd: "..",
    },
    {
      // Production mode, not `next dev`: dev's on-demand Turbopack compile
      // + HMR produced SSR races ("clientReferenceManifest") that rendered
      // empty pages mid-test. A single upfront build + `next start` is
      // deterministic. Wipe .next first — CLAUDE.md: never share the dir
      // between build and a running dev server.
      command: `node -e "fs.rmSync('.next',{recursive:true,force:true})" && npx next build && npx next start --port ${APP_PORT}`,
      url: `http://127.0.0.1:${APP_PORT}/login`,
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
      env: { API_BASE_URL: `http://127.0.0.1:${FLASK_PORT}` },
    },
  ],
});

