# D4 — Human-nurse baseline study design

**STATUS: NOT EXECUTED.** No nurse study has run. The project document's
"human-nurse baseline, n=200" has no source.

## The question

Given the same patient description the model receives, what urgency does a
nurse assign? This produces the comparison the paper cannot currently make: the
model is measured against a label set, not against practice.

## Design

- **Cases.** n=200 drawn at the CONCEPT level then rendered, stratified by
  urgency. Concept-level sampling matters for the same reason as D1: 200 rows
  from 30 concepts is not n=200.
- **Blinding.** The nurse sees the patient description only. No model output, no
  label, no concept id, no urgency column.
- **Order.** Randomised per participant, seeded and recorded.
- **Participants.** Report how many, their setting and their experience.
  A baseline from one nurse is one nurse's practice.

## Analysis

1. Nurse-vs-label agreement (κ), which is the baseline figure.
2. Model-vs-label agreement on the same 200 cases, from a single inference pass.
3. Model-vs-nurse agreement.
4. **Per-class, and CRITICAL separately.** A headline accuracy hides the only
   error direction that matters.

## Two things to fix in the design before running it

- **The corpus is generated.** A nurse rating generated text is rating the
  generator as much as the taxonomy. State this as a limitation of the baseline
  rather than of the model.
- **Over-triage is not symmetric with under-triage** and the analysis must not
  average them. Report the confusion matrix.

## What executing this does NOT establish

That the model is safe to deploy. It establishes what a nurse does on the same
inputs, which is a comparison, not a clearance.
