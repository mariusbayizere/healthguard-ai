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
import { render, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import type { AxeResults } from "axe-core";

import { QueueTable } from "@/components/QueueTable";
import { PatientMessage } from "@/components/PatientMessage";
import { UrgencyBadge } from "@/components/UrgencyBadge";
import { Alert, Button, Card, Empty, Field, Skeleton, inputClass } from "@/components/ui";
import { setViewportMatches } from "@/test/setup";
import type { QueueEntry } from "@/api/types";

const ROWS: QueueEntry[] = [
  { id: 1, queue_number: 12, urgency_level: "CRITICAL", status: "WAITING",
    patient_id: 1, patient_name: "Uwimana Claudine", doctor_name: null,
    estimated_wait: 0, band: "CRITICAL", requires_human_review: false } as QueueEntry,
  { id: 2, queue_number: 9, urgency_level: "URGENT", status: "IN_PROGRESS",
    patient_id: 2, patient_name: "Nshimiyimana Eric", doctor_name: "Dr Mukamana",
    estimated_wait: 25, band: "URGENT", requires_human_review: false } as QueueEntry,
  { id: 3, queue_number: 13, urgency_level: "ROUTINE", status: "WAITING",
    patient_id: 3, patient_name: "Mugisha Jean", doctor_name: null,
    estimated_wait: 0, band: "NEEDS_REVIEW", requires_human_review: true } as QueueEntry,
];

const RECEIPT =
  "Your report has been received. Your queue number is 12 and you are number 1 in the queue. " +
  "If you feel worse or this is an emergency, go to the health centre immediately.";

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

  it("announces a new review case by its band, and the board stays violation-free", async () => {
    // Item 2d made the band visible; the live region must say the same thing.
    const before = ROWS.filter((r) => r.id !== 3);
    const { container, rerender } = render(<QueueTable rows={before} />);
    rerender(<QueueTable rows={ROWS} />);
    const live = within(container).getByRole("status");
    expect(live.textContent).toMatch(/^New case the model could not classify\. Review it first\./);
    expect(live).toHaveTextContent("1 needing review");
    expect(live.textContent).not.toMatch(/\b1 routine/);
    const results = (await axe(container, {
      rules: { "color-contrast": { enabled: false } },
    })) as unknown as AxeResults;
    expect(results.violations.map((v) => v.id)).toEqual([]);
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

  it("both patient-message states", async () => {
    await expectNoViolations(
      <div>
        <PatientMessage text={RECEIPT} language="english" />
        <PatientMessage text="Your queue number is {queue_number}." language="english" />
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
