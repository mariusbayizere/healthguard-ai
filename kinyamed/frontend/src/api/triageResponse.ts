/** The parts of POST /triage's response that item 2 added.
 *
 * `api/types.ts` still describes the previous response (retired fields
 * `patient_response | null`, `response_pending`, `ai_response_rw`), and it holds
 * uncommitted work, so these fields are read here, checked at runtime, rather
 * than typed there. Fold this into `types.ts` when that file is committed.
 */
export interface TriageReview {
  requires_human_review: boolean;
  review_reason: string | null;
  clinician_hint_notice: string;
  patient_response: string;
  patient_message_language: string;
}

export function readTriageReview(data: unknown): TriageReview | null {
  if (!data || typeof data !== "object") return null;
  const d = data as Record<string, unknown>;
  if (
    typeof d["requires_human_review"] !== "boolean" ||
    typeof d["clinician_hint_notice"] !== "string" ||
    typeof d["patient_response"] !== "string" ||
    typeof d["patient_message_language"] !== "string"
  ) {
    return null;
  }
  return {
    requires_human_review: d["requires_human_review"],
    review_reason: typeof d["review_reason"] === "string" ? d["review_reason"] : null,
    clinician_hint_notice: d["clinician_hint_notice"],
    patient_response: d["patient_response"],
    patient_message_language: d["patient_message_language"],
  };
}
