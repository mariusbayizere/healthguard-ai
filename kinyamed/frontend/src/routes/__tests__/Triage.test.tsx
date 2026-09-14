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
