import { useQueue } from "@/api/hooks";
import { bandOf } from "@/api/queueBand";
import { QUEUE_BAND, type QueueBand } from "@/api/queueBand.gen";
import { QueueTable } from "@/components/QueueTable";
import { Alert, Button, Card } from "@/components/ui";

const TILE_EDGE: Record<QueueBand, string> = {
  CRITICAL: "border-l-critical",
  NEEDS_REVIEW: "border-l-ink-900",
  URGENT: "border-l-urgent",
  ROUTINE: "border-l-routine",
};

export function Queue() {
  const queue = useQueue();
  const rows = queue.data ?? [];
  // Counted by band, like the list below: a flagged ROUTINE counted as routine
  // would hide it in the summary exactly as it used to be hidden in the list.
  const counts = rows.reduce<Record<string, number>>((acc, r) => {
    const band = bandOf(r);
    acc[band] = (acc[band] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {queue.isError && (
        // A dropped connection and a rejected request need different actions
        // from the reader, so they are not rendered identically. See
        // docs/frontend-limitations.md on intermittent connectivity.
        <Alert
          kind={(queue.error as { status?: number }).status === 0 ? "offline" : "error"}
          action={
            <Button variant="quiet" onClick={() => void queue.refetch()}>
              Retry
            </Button>
          }
        >
          {(queue.error as Error).message}
        </Alert>
      )}

      {/* The counts are the half-second read. A nurse walking past should get
          "two critical" without focusing on the table at all. */}
      {/* Two by two on a phone, four across from 640px. Stacked, the tiles cost
          most of a phone screen before the first patient appears -- the counts
          pushing the thing they summarise below the fold. */}
      <div className="grid max-w-2xl grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-4">
        {QUEUE_BAND.map((band) => (
          <div
            key={band}
            data-tile={band}
            className={`rounded-lg border border-ink-200 border-l-4 bg-white px-3 py-3 shadow-card sm:px-5 sm:py-4 ${TILE_EDGE[band]}`}
          >
            <div className="text-xs font-semibold uppercase tracking-wide text-ink-600">
              {band.replace("_", " ")}
            </div>
            <div className="tnum mt-1 text-2xl font-semibold text-ink-900">
              {counts[band] ?? 0}
            </div>
          </div>
        ))}
      </div>

      <Card
        title="Waiting"
        actions={
          <span className="text-xs text-ink-600">
            {queue.isFetching ? "Refreshing…" : "Updates every 5 seconds"}
          </span>
        }
      >
        <QueueTable rows={rows} isLoading={queue.isLoading} />
        <p className="mt-4 border-t border-dashed border-ink-200 pt-3 text-xs text-ink-600">
          Ordered by band -- critical, then cases the model could not classify,
          then urgent, then routine -- and by arrival within each. The wait estimate is
          derived from queue depth and a capacity constant; it is not a
          commitment and is not sent to the patient.
        </p>
      </Card>
    </div>
  );
}
