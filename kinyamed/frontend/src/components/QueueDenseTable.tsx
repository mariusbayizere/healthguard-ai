import type { ReactNode } from "react";
import type { QueueEntry } from "@/api/types";
import { UrgencyBadge } from "./UrgencyBadge";

/** The queue at a nurses' station. A real table, only where one fits.
 *
 * Separate from `QueueCards` because it answers a different question: scanning
 * six facts across many patients at once, which is what a grid is for and what
 * a stack of cards is bad at. Neither is a responsive variant of the other.
 *
 * This component never renders below its breakpoint. `QueueTable` chooses, so
 * there is no `hidden` class here and no possibility of a table being present
 * but invisible on a phone.
 */
const EDGE: Record<string, string> = {
  CRITICAL: "border-l-critical bg-critical-soft/40",
  URGENT: "border-l-urgent bg-urgent-soft/40",
  ROUTINE: "border-l-routine bg-white",
};

function waitText(minutes: number | null): string {
  return minutes == null ? "—" : `~${minutes} min`;
}

export function QueueDenseTable({
  rows,
  renderActions,
}: {
  rows: QueueEntry[];
  // `| undefined` explicitly: QueueTable forwards its own optional prop
  // straight through, and `exactOptionalPropertyTypes` distinguishes an
  // absent property from one explicitly set to undefined.
  renderActions?: ((entry: QueueEntry) => ReactNode) | undefined;
}) {
  return (
    <table className="w-full border-collapse">
      <caption className="sr-only">Patients waiting, most urgent first</caption>
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
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.id}
            className={`border-b border-l-4 border-ink-200 ${
              EDGE[row.urgency_level] ?? "border-l-ink-300"
            }`}
          >
            <td className="py-3 pl-4 pr-3 align-middle">
              <UrgencyBadge level={row.urgency_level} />
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
    </table>
  );
}
