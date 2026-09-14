import type { QueueBand } from "@/api/queueBand.gen";
import type { QueueEntry } from "@/api/types";
import { UrgencyBadge } from "./UrgencyBadge";

/** What the cards and the table share about bands (item 2d).
 *
 * NOT RED. Red is CRITICAL's, and a second red band would teach the eye that red
 * means "look at this" rather than "life-threatening". NEEDS REVIEW is the
 * darkest neutral in the palette instead: a solid ink bar with white text. It is
 * the one header on the board that is filled, so it is found first after
 * CRITICAL's red rows, and it cannot be confused with any urgency colour or with
 * the blue of an action. No new colour token: the palette is closed on purpose
 * (tailwind.config.js).
 */
export const BAND_HEADER: Record<QueueBand, string> = {
  CRITICAL: "text-xs font-semibold uppercase tracking-wide text-ink-600",
  NEEDS_REVIEW: "rounded bg-ink-900 px-4 py-2 text-base font-semibold text-white",
  URGENT: "text-xs font-semibold uppercase tracking-wide text-ink-600",
  ROUTINE: "text-xs font-semibold uppercase tracking-wide text-ink-600",
};

/** Left edge and ground per band. Review rows are ink, not their predicted class. */
export const BAND_EDGE: Record<QueueBand, string> = {
  CRITICAL: "border-l-critical bg-critical-soft/40",
  NEEDS_REVIEW: "border-l-ink-900 bg-ink-50",
  URGENT: "border-l-urgent bg-urgent-soft/40",
  ROUTINE: "border-l-routine bg-white",
};

/** The urgency cell.
 *
 * Outside the review band: the urgency badge. Inside it, the model's class is
 * still shown -- it is a prioritisation hint for a clinician -- but as outlined
 * neutral text that says what it is, never as the filled green ROUTINE badge,
 * which reads as "routine, fine" on a case the model could not classify.
 */
export function RowUrgency({
  row,
  band,
  size = "md",
}: {
  row: QueueEntry;
  band: QueueBand;
  size?: "sm" | "md";
}) {
  if (band !== "NEEDS_REVIEW") return <UrgencyBadge level={row.urgency_level} size={size} />;
  return (
    <span className="inline-block max-w-[14rem] rounded border border-ink-700 px-2.5 py-1 text-sm font-medium leading-snug text-ink-800">
      Model hint (low confidence): {row.urgency_level}
    </span>
  );
}
