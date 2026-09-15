import type { ReactNode } from "react";
import type { BandGroup } from "@/api/queueBand";
import type { QueueEntry } from "@/api/types";
import { BAND_EDGE, BAND_HEADER, RowUrgency } from "./QueueBandParts";

/** The queue at a nurses' station. A real table, only where one fits.
 *
 * Separate from `QueueCards` because it answers a different question: scanning
 * six facts across many patients at once, which is what a grid is for and what
 * a stack of cards is bad at. Neither is a responsive variant of the other.
 *
 * This component never renders below its breakpoint. `QueueTable` chooses, so
 * there is no `hidden` class here and no possibility of a table being present
 * but invisible on a phone.
 *
 * BANDS (item 2d). One `<tbody>` per band, opened by a row-group header, so the
 * band is a heading over its rows for a screen reader as well as on screen.
 */
function waitText(minutes: number | null): string {
  return minutes == null ? "—" : `~${minutes} min`;
}

export function QueueDenseTable({
  groups,
  renderActions,
}: {
  groups: BandGroup[];
  // `| undefined` explicitly: QueueTable forwards its own optional prop
  // straight through, and `exactOptionalPropertyTypes` distinguishes an
  // absent property from one explicitly set to undefined.
  renderActions?: ((entry: QueueEntry) => ReactNode) | undefined;
}) {
  const columns = renderActions ? 7 : 6;
  return (
    <table className="w-full border-collapse">
      <caption className="sr-only">
        Patients waiting, in bands: critical, cases the model could not classify, urgent,
        routine; arrival order within each
      </caption>
      <thead>
        <tr className="text-left text-xs uppercase tracking-wide text-ink-600">
          <th scope="col" className="py-2 pl-4 pr-3 font-semibold">Urgency</th>
          <th scope="col" className="py-2 px-3 font-semibold">No.</th>
          <th scope="col" className="py-2 px-3 font-semibold">Patient</th>
          <th scope="col" className="py-2 px-3 font-semibold">Status</th>
          <th scope="col" className="py-2 px-3 font-semibold">Wait</th>
          <th scope="col" className="py-2 px-3 font-semibold">Doctor</th>
          {renderActions && (
            <th scope="col" className="py-2 px-3 font-semibold">Actions</th>
          )}
        </tr>
      </thead>
      {groups.map(({ key, band, label, rows }) => (
        <tbody key={key} data-band={band}>
          <tr>
            <th scope="rowgroup" colSpan={columns} className="px-0 pb-2 pt-5 text-left">
              <span className={`block ${BAND_HEADER[band]}`}>
                {label} <span className="tnum">({rows.length})</span>
              </span>
            </th>
          </tr>
          {rows.map((row) => (
            <tr
              key={row.id}
              className={`border-b border-l-4 border-ink-200 ${BAND_EDGE[band]}`}
            >
              <td className="py-3 pl-4 pr-3 align-middle">
                <RowUrgency row={row} band={band} />
              </td>
              <td className="tnum py-3 px-3 align-middle text-lg font-semibold text-ink-900">
                {row.queue_number}
              </td>
              <td className="py-3 px-3 align-middle font-medium text-ink-900">
                {row.patient_name ?? `Patient #${row.patient_id ?? "?"}`}
              </td>
              <td className="py-3 px-3 align-middle text-sm text-ink-700">
                {row.status.replace("_", " ").toLowerCase()}
              </td>
              <td className="tnum py-3 px-3 align-middle text-sm text-ink-700">
                {waitText(row.estimated_wait)}
              </td>
              <td className="py-3 px-3 align-middle text-sm text-ink-700">
                {row.doctor_name ?? <span className="text-ink-600">unassigned</span>}
              </td>
              {renderActions && (
                <td className="py-3 px-3 align-middle">{renderActions(row)}</td>
              )}
            </tr>
          ))}
        </tbody>
      ))}
    </table>
  );
}
