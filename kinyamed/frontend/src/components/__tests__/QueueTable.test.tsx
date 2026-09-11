import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { QueueTable } from "../QueueTable";
import { setViewportMatches } from "@/test/setup";
import type { QueueEntry } from "@/api/types";

const rows: QueueEntry[] = [
  { id: 1, queue_number: 7, urgency_level: "CRITICAL", status: "WAITING",
    patient_name: "Critical Case", doctor_name: null, estimated_wait: 0 },
  { id: 2, queue_number: 8, urgency_level: "ROUTINE", status: "WAITING",
    patient_name: "Routine Case", doctor_name: null, estimated_wait: 40 },
];

afterEach(() => setViewportMatches(false));

describe("QueueTable", () => {
  it("renders CARDS on a phone, and no table at all", () => {
    // The guarantee: below the breakpoint the queue is a different component,
    // not a narrower table. A table that is merely hidden is still a table in
    // the DOM -- built, reconciled on every 5-second poll, and one CSS
    // regression away from overflowing a 360px screen.
    setViewportMatches(false);
    const { container } = render(<QueueTable rows={rows} />);

    expect(container.querySelector("table")).toBeNull();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(container.querySelector(".overflow-x-auto")).toBeNull();
  });

  it("renders the TABLE above the breakpoint, and no card list", () => {
    setViewportMatches(true);
    const { container } = render(<QueueTable rows={rows} />);

    expect(container.querySelector("table")).not.toBeNull();
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });

  it("announces each patient exactly once, in either layout", () => {
    // With both layouts in the DOM this was 2 per patient, and only
    // `display:none` kept the duplicate out of the accessibility tree.
    setViewportMatches(false);
    const cards = render(<QueueTable rows={rows} />);
    expect(within(cards.container).getAllByText("CRITICAL")).toHaveLength(1);
    cards.unmount();

    setViewportMatches(true);
    const table = render(<QueueTable rows={rows} />);
    expect(within(table.container).getAllByText("CRITICAL")).toHaveLength(1);
  });

  it("names the urgency in text, not colour alone", () => {
    render(<QueueTable rows={rows} />);
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
    expect(screen.getByText("ROUTINE")).toBeInTheDocument();
  });

  it("shows a loading state rather than an empty one before data arrives", () => {
    render(<QueueTable rows={[]} isLoading />);
    // The bug this pins: an empty array during the first fetch previously
    // rendered "Nobody is waiting", stating a clinical fact that may be false.
    expect(screen.getByText(/loading the queue/i)).toBeInTheDocument();
    expect(screen.queryByText(/nobody is waiting/i)).not.toBeInTheDocument();
  });

  it("renders every row it is given, in the order given", () => {
    setViewportMatches(true);
    render(<QueueTable rows={rows} />);
    const body = screen.getAllByRole("row").slice(1);
    expect(body).toHaveLength(2);
    expect(within(body[0]!).getByText("Critical Case")).toBeInTheDocument();
  });

  it("shows an empty state rather than a bare table", () => {
    render(<QueueTable rows={[]} />);
    // Both the live region and the visible empty state say "nobody is
    // waiting" -- that is correct, so this asserts on the visible state's own
    // secondary copy rather than on text they share.
    expect(
      screen.getByText(/submitted assessments appear here immediately/i),
    ).toBeInTheDocument();
  });
});

describe("QueueTable live region", () => {
  it("keeps the announcer mounted when the queue empties", () => {
    // The regression this pins: with the announcer inside the populated
    // branch, the last patient leaving unmounted the live region, so the
    // transition to an empty waiting room could never be announced.
    const { rerender } = render(<QueueTable rows={rows} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    rerender(<QueueTable rows={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Queue updated. Nobody is waiting.",
    );
    // Both the live region and the visible empty state say "nobody is
    // waiting" -- that is correct, so this asserts on the visible state's own
    // secondary copy rather than on text they share.
    expect(
      screen.getByText(/submitted assessments appear here immediately/i),
    ).toBeInTheDocument();
  });
});
