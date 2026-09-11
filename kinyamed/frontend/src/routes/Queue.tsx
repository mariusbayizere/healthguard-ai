import { useQueue } from "@/api/hooks";
import { QueueTable } from "@/components/QueueTable";
import { Alert, Button, Card } from "@/components/ui";

export function Queue() {
  const queue = useQueue();
  const rows = queue.data ?? [];
  const counts = rows.reduce<Record<string, number>>((acc, r) => {
    acc[r.urgency_level] = (acc[r.urgency_level] ?? 0) + 1;
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
      {/* Three across even at 360px. Stacked, these three tiles cost about 400px
          of a phone screen before the first patient appears -- the counts
          pushing the thing they summarise below the fold. */}
      <div className="grid max-w-xl grid-cols-3 gap-2 sm:gap-4">
        {(["CRITICAL", "URGENT", "ROUTINE"] as const).map((level) => (
          <div
            key={level}
            className={[
              "rounded-lg border border-ink-200 border-l-4 bg-white px-3 py-3 shadow-card sm:px-5 sm:py-4",
              level === "CRITICAL" ? "border-l-critical"
                : level === "URGENT" ? "border-l-urgent" : "border-l-routine",
            ].join(" ")}
          >
            <div className="text-xs font-semibold uppercase tracking-wide text-ink-600">
              {level}
            </div>
            <div className="tnum mt-1 text-2xl font-semibold text-ink-900">
              {counts[level] ?? 0}
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
          Ordered by clinical priority, then arrival. The wait estimate is
          derived from queue depth and a capacity constant; it is not a
          commitment and is not sent to the patient.
        </p>
      </Card>
    </div>
  );
}
