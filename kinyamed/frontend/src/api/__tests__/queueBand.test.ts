import { describe, expect, it } from "vitest";
import { bandOf, groupByBand } from "../queueBand";
import { BAND_LABEL, QUEUE_BAND } from "../queueBand.gen";
import type { QueueEntry } from "../types";

type Row = QueueEntry & { band?: string; queue_position?: number; requires_human_review?: boolean };

function row(id: number, urgency: QueueEntry["urgency_level"], extra: Partial<Row> = {}): Row {
  return {
    id, queue_number: id, urgency_level: urgency, status: "WAITING",
    patient_name: `Patient ${id}`, doctor_name: null, estimated_wait: null, ...extra,
  };
}

describe("band constants", () => {
  it("orders NEEDS REVIEW second, below CRITICAL only", () => {
    expect(QUEUE_BAND).toEqual(["CRITICAL", "NEEDS_REVIEW", "URGENT", "ROUTINE"]);
  });

  it("says what the review band means to a clinician", () => {
    expect(BAND_LABEL.NEEDS_REVIEW).toBe("Model could not classify — review these first");
  });
});

describe("bandOf", () => {
  it("uses the band the server sent", () => {
    expect(bandOf(row(1, "ROUTINE", { band: "NEEDS_REVIEW" }))).toBe("NEEDS_REVIEW");
    expect(bandOf(row(2, "ROUTINE", { band: "ROUTINE" }))).toBe("ROUTINE");
  });

  it("fails safe when the band is missing: never ROUTINE or URGENT by default", () => {
    // A row without a band (an optimistic cache insert, an older API) is one we
    // cannot place, so it goes where a clinician looks first after CRITICAL.
    expect(bandOf(row(1, "ROUTINE"))).toBe("NEEDS_REVIEW");
    expect(bandOf(row(2, "URGENT"))).toBe("NEEDS_REVIEW");
    expect(bandOf(row(3, "CRITICAL"))).toBe("CRITICAL");
  });

  it("fails safe on a band it does not recognise", () => {
    expect(bandOf(row(1, "ROUTINE", { band: "SOMETHING_NEW" }))).toBe("NEEDS_REVIEW");
    expect(bandOf(row(2, "CRITICAL", { band: "SOMETHING_NEW" }))).toBe("CRITICAL");
  });

  it("never lets a CRITICAL prediction sort below the CRITICAL band", () => {
    expect(bandOf(row(1, "CRITICAL", { band: "ROUTINE" }))).toBe("CRITICAL");
  });
});

describe("groupByBand", () => {
  it("groups in band order, skips empty bands, and keeps server order within a band", () => {
    // Given in the urgency order hooks.ts sorts by, which is the wrong order.
    const rows = [
      row(4, "CRITICAL", { band: "CRITICAL", queue_position: 1 }),
      row(1, "URGENT", { band: "URGENT", queue_position: 4 }),
      row(3, "URGENT", { band: "NEEDS_REVIEW", queue_position: 3 }),
      row(2, "ROUTINE", { band: "NEEDS_REVIEW", queue_position: 2 }),
      row(5, "ROUTINE", { band: "ROUTINE", queue_position: 5 }),
    ];
    const groups = groupByBand(rows);
    expect(groups.map((g) => g.band)).toEqual(["CRITICAL", "NEEDS_REVIEW", "URGENT", "ROUTINE"]);
    expect(groups.map((g) => g.rows.map((r) => r.id))).toEqual([[4], [2, 3], [1], [5]]);
    expect(groups[1]!.label).toBe(BAND_LABEL.NEEDS_REVIEW);
  });

  it("falls back to queue number within a band when positions are absent", () => {
    const groups = groupByBand([
      row(9, "ROUTINE", { band: "ROUTINE" }),
      row(7, "ROUTINE", { band: "ROUTINE" }),
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0]!.rows.map((r) => r.id)).toEqual([7, 9]);
  });

  it("property: no flagged case ever lands below an unflagged non-CRITICAL case", () => {
    // Seeded LCG so a failure reproduces.
    let seed = 20260914;
    const next = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
    const urgencies = ["CRITICAL", "URGENT", "ROUTINE"] as const;
    for (let sequence = 0; sequence < 200; sequence++) {
      const n = 1 + Math.floor(next() * 12);
      const rows: Row[] = [];
      for (let i = 0; i < n; i++) {
        const urgency = urgencies[Math.floor(next() * 3)]!;
        const flagged = next() < 0.4;
        // Some rows arrive with neither field, as the optimistic insert does.
        const unknown = next() < 0.1;
        const band = urgency === "CRITICAL" ? "CRITICAL" : flagged ? "NEEDS_REVIEW" : urgency;
        rows.push(row(i + 1, urgency, unknown ? {} : { requires_human_review: flagged, band }));
      }
      rows.sort(() => next() - 0.5);
      const flat = groupByBand(rows).flatMap((g) => g.rows) as Row[];
      expect(flat).toHaveLength(n);
      flat.forEach((upper, i) => {
        for (const lower of flat.slice(i + 1)) {
          const context = `sequence ${sequence}: #${upper.id} above #${lower.id}`;
          // Flagged: the server said review is required. Unflagged: it said not.
          // A row with no flag is neither, and is placed by the fail-safe.
          const flagged = lower.requires_human_review === true;
          const unflagged = upper.requires_human_review === false;
          expect(flagged && unflagged && upper.urgency_level !== "CRITICAL", context).toBe(false);
          expect(lower.urgency_level === "CRITICAL" && upper.urgency_level !== "CRITICAL", context)
            .toBe(false);
        }
      });
    }
  });
});
