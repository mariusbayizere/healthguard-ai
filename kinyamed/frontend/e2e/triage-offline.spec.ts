/// <reference lib="dom" />
import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

/** A recording of the real 503, pinned to the API by a backend contract test. */
const offline = JSON.parse(
  readFileSync(new URL("./fixtures/triage-model-unavailable.json", import.meta.url), "utf-8"),
) as { status: number; headers: Record<string, string>; body: { error: { message: string } } };

async function signedInWithOfflineTriage(page: Page) {
  await page.addInitScript(() => localStorage.setItem("kinyamed.token", "e2e-token"));

  // Anything not served below is an unexpected call; answer it loudly.
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({ status: 404, json: { detail: `unrouted in e2e: ${route.request().url()}` } }),
  );
  await page.route("**/health/ready", (route) =>
    route.fulfill({ json: { status: "ready", database: "ok", model: false } }),
  );
  await page.route("**/api/v1/patients**", (route) =>
    route.fulfill({ json: [{ id: 7, name: "Uwimana Alice", phone: null }] }),
  );
  await page.route("**/api/v1/triage", (route) =>
    route.fulfill({ status: offline.status, headers: offline.headers, json: offline.body }),
  );
}

test("a nurse sees the full manual-triage instruction when triage returns 503", async ({ page }) => {
  await signedInWithOfflineTriage(page);
  await page.goto("/");

  await page.getByRole("combobox").selectOption("7");
  await page.getByRole("textbox").fill("sinshobora guhumeka");
  await page.getByRole("button", { name: /assess/i }).click();

  const alert = page.getByRole("alert", { name: /automated triage is offline/i });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText(offline.body.error.message);
  await expect(page.getByText(/request failed/i)).toHaveCount(0);

  // Non-dismissible, and it does not go away on its own.
  await expect(alert.getByRole("button")).toHaveCount(0);
  await page.waitForTimeout(5_000);
  await expect(alert).toBeVisible();
});

test("every screen carries the offline banner while readiness reports model: false", async ({ page }) => {
  await signedInWithOfflineTriage(page);
  await page.goto("/");
  await expect(page.getByText("Automated triage offline — triage manually")).toBeVisible();
});
