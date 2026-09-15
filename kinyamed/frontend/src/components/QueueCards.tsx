import type { ReactNode } from "react";
import type { BandGroup } from "@/api/queueBand";
import type { QueueEntry } from "@/api/types";
import { BAND_EDGE, BAND_HEADER, RowUrgency } from "./QueueBandParts";

/** The queue on a phone. A LIST OF PATIENTS, not a narrowed table.
 *
 * This is a separate component rather than a breakpoint on the table because
 * it is a different thing, not a smaller one. A table answers "compare these
 * rows across these columns" -- the nurses'-station question. A phone in a
 * corridor asks "who is next, and how bad", one patient at a time, and the
 * answer is a card with a reading order: acuity, then identity, then detail.
 *
 * The columns are not narrowed, dropped or scrolled sideways. They are
 * re-composed: urgency and queue number lead on one line, the name gets its
 * own line at full width so long Rwandan names do not wrap mid-word into a
 * 90px column, and the remaining facts become a definition list that wraps
 * naturally instead of a row that overflows.
 *
 * HIERARCHY. The badge leads. An earlier build set the queue number at 36px
 * against a 12px badge, so the largest thing on every row was the ticket and
 * not the acuity -- the whole brief inverted.
 *
 * BANDS (item 2d). Patients are grouped under a heading per band, so a case the
 * model could not classify sits in its own group above URGENT and ROUTINE
 * rather than as a flag on a card at the bottom of the list.
 */
function waitText(minutes: number | null): string {
  return minutes == null ? "—" : `~${minutes} min`;
}

export function QueueCards({
  groups,
  renderActions,
}: {
  groups: BandGroup[];
  // `| undefined` explicitly: QueueTable forwards its own optional prop
  // straight through, and `exactOptionalPropertyTypes` distinguishes an
  // absent property from one explicitly set to undefined.
  renderActions?: ((entry: QueueEntry) => ReactNode) | undefined;
}) {
  return (
    <div className="space-y-6">
      {groups.map(({ key, band, label, rows }) => (
        <div key={key} role="group" aria-labelledby={`band-${key}`} data-band={band}>
          <h3 id={`band-${key}`} className={BAND_HEADER[band]}>
            {label} <span className="tnum">({rows.length})</span>
          </h3>
          <ul className="mt-3 space-y-3">
            {rows.map((row) => (
              <li
                key={row.id}
                className={`rounded border border-ink-200 border-l-4 p-4 ${BAND_EDGE[band]}`}
              >
                <div className="flex flex-wrap items-center gap-3">
                  <RowUrgency row={row} band={band} />
                  <span className="tnum text-xl font-semibold text-ink-900">
                    #{row.queue_number}
                  </span>
                </div>
                <p className="mt-2 text-base font-medium text-ink-900">
                  {row.patient_name ?? `Patient #${row.patient_id ?? "?"}`}
                </p>
                <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-ink-700">
                  <div className="flex gap-1">
                    <dt className="text-ink-600">Status:</dt>
                    <dd>{row.status.replace("_", " ").toLowerCase()}</dd>
                  </div>
                  <div className="flex gap-1">
                    <dt className="text-ink-600">Wait:</dt>
                    <dd className="tnum">{waitText(row.estimated_wait)}</dd>
                  </div>
                  <div className="flex gap-1">
                    <dt className="text-ink-600">Doctor:</dt>
                    <dd>{row.doctor_name ?? "unassigned"}</dd>
                  </div>
                </dl>
                {renderActions && <div className="mt-3">{renderActions(row)}</div>}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
