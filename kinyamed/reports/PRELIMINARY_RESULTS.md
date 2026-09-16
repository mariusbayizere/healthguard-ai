# Preliminary results — attempted 2026-09-16

> **SEED PROVENANCE — train 150 distinct source phrases (295,575 rows), test 15 (34,425 rows), shared seeds 0.
> Largest single seed is 26.1% of the test split. Both splits come from the same generator and the same seed
> inventory, so any metric measured across them describes generalisation WITHIN the generator's distribution, not
> clinical performance.**
> (`ml_model/dataset/seed_provenance.py` → `measurements/seed_provenance.txt`)

**Outcome in one line: no preliminary numbers exist, because no model was trained. The pipeline refused, and the
refusal is the result.**

The four-step plan was executed in order, test-first, without waiving a gate or modifying the pipeline. Steps 1–3
ran and are reported below. Steps 4 and 5 have no checkpoint to evaluate.

---

## Step 1 — dataset generation to the FR-04-07 target of 1,000,000

**Generated:** 1,000,000 rows, seed 42, 130 s, peak 96 MB (`dataset/generate_large_dataset.py --target 1000000`).
The generator's own quality targets passed ("All quality targets met").

**Run through the CORPUS_REBUILD §3 gates** (`dataset/corpus_gates.py`, 19 tests; no gate waived; NOT COMPUTABLE
is never a pass):

| Gate | Verdict | Detail |
|---|---|---|
| G1 rows per seed | NOT COMPUTABLE | the generated corpus carries no seed column; measured on the attributed split below |
| G2 distinct seeds | NOT COMPUTABLE here; **FAIL** on the attributed split | 15 distinct seeds in the eval split against a floor of 3,000 per language |
| G3 lexical diversity | NOT COMPUTABLE | the floor is a fraction of the pilot's own diversity, and no pilot exists |
| G4 near-duplicate seeds | NOT COMPUTABLE here; PASS on the attributed split | 0 of 15 seeds near-duplicate, 0 exact |
| G5 machine transformation | **FAIL** | no `generation_method` column: the origin of every row is unknown, and an unattributable row is refused rather than assumed native |
| G6 frame consistency | NOT COMPUTABLE | no `reporter` or `patient_age_group` per row; the age axis awaits E6 |
| G7 provenance | **FAIL** | no `seed_id`, `generation_method`, `author_code` or `validated_by` columns |
| G8 author concentration | **FAIL** | no `author_code`: authorship is unrecorded (the corpus has no authors) |
| G9 surface variation | **FAIL** | 0.0% not sentence-cased (needs 15%), **0 rows in capitals**, 20.0% without terminal punctuation (needs 20%), **0 rows with stray spacing** |

**On the phrase-attributed v2 split, where seeds can be counted** (`eval_phrase_holdout.csv`, 34,425 rows):
6 gates FAIL (G1, G2, G5, G7, G8, G9), 2 NOT COMPUTABLE, 1 PASS (G4). G1's worst seed produces **8,975 rows,
26.07% of the split**.

### The largest gate-passing corpus is 0 rows

**Not a size problem.** G2's floor is on **seeds**, not rows: ≥ 3,000 distinct seed phrases per language. The
generator's inventory is **165 phrases** (`dataset/vocabulary.py` `PHRASE_FORMS`). Therefore:

| Seeds available | Rows allowed by G1 (50/seed) | Passes G2? | Largest passing corpus |
|---|---|---|---|
| **165 (today)** | 8,250 | **No** (needs 3,000) | **0 rows** |
| 3,000 | 150,000 | Yes | 150,000 |
| 20,000 | 1,000,000 | Yes | **1,000,000 — the FR-04-07 target** |

**The shortfall to 1M is 19,835 seed phrases, not 999,000-odd rows.** Rows are free; seeds must be written by
native-speaker clinicians. Even at 165 seeds, G5, G7, G8 and G9 would still fail: the generator has no authors, no
per-row provenance, and produces no surface variation. **No quantity of generated rows passes the gates.**

## Step 2 — seed provenance (measured before any training)

| Split | Rows | Distinct seeds | Max rows per seed | Largest seed share |
|---|---|---|---|---|
| train | 295,575 | **150** | 8,129 | 2.75% |
| test | 34,425 | **15** | 8,975 | **26.07%** |
| shared seeds | — | **0** | — | 0 test rows from a shared seed |

The splits are seed-disjoint, which is required (L8) and enforced. **Disjoint is not independent:** both come from
one generator and one 165-phrase inventory. A metric measured across them is a within-distribution number.

## Step 3 — training through the committed pipeline

Run unmodified, with the 1M corpus as training data:

```
python -m training.pipeline --train <1M corpus> --gold-test dataset/processed/gate_n9_gold.csv \
    --gold-calibration dataset/processed/gold_calibration.csv \
    --config training/configs/pipeline_default.json --seed 42 --out <run dir>
```

**REFUSED. Exit 2 in 9.6 s, peak 249 MB. "Nothing was trained."** 39 refusal lines:

- **38 test-split gate cells** are INSUFFICIENT DATA on the n=9 gold set (17,942 rows from 9 distinct source
  sentences): gate 1 needs 710 distinct scenarios, gate 5 needs 365 per pure language, gate 7 needs 720.
- **The calibration split does not exist**, so no temperature and no safety thresholds can be fitted.
- The leakage check did not run: the refusal happens before the training corpus is read.

The pipeline was not modified, and no gate was lowered to let it proceed.

## Steps 4 and 5 — evaluation and probe of the new checkpoint

**NOT PRODUCED — no model was trained.** The table the plan specifies is left empty rather than filled from a
different source:

| Metric | Value | Distinct seeds in cell | 95% CI (resampled by source sentence) | Majority-class floor |
|---|---|---|---|---|
| any | **NOT PRODUCED** | — | — | — |

**Why this is not a technicality.** Had the pipeline been forced to run, every cell of that table would have been
computed on **15 distinct source sentences**. The interval resampled by source sentence would then look like the
one already on record for v2d: accuracy **[0.400, 0.914]**, CRITICAL recall **[0.08, 1.00]** (MODEL_AUDIT §4.2).
A number with that interval does not distinguish a safe model from a dangerous one, which is the whole reason the
gate refuses.

**The majority-class floors are already measured** and stand ready for comparison
(`measurements/majority_baseline.txt`): v2 eval split **0.3418** (always URGENT); the n=9 gold set **0.4995**
(always CRITICAL).

### The surface-fragility baseline the comparison would use

v2d, the only checkpoint that exists (`training/probe.py`, MODEL_AUDIT §11) — **NOT A GATE METRIC**:

| Surface variant | v2d flip rate | What a corpus with G9 variation should show |
|---|---|---|
| capitalisation | **31.5%** | materially lower |
| typos | **21.0%** | materially lower |
| punctuation removed | 5.0% | lower |
| extra whitespace | 0.0% | unchanged (the tokenizer normalises it) |

A new checkpoint trained on a corpus that carries surface variation should beat these, and that would be a real
result. **It cannot be produced from the current generator**, whose output contains 0 capitalised rows, 0 rows
with stray spacing and no typos at all (step 1, G9).

## What this does and does not change

- **The §16 gates remain UNMET.** No metric in this document is a gate result, and none is a clinical claim.
- **The model remains not-for-deployment.** v2d is an audit artefact and NOT A BASELINE (MODEL_AUDIT).
- **The clinician gold-set path in STATE.md is unchanged and remains the only route to a publishable claim.**
  Nothing here replaces it.
- **What would let step 3 run:** a calibration split, and a test split meeting EVAL_SET_SPEC. Both come from the
  pilot. The same bottleneck — native-authored seeds — also governs whether a synthetic corpus could ever pass
  G2.
