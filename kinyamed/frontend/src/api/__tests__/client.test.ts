import { afterEach, describe, expect, it, vi } from "vitest";
import fixture from "../../../e2e/fixtures/triage-model-unavailable.json";
import { ApiError, request } from "../client";

function respond(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("request() error surfacing", () => {
  it("carries the API's own message and code from the error envelope", async () => {
    respond(fixture.status, fixture.body);

    const error = (await request("/triage", { method: "POST" }).catch((e: unknown) => e)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(503);
    expect(error.code).toBe("TRIAGE_MODEL_UNAVAILABLE");
    expect(error.message).toBe(fixture.body.error.message);
    expect(error.message).not.toMatch(/request failed/i);
  });

  it("still reads a bare FastAPI detail string", async () => {
    respond(404, { detail: "Not Found" });
    const error = (await request("/nope").catch((e: unknown) => e)) as ApiError;
    expect(error.message).toBe("Not Found");
    expect(error.code).toBeUndefined();
  });
});
