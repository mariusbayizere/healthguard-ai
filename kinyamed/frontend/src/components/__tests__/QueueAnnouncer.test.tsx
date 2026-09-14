import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QueueAnnouncer } from "../QueueAnnouncer";
import type { QueueEntry } from "@/api/types";

// As GET /queue returns rows since item 2d: each carries its band.
const row = (id: number, urgency: QueueEntry["urgency_level"]): QueueEntry => ({
  id, queue_number: id, urgency_level: urgency, status: "WAITING",
  patient_name: `Patient ${id}`, doctor_name: null, estimated_wait: 0,
  band: urgency, requires_human_review: false,
} as QueueEntry);

/** A case the model could not classify: predicted `urgency`, band NEEDS_REVIEW. */
const flagged = (id: number, urgency: QueueEntry["urgency_level"]): QueueEntry => ({
  ...row(id, urgency), band: "NEEDS_REVIEW", requires_human_review: true,
} as QueueEntry);

describe("QueueAnnouncer", () => {
  it("says nothing on first render", () => {
    // The user is about to read the board; announcing it talks over them.
    render(<QueueAnnouncer rows={[row(1, "ROUTINE")]} />);
    expect(screen.getByRole("status")).toHaveTextContent("");
  });

  it("stays silent when a poll returns an unchanged queue", () => {
    // 12 polls a minute. Announcing each one is how a nurse learns to switch
    // announcements off, taking the one that mattered with it.
    const rows = [row(1, "ROUTINE"), row(2, "URGENT")];
    const { rerender } = render(<QueueAnnouncer rows={rows} />);
    rerender(<QueueAnnouncer rows={[...rows]} />);
    expect(screen.getByRole("status")).toHaveTextContent("");
  });

  it("announces a change in composition", () => {
    const { rerender } = render(<QueueAnnouncer rows={[row(1, "ROUTINE")]} />);
    rerender(<QueueAnnouncer rows={[row(1, "ROUTINE"), row(2, "URGENT")]} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Queue updated. 2 waiting: 0 critical, 0 needing review, 1 urgent, 1 routine.",
    );
  });

  it("leads with a new critical patient", () => {
    // Whatever else moved, the fact that decides who is seen next is first.
    const { rerender } = render(<QueueAnnouncer rows={[row(1, "ROUTINE")]} />);
    rerender(<QueueAnnouncer rows={[row(1, "ROUTINE"), row(2, "CRITICAL")]} />);
    expect(screen.getByRole("status").textContent).toMatch(
      /^New critical patient in the queue\./,
    );
  });

  it("counts a flagged case by its band, never as the model's guess", () => {
    // Before this, "sinshobora guhumeka" (ROUTINE at 0.598, flagged) was
    // announced as "1 routine": the pre-2d board, spoken.
    const { rerender } = render(<QueueAnnouncer rows={[row(1, "ROUTINE")]} />);
    rerender(<QueueAnnouncer rows={[row(1, "ROUTINE"), flagged(2, "ROUTINE")]} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "2 waiting: 0 critical, 1 needing review, 0 urgent, 1 routine.",
    );
  });

  it("says that a case the model could not classify has arrived", () => {
    const { rerender } = render(<QueueAnnouncer rows={[row(1, "URGENT")]} />);
    rerender(<QueueAnnouncer rows={[row(1, "URGENT"), flagged(2, "ROUTINE")]} />);
    expect(screen.getByRole("status").textContent).toMatch(
      /^New case the model could not classify\. Review it first\./,
    );
    expect(screen.getByRole("status").textContent).not.toMatch(/new critical/i);
  });

  it("counts several new review cases in one sentence", () => {
    const { rerender } = render(<QueueAnnouncer rows={[]} />);
    rerender(<QueueAnnouncer rows={[flagged(1, "URGENT"), flagged(2, "ROUTINE")]} />);
    expect(screen.getByRole("status").textContent).toMatch(
      /^2 new cases the model could not classify\. Review them first\./,
    );
  });

  it("puts a new critical patient before a new review case", () => {
    const { rerender } = render(<QueueAnnouncer rows={[]} />);
    rerender(<QueueAnnouncer rows={[flagged(1, "ROUTINE"), row(2, "CRITICAL")]} />);
    expect(screen.getByRole("status").textContent).toMatch(
      /^New critical patient in the queue\. New case the model could not classify\./,
    );
  });

  it("announces when a flagged case changes band with no change in total", () => {
    // A clinician raises the review threshold: a routine case becomes a review
    // case. Same number waiting, different board -- it must be spoken.
    const { rerender } = render(<QueueAnnouncer rows={[row(1, "ROUTINE")]} />);
    rerender(<QueueAnnouncer rows={[flagged(1, "ROUTINE")]} />);
    expect(screen.getByRole("status")).toHaveTextContent("1 needing review");
  });

  it("treats a row with no band as needing review, as the board does", () => {
    // The optimistic insert after a submission carries no band until the next poll.
    const bare = { id: 9, queue_number: 9, urgency_level: "ROUTINE", status: "WAITING",
      patient_name: "Just Submitted", doctor_name: null, estimated_wait: null } as QueueEntry;
    const { rerender } = render(<QueueAnnouncer rows={[]} />);
    rerender(<QueueAnnouncer rows={[bare]} />);
    expect(screen.getByRole("status")).toHaveTextContent("1 needing review, 0 urgent, 0 routine");
  });

  it("announces an emptied queue in words, not as a count of zero", () => {
    const { rerender } = render(<QueueAnnouncer rows={[row(1, "URGENT")]} />);
    rerender(<QueueAnnouncer rows={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Queue updated. Nobody is waiting.",
    );
  });

  it("re-announces when the queue returns to a previous state", () => {
    // 3 -> 4 -> 3. An identical string written to a live region is not
    // re-read by most screen readers, so the second '3' would be silent.
    const three = [row(1, "ROUTINE"), row(2, "URGENT"), row(3, "CRITICAL")];
    const four = [...three, row(4, "ROUTINE")];
    const { rerender } = render(<QueueAnnouncer rows={three} />);
    rerender(<QueueAnnouncer rows={four} />);
    const afterGrow = screen.getByRole("status").textContent;
    rerender(<QueueAnnouncer rows={three} />);
    const afterShrink = screen.getByRole("status").textContent;
    expect(afterShrink).not.toBe(afterGrow);
    expect(afterShrink).toContain("3 waiting");
  });

  it("is announced politely and read as a whole", () => {
    render(<QueueAnnouncer rows={[]} />);
    const live = screen.getByRole("status");
    // assertive would interrupt the person mid-word, usually while they are
    // reading this same queue.
    expect(live).toHaveAttribute("aria-live", "polite");
    expect(live).toHaveAttribute("aria-atomic", "true");
    expect(live).toHaveClass("sr-only");
  });
});
