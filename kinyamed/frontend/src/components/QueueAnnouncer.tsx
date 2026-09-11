import { useEffect, useRef, useState } from "react";
import type { QueueEntry } from "@/api/types";
import { URGENCY } from "@/api/types";

/** Tells a screen-reader user that the board changed.
 *
 * THE GAP THIS CLOSES. The queue repaints every 5 seconds. A sighted nurse
 * glances up and sees a new row; a nurse using a screen reader gets nothing at
 * all, because React swapping table rows is not an event any assistive
 * technology reports. They would have to re-read the whole board on a hunch to
 * discover that a CRITICAL patient had arrived. The polling interval was
 * chosen on clinical grounds -- "a minute is long enough for a critical
 * arrival to be missed" -- and that reasoning only held for people who can see
 * the screen.
 *
 * WHAT IT DOES NOT DO. It does not announce every poll. Twelve interruptions a
 * minute reading an unchanged board is worse than silence: it is the state in
 * which people switch the announcements off, and then the one that mattered is
 * gone too. It speaks only when the COMPOSITION changes -- a different number
 * of patients, or a different count at some urgency.
 *
 * A new CRITICAL leads the sentence. If two things changed, the one that
 * decides who is seen next is the one heard first.
 */
function summarise(rows: QueueEntry[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const level of URGENCY) counts[level] = 0;
  for (const row of rows) {
    counts[row.urgency_level] = (counts[row.urgency_level] ?? 0) + 1;
  }
  return counts;
}

function sentence(
  counts: Record<string, number>,
  previous: Record<string, number> | null,
  total: number,
): string {
  const parts: string[] = [];

  // Lead with a new critical arrival, whatever else moved.
  const criticalNow = counts["CRITICAL"] ?? 0;
  const criticalBefore = previous?.["CRITICAL"] ?? 0;
  if (criticalNow > criticalBefore) {
    const arrived = criticalNow - criticalBefore;
    parts.push(
      arrived === 1
        ? "New critical patient in the queue."
        : `${arrived} new critical patients in the queue.`,
    );
  }

  parts.push(
    total === 0
      ? "Queue updated. Nobody is waiting."
      : `Queue updated. ${total} waiting:` +
          ` ${counts["CRITICAL"] ?? 0} critical,` +
          ` ${counts["URGENT"] ?? 0} urgent,` +
          ` ${counts["ROUTINE"] ?? 0} routine.`,
  );
  return parts.join(" ");
}

export function QueueAnnouncer({ rows }: { rows: QueueEntry[] }) {
  const previous = useRef<Record<string, number> | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const counts = summarise(rows);

    // The first render is not a change. The user is about to read the board
    // anyway; announcing it here would talk over them doing so.
    if (previous.current === null) {
      previous.current = counts;
      return;
    }

    const changed = URGENCY.some(
      (level) => counts[level] !== previous.current?.[level],
    );
    if (!changed) return;

    const next = sentence(counts, previous.current, rows.length);
    previous.current = counts;
    // Re-assert even when the text repeats: an identical string assigned to a
    // live region is not re-announced by most screen readers, so a queue that
    // went 3 -> 4 -> 3 would fall silent on the way back. The zero-width
    // space makes consecutive messages distinct without being spoken.
    setMessage((current) => (current === next ? `${next}​` : next));
  }, [rows]);

  return (
    // `polite` and not `assertive`, including for a critical arrival.
    // `assertive` interrupts mid-word, and the person it interrupts is usually
    // reading this same queue. Polite speaks at the next pause, which on a
    // 5-second poll is a delay of seconds, not minutes.
    <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">
      {message}
    </p>
  );
}
