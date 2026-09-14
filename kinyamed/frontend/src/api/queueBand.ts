import { BAND_LABEL, QUEUE_BAND, type QueueBand } from "./queueBand.gen";
import type { QueueEntry } from "./types";

/** The four queue bands (item 2d), read from GET /queue.
 *
 * `band`, `queue_position` and `requires_human_review` are read here at runtime
 * rather than typed on `QueueEntry`, because `api/types.ts` holds uncommitted
 * work (the same arrangement as `triageResponse.ts`). Fold them into
 * `QueueEntry` when that file is committed.
 *
 * `hooks.ts` sorts the queue by urgency alone, which is the ordering item 2d
 * replaces, so grouping and within-band order are decided here, from the
 * server's band and position, and not from the order rows arrive in.
 */

export interface BandGroup {
  band: QueueBand;
  label: string;
  rows: QueueEntry[];
}

function field(row: QueueEntry, name: string): unknown {
  return (row as unknown as Record<string, unknown>)[name];
}

function isBand(value: unknown): value is QueueBand {
  return typeof value === "string" && (QUEUE_BAND as readonly string[]).includes(value);
}

/** The band a row sorts in.
 *
 * FAIL SAFE (L4). A row whose band is missing or unrecognised -- the optimistic
 * insert after a submission, or an API this client predates -- is one the
 * board cannot place. It goes to NEEDS REVIEW, not to its predicted class: the
 * safe error is a confident ROUTINE shown for one poll among the cases to look
 * at first, never an unclassified case shown among the routine ones. A CRITICAL
 * prediction always stays CRITICAL.
 */
export function bandOf(row: QueueEntry): QueueBand {
  if (row.urgency_level === "CRITICAL") return "CRITICAL";
  const band = field(row, "band");
  return isBand(band) ? band : "NEEDS_REVIEW";
}

function position(row: QueueEntry): number {
  const value = field(row, "queue_position");
  return typeof value === "number" && value > 0 ? value : Number.POSITIVE_INFINITY;
}

/** Rows grouped by band, in band order, each in the server's order. Empty bands are omitted. */
export function groupByBand(rows: QueueEntry[]): BandGroup[] {
  return QUEUE_BAND.map((band) => ({
    band,
    label: BAND_LABEL[band],
    rows: rows
      .filter((row) => bandOf(row) === band)
      .sort((a, b) => position(a) - position(b) || a.queue_number - b.queue_number),
  })).filter((group) => group.rows.length > 0);
}
