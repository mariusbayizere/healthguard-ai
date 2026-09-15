# Protocols for the six claims that need people

Six claims in the project document cannot be produced by engineering (listed in the
table below). They are **records of events** — assertions that specific people did
specific things. No amount of code makes them true.

For each, this directory holds **the instrument, not the result**: the thing a
person executes the moment one is available.

| # | Claim | Instrument | Status |
|---|---|---|---|
| D1 | κ=0.84 inter-rater agreement | `d1-annotation-protocol.md` | not executed — no second annotator |
| D2 | Taxonomy approved by a nurse at CHUK | `d2-clinician-review-pack.md` | not executed — no clinician has reviewed |
| D3 | 1,200 examples rated 1–5 by native speakers | `d3-speaker-rating-instrument.md` | not executed — no rating session has run |
| D4 | Human-nurse baseline, n=200 | `d4-nurse-baseline-design.md` | not executed — no nurse study has run |
| D5 | Consultations with CHWs at three health centres | `d5-chw-consultation-guide.md` | not executed — did not occur |
| D6 | Deployment at health centres in Rwanda | `d6-deployment-runbook.md` | not executed — not deployed |

**No value for any of the six exists anywhere in this repository, and none may
be written.** Where the paper needs one it carries `\PENDING{}`, so a compile
shows an unfilled slot rather than silently omitting the claim.

A protocol that has been executed records its own date, operator and outputs in
its header. Every header below says NOT EXECUTED.
