import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PatientMessage } from "../PatientMessage";

const RECEIPT =
  "Your report has been received. Your queue number is 12 and you are number 3 in the queue. " +
  "If you feel worse or this is an emergency, go to the health centre immediately.";

describe("PatientMessage", () => {
  it("shows the receipt verbatim", () => {
    render(<PatientMessage text={RECEIPT} language="english" />);
    expect(screen.getByText(RECEIPT)).toBeInTheDocument();
  });

  it("says the message is the same for every patient and not a triage result", () => {
    render(<PatientMessage text={RECEIPT} language="english" />);
    expect(screen.getByText(/same for every patient/i)).toBeInTheDocument();
    expect(screen.getByText(/english only/i)).toBeInTheDocument();
  });

  it("withholds a message containing an unfilled slot", () => {
    render(<PatientMessage text="Your queue number is {queue_number}." language="english" />);
    expect(screen.queryByText(/\{queue_number\}/)).not.toBeInTheDocument();
    expect(screen.getByText(/message withheld/i)).toBeInTheDocument();
  });
});
