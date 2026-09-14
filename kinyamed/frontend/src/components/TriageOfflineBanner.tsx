import { useEffect, useState } from "react";
import { isTriageModelLoaded } from "@/api/readiness";

/** How often the banner re-checks. The model only changes on a restart. */
export const READINESS_POLL_MS = 15_000;

/** A persistent, non-dismissible bar on every screen while automated triage is off.
 *
 * Mounted above the router (`main.tsx`), so it is on the doctor board, the
 * queue and the intake form alike, and on the sign-in screen: whoever is
 * looking at this system should know it is not triaging. It has no close
 * control and no timeout; it goes only when the API reports `model: true`.
 * Nothing renders until the first probe answers, so a working system does not
 * flash a false alarm on load.
 */
export function TriageOfflineBanner() {
  const [loaded, setLoaded] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const result = await isTriageModelLoaded();
      if (!cancelled) setLoaded(result);
    };
    void check();
    const interval = setInterval(() => void check(), READINESS_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (loaded !== false) return null;
  return (
    <div
      role="alert"
      className="sticky top-0 z-50 border-b-4 border-urgent bg-urgent-soft px-4 py-3 text-center text-base font-semibold text-ink-900"
    >
      Automated triage offline — triage manually
    </div>
  );
}
