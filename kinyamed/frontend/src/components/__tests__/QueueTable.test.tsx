import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { QueueTable } from "../QueueTable";
import { setViewportMatches } from "@/test/setup";
import type { QueueEntry } from "@/api/types";

// As GET /queue returns them since item 2d: every row carries its band.
const rows: QueueEntry[] = [
  { id: 1, queue_number: 7, urgency_level: "CRITICAL", status: "WAITING",
    patient_name: "Critical Case", doctor_name: null, estimated_wait: 0,
    band: "CRITICAL", queue_position: 1, requires_human_review: false } as QueueEntry,
  { id: 2, queue_number: 8, urgency_level: "ROUTINE", status: "WAITING",
    patient_name: "Routine Case", doctor_name: null, estimated_wait: 40,
    band: "ROUTINE", queue_position: 2, requires_human_review: false } as QueueEntry,
];

const REVIEW_LABEL = "Model could not classify — review these first";

/** The live case: "sinshobora guhumeka", ROUTINE at 0.598, flagged. Given in the
 *  server's order, which puts it first (item 2d). */
const banded: QueueEntry[] = [
  { id: 12, queue_number: 22, urgency_level: "ROUTINE", status: "WAITING",
    patient_name: "Cannot Breathe", doctor_name: null, estimated_wait: 0,
    band: "NEEDS_REVIEW", queue_position: 1, requires_human_review: true },
  { id: 11, queue_number: 21, urgency_level: "URGENT", status: "WAITING",
    patient_name: "Urgent Sure", doctor_name: null, estimated_wait: 5,
    band: "URGENT", queue_position: 2, requires_human_review: false },
  { id: 10, queue_number: 20, urgency_level: "ROUTINE", status: "WAITING",
    patient_name: "Routine Sure", doctor_name: null, estimated_wait: 10,
    band: "ROUTINE", queue_position: 3, requires_human_review: false },
] as unknown as QueueEntry[];

function before(a: HTMLElement, b: HTMLElement): boolean {
  return Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
}

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

  it("renders every row it is given, in the order the API gave", () => {
    setViewportMatches(true);
    render(<QueueTable rows={rows} />);
    // Patient rows only; each band also opens with a header row.
    const body = screen.getAllByRole("row").filter((r) => within(r).queryAllByRole("cell").length);
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

describe("QueueTable bands (item 2d)", () => {
  it.each([false, true])(
    "shows the flagged case, first in the API order, under its own NEEDS REVIEW header (dense=%s)",
    (dense) => {
      setViewportMatches(dense);
      render(<QueueTable rows={banded} />);
      const header = screen.getByText(REVIEW_LABEL);
      const flagged = screen.getByText("Cannot Breathe");
      expect(before(header, flagged)).toBe(true);
      expect(before(flagged, screen.getByText("Urgent Sure"))).toBe(true);
      expect(before(flagged, screen.getByText("Routine Sure"))).toBe(true);
    },
  );

  it.each([false, true])("gives the band a header, not a badge (dense=%s)", (dense) => {
    setViewportMatches(dense);
    render(<QueueTable rows={banded} />);
    const header = screen.getByText(REVIEW_LABEL);
    // A heading in cards; a row-group header in the table. Either way it names
    // the group the rows below it belong to, for a screen reader too.
    if (dense) {
      expect(header.closest("th")).toHaveAttribute("scope", "rowgroup");
    } else {
      expect(header.closest("h3")).not.toBeNull();
    }
  });

  it.each([false, true])("does not use red for the review band (dense=%s)", (dense) => {
    // Red is CRITICAL's and nothing else's.
    setViewportMatches(dense);
    const { container } = render(<QueueTable rows={banded} />);
    const band = container.querySelector('[data-band="NEEDS_REVIEW"]');
    expect(band).not.toBeNull();
    expect(band!.outerHTML).not.toMatch(/critical/);
  });

  it("keeps the model's class visible in the review band, labelled as a low-confidence hint", () => {
    render(<QueueTable rows={banded} />);
    const card = screen.getByText("Cannot Breathe").closest("li")!;
    expect(within(card).getByText(/model hint/i)).toHaveTextContent("ROUTINE");
    // Not the saturated green badge, which reads as "routine, fine".
    expect(card.innerHTML).not.toMatch(/bg-routine/);
  });

  it("renders no header for a band with nobody in it", () => {
    render(<QueueTable rows={rows} />);
    expect(screen.queryByText(REVIEW_LABEL)).not.toBeInTheDocument();
  });

  it("labels a row with no band as needing review, where the API placed it", () => {
    // Unknown band is shown as unclassified (fail safe), but the row is not moved:
    // position is the server's decision.
    const bare = { id: 30, queue_number: 30, urgency_level: "ROUTINE",
      status: "WAITING", patient_name: "No Band", doctor_name: null,
      estimated_wait: null } as QueueEntry;
    render(<QueueTable rows={[rows[0]!, bare, rows[1]!]} />);
    const header = screen.getByText(REVIEW_LABEL);
    expect(before(screen.getByText("Critical Case"), header)).toBe(true);
    expect(before(header, screen.getByText("No Band"))).toBe(true);
    expect(before(screen.getByText("No Band"), screen.getByText("Routine Case"))).toBe(true);
  });

  it.each([false, true])(
    "property: the rendered patient order is exactly the API order (dense=%s)",
    (dense) => {
      setViewportMatches(dense);
      let seed = 20260915;
      const next = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
      const urgencies = ["CRITICAL", "URGENT", "ROUTINE"] as const;
      const bands = ["CRITICAL", "NEEDS_REVIEW", "URGENT", "ROUTINE", undefined];
      for (let sequence = 0; sequence < 40; sequence++) {
        const n = 1 + Math.floor(next() * 10);
        const api = Array.from({ length: n }, (_, i) => {
          const band = bands[Math.floor(next() * bands.length)];
          return {
            id: i + 1, queue_number: 200 + i, urgency_level: urgencies[Math.floor(next() * 3)]!,
            status: "WAITING", patient_name: `Order Probe ${i + 1}`, doctor_name: null,
            estimated_wait: 0, ...(band === undefined ? {} : { band }), queue_position: i + 1,
          } as QueueEntry;
        }).sort(() => next() - 0.5);
        const { container, unmount } = render(<QueueTable rows={api} />);
        const rendered = [...container.querySelectorAll("li, tbody tr")]
          .map((el) => el.textContent?.match(/Order Probe \d+/)?.[0])
          .filter(Boolean);
        expect(rendered, `sequence ${sequence}`).toEqual(api.map((r) => r.patient_name));
        unmount();
      }
    },
  );
});
