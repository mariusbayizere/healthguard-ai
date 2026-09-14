import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TriageOfflineBanner } from "../TriageOfflineBanner";

const BANNER = /automated triage offline — triage manually/i;

function readiness(respond: () => Promise<Response>) {
  const fetchMock = vi.fn((_url: string) => respond());
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("TriageOfflineBanner", () => {
  it("is shown while readiness reports model: false", async () => {
    const fetchMock = readiness(async () =>
      new Response(JSON.stringify({ status: "ready", database: "ok", model: false })),
    );
    render(<TriageOfflineBanner />);
    expect(await screen.findByRole("alert")).toHaveTextContent(BANNER);
    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/health\/ready$/);
  });

  it("is absent while readiness reports model: true", async () => {
    const fetchMock = readiness(async () =>
      new Response(JSON.stringify({ status: "ready", database: "ok", model: true })),
    );
    render(<TriageOfflineBanner />);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    await Promise.resolve();
    expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
  });

  it("fails closed: an unreachable readiness probe shows the banner", async () => {
    readiness(async () => {
      throw new TypeError("network down");
    });
    render(<TriageOfflineBanner />);
    expect(await screen.findByRole("alert")).toHaveTextContent(BANNER);
  });

  it("has no control to dismiss it", async () => {
    readiness(async () =>
      new Response(JSON.stringify({ status: "ready", database: "ok", model: false })),
    );
    render(<TriageOfflineBanner />);
    const alert = await screen.findByRole("alert");
    expect(alert.querySelectorAll("button")).toHaveLength(0);
  });
});
