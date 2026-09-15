# Construct — what KinyaMed measures (proposal, not adopted)

**Status 2026-09-15: proposal only.** Adoption is the lead clinician's decision (H6).
Nothing here changes code, labels or specification.

## What the system does

**Not ETAT triage.** ETAT assigns categories by examining the child on arrival (manual p. 3, p. 36). No
document in the repo authorises urgency from an unexamined report (`TAXONOMY_SCOPE.md` §2b).

**Queue prioritisation from a patient-authored symptom report.** Text written or relayed by a patient or carer,
before any examination, is mapped to CRITICAL / URGENT / ROUTINE with a confidence score, and the queue is
ordered by it. Staff still triage in person.

## Proposed ground truth

**The urgency an experienced clinician assigns given ONLY the text:** no examination, no questions, no facts
the text does not state. In practice: the adjudicated label from two independent clinicians and an adjudicator. D7 §3 already drafts "judged from the text alone" as a task framing. Here it becomes the construct,
not a way of applying ETAT.

**It can support:**
- model agreement with clinicians reading the same text, per language, voice and length;
- how reliable clinicians' text-only judgement is (κ), which caps what model agreement can mean;
- which texts are too uninformative to agree on.

**It cannot support:**
- **Accuracy against the patient's true condition.** Clinician-judgement-from-text is not validated against
  patient outcomes, so **agreement with clinicians is not accuracy against truth.**
- "CRITICAL recall ≥ 0.91" as a safety claim. It would mean agreement with clinicians' CRITICAL reading of text,
  not recall of critically ill patients.
- Equivalence to ETAT or bedside triage, or safety with real patients.
- Finding **shared blind spots.** A sign the text omits is invisible to annotators and model alike. Both miss the
  same patient, and agreement hides it.

Linking it to truth needs an outcome study on consented real patients (H2).

## What would change if adopted

**D7 annotation protocol**
- **§3:** definitions are written for text-only judgement and approved by the lead clinician. The "Source
  category (e.g. ETAT)" column and the B1/B3 dependency are removed. The framing paragraph becomes the
  construct definition, including the rule on unstated signs.
- **§3:** `not_enough_information` becomes central. Whether "cannot be assessed safely from text" is a separate
  outcome, or maps to NEEDS REVIEW, is a clinical decision.
- **§4:** worked examples cite those definitions, not manual passages.
- **§10:** add that agreement is not accuracy against outcomes.

**EVAL_SET_SPEC.md**
- **§11:** B1–B3 no longer unblock labels; the lead clinician's written definitions (B5) do. B2 may still
  organise the domain axis (§7).
- **§4:** gate metrics are reworded as agreement with the clinician-from-text label. Their thresholds (0.91,
  < 1%) have no source under this construct and need ratifying or replacing (H6).
- **§9:** κ is reported as the construct's reliability, beside model-vs-gold agreement.
- **§7:** new per-item annotator field, **information sufficiency** (the text states enough to judge: yes/no).
  Coverage only, never gated.
- **§10:** add the outcome limitation.

**Not decided:** adoption, E6, thresholds, renaming.
