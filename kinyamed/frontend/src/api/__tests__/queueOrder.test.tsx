import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { keys, useQueue, useSubmitTriage } from "../hooks";
import type { QueueEntry } from "../types";

/** The server orders the queue (item 2d: CRITICAL, NEEDS REVIEW, URGENT, ROUTINE).
 *  The client used to re-sort by urgency alone -- a second source of truth for
 *  who is seen next, which put a flagged ROUTINE below every URGENT. */

type Row = QueueEntry & { band?: string; queue_position?: number };

const row = (id: number, urgency: QueueEntry["urgency_level"], band: string, position: number): Row => ({
  id, queue_number: 100 + id, urgency_level: urgency, status: "WAITING",
  patient_name: `Patient ${id}`, doctor_name: null, estimated_wait: 0,
  band, queue_position: position,
});

function wrapper(client: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

function serveQueue(items: Row[]) {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ items }))));
}

beforeEach(() => localStorage.setItem("kinyamed.token", "test-token"));
afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("useQueue keeps the server's order", () => {
  it("does not move an URGENT above a flagged ROUTINE", async () => {
    // Server order: the flagged ROUTINE is first. An urgency sort would put
    // the URGENT row first and bury the case the model could not classify.
    const api = [
      row(1, "ROUTINE", "NEEDS_REVIEW", 1),
      row(2, "URGENT", "URGENT", 2),
      row(3, "ROUTINE", "ROUTINE", 3),
    ];
    serveQueue(api);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useQueue(), { wrapper: wrapper(client) });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data!.map((r) => r.id)).toEqual([1, 2, 3]);
  });

  it("property: for any API order, the hook returns exactly that order", async () => {
    let seed = 20260915;
    const next = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
    const urgencies = ["CRITICAL", "URGENT", "ROUTINE"] as const;
    const bands = ["CRITICAL", "NEEDS_REVIEW", "URGENT", "ROUTINE"];
    for (let sequence = 0; sequence < 25; sequence++) {
      const n = 1 + Math.floor(next() * 12);
      const api = Array.from({ length: n }, (_, i) =>
        row(i + 1, urgencies[Math.floor(next() * 3)]!, bands[Math.floor(next() * 4)]!, i + 1),
      ).sort(() => next() - 0.5);
      serveQueue(api);
      const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      const { result, unmount } = renderHook(() => useQueue(), { wrapper: wrapper(client) });
      await waitFor(() => expect(result.current.data).toBeDefined());
      expect(result.current.data!.map((r) => r.id), `sequence ${sequence}`).toEqual(api.map((r) => r.id));
      unmount();
      vi.unstubAllGlobals();
    }
  });
});

describe("useSubmitTriage inserts the new row where the server placed it", () => {
  it("splices at the server's queue_position with the server's band, and re-sorts nothing", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const cached = [row(1, "CRITICAL", "CRITICAL", 1), row(2, "URGENT", "URGENT", 2), row(3, "ROUTINE", "ROUTINE", 3)];
    client.setQueryData(keys.queue, cached);
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      triage_id: 9, patient_id: 9, patient_name: "Cannot Breathe", urgency_level: "ROUTINE",
      confidence_score: 0.598, requires_human_review: true, review_reason: "low confidence",
      queue_id: 9, queue_number: 109, queue_position: 2, band: "NEEDS_REVIEW",
      band_label: "Model could not classify — review these first", estimated_wait: 0,
    }), { status: 201 })));
    const { result } = renderHook(() => useSubmitTriage(), { wrapper: wrapper(client) });
    await act(async () => {
      await result.current.mutateAsync({ patient_id: 9, symptoms_input: "sinshobora guhumeka" });
    });
    const after = client.getQueryData<Row[]>(keys.queue)!;
    expect(after.map((r) => r.id)).toEqual([1, 9, 2, 3]);
    const inserted = after[1]!;
    expect(inserted.band).toBe("NEEDS_REVIEW");
    expect(inserted.queue_position).toBe(2);
  });

  it("appends when the server's position is past the end of the cached list", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(keys.queue, [row(1, "CRITICAL", "CRITICAL", 1)]);
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      triage_id: 5, patient_id: 5, patient_name: "Late", urgency_level: "ROUTINE",
      confidence_score: 0.9, requires_human_review: false, review_reason: null,
      queue_id: 5, queue_number: 105, queue_position: 7, band: "ROUTINE", band_label: "Routine",
      estimated_wait: 30,
    }), { status: 201 })));
    const { result } = renderHook(() => useSubmitTriage(), { wrapper: wrapper(client) });
    await act(async () => {
      await result.current.mutateAsync({ patient_id: 5, symptoms_input: "anything at all" });
    });
    expect(client.getQueryData<Row[]>(keys.queue)!.map((r) => r.id)).toEqual([1, 5]);
  });
});
