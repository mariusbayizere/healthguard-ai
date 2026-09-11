/** Automated accessibility checks over every view and state.
 *
 * AUDIT 2.4. The accessibility claim in this project was reasoned, not
 * audited: urgency carried in text as well as colour, 44px targets, distinct
 * states -- all decided at design time and none of it verified by anything
 * that runs. Two of those turned out to be false in the shipped build (the
 * targets were 20px, and "unassigned" failed AA), which is what a design
 * intention with no test behind it is worth.
 *
 * axe is not a substitute for a screen-reader session and does not claim to
 * catch most issues. It catches the mechanical ones -- unlabelled controls,
 * broken heading order, list semantics, ARIA that points at nothing, colour
 * contrast it can compute -- and those are exactly the ones that regress
 * silently when a component is refactored.
 *
 * The colour-contrast rule is DISABLED here, and that is not a way of avoiding
 * it. jsdom applies no stylesheet and implements no canvas, so axe cannot read
 * a rendered colour at all -- left on, the rule cannot pass or fail, it just
 * throws canvas errors on every assertion and trains the reader to ignore the
 * output. The contrast guarantee lives in `contrast.test.ts`, which computes
 * WCAG ratios from the palette itself. That test is what caught `ink-500` on
 * white at 3.94:1.
 */
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import type { AxeResults } from "axe-core";

import { QueueTable } from "@/components/QueueTable";
import { PendingResponse } from "@/components/PendingResponse";
import { UrgencyBadge } from "@/components/UrgencyBadge";
import { Alert, Button, Card, Empty, Field, Skeleton, inputClass } from "@/components/ui";
import { setViewportMatches } from "@/test/setup";
import type { QueueEntry, TriageResult } from "@/api/types";

const ROWS: QueueEntry[] = [
  { id: 1, queue_number: 12, urgency_level: "CRITICAL", status: "WAITING",
    patient_id: 1, patient_name: "Uwimana Claudine", doctor_name: null,
    estimated_wait: 0 },
  { id: 2, queue_number: 9, urgency_level: "URGENT", status: "IN_PROGRESS",
    patient_id: 2, patient_name: "Nshimiyimana Eric", doctor_name: "Dr Mukamana",
    estimated_wait: 25 },
];

const RESULT: TriageResult = {
  triage_id: 1, patient_id: 1, patient_name: "Uwimana Claudine",
  urgency_level: "CRITICAL", possible_conditions: null, confidence_score: 0.81,
  ai_response_rw: null,
  patient_response: "Muraho. Ubu ni ubuvuzi bwihutirwa cyane.",
  response_pending: false, response_pending_reason: null,
  language_detected: "rw", queue_id: 1, queue_number: 12, queue_position: 1,
  estimated_wait: 0, created_at: "2026-09-11T08:00:00Z",
};

/** Fail on violations, and say which rule and which element. */
async function expectNoViolations(ui: React.ReactElement): Promise<void> {
  const { container } = render(ui);
  const results = (await axe(container, {
    rules: { "color-contrast": { enabled: false } },
  })) as unknown as AxeResults;
  const described = results.violations.map((v) => ({
    rule: v.id,
    impact: v.impact,
    help: v.help,
    nodes: v.nodes.map((n) => n.html.slice(0, 120)),
  }));
  expect(described, JSON.stringify(described, null, 2)).toEqual([]);
}

describe("accessibility", () => {
  it("queue as cards (phone)", async () => {
    setViewportMatches(false);
    await expectNoViolations(<QueueTable rows={ROWS} />);
  });

  it("queue as a dense table (station)", async () => {
    setViewportMatches(true);
    await expectNoViolations(<QueueTable rows={ROWS} />);
  });

  it("queue with row actions, as the doctor board renders them", async () => {
    setViewportMatches(false);
    await expectNoViolations(
      <QueueTable
        rows={ROWS}
        renderActions={(entry) => (
          <div className="flex flex-col gap-2">
            <select
              aria-label={`Assign a doctor to queue number ${entry.queue_number}`}
              className={inputClass}
              defaultValue=""
            >
              <option value="">Assign…</option>
              <option value="1">Dr Mukamana</option>
            </select>
            <Button>Seeing now</Button>
            <Button variant="danger">Done</Button>
          </div>
        )}
      />,
    );
  });

  it("loading state", async () => {
    await expectNoViolations(<Skeleton />);
  });

  it("empty state", async () => {
    await expectNoViolations(<QueueTable rows={[]} />);
  });

  it("all three alert kinds", async () => {
    await expectNoViolations(
      <div>
        <Alert>The server rejected the request.</Alert>
        <Alert kind="offline" action={<Button variant="quiet">Retry</Button>}>
          No connection.
        </Alert>
        <Alert kind="ok">Saved.</Alert>
      </div>,
    );
  });

  it("all three patient-message states", async () => {
    await expectNoViolations(
      <div>
        <PendingResponse result={RESULT} />
        <PendingResponse
          result={{ ...RESULT, patient_response: null, response_pending: true,
                    response_pending_reason: "No speaker-authored response." }}
        />
        <PendingResponse result={{ ...RESULT, patient_response: "Muraho {name}" }} />
      </div>,
    );
  });

  it("form primitives", async () => {
    await expectNoViolations(
      <Card title="New assessment">
        <Field label="Patient" hint="Their own words.">
          <select className={inputClass} defaultValue="">
            <option value="">Select…</option>
          </select>
        </Field>
        <Field label="What the patient says">
          <textarea className={inputClass} defaultValue="" />
        </Field>
        <Button type="submit">Assess</Button>
      </Card>,
    );
  });

  it("every urgency badge", async () => {
    await expectNoViolations(
      <div>
        <UrgencyBadge level="CRITICAL" />
        <UrgencyBadge level="URGENT" />
        <UrgencyBadge level="ROUTINE" />
        <UrgencyBadge level="CRITICAL" size="sm" />
      </div>,
    );
  });

  it("empty primitive", async () => {
    await expectNoViolations(<Empty title="Nothing here">Secondary.</Empty>);
  });
});
