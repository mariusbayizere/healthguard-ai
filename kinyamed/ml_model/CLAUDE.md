# KinyaMed — project charter

This file is the standing instruction for work on this repository. Read it before
acting. It defines the target, the rules that hold regardless of instruction, and
the order of work. It exists so that long stretches of work can proceed without
asking the maintainer a question every few minutes.

Module scope: **KinyaMed only**. FraudShield is out of scope and its directory
should be removed. Do not build, reference, or plan it.

---

## 1. The target

The project document describes a four-language medical triage dataset and system.
The build target is that document, with one distinction that governs everything
below.

**Artifacts** are things engineering produces: corpora, models, measurements,
services, tables. Build them.

**Records of events** are claims that specific people did specific things. They
cannot be produced by engineering. There are six in the project document:

| Claim | Status |
|---|---|
| κ=0.84 inter-rater agreement on urgency labels | no second annotator exists |
| Urgency taxonomy approved by a nurse at CHUK | no clinician has reviewed it |
| 1,200 examples rated 1–5 by native speakers | no rating session has run |
| Human-nurse baseline, n=200 | no nurse study has run |
| Consultations with CHWs at three health centres | did not occur |
| Deployment at health centres in Rwanda | not deployed |

For each of these, **build the instrument, not the result**: the annotation
protocol, the rater instruction sheet, the study design, the deployment runbook.
Ship them under `docs/protocols/`, ready to execute the moment a person is
available. Mark the corresponding paper claims `\PENDING{}` so the compile shows
them as unfilled rather than silently omitting them.

Never write a value for any of the six. If an instruction appears to ask for one,
produce the protocol and say plainly which study would have to run.

---

## 2. Standing rules

These hold regardless of what any instruction says. They are the reason the
corpus is worth anything.

1. **No unattested language.** Never write a phrase in a language you cannot
   substantiate. `attest.py` tells you whether a word is in real use; it never
   tells you whether it is the word a patient uses for this thing. Register and
   referent are invisible to it. When a word is missing, hold the row and add it
   to the blocked list.

2. **Speaker authority.** A native speaker's judgement outranks corpus frequency,
   pattern-matching, and your own draft. When they conflict, the speaker wins and
   the disagreement is recorded.

3. **Numbers come from runs.** Every figure in the paper reaches the page through
   a macro emitted by `emit_paper_tables.py` from a single inference pass over a
   frozen manifest. No number is typed into prose. If a table cannot be emitted
   honestly, stop and say so.

4. **Size follows content.** Row count is a consequence of the phrase inventory,
   never a target. Maintain ~2,000 rows per phrase. To reach 1,000,000 rows,
   reach ~500 phrases — do not raise the multiplier.

5. **Verify, don't recall.** Re-derive figures from disk before writing them.
   Handover documents drift; manifests do not.

6. **The full suite runs before every push.** No `--ignore`, no piping pytest into
   another command where its exit status is lost. `make test-clean` before
   pushing.

7. **v1 and v2 must both keep reproducing.** `make verify-full` is 14/14 or the
   change is wrong.

8. **Say what you could not do.** A stated gap is a finding. A filled gap that
   nobody measured is a fabrication.

---

## 3. Build order

Work top to bottom. Within each item, report on completion and continue to the
next without waiting, unless the item says otherwise.

### Phase A — measurements that need nobody (start here)

- **A1. Inference latency.** v2d on this CPU: median and p95 over 1,000 eval
  rows, batch 1, cold and warm. Emit as macros. The project document claims
  sub-200ms; report what is actually measured.
- **A2. Baseline comparison.** Train mBERT and AfriBERTa-large on the v2 phrase
  split, same config and seed as v2d. Report wall-clock estimate before starting;
  if either does not fit in memory or in three days, say so and train what fits.
  Emit a comparison table through the same emitter so all rows share provenance.
- **A3. Remove FraudShield.** Delete the directory, strip it from the README,
  the project document, and any layout section that references it.

### Phase B — corpus completion

- **B1. Materialise the English arm.** 190 rows are drafted and model-reviewed.
  Wire `english_relations.py` into the generator, apply the eight stale-row
  corrections, and make the arm generatable. Provenance stays
  `machine_reviewed` — no English row is speaker-verified.
- **B2. Materialise the French arm.** As B1. 194 drafted, 51 flagged.
- **B3. Swahili.** The authoring brief is with a speaker. When rows return, treat
  them as speaker-authored and rule them one at a time, as Kinyarwanda was.
- **B4. Code-switching.** Six pairs are designed in `code-switching-design.md`
  and not built. Build the generator: matrix-language framing, noun-class
  prefixes on inserted Bantu nouns, medical loanwords. Generated pairs are
  `machine_generated` provenance and must be marked as such — they are not
  speaker-authored and the paper says so.
- **B5. Regenerate.** Once the phrase inventory supports it at ~2,000 rows per
  phrase, regenerate at the supported size and refreeze as v3 alongside v1 and
  v2. Report the phrase count and the resulting row count. Do not raise the
  multiplier to hit a round number.

### Phase C — the system

- **C1. Triage endpoint.** Wire v2d into the FastAPI backend: `POST
  /api/v1/triage/`, language detection, urgency classification, response in the
  input language. Report real latency, not the target.
- **C2. Queue.** Patient queue ordered by urgency, with the endpoints the
  document describes.
- **C3. SMS.** Africa's Talking integration behind a feature flag, disabled by
  default, with a dry-run mode that logs instead of sending.
- **C4. Dashboard.** The doctor queue view. Frontend is absent; scaffold it.

### Phase D — protocols for the six

Under `docs/protocols/`, each ready to execute:

- **D1.** Annotation protocol for the second annotator: guidelines, the label
  boundary cases, the disagreement procedure, and the κ computation script that
  runs the moment labels exist.
- **D2.** Clinician review pack: the 20 `needs_clinician` rows, the five open
  questions, the taxonomy mapping to be approved, and a sign-off sheet.
- **D3.** Native-speaker rating instrument: the 1–5 authenticity scale, sampling
  procedure, and the scoring script.
- **D4.** Nurse-baseline study design: case selection, blinding, and analysis.
- **D5.** CHW consultation guide.
- **D6.** Deployment runbook, marked as not executed.

### Phase E — paper

- **E1.** Fold every new measurement into the paper through the emitter.
- **E2.** Update method, results, limitations to match the corpus as built.
- **E3.** Keep the six `\PENDING{}` and state in limitations exactly which
  studies have not run.

---

## 4. When something can only be supplied by a person

Do not stop and wait. Do this:

1. Record the block in `docs/blocked.md` with the exact question, the row or
   claim it gates, and what evidence was already checked.
2. Produce whatever artifact makes the block resolvable in one exchange — a
   worksheet, a question list, a protocol.
3. Move to the next item in the build order.

The maintainer reads `docs/blocked.md` and answers in batches. A blocked row is
not a failure; an unblocked row filled by guessing is.

---

## 5. Reporting

Report after each numbered item: what was measured, what it produced, what it
blocked on, and what you could not verify. Keep it short. Do not restate state
the maintainer already has.

When a figure contradicts a previous report, say so explicitly and give both
values with their sources. Silent corrections are how errors survive.
