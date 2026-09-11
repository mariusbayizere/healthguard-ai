import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PendingResponse } from "../PendingResponse";
import type { TriageResult } from "@/api/types";

const base: TriageResult = {
  triage_id: 1, patient_id: 1, patient_name: "Uwimana",
  urgency_level: "CRITICAL", possible_conditions: null, confidence_score: 0.51,
  ai_response_rw: null, patient_response: null, response_pending: true,
  response_pending_reason: "no english template is authored",
  language_detected: "english", queue_number: 3, queue_position: 1,
  estimated_wait: null, created_at: "2026-09-09T00:00:00Z", queue_id: 11,
};

describe("PendingResponse", () => {
  it("shows the reason, and no advice, when nothing is authored", () => {
    render(<PendingResponse result={base} />);
    expect(screen.getByText(/no message available/i)).toBeInTheDocument();
    expect(screen.getByText(/no english template is authored/i)).toBeInTheDocument();
    // The invariant: a pending state must not read as guidance to the patient.
    expect(screen.queryByRole("blockquote")).not.toBeInTheDocument();
  });

  it("renders speaker-authored text when it exists", () => {
    render(
      <PendingResponse
        result={{
          ...base,
          response_pending: false,
          response_pending_reason: null,
          patient_response: "Jya kwa muganga ubu bwangu, ntutegereze.",
          language_detected: "kinyarwanda",
        }}
      />,
    );
    expect(screen.getByText(/jya kwa muganga/i)).toBeInTheDocument();
    expect(screen.queryByText(/no message available/i)).not.toBeInTheDocument();
  });

  it("withholds a message containing an unfilled slot", () => {
    render(
      <PendingResponse
        result={{ ...base, response_pending: false, patient_response: "Muraho {name}." }}
      />,
    );
    // Defence in depth. The API already refuses to emit an unfilled slot; if
    // that ever regresses, a patient must still not read "Muraho {name}".
    expect(screen.getByText(/message withheld/i)).toBeInTheDocument();
    expect(screen.queryByText(/muraho/i)).not.toBeInTheDocument();
  });
});
