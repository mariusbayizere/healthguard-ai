import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import fixture from "../../../e2e/fixtures/triage-model-unavailable.json";
import { Triage } from "../Triage";

const MESSAGE = fixture.body.error.message;

function renderTriage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Triage />
    </QueryClientProvider>,
  );
}

/** /patients answers with one patient; /triage answers with `triage()`. */
function serve(triage: () => Response | Promise<Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      url.includes("/patients")
        ? new Response(JSON.stringify([{ id: 7, name: "Uwimana", phone: null }]))
        : triage(),
    ),
  );
}

const offline = () =>
  new Response(JSON.stringify(fixture.body), {
    status: fixture.status,
    headers: fixture.headers,
  });

async function submit() {
  // Wait for the patient list, or the select has nothing to choose.
  await screen.findByRole("option", { name: /uwimana/i }, { timeout: 5_000 });
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "7" } });
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "sinshobora guhumeka" },
  });
  fireEvent.click(screen.getByRole("button", { name: /assess/i }));
}

beforeEach(() => localStorage.setItem("kinyamed.token", "test-token"));
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  localStorage.clear();
});

describe("Triage when automated triage is offline", () => {
  it("shows the full manual-triage instruction, not a generic failure", async () => {
    serve(offline);
    renderTriage();
    await submit();

    const alert = await screen.findByRole("alert", { name: /automated triage is offline/i });
    expect(within(alert).getByText(MESSAGE)).toBeInTheDocument();
    expect(screen.queryByText(/request failed/i)).not.toBeInTheDocument();
  });

  it("cannot be dismissed: the alert has no control to close it", async () => {
    serve(offline);
    renderTriage();
    await submit();

    const alert = await screen.findByRole("alert", { name: /automated triage is offline/i });
    expect(within(alert).queryAllByRole("button")).toHaveLength(0);
  });

  it("does not disappear on its own, or while a retry is in flight", async () => {
    serve(offline);
    renderTriage();
    await submit();
    await screen.findByRole("alert", { name: /automated triage is offline/i });

    // A retry that never answers: the alert must survive the pending state.
    serve(() => new Promise<Response>(() => {}));
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: /assess/i }));
    await act(async () => {
      vi.advanceTimersByTime(10 * 60 * 1000);
    });

    expect(
      screen.getByRole("alert", { name: /automated triage is offline/i }),
    ).toBeInTheDocument();
  });

  it("keeps what the nurse typed", async () => {
    serve(offline);
    renderTriage();
    await submit();
    await screen.findByRole("alert", { name: /automated triage is offline/i });
    expect(screen.getByRole("textbox")).toHaveValue("sinshobora guhumeka");
  });
});

const RECEIPT =
  "Your report has been received. Your queue number is 12 and you are number 1 in the queue. " +
  "If you feel worse or this is an emergency, go to the health centre immediately.";

function assessed(overrides: Record<string, unknown> = {}) {
  return () =>
    new Response(
      JSON.stringify({
        triage_id: 1, patient_id: 7, patient_name: "Uwimana",
        urgency_level: "ROUTINE", confidence_score: 0.598,
        requires_human_review: true,
        review_reason: "Model confidence 0.60 is below the review threshold 0.75.",
        clinician_hint_notice:
          "Urgency and confidence are a prioritisation hint for clinicians reviewing the queue. They are not advice for the patient.",
        patient_response: RECEIPT, patient_message_language: "english",
        language_detected: "kinyarwanda", queue_id: 3, queue_number: 12,
        queue_position: 1, estimated_wait: 0, created_at: "2026-09-14T08:00:00Z",
        ...overrides,
      }),
      { status: 201 },
    );
}

describe("Triage result", () => {
  it("labels the urgency as a hint for clinicians, not advice for the patient", async () => {
    serve(assessed());
    renderTriage();
    await submit();
    const hint = await screen.findByRole("region", { name: /prioritisation hint/i });
    expect(within(hint).getByText(/clinicians only/i)).toBeInTheDocument();
    expect(within(hint).getByText(/not advice for the patient/i)).toBeInTheDocument();
  });

  it("flags a low-confidence result for clinician review, with the reason", async () => {
    serve(assessed());
    renderTriage();
    await submit();
    const review = await screen.findByRole("status", { name: /needs clinician review/i });
    expect(within(review).getByText(/below the review threshold 0.75/i)).toBeInTheDocument();
  });

  it("shows no review flag when the API does not require one", async () => {
    serve(assessed({ requires_human_review: false, review_reason: null }));
    renderTriage();
    await submit();
    await screen.findByRole("region", { name: /prioritisation hint/i });
    expect(screen.queryByRole("status", { name: /needs clinician review/i })).not.toBeInTheDocument();
  });

  it("puts no urgency in the patient's message section", async () => {
    serve(assessed());
    renderTriage();
    await submit();
    const message = await screen.findByRole("region", { name: /message for the patient/i });
    expect(within(message).getByText(RECEIPT)).toBeInTheDocument();
    for (const level of [/critical/i, /urgent/i, /routine/i]) {
      expect(within(message).queryByText(level)).not.toBeInTheDocument();
    }
  });
});

