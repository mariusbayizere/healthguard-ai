import { readdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";

/** The browser tests guard two safety interlocks: a nurse sees the full
 *  manual-triage instruction on 503, and every screen shows the offline banner.
 *  They ran only when someone remembered. These checks fail if CI stops running
 *  them, or if a `test.only` could quietly skip the rest.
 *
 *  Structural, dependency-free checks on the workflow text: no YAML library is a
 *  direct dependency of this package, and a transitive one could disappear. */

// Paths as strings: under jsdom, `URL` is jsdom's class and node:fs rejects it.
const here = dirname(decodeURIComponent(new URL(import.meta.url).pathname));
const frontend = resolve(here, "../..");
const workflow = readFileSync(resolve(frontend, "../../.github/workflows/ci.yml"), "utf-8");
const config = readFileSync(resolve(frontend, "playwright.config.ts"), "utf-8");

function job(name: string): string | null {
  const start = workflow.search(new RegExp(`^  ${name}:\\s*$`, "m"));
  if (start < 0) return null;
  const rest = workflow.slice(start + 1);
  const end = rest.search(/^ {2}[a-z][a-z0-9-]*:\s*$/m);
  return end < 0 ? rest : rest.slice(0, end);
}

describe("CI runs the browser tests", () => {
  const e2e = job("e2e");

  it("has an e2e job", () => {
    expect(e2e, "no `e2e:` job in .github/workflows/ci.yml").not.toBeNull();
  });

  it("runs every spec through the package script, from the frontend directory", () => {
    expect(e2e).toMatch(/working-directory:\s*kinyamed\/frontend/);
    expect(e2e).toMatch(/run:\s*npm run e2e\b/);
    expect(readFileSync(resolve(frontend, "package.json"), "utf-8"))
      .toMatch(/"e2e":\s*"playwright test"/);
  });

  it("installs from the lockfile and provides the Chrome channel the config uses", () => {
    expect(e2e).toMatch(/run:\s*npm ci\b/);
    expect(config).toMatch(/channel:\s*"chrome"/);
    // --force: GitHub's Ubuntu runners ship a Chrome that Playwright otherwise
    // refuses to install the `chrome` channel over.
    expect(e2e).toMatch(/npx playwright install --with-deps --force chrome/);
  });

  it("cannot pass by being allowed to fail", () => {
    expect(e2e).not.toMatch(/continue-on-error:\s*true/);
    expect(e2e).not.toMatch(/\|\|\s*true/);
  });

  it("keeps the trace when a browser test fails, so the failure can be read", () => {
    expect(e2e).toMatch(/if:\s*failure\(\)/);
    expect(e2e).toMatch(/actions\/upload-artifact@v4/);
  });

  it("forbids test.only in CI, so one focused test cannot silently skip the rest", () => {
    expect(config).toMatch(/forbidOnly:\s*!!process\.env\.CI/);
  });

  it("finds at least the two interlock specs where the config looks", () => {
    expect(config).toMatch(/testDir:\s*"\.\/e2e"/);
    const specs = readdirSync(resolve(frontend, "e2e")).filter((f) => f.endsWith(".spec.ts"));
    expect(specs).toContain("triage-offline.spec.ts");
  });
});
