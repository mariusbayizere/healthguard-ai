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

describe("groupByBand renders the API order, and never reorders it", () => {
  it("segments rows by band in the order the API returned them", () => {
    const rows = [
      row(4, "CRITICAL", { band: "CRITICAL", queue_position: 1 }),
      row(2, "ROUTINE", { band: "NEEDS_REVIEW", queue_position: 2 }),
      row(3, "URGENT", { band: "NEEDS_REVIEW", queue_position: 3 }),
      row(1, "URGENT", { band: "URGENT", queue_position: 4 }),
      row(5, "ROUTINE", { band: "ROUTINE", queue_position: 5 }),
    ];
    const groups = groupByBand(rows);
    expect(groups.map((g) => g.band)).toEqual(["CRITICAL", "NEEDS_REVIEW", "URGENT", "ROUTINE"]);
    expect(groups.map((g) => g.rows.map((r) => r.id))).toEqual([[4], [2, 3], [1], [5]]);
    expect(groups[1]!.label).toBe(BAND_LABEL.NEEDS_REVIEW);
  });

  it("does not sort within a band, even when positions disagree with the order", () => {
    // The server is authoritative. If its order and its positions ever
    // disagreed, the board shows the order and the bug is the server's.
    const groups = groupByBand([
      row(9, "ROUTINE", { band: "ROUTINE", queue_position: 2 }),
      row(7, "ROUTINE", { band: "ROUTINE", queue_position: 1 }),
    ]);
    expect(groups[0]!.rows.map((r) => r.id)).toEqual([9, 7]);
  });

  it("starts a new segment when a band reappears, instead of merging rows out of order", () => {
    const groups = groupByBand([
      row(1, "ROUTINE", { band: "NEEDS_REVIEW" }),
      row(2, "ROUTINE", { band: "ROUTINE" }),
      row(3, "URGENT", { band: "NEEDS_REVIEW" }),
    ]);
    expect(groups.map((g) => g.band)).toEqual(["NEEDS_REVIEW", "ROUTINE", "NEEDS_REVIEW"]);
    expect(new Set(groups.map((g) => g.key)).size).toBe(3);
  });

  it("property: flattening the segments gives back exactly the API order", () => {
    let seed = 20260915;
    const next = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
    const urgencies = ["CRITICAL", "URGENT", "ROUTINE"] as const;
    const bands = ["CRITICAL", "NEEDS_REVIEW", "URGENT", "ROUTINE", undefined, "UNKNOWN"];
    for (let sequence = 0; sequence < 300; sequence++) {
      const n = Math.floor(next() * 15);
      const rows: Row[] = Array.from({ length: n }, (_, i) => {
        const band = bands[Math.floor(next() * bands.length)];
        return row(i + 1, urgencies[Math.floor(next() * 3)]!, band === undefined ? {} : { band });
      }).sort(() => next() - 0.5);
      const groups = groupByBand(rows);
      expect(groups.flatMap((g) => g.rows.map((r) => r.id)), `sequence ${sequence}`)
        .toEqual(rows.map((r) => r.id));
      groups.forEach((g) => g.rows.forEach((r) => expect(bandOf(r)).toBe(g.band)));
      groups.slice(1).forEach((g, i) => expect(g.band).not.toBe(groups[i]!.band));
    }
  });
});
