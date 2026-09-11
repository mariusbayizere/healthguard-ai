import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QueueAnnouncer } from "../QueueAnnouncer";
import type { QueueEntry } from "@/api/types";

const row = (id: number, urgency: QueueEntry["urgency_level"]): QueueEntry => ({
  id, queue_number: id, urgency_level: urgency, status: "WAITING",
  patient_name: `Patient ${id}`, doctor_name: null, estimated_wait: 0,
});

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
      "Queue updated. 2 waiting: 0 critical, 1 urgent, 1 routine.",
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
