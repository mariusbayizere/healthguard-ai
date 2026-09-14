import { useState, type FormEvent } from "react";
import { ApiError } from "@/api/client";
import { usePatients, useSubmitTriage } from "@/api/hooks";
import { readTriageReview } from "@/api/triageResponse";
import { PatientMessage } from "@/components/PatientMessage";
import { TriageOfflineAlert } from "@/components/TriageOfflineAlert";
import { UrgencyBadge } from "@/components/UrgencyBadge";
import { Alert, Button, Card, Field, inputClass } from "@/components/ui";

export function Triage() {
  const patients = usePatients();
  const submit = useSubmitTriage();
  const [patientId, setPatientId] = useState("");
  const [symptoms, setSymptoms] = useState("");
  // The fail-closed instruction outlives the mutation state on purpose: a retry
  // resets `submit.error`, and the instruction must not vanish while it runs.
  // Only a successful assessment clears it.
  const [offlineMessage, setOfflineMessage] = useState<string | null>(null);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit.mutate(
      { patient_id: Number(patientId), symptoms_input: symptoms },
      {
        onSuccess: () => setOfflineMessage(null),
        onError: (error) => {
          if (error instanceof ApiError && error.code === "TRIAGE_MODEL_UNAVAILABLE") {
            setOfflineMessage(error.message);
          }
        },
      },
    );
  }

  const result = submit.data;
  const review = readTriageReview(result);
  const offline = offlineMessage !== null;

  return (
    <div className="space-y-6">
      {offline && <TriageOfflineAlert message={offlineMessage} />}
      <Card title="New assessment">
        <form onSubmit={onSubmit} className="space-y-5">
          {submit.isError && !offline && <Alert>{(submit.error as Error).message}</Alert>}

          <Field label="Patient">
            <select
              className={inputClass}
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              required
            >
              <option value="">
                {patients.isLoading
                  ? "Loading patients…"
                  : (patients.data ?? []).length === 0
                    ? "No patients registered — register one first"
                    : "Select a patient…"}
              </option>
              {(patients.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}{p.phone ? ` · ${p.phone}` : ""}
                </option>
              ))}
            </select>
          </Field>

          <Field
            label="What the patient says"
            hint="Record their own words, not a summary. The classifier was trained on patient-voice descriptions, and a clinical paraphrase is a different kind of text."
          >
            <textarea
              className={`${inputClass} min-h-32 resize-y`}
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              required
            />
          </Field>

          <Button type="submit" disabled={submit.isPending || !patientId}>
            {submit.isPending ? "Assessing…" : "Assess and add to queue"}
          </Button>
        </form>
      </Card>

      {result && !offline && (
        <Card title="Result">
          <section aria-labelledby="hint-title">
            <h3 id="hint-title" className="mb-1 text-sm font-semibold uppercase tracking-wide text-ink-600">
              Prioritisation hint — clinicians only
            </h3>
            <p className="mb-4 text-sm text-ink-700">
              {review?.clinician_hint_notice ??
                "The urgency below is a prioritisation hint for clinicians. It is not advice for the patient."}
            </p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:flex sm:flex-wrap sm:gap-10">
              <div>
                <div className="text-xs uppercase tracking-wide text-ink-600">Urgency hint</div>
                <div className="mt-1"><UrgencyBadge level={result.urgency_level} /></div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-ink-600">Queue number</div>
                <div className="tnum mt-1 text-queue font-semibold">{result.queue_number}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-ink-600">Position</div>
                <div className="tnum mt-1 text-xl font-semibold">{result.queue_position}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-ink-600">Language</div>
                <div className="mt-1 text-xl">{result.language_detected ?? "—"}</div>
              </div>
            </div>

            {review?.requires_human_review && (
              <div
                role="status"
                aria-labelledby="review-title"
                className="mt-5 rounded-r border-l-4 border-urgent bg-urgent-soft px-4 py-3"
              >
                <p id="review-title" className="font-semibold text-ink-900">
                  Needs clinician review
                </p>
                <p className="mt-1 text-sm text-ink-800">{review.review_reason}</p>
              </div>
            )}

            {/* The number is a softmax maximum from an uncalibrated model. Shown
                because hiding it would be worse, labelled because rendering it as
                a percentage invites it to be read as a probability. */}
            <p className="mt-4 text-xs text-ink-600">
              {result.confidence_score == null
                ? "No confidence score returned."
                : `Model score ${result.confidence_score.toFixed(3)} — an uncalibrated
                   softmax value, not a probability. It does not mean the model is
                   ${Math.round(result.confidence_score * 100)}% likely to be right.`}
            </p>
          </section>

          <section aria-labelledby="message-title" className="mt-8 border-t border-dashed border-ink-200 pt-6">
            <h3 id="message-title" className="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-600">
              Message for the patient
            </h3>
            {review ? (
              <PatientMessage text={review.patient_response} language={review.patient_message_language} />
            ) : (
              <p role="status" className="text-sm text-ink-700">
                The API returned no patient receipt. Do not improvise one; give the
                patient their queue number in person.
              </p>
            )}
          </section>
        </Card>
      )}
    </div>
  );
}
