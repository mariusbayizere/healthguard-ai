import type { Urgency } from "@/api/types";

/** The single most important element in this interface.
 *
 * Urgency is carried on FOUR redundant channels so that losing any one still
 * leaves it legible:
 *   1. fill colour        -- fastest to perceive
 *   2. the word itself    -- survives colour blindness and greyscale printing
 *   3. weight and size    -- it is the largest thing on the row
 *   4. sort position      -- handled by the queue, not here
 *
 * SIZED UP DELIBERATELY. The first build set this at 12px beside a 36px queue
 * number, so the largest element on every row was the least clinically
 * important one and the eye landed on the ticket rather than the acuity. The
 * badge now leads.
 *
 * The tone is flat: gradients and shadows on a status chip add nothing and cost
 * legibility on a poor screen in bright light.
 */
const STYLES: Record<Urgency, string> = {
  CRITICAL: "bg-critical text-white ring-critical-edge",
  URGENT: "bg-urgent text-white ring-urgent-edge",
  ROUTINE: "bg-routine text-white ring-routine-edge",
};

export function UrgencyBadge({
  level,
  size = "md",
}: {
  level: Urgency;
  size?: "sm" | "md";
}) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full font-semibold uppercase",
        "tracking-wide ring-1 ring-inset",
        size === "sm" ? "px-2.5 py-0.5 text-sm" : "px-3 py-1 text-base",
        STYLES[level],
      ].join(" ")}
    >
      {level}
    </span>
  );
}
