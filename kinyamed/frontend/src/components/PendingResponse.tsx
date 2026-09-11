import type { TriageResult } from "@/api/types";

/** The patient-facing message, or an explicit statement that there isn't one.
 *
 * THIS COMPONENT EXISTS TO MAKE AN ABSENCE VISIBLE. The sentence a patient
 * reads is speaker-authored or it does not exist; when it does not, this shows
 * the reason to STAFF, in English, styled as a notice rather than as content.
 *
 * It must never be mistaken for advice, so it does not use the calm green of a
 * real response and it does not centre a friendly message. A placeholder that
 * reads as real is worse than a blank, because everyone downstream -- a
 * reviewer, a screenshot, a demo -- treats it as working.
 */
/** An unfilled `{slot}` must never reach a patient.
 *
 * The API already guarantees this -- the SMS composer refuses to send text
 * containing one -- so this is defence in depth rather than the primary check.
 * It is here because the cost of the guarantee moving or regressing upstream is
 * a patient reading "Muraho {name}", and the cost of the check is one regex.
 */
const UNFILLED_SLOT = /\{[a-z_]+\}/i;

export function PendingResponse({ result }: { result: TriageResult }) {
  const malformed =
    result.patient_response != null && UNFILLED_SLOT.test(result.patient_response);

  if (malformed) {
    return (
      <div role="status" className="border-l-4 border-critical bg-critical-soft px-4 py-3 rounded-r">
        <p className="font-semibold text-critical">Message withheld</p>
        <p className="mt-1 text-sm text-ink-700">
          The response template for this language contains an unfilled
          placeholder and has not been shown. Report this — a template reached
          the patient path without being completed.
        </p>
      </div>
    );
  }

  if (!result.response_pending && result.patient_response) {
    return (
      <figure className="border-l-4 border-routine bg-routine-soft px-4 py-3 rounded-r">
        <blockquote className="text-lg text-ink-900">
          {result.patient_response}
        </blockquote>
        <figcaption className="mt-2 text-xs text-ink-600">
          Speaker-authored template
          {result.language_detected ? ` · ${result.language_detected}` : ""}
        </figcaption>
      </figure>
    );
  }

  return (
    <div
      role="status"
      className="border-l-4 border-urgent bg-urgent-soft px-4 py-3 rounded-r"
    >
      <p className="font-semibold text-urgent">No message available for this patient</p>
      <p className="mt-1 text-sm text-ink-700">
        {result.response_pending_reason ??
          "No speaker-authored response exists for this language."}
      </p>
      <p className="mt-2 text-sm text-ink-700">
        Tell the patient their urgency and queue number in person. Nothing has
        been written in this language, and the system will not invent it.
      </p>
    </div>
  );
}
