import { useEffect, useRef } from "react";

/** The API refused to triage because no trained model could classify.
 *
 * BLOCKING AND NON-DISMISSIBLE, ON PURPOSE. It is not a toast: it has no close
 * control and no timeout, and the intake form keeps it until a later
 * assessment succeeds. It is not a modal either: a modal nobody can close
 * would also lock the nurse out of the queue board, which is where manual
 * triage continues. Focus moves to it so a keyboard or screen-reader user
 * lands on the instruction, not on the submit button they just pressed.
 *
 * `message` is the API's own text, shown verbatim.
 */
export function TriageOfflineAlert({ message }: { message: string }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => ref.current?.focus(), []);

  return (
    <section
      ref={ref}
      role="alert"
      aria-labelledby="triage-offline-title"
      tabIndex={-1}
      className="rounded-lg border-4 border-urgent bg-urgent-soft px-5 py-5 outline-none sm:px-6"
    >
      <h2 id="triage-offline-title" className="text-xl font-semibold text-ink-900">
        Automated triage is offline
      </h2>
      <p className="mt-2 text-base text-ink-900">{message}</p>
    </section>
  );
}
