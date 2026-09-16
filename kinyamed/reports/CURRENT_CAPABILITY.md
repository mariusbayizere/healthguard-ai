# KinyaMed — current capability (2026-09-14)

**Not deployed, and must not be used with patients.**

> **NOT REPRODUCIBLE figures** (marked 2026-09-15, docs/ENGINEERING_SPEC.md L6). Every model measurement on this page, marked † below, comes from MODEL_AUDIT §3–§6. That report was produced by `scratchpad/ml_audit.py` and `scratchpad/latency_audit.py`, which were never committed and no longer exist. Not re-derived. The reproducible statement is that the deployment gate refuses to measure anything on the current set: 0 of 45 cells (DATASET_AUDIT §10).

## The evaluation is too small to trust

Every quality number below comes from **9 distinct Kinyarwanda sentences (4 CRITICAL)**, repeated with varied
framing as 17,942 rows. English, French, Swahili and mixed-language input have **no test data**. At n=9, the
intervals cannot separate a safe model from a dangerous one.

## What it does

- Staff enter a patient's symptom text. A fine-tuned AfroXLMR-mini model (v2d, trained on Kinyarwanda only)
  suggests CRITICAL, URGENT or ROUTINE with a confidence score, as a staff-facing hint.
- Queue order: CRITICAL, then cases below 0.75 confidence ("model could not classify"), then URGENT, then
  ROUTINE.
- Patients receive only a receipt, a queue position and an instruction to go to the health centre if they feel
  worse, **in English only**.
- With no model loaded, triage is refused and staff are told to triage manually.

## The model is an audit artefact, NOT A BASELINE (2026-09-16)

Measured by `ml_model/training/probe.py` on 200 texts from the v2 eval split; no gold labels, **NOT A GATE
METRIC** (MODEL_AUDIT §11):

- **Surface variation alone changes the predicted urgency:** capitalisation **31.5%**, a realistic typo **21.0%**, punctuation removed **5.0%**, extra whitespace **0.0%**. Cause: the corpus has 0 capitalised rows, 0 double spaces and no typos (CORPUS_REBUILD §3.1, gate G9). Not fixed by normalising input.
- **Uniformly unconfident:** mean probabilities 0.36 / 0.33 / 0.31; the highest CRITICAL probability in the sample
  is **0.55**, so every prediction falls under the 0.75 review threshold and is flagged for a clinician.
- **No single-class collapse** (CRITICAL 102, URGENT 33, ROUTINE 65); deterministic; label order correct.
- The majority-class floor on the n=9 set where 0.707 was measured is **0.4995**
  (`reports/measurements/majority_baseline.py`). The 0.707 is weak evidence, not evidence of deployability.
- **v2d is not a baseline.** No future model is compared against it and no retraining of it is planned.

## What it cannot do

- † **93.4% of test-set predictions fall below 0.75** and are flagged for a clinician. **NOT REPRODUCIBLE** (`ml_audit.py`).
- † **Confident errors are not flagged.** "douleur thoracique, je ne peux pas respirer" came back ROUTINE at 0.78. **NOT REPRODUCIBLE** (`ml_audit.py`).
- † **11 of 20 emergency phrases went to ROUTINE** (unvalidated probe; **NOT REPRODUCIBLE**, `ml_audit.py`), including "sinshobora guhumeka" ("I can't
  breathe").
- **The red-flag rules layer exists but holds no terms**, so it changes nothing. `data/lexicon/red_flags.csv` ships empty because there is no validated clinical term list (H10). When terms are added, a match forces CRITICAL before the model runs, and PostgreSQL refuses any lowered urgency.

## Measured (v2d; 95% CI resampling the 9 sentences) — † NOT REPRODUCIBLE, `ml_audit.py`

| Metric | Measured | 95% CI | Required |
|---|---|---|---|
| Accuracy | 0.707 | 0.40–0.91 | ≥ 0.82 |
| CRITICAL recall | 0.850 | 0.08–1.00 | ≥ 0.91 |
| URGENT recall | 0.496 | 0.16–0.85 | ≥ 0.86 |
| CRITICAL→ROUTINE | 0% | 4 sentences only | < 1% |
| Calibration error | 0.188 | — | ≤ 0.05 |

† **Speed** (2015 laptop CPU, Phase 0 audit, not re-run): model inference p95 217 ms (target < 200). At 50
concurrent API requests, 136 of 200 failed. **NOT REPRODUCIBLE** (`latency_audit.py`).

## Required before deployment (docs/ENGINEERING_SPEC.md §16)

On a clinician-labelled test set: all 15 gate metrics met with intervals; CRITICAL recall ≥ 0.91 in each of
Kinyarwanda, English, French and Swahili; CRITICAL→ROUTINE < 1%; red-flag safety suite 100%; calibration error
≤ 0.05. Also: `mypy --strict` clean (**now met**: 0 errors since `994bbdf`, reproducible with `mypy --strict app main.py`; the exception is cleared); zero critical accessibility
violations; Lighthouse ≥ 90; no high-severity vulnerabilities; a clean security scan.

No ethics approval is on file, and real-patient work requires it.

Sources: `reports/MODEL_AUDIT.md` §3, §4.2, §5, §6.1; `reports/STATE.md` items 1, 2, 2d.
