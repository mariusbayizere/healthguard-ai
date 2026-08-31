# HealthGuard AI Platform

[![CI](https://github.com/mariusbayizere/healthguard-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/mariusbayizere/healthguard-ai/actions/workflows/ci.yml)

A unified AI platform solving two critical problems in emerging markets:

- **KinyaMed** — AI-powered medical triage and patient queue system for Kinyarwanda-speaking populations.
- **FraudShield** — real-time fraud detection engine for financial transactions.

**Status:** 🚧 under active development. The triage dataset pipeline is complete and
verifiable; no model has been trained on the leakage-controlled splits yet, so this
repository currently contains **no accuracy claims**.

---

## What the badge means

CI re-derives every committed digest from seed 42 on a clean machine, on every push:
it regenerates the sample corpus, re-runs both splits, and compares SHA-256 digests
against the committed manifests. The dataset pipeline imports nothing outside the
Python standard library, so this check cannot break because of an upstream release.

Reproduce it yourself:

```bash
make verify        # regenerate the committed sample + both splits, check digests (seconds)
make verify-full   # regenerate all 1,000,000 rows and check every frozen digest (~1 min)
make test          # 33 tests
```

`make verify` needs no dependencies at all. Only training does.

---

## The dataset is template-generated. Read this before quoting any number.

The corpus is **1,000,000 rows generated from 184 seed phrases** by
`dataset/generate_large_dataset.py`, combined across 5 languages
(Kinyarwanda, English, French, Swahili, and code-mixed), 3 urgency classes,
and 9 clinical domains. It is **not** collected clinical text.

What that means, stated plainly:

- **Row count is not evidence of diversity.** A million rows resting on 184 seed
  phrases carry roughly 184 phrasings' worth of linguistic variety, not a million.
  `dataset/raw/symptoms_large.neardup.json` records the honest figure: a median of
  5,674 rows per phrase.
- **A high score here is a lower bound on difficulty, not a measure of clinical
  readiness.** The templates are regular; real patient language is not. Expect a
  large drop on genuine clinical text.
- **No real patient data is involved**, so nothing here carries privacy risk — and
  equally, nothing here has been validated by a clinician.
- The intended use is to exercise and de-risk the pipeline — leakage control,
  reproducibility, crash safety — before real data is available. Treat every metric
  produced from it as an engineering signal, not a medical one.

Under-triage (missing a CRITICAL case) is the failure that matters, which is why the
training script weights the loss by inverse class frequency and gates on CRITICAL
recall rather than accuracy.

---

## The two splits measure different things

Both hold out **whole groups**, never individual rows, and both are frozen to a
versioned manifest recording seeds, SHA-256 digests, and a full leakage report.

### `eval_manifest_phrase_v1.json` — unseen wording

Holds out entire phrase groups: 94,226 eval rows built on 16 seed phrases the model
never saw in training.

```
leakage: substring_violations 0 | phrase_overlap 0 | eval_rows_leaked_fraction 0.0
```

**This is the split that supports a "generalises to wording it has never seen" claim.**

Phrase groups are **substring-closed**. Some seed phrases contain others — for example
`ububabare bukabije mu nda` sits inside
`ububabare bukabije mu nda ndi utwite kandi ndavuye amaraso`. Holding out only the
inner phrase would leave its exact characters in every training row built on the outer
one: an exact-match overlap check reports **zero leakage while the model has plainly
seen the string**. Nested phrases therefore move across the split as a single unit,
and the check is cross-language, because leakage is textual regardless of which
language list a phrase came from.

### `eval_manifest_family_v1.json` — unseen category combinations

Holds out whole families (`language-pair : label : domain`): 114,321 eval rows across
18 families absent from training.

```
leakage: family_overlap 0 | phrase_overlap 50 | substring_violations 54
         eval_rows_whose_phrase_appears_in_train 114321 | eval_rows_leaked_fraction 1.0
```

> **`substring_violations: 54` and `eval_rows_leaked_fraction: 1.0` in the family
> manifest are expected and by design — not damage, and not a bug.**
>
> A family holdout partitions on `language-pair : label : domain`. Seed phrases recur
> across families by construction, so every family-eval row is built on a phrase that
> also appears somewhere in training. That is what makes this split test *category*
> generalisation. The numbers are recorded rather than suppressed precisely so the
> limitation is visible to anyone reading the manifest.

**Do not quote a family-split score as evidence of robustness to unseen phrasing.**
It measures exactly one thing: generalisation to unseen language × label × domain
combinations. Use the phrase split for wording claims. The family split's eval matrix
is the better-balanced of the two — every language × class cell holds at least 5,047
rows, with no cell too thin to report.

---

## Reproducing the full pipeline

```bash
make dataset   # generate 1,000,000 rows from seed 42, then validate
make splits    # build both leakage-controlled splits
make freeze    # freeze both eval sets to versioned manifests with digests
make verify-full
```

Everything derived is git-ignored. What is committed is the **code, the manifests, the
split reports, and a 1,000-row sample** — the sample exists so the pipeline runs
end-to-end from a clean clone without generating a million rows.

### Crash safety

Development hit a real `systemd-oomd` kill mid-run, which is why the pipeline is built
to survive one:

- outputs are streamed, never held in memory — the split peaks at ~98 MiB for 1M rows
- every write goes to a temp file, is fsynced, and is atomically renamed, so a kill
  leaves the previous complete file or nothing, never a truncated file that passes a
  shallow check
- each step checkpoints against a fingerprint of its inputs, so a restart costs one
  step rather than the whole run
- training checkpoints every 200 steps and refuses to resume into a different
  configuration

That last point is not theoretical. A crash during development left a
`.train_phrase_holdout.csv.*.partial` of **228,007,694 bytes — byte-identical in size
to a valid output**. Written directly to its destination it would have passed `ls`,
passed a size check, and been trained on silently.

---

## Repository layout

```
kinyamed/ml_model/
  dataset/
    vocabulary.py               184 seed phrases — the real input
    generate_large_dataset.py   deterministic corpus generation (seed 42)
    validate_dataset.py         balance, duplication and encoding checks
    near_duplicates.py          MinHash/LSH near-duplicate scan
    split_dataset.py            streaming, atomic, resumable splitter
    freeze_eval.py              versioned manifests + per-cell eval matrix
    atomicio.py                 atomic writes and step checkpoints
    sample/                     committed 1,000-row sample + its manifest
    processed/                  manifests and split reports (CSVs are ignored)
  training/
    train_holdout.py            checkpointed, resumable training
  tests/                        33 tests
  verify.py                     re-derives every committed digest
kinyamed/backend/               FastAPI triage service
fraudshield/                    fraud detection module
infrastructure/                 Docker and Kubernetes manifests
```

## Tech stack

- **NLP:** AfroXLMR (`Davlan/afro-xlmr-mini`) via HuggingFace Transformers
- **Backend:** FastAPI (Python) + Spring Boot (Java)
- **Frontend:** React.js + Tailwind CSS
- **Streaming:** Apache Kafka
- **Database:** PostgreSQL + Redis
- **Infrastructure:** Docker + Kubernetes
