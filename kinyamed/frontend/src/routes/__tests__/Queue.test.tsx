import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Queue } from "../Queue";

const ITEMS = [
  { id: 1, queue_number: 1, urgency_level: "ROUTINE", status: "WAITING", band: "ROUTINE",
    requires_human_review: false, patient_name: "Routine One", estimated_wait: 10 },
  { id: 2, queue_number: 2, urgency_level: "ROUTINE", status: "WAITING", band: "NEEDS_REVIEW",
    requires_human_review: true, patient_name: "Cannot Breathe", estimated_wait: 0 },
];

beforeEach(() => {
  localStorage.setItem("kinyamed.token", "test-token");
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ items: ITEMS }))));
});
afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("Queue counts", () => {
  it("counts by band, so a flagged ROUTINE is not reported as routine", async () => {
    // The tiles are the half-second read. Counting the flagged case as ROUTINE
    // would hide it in the summary exactly as it was hidden in the list.
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><Queue /></QueryClientProvider>);
    await screen.findByText("Cannot Breathe");
    const tile = (name: RegExp) => screen.getByText(name, { selector: "[data-tile] *" }).closest("[data-tile]") as HTMLElement;
    expect(within(tile(/^needs review$/i)).getByText("1")).toBeInTheDocument();
    expect(within(tile(/^routine$/i)).getByText("1")).toBeInTheDocument();
    expect(within(tile(/^critical$/i)).getByText("0")).toBeInTheDocument();
  });
});
