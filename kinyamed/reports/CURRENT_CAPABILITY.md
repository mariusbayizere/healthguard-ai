# KinyaMed — current capability (2026-09-14)

**Not deployed, and must not be used with patients.**

> **NOT REPRODUCIBLE figures** (marked 2026-09-15, CLAUDE.md L6). Every model measurement on this page, marked † below, comes from MODEL_AUDIT §3–§6. That report was produced by `scratchpad/ml_audit.py` and `scratchpad/latency_audit.py`, which were never committed and no longer exist. Not re-derived. The reproducible statement is that the deployment gate refuses to measure anything on the current set: 0 of 45 cells (DATASET_AUDIT §10).

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

## Required before deployment (CLAUDE.md §16)

On a clinician-labelled test set: all 15 gate metrics met with intervals; CRITICAL recall ≥ 0.91 in each of
Kinyarwanda, English, French and Swahili; CRITICAL→ROUTINE < 1%; red-flag safety suite 100%; calibration error
≤ 0.05. Also: `mypy --strict` clean (**now met**: 0 errors since `994bbdf`, reproducible with `mypy --strict app main.py`; the exception is cleared); zero critical accessibility
violations; Lighthouse ≥ 90; no high-severity vulnerabilities; a clean security scan.

No ethics approval is on file, and real-patient work requires it.

Sources: `reports/MODEL_AUDIT.md` §3, §4.2, §5, §6.1; `reports/STATE.md` items 1, 2, 2d.
