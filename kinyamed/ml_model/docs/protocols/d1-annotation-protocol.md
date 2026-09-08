# D1 — Annotation protocol for a second annotator

**STATUS: NOT EXECUTED.** No second annotator exists. κ has never been computed
because there is only one label set. The project document's κ=0.84 has no
source.

## What is being measured

Agreement between two independent annotators assigning CRITICAL / URGENT /
ROUTINE to the same items, reported as Cohen's κ with a confidence interval.

**Not** agreement between an annotator and the existing labels. The existing
labels are one person's, and scoring a second person against them measures
compliance, not agreement.

## Procedure

1. **Sample.** Draw items at the CONCEPT level, not the row level. Rows are
   frame permutations; two rows of one concept are not two items and would
   inflate κ. Recommended: all 96 concepts represented in the corpus, both
   persons where both apply.
2. **Blind.** The second annotator sees the phrase and nothing else — no
   existing label, no urgency column, no domain, no anchor. Concept ids are
   replaced with random tokens.
3. **Independent.** No discussion until both label sets are complete and
   committed to disk.
4. **Order.** Randomised per annotator, seeded and recorded.

## The label boundary cases

These are where disagreement will concentrate, and the annotator sees them
without guidance so that disagreement is measured rather than trained away.
Recorded here for the analysis, not for the instruction sheet:

- **CRITICAL vs URGENT.** The corpus's own classifier fails here and nowhere
  else. Expect the human boundary to be soft in the same place.
- **Fever with a danger sign vs fever alone.** IMCI treats the danger sign as
  decisive; a lay annotator may not.
- **Service concepts.** A refill request and a screening visit are ROUTINE by
  construction, but read as "not ill" rather than "not urgent".
- **Observer signs the patient reports.** A patient reporting their own
  confusion or drowsiness.

## Disagreement procedure

1. Compute κ **before** any reconciliation. That number is the result.
2. Reconcile disagreements in a recorded session; keep both original labels.
3. Report κ, the reconciled set, and the count of items changed. Never report a
   post-reconciliation κ as the agreement figure.

## Computation

`scripts/compute_kappa.py` runs the moment two label files exist. It refuses on
a single file rather than reporting a number.

## What executing this does NOT establish

Two annotators agreeing does not make the taxonomy clinically correct. That is
D2.
