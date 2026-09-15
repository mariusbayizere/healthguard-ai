import { BAND_LABEL, QUEUE_BAND, type QueueBand } from "./queueBand.gen";
import type { QueueEntry } from "./types";

/** The four queue bands (item 2d), read from GET /queue.
 *
 * `band`, `queue_position` and `requires_human_review` are read here at runtime
 * rather than typed on `QueueEntry`, because `api/types.ts` holds uncommitted
 * work (the same arrangement as `triageResponse.ts`). Fold them into
 * `QueueEntry` when that file is committed.
 *
 * ORDER IS THE SERVER'S. The API returns the queue already ordered by band and
 * arrival (item 2d); nothing on the client sorts it. Grouping here only draws a
 * header wherever the band changes along that order. If the server ever
 * returned bands out of order, the board would show a repeated header rather
 * than silently rearranging patients -- the bug stays visible, and there is
 * still one source of truth for who is seen next.
 */

export interface BandGroup {
  /** Unique per segment: a band can appear twice if the API order says so. */
  key: string;
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

/** Consecutive runs of one band, in exactly the order given. Empty bands never appear. */
export function groupByBand(rows: QueueEntry[]): BandGroup[] {
  const groups: BandGroup[] = [];
  for (const row of rows) {
    const band = bandOf(row);
    const last = groups[groups.length - 1];
    if (last && last.band === band) {
      last.rows.push(row);
    } else {
      groups.push({ key: `${band}-${groups.length}`, band, label: BAND_LABEL[band], rows: [row] });
    }
  }
  return groups;
}
