import type { ReactNode } from "react";
import type { QueueEntry } from "@/api/types";
import { useMediaQuery } from "@/lib/useMediaQuery";
import { QueueAnnouncer } from "./QueueAnnouncer";
import { QueueCards } from "./QueueCards";
import { QueueDenseTable } from "./QueueDenseTable";
import { Empty, Skeleton } from "./ui";

/** Chooses between two DIFFERENT components, and renders exactly one.
 *
 * A table does not work on a phone, and the fix is not a narrower table. It is
 * `QueueCards`: a list of patients composed for one-at-a-time reading, with
 * its own hierarchy. `QueueDenseTable` is the nurses'-station grid. Neither is
 * a responsive variant of the other, so neither is written as breakpoint
 * classes on the other.
 *
 * WHY A MEDIA QUERY AND NOT `hidden md:block`. The earlier version rendered
 * both layouts and hid one with CSS. That is invisible in a screenshot and
 * expensive in a browser: every patient built a card AND a table row, so a
 * 40-patient queue reconciled ~500 elements on each 5-second poll to paint
 * half of them, on the cheapest Android in the building. Choosing in JS means
 * one exists.
 *
 * It also removes a correctness trap. With CSS hiding, `display:none` is the
 * only thing keeping the hidden copy out of the accessibility tree; any
 * stacking, printing or forced-colours context that neutralises it announces
 * every patient twice. Now there is only one copy to announce.
 *
 * BREAKPOINT IS PER-VIEW. The read-only queue fits six columns from 768px. The
 * doctor board adds an Actions column holding a select and two buttons, and at
 * 768px its min-content width exceeded the viewport -- measured at scrollWidth
 * 781 against clientWidth 768, with the Assign dropdown cut off at the right
 * edge. That board stays in cards until 1024px.
 */
const BREAKPOINT = {
  md: "(min-width: 768px)",
  lg: "(min-width: 1024px)",
} as const;

export function QueueTable({
  rows,
  isLoading = false,
  renderActions,
  tableFrom = "md",
}: {
  rows: QueueEntry[];
  isLoading?: boolean;
  renderActions?: (entry: QueueEntry) => ReactNode;
  /** Width at which the dense table replaces the cards. Views carrying an
   *  Actions column need `lg`; see the note above. */
  tableFrom?: keyof typeof BREAKPOINT;
}) {
  const dense = useMediaQuery(BREAKPOINT[tableFrom]);

  // Order matters: loading is checked FIRST. Reporting an empty waiting room
  // before the first fetch returns is a false clinical statement, not a
  // cosmetic flaw.
  if (isLoading) return <Skeleton />;

  // The announcer renders ABOVE the empty branch, not inside the populated
  // one. Below it, the last patient leaving the queue would UNMOUNT the live
  // region -- so "nobody is waiting" could never be spoken, which is the one
  // transition a nurse most needs told rather than discovered. It paints
  // nothing either way.
  return (
    <>
      <QueueAnnouncer rows={rows} />
      {rows.length === 0 ? (
        <Empty title="Nobody is waiting">
          Submitted assessments appear here immediately. If you expected
          patients, check the connection indicator above.
        </Empty>
      ) : dense ? (
        <QueueDenseTable rows={rows} renderActions={renderActions} />
      ) : (
        <QueueCards rows={rows} renderActions={renderActions} />
      )}
    </>
  );
}
