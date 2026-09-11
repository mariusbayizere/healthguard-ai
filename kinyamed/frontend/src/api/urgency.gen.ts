/* GENERATED FILE — DO NOT EDIT BY HAND.
 *
 * Written by backend/scripts/gen_frontend_constants.py from
 * `app.models.triage_result.UrgencyLevel`, which is the single definition of
 * the clinical ordering. AUDIT 1.3.
 *
 * To change the ordering, change the Python enum and regenerate. Editing this
 * file makes the queue sort differently from the server that fills it, and
 * `tests/unit/test_frontend_constants.py` will fail rather than let that ship.
 */

export const URGENCY = [
  "CRITICAL",
  "URGENT",
  "ROUTINE",
] as const;

export type Urgency = (typeof URGENCY)[number];

/** Queue sort key; lower sorts earlier. Mirrors
 *  `UrgencyLevel.priority` exactly, including its base. */
export const URGENCY_RANK: Record<Urgency, number> = {
  CRITICAL: 1,
  URGENT: 2,
  ROUTINE: 3,
};
