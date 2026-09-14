/* GENERATED FILE — DO NOT EDIT BY HAND.
 *
 * Written by backend/scripts/gen_frontend_constants.py from
 * `app.models.queue_band.QueueBand`, which defines the order the queue is
 * sorted in (item 2d) and the header a clinician reads above each band.
 *
 * `tests/unit/test_frontend_constants.py` fails if this drifts from the enum.
 */

/** Queue bands, in the order the server sorts them. */
export const QUEUE_BAND = [
  "CRITICAL",
  "NEEDS_REVIEW",
  "URGENT",
  "ROUTINE",
] as const;

export type QueueBand = (typeof QUEUE_BAND)[number];

/** The header text above each band. */
export const BAND_LABEL: Record<QueueBand, string> = {
  CRITICAL: "Critical",
  NEEDS_REVIEW: "Model could not classify — review these first",
  URGENT: "Urgent",
  ROUTINE: "Routine",
};
