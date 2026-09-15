import { defineConfig } from "@playwright/test";

/** Browser tests for what a person actually sees.
 *
 * The API is not started: each spec serves recorded responses with
 * `page.route`, and the recordings that matter are pinned to the real API by
 * backend tests (see `backend/tests/unit/test_triage_unavailable_contract.py`).
 *
 * Runs on the system Chrome (`channel: "chrome"`) so no browser download is
 * needed locally. CI installs it in the `e2e` job of `.github/workflows/ci.yml`,
 * and `src/__tests__/ci-e2e.test.ts` fails if that job disappears.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  // In CI a stray `test.only` would run one spec and report green. Fail instead.
  forbidOnly: !!process.env.CI,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    channel: "chrome",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npx vite --port 5173 --strictPort",
    url: "http://localhost:5173",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
