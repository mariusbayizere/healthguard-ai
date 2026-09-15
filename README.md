# HealthGuard AI — KinyaMed (research prototype)

> **Not deployed. It must not be used with patients.** No ethics approval is on file, and no clinician has
> validated anything in this repository.
> ([CURRENT_CAPABILITY.md](kinyamed/reports/CURRENT_CAPABILITY.md))

**Start with the audit.** The reports are the source of truth; this page links to them.

| Report | What it establishes |
|---|---|
| [CURRENT_CAPABILITY.md](kinyamed/reports/CURRENT_CAPABILITY.md) | One page: what the prototype does and cannot do |
| [MODEL_AUDIT.md](kinyamed/reports/MODEL_AUDIT.md) | The model against its gates |
| [DATASET_AUDIT.md](kinyamed/reports/DATASET_AUDIT.md) · [CORPUS_REBUILD.md](kinyamed/reports/CORPUS_REBUILD.md) | What the corpus is, why it must be replaced, and the path to a defensible one |
| [TAXONOMY_SCOPE.md](kinyamed/reports/TAXONOMY_SCOPE.md) · [CONSTRUCT.md](kinyamed/reports/CONSTRUCT.md) | The missing clinical basis |
| [EVAL_SET_SPEC.md](kinyamed/reports/EVAL_SET_SPEC.md) | The evaluation set that deployment gates require, and how large it must be |
| [STATE.md](kinyamed/reports/STATE.md) | Current work, corrections to the specification, and everything blocked on a person or document |

**Numbers on this page.** Only figures that a script committed to this repository reproduces are stated here,
each with the command. The Phase 0 model measurements (accuracy, recall, intervals, calibration, latency) came
from scripts that were never committed, so they are not repeated here. See MODEL_AUDIT §9.

## What it is

A staff-operated web app and API. Staff enter a patient's symptom text. A fine-tuned AfroXLMR-mini model, trained
on Kinyarwanda only, suggests CRITICAL, URGENT or ROUTINE with a confidence score, as a staff-facing hint. The
queue is ordered by that suggestion. Patients receive only a receipt and queue position, in English.
([CURRENT_CAPABILITY.md](kinyamed/reports/CURRENT_CAPABILITY.md))

## No clinical basis yet

**No document in this repository authorises assigning urgency from a written report about a patient nobody has
examined.** The only clinical instrument present, the WHO ETAT participant manual (2005), defines its categories
by examining children on arrival. It does not address remote or written reports.
([TAXONOMY_SCOPE.md §2, §2a, §2b](kinyamed/reports/TAXONOMY_SCOPE.md))

Earlier versions of this README called the project "AI-powered medical triage". That claim is withdrawn.
- A proposed description of what the system actually measures is in [CONSTRUCT.md](kinyamed/reports/CONSTRUCT.md).
  It is **not adopted**; that is a clinical-lead decision.
- Code and API names still say "triage" (for example `POST /api/v1/triage`). Every such use is listed in
  [STATE.md, SRS correction A27](kinyamed/reports/STATE.md). Nothing has been renamed yet.

## The corpus is not a validated dataset

- **330,000 rows of Kinyarwanda from 165 distinct phrases.** English, French and Swahili have no rows.
  Reproduce: `cd kinyamed/ml_model && python ../reports/measurements/grammatical_person.py`.
- **It regenerates exactly from seed 42**, every frozen digest included: `make verify-full`. That shows the
  pipeline is deterministic, not that the data is valid.
- **There is no per-row provenance, no clinician validation and no inter-rater agreement.** It is **not
  publishable** and must not be cited as a dataset. ([DATASET_AUDIT.md §6](kinyamed/reports/DATASET_AUDIT.md),
  [CORPUS_REBUILD.md §1](kinyamed/reports/CORPUS_REBUILD.md))

## The model cannot be evaluated on the data that exists

The only held-out reporting set is **17,942 rows from 9 distinct Kinyarwanda sentences**, the same template
collapse as the training corpus. English, French, Swahili and mixed-language input have no test data.
([DATASET_AUDIT.md §10](kinyamed/reports/DATASET_AUDIT.md))

The deployment gate therefore **refuses to report any metric**. It measures 0 of 45 gate cells, and prints for
example `INSUFFICIENT DATA (8,962 rows from 4 distinct source sentences; need 365 distinct)`.

```bash
cd kinyamed/ml_model
python scripts/gate_on_current_holdout.py --model <v2d model dir>   # writes the gold file, then stops at the gate
python training/evaluate.py --gold dataset/processed/gate_n9_gold.csv --check-gold
```

The refusal is the result. A metric needs the clinician-labelled evaluation set that
[EVAL_SET_SPEC.md](kinyamed/reports/EVAL_SET_SPEC.md) specifies, and it does not exist yet.

**The red-flag rules layer is built but empty.** No validated clinical terms exist yet, so it matches nothing (`kinyamed/data/lexicon/red_flags.csv`). When terms are added, it can only escalate, and the database enforces that. ([CURRENT_CAPABILITY.md](kinyamed/reports/CURRENT_CAPABILITY.md))

## Software state

- **Tests** on branch `audit-p0-p1-and-frontend`, re-run 2026-09-15:
  - backend: 335 passed (`cd kinyamed/backend && python -m pytest`);
  - frontend: 146 passed (`cd kinyamed/frontend && npx vitest run`);
  - `mypy --strict`: 0 errors.
- **Stack actually present:**
  - FastAPI with PostgreSQL 16;
  - React 18 + TypeScript 5 + Tailwind + Vite;
  - PyTorch and Transformers for the model.
- **Not present:**
  - Redis is configured but unused by application code;
  - no Kafka, WebSocket, Docker, Kubernetes, Prometheus or Grafana;
  - no OAuth, and no live SMS provider.

  ([STATE.md, SRS corrections A7–A12, A23](kinyamed/reports/STATE.md))
- **The paper is not submittable.** Its clinical-anchor count and concept total disagree with the repository.
  ([STATE.md, SRS corrections A25, A26](kinyamed/reports/STATE.md))

## Continuous integration

CI runs on every branch and pull request. It covers:
- dataset reproducibility;
- training checkpoint tests;
- repository hygiene;
- the backend suite;
- frontend typecheck, tests and build;
- browser tests;
- lint.

Status is recorded in [STATE.md](kinyamed/reports/STATE.md), not shown as a badge, because a single badge
overstates what it covers.

## Licence and data

**No real patient data is in this repository.** The corpus has **no declared dataset licence**, and the licence
terms of its clinical anchors are unresolved. ([DATASET_AUDIT.md §6](kinyamed/reports/DATASET_AUDIT.md))
