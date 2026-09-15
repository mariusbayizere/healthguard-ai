import { useAssignDoctor, useOnDutyDoctors, useQueue, useSetQueueStatus } from "@/api/hooks";
import { QueueTable } from "@/components/QueueTable";
import { Alert, Button, Card, inputClass } from "@/components/ui";

export function Doctor() {
  const queue = useQueue();
  const doctors = useOnDutyDoctors();
  const setStatus = useSetQueueStatus();
  const assign = useAssignDoctor();
  const error = queue.error ?? setStatus.error ?? assign.error;

  return (
    <div className="space-y-6">
      {error && <Alert>{(error as Error).message}</Alert>}
      <Card
        title="Next to be seen"
        actions={
          <span className="text-xs text-ink-600">
            {(doctors.data ?? []).length} on duty
          </span>
        }
      >
        <QueueTable
          rows={queue.data ?? []}
          isLoading={queue.isLoading}
          /* Cards until 1024px. With the Actions column this table overflowed
             the viewport at exactly 768 -- the tablet width this runs on. */
          tableFrom="lg"
          renderActions={(entry) => (
            /* Stacked and full-width on phones: three controls side by side
               in a card is a mis-tap waiting to happen when the outcome is a
               patient's queue status. */
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
              <select
                aria-label={`Assign a doctor to queue number ${entry.queue_number}`}
                className={`${inputClass} sm:w-auto`}
                value=""
                onChange={(e) =>
                  e.target.value &&
                  assign.mutate({ id: entry.id, doctorId: Number(e.target.value) })
                }
              >
                <option value="">Assign…</option>
                {(doctors.data ?? []).map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
              <Button
                onClick={() => setStatus.mutate({ id: entry.id, status: "IN_PROGRESS" })}
              >
                Seeing now
              </Button>
              {/* Completing removes the patient from the board and there is no
                  undo in this UI, so it asks. A mis-tap here loses someone's
                  place in a queue. */}
              <Button
                variant="danger"
                onClick={() => {
                  if (
                    window.confirm(
                      `Mark queue number ${entry.queue_number} as done? ` +
                        "They will be removed from the waiting list.",
                    )
                  ) {
                    setStatus.mutate({ id: entry.id, status: "DONE" });
                  }
                }}
              >
                Done
              </Button>
            </div>
          )}
        />
        <p className="mt-4 border-t border-dashed border-ink-200 pt-3 text-xs text-ink-600">
          The urgency shown is the model's suggestion. It has not been approved
          by a clinician and the model does not meet its own acceptance
          threshold — treat this as a suggested order, not a clinical decision.
        </p>
      </Card>
    </div>
  );
}
