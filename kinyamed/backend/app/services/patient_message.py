"""The only text this service addresses to a patient.

WHY IT SAYS SO LITTLE
---------------------
The classifier scored accuracy 0.7065 and ECE 0.18 on a nine-sentence held-out
set (reports/MODEL_AUDIT.md). It may order a queue that a clinician reviews. It
is not fit to tell a patient that their condition can wait, and an
urgency-specific message is exactly that: the ROUTINE templates said "make an
appointment" and "it is safe to wait for a normal appointment" to a patient the
model had misclassified as ROUTINE for "I can't breathe".

So every patient, whatever the model concluded, receives the same receipt: the
report was received, their place in the queue, and a generic escalation line.
`patient_receipt` is not given the urgency, so it cannot vary with it.

ENGLISH ONLY, AND THAT IS A KNOWN GAP
-------------------------------------
This sentence has not been translated. Kinyarwanda, French and Swahili versions
need a speaker (docs/ENGINEERING_SPEC.md §10.2); a machine translation would put unreviewed
text in front of a patient. Until then a patient who does not read English gets
the receipt in a language they may not read, which is a usability gap, not an
instruction that could harm them.
"""

from __future__ import annotations

from typing import Final

PATIENT_MESSAGE_LANGUAGE: Final = "english"

ESCALATION_LINE: Final = (
    "If you feel worse or this is an emergency, go to the health centre immediately."
)


def patient_receipt(*, queue_number: int, queue_position: int) -> str:
    """The receipt for a submitted report. Deliberately independent of urgency."""
    return (
        "Your report has been received. "
        f"Your queue number is {queue_number} and you are number {queue_position} "
        f"in the queue. {ESCALATION_LINE}"
    )
