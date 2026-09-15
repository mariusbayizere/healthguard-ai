import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";

/** CI must run on every branch and every pull request. Until 2026-09-15 the push
 *  trigger was `branches: [main]`, so a pushed branch ran nothing and none of
 *  the backend, frontend, e2e or lint jobs had ever run on GitHub. A filter on
 *  the trigger is how a branch goes unchecked, so these tests forbid one.
 *
 *  Structural checks on the workflow text, like ci-e2e.test.ts, and for the same
 *  reason: no YAML library is a direct dependency of this package. */

const here = dirname(decodeURIComponent(new URL(import.meta.url).pathname));
const workflow = readFileSync(resolve(here, "../../../../.github/workflows/ci.yml"), "utf-8");

/** The body of a top-level key (e.g. `on:`), up to the next top-level key. */
function topLevel(key: string): string | null {
  const start = workflow.search(new RegExp(`^${key}:\\s*$`, "m"));
  if (start < 0) return null;
  const rest = workflow.slice(workflow.indexOf("\n", start) + 1);
  const end = rest.search(/^[a-z_]+:/m);
  return end < 0 ? rest : rest.slice(0, end);
}

/** The body of one event under `on:` (e.g. `push`), up to the next event. */
function trigger(on: string, event: string): string | null {
  const start = on.search(new RegExp(`^  ${event}:.*$`, "m"));
  if (start < 0) return null;
  const rest = on.slice(on.indexOf("\n", start) + 1);
  const end = rest.search(/^ {2}[a-z_]+:/m);
  return end < 0 ? rest : rest.slice(0, end);
}

const FILTERS = /^\s+(branches|branches-ignore|tags|tags-ignore|paths|paths-ignore):/m;

describe("CI runs on every branch and every pull request", () => {
  const on = topLevel("on");

  it("has an `on:` block", () => {
    expect(on, "no top-level `on:` in .github/workflows/ci.yml").not.toBeNull();
  });

  it("runs on a push to any branch, with no branch or path filter", () => {
    const push = trigger(on ?? "", "push");
    expect(push, "no `push:` trigger").not.toBeNull();
    expect(push).not.toMatch(FILTERS);
  });

  it("runs on every pull request, with no base-branch or path filter", () => {
    const pr = trigger(on ?? "", "pull_request");
    expect(pr, "no `pull_request:` trigger").not.toBeNull();
    expect(pr).not.toMatch(FILTERS);
  });

  it("can still be run by hand", () => {
    expect(trigger(on ?? "", "workflow_dispatch")).not.toBeNull();
  });

  it("does not restrict any job to main from inside the job", () => {
    expect(workflow).not.toMatch(/github\.ref\s*==\s*'refs\/heads\/main'/);
    expect(workflow).not.toMatch(/github\.ref_name\s*==\s*'main'/);
  });

  it("allows no job to fail and still report success", () => {
    expect(workflow).not.toMatch(/continue-on-error:\s*true/);
  });

  it("keeps every gate job", () => {
    for (const name of [
      "reproducibility",
      "reproducibility-full",
      "training-tests",
      "hygiene",
      "backend",
      "frontend",
      "e2e",
      "lint",
    ]) {
      expect(workflow, `job \`${name}\` is missing`).toMatch(new RegExp(`^  ${name}:\\s*$`, "m"));
    }
  });
});
