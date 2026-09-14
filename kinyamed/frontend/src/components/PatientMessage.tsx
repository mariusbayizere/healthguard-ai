/** The receipt the API wrote for the patient, shown to the staff member.
 *
 * It is the SAME for every patient whatever the model concluded: report
 * received, queue place, and a generic escalation line. The model's urgency is
 * a hint for clinicians and is never turned into advice here -- a model at
 * accuracy 0.71 on a nine-sentence test set is not fit to tell anyone their
 * condition can wait. The caption says so, so nobody reads the receipt as a
 * triage result.
 */

/** An unfilled `{slot}` must never reach a patient. Defence in depth. */
const UNFILLED_SLOT = /\{[a-z_]+\}/i;

export function PatientMessage({ text, language }: { text: string; language: string }) {
  if (UNFILLED_SLOT.test(text)) {
    return (
      <div role="status" className="rounded-r border-l-4 border-critical bg-critical-soft px-4 py-3">
        <p className="font-semibold text-critical">Message withheld</p>
        <p className="mt-1 text-sm text-ink-700">
          The receipt contains an unfilled placeholder and has not been shown.
          Report this.
        </p>
      </div>
    );
  }

  return (
    <figure className="rounded-r border-l-4 border-ink-500 bg-ink-100 px-4 py-3">
      <blockquote className="text-lg text-ink-900">{text}</blockquote>
      <figcaption className="mt-2 text-xs text-ink-600">
        The same for every patient — not a triage result.
        {language === "english" ? " English only: no reviewed translation exists yet." : ""}
      </figcaption>
    </figure>
  );
}
