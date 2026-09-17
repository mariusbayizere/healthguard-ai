import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";

/** The backend suite runs against a real PostgreSQL (tests/conftest.py creates and
 *  migrates `kinyamed_test`) and reads DATABASE_URL from the environment or a
 *  git-ignored `.env`. A developer machine has both; a GitHub runner has neither,
 *  so conftest could not load and pytest exited 4 (run #77). These checks fail if
 *  the job loses its database service or the variables conftest and Settings need.
 *
 *  Structural checks on the workflow text, as in ci-e2e.test.ts. */

const here = dirname(decodeURIComponent(new URL(import.meta.url).pathname));
const frontend = resolve(here, "../..");
const workflow = readFileSync(resolve(frontend, "../../.github/workflows/ci.yml"), "utf-8");
const conftest = readFileSync(resolve(frontend, "../backend/tests/conftest.py"), "utf-8");

function job(name: string): string | null {
  const start = workflow.search(new RegExp(`^  ${name}:\\s*$`, "m"));
  if (start < 0) return null;
  const rest = workflow.slice(start + 1);
  const end = rest.search(/^ {2}[a-z][a-z0-9-]*:\s*$/m);
  return end < 0 ? rest : rest.slice(0, end);
}

describe("CI gives the backend suite the database its conftest needs", () => {
  const backend = job("backend") ?? "";

  it("starts PostgreSQL 16 as a service, and waits until it is ready", () => {
    expect(backend).toMatch(/services:\s*\n\s+postgres:\s*\n\s+image:\s*postgres:16\b/);
    expect(backend).toMatch(/--health-cmd[= ]"?pg_isready/);
    expect(backend).toMatch(/-\s*5432:5432/);
  });

  it("runs a Redis, so the logout blocklist tests do not silently skip", () => {
    // FR-05-10. The blocklist fixture skips when Redis is unreachable, and a
    // skipped test is a test nobody is running. The degraded path needs no
    // service: it points the client at a closed port on purpose.
    expect(backend).toMatch(/redis:\s*\n\s+image:\s*redis:7\b/);
    expect(backend).toMatch(/--health-cmd[= ]"?redis-cli ping/);
    expect(backend).toMatch(/-\s*6379:6379/);
  });

  it("sets DATABASE_URL, which conftest refuses to run without", () => {
    expect(conftest).toMatch(/DATABASE_URL must be set/);
    expect(backend).toMatch(/DATABASE_URL:\s*postgresql:\/\/\S+@localhost:5432\/\S+/);
  });

  it("sets every Settings field that has no default, with values that are not secrets", () => {
    // SECRET_KEY was removed from Settings on 2026-09-17 (tokens are RS256 and
    // nothing read it). CI must not set it again, or the trap comes back.
    expect(backend).not.toMatch(/SECRET_KEY:/);
    expect(backend).toMatch(/SMS_API_KEY:\s*\S+/);
    expect(backend).toMatch(/SMS_ENABLED:\s*"?false"?/);
    expect(backend).not.toMatch(/\$\{\{\s*secrets\./);
  });
});

describe("CI's dependency-free ML job can collect the whole suite", () => {
  const repro = job("reproducibility") ?? "";

  it("still installs nothing but pytest (the guard stays in the test files, not the job)", () => {
    expect(repro).toMatch(/pip install --disable-pip-version-check pytest==/);
    expect(repro).not.toMatch(/requirements/);
  });
});
