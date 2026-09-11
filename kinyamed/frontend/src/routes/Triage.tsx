import { useState, type FormEvent } from "react";
import { usePatients, useSubmitTriage } from "@/api/hooks";
import { PendingResponse } from "@/components/PendingResponse";
import { UrgencyBadge } from "@/components/UrgencyBadge";
import { Alert, Button, Card, Field, inputClass } from "@/components/ui";

export function Triage() {
  const patients = usePatients();
  const submit = useSubmitTriage();
  const [patientId, setPatientId] = useState("");
  const [symptoms, setSymptoms] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit.mutate({ patient_id: Number(patientId), symptoms_input: symptoms });
  }

  const result = submit.data;

  return (
    <div className="space-y-6">
      <Card title="New assessment">
        <form onSubmit={onSubmit} className="space-y-5">
          {submit.isError && <Alert>{(submit.error as Error).message}</Alert>}

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

      {result && (
        <Card title="Result">
          <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:flex sm:flex-wrap sm:gap-10">
            <div>
              <div className="text-xs uppercase tracking-wide text-ink-600">Urgency</div>
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

          <h3 className="mt-8 mb-2 text-sm font-semibold uppercase tracking-wide text-ink-600">
            Message for the patient
          </h3>
          <PendingResponse result={result} />

          {/* The number is a softmax maximum from an uncalibrated model. Shown
              because hiding it would be worse, labelled because rendering it as
              a percentage invites it to be read as a probability. */}
          <p className="mt-6 border-t border-dashed border-ink-200 pt-3 text-xs text-ink-600">
            {result.confidence_score == null
              ? "No confidence score returned."
              : `Model score ${result.confidence_score.toFixed(3)} — an uncalibrated
                 softmax value, not a probability. It does not mean the model is
                 ${Math.round(result.confidence_score * 100)}% likely to be right.`}
          </p>
        </Card>
      )}
    </div>
  );
}
