# Every number in the paper, and what produces it

**Built 2026-09-17** for the check "does anything in the paper lack a source?". Each row
gives a figure as it appears in `ml_model/paper/`, the command or file that produces it,
and the report that records it.

**Three provenance classes, and the paper marks the third:**

| Class | Meaning |
|---|---|
| **A — script** | A committed script recomputes it. Re-run the command and the number reappears. |
| **B — committed record** | Read from a committed artefact (a frozen manifest, a run record, a review CSV) that a committed script wrote. |
| **C — document only** | Recorded in a repository document with no script behind it. **The paper marks each of these NOT REPRODUCIBLE inline, or states the direction without the figure.** |

`make reproduce` re-derives every class-A figure below from a clean clone (8 steps).

---

## The headline result (§Results 1, Abstract, Conclusion)

| Figure | Source | Class |
|---|---|---|
| 1,000,000 rows generated | `dataset/generate_large_dataset.py --target 1000000 --seed 42` | A |
| 130 seconds; ~7,700 rows/s | same run (elapsed time; the rate is 1,000,000 ÷ 130) | A |
| 4 of 9 gates FAIL as generated; 6 of 9 on the attributed split | `dataset/corpus_gates.py`; `reports/PRELIMINARY_RESULTS.md` | A |
| 165 distinct seed phrases | `dataset/vocabulary.py` `PHRASE_FORMS`, counted by `corpus_gates.py --seeds` | A |
| G1 cap 50 rows/seed; 0.1% share; G2 floor 3,000 seeds; G4 2% at Jaccard 0.85; G8 20% | `dataset/corpus_gates.py` constants; `reports/CORPUS_REBUILD.md` §3 | A |
| 8,250 / 150,000 / 1,000,000 rows allowed; **0 rows** at 165 seeds | `corpus_gates.largest_passing_corpus()` | A |
| 19,835 seeds short; 660–990 clinician-hours | 20,000 − 165; hours from `CLINICIAN_BRIEF` rates, **stated in the paper as an assumption** | A (arithmetic) |
| worst seed 8,975 rows = 26.07% of the split | `corpus_gates.py --seed-column phrase`; `measurements/corpus_gates_v2_eval.txt` | A |
| G9: 0 capitalised rows, 0 with stray spacing, 20.0% without terminal punctuation | `corpus_gates.py` G9 | A |

## Evaluation set and seed provenance (§Results 2, §Limitations)

| Figure | Source | Class |
|---|---|---|
| 17,942 rows from 9 distinct sentences, 4 critical | `scripts/gate_on_current_holdout.py --check-only`; `reports/DATASET_AUDIT.md` §10 | A |
| 38 gate cells refused | `training/evaluate.py --check-gold`; `measurements/gate_n9_check_gold.txt` | A |
| 710 / 365 / 720 required distinct sentences | `training/eval_spec.py --verify` (power derivation, recomputed by test) | A |
| train 150 seeds / 295,575 rows; test 15 / 34,425; 0 shared; 26.07% largest | `dataset/seed_provenance.py`; `measurements/seed_provenance.txt` | A |
| majority floors 0.4995 (n=9 set) and 0.3418 (v2 eval) | `reports/measurements/majority_baseline.py` | A |
| v1 leakage: 114,321 rows, 100%, `phrase_overlap` 50 | `dataset/processed/eval_manifest_*_v1.json`, written by `dataset/split_dataset.py` | B |
| 89.2% (101,945 of 114,321) family rows verbatim in phrase-training | same manifests | B |
| v2 leakage 0.0% both directions (24,900 / 34,425) | `eval_manifest_*_v2.json`; re-derived by `make verify-full` | B |

## Gate-design failure (§Results 2, §Discussion)

| Figure | Source | Class |
|---|---|---|
| 0.9749 critical recall; 0.0083 urgent recall; 0.5337 precision; 0.5349 ceiling | `training/holdout_eval.py --writeup` → `paper/generated/results_macros.tex`, from committed run records | B |

These are the only model-derived figures in the paper. They carry an explicit
no-quality-conclusion label, and support a claim about the gate's logic, not about either
configuration's performance.

## Probe and surface invariance (§Results 3, §Discussion, §Conclusion)

| Figure | Source | Class |
|---|---|---|
| flip rates 31.5% capitalisation, 21.0% typos, 5.0% punctuation, 0.0% whitespace | `training/probe.py`; `measurements/probe_v2d.txt`; `MODEL_AUDIT` §11 | A |
| vocabulary of 5 tokens on a tokenizer-less directory | `training/probe.py` encoding check; `MODEL_AUDIT` §11.1 | A |
| highest p(CRITICAL) 0.55 | `training/probe.py` | A |
| 26× beyond throughput at the stated concurrency | `backend/scripts/benchmark_inference.py`; `MODEL_AUDIT` §3.3 | A |

## Corpus construction (§Method)

| Figure | Source | Class |
|---|---|---|
| 330,000 rows from 165 phrases | `dataset/generate_large_dataset.py`; `make verify-full` digests | A |
| 115 / 70 / 95 minutes; 3.7–10.8M trainable parameters | `training/run_records/last_run_v2*.json` | B |
| review briefs: 256 rows, 50 inapplicable, 15 / 11 / 9 concepts removed | `review/build_*_brief.py` and the committed review CSVs | B |
| anchor table: 24 / 15 / 11 document-anchored, 20 clinician-defined | `docs/clinical-anchors.md` — **paper marks these as unverified anchor records** | C |
| phrase provenance split (previously "82 of 165, 49.7%") | **CUT.** No committed script aggregates the per-phrase column; the paper now says "roughly half" and names the gap | C |
| external corpora: 3,449 news articles; 5,609 CHW questions; 26,390 / 42,576 / 28,621 lines | `docs/language-resources.md`, `docs/swahili-source-audit.md` (audits of third-party sources) | C |

## Figures the paper marks NOT REPRODUCIBLE or cut

| Figure | Disposition |
|---|---|
| keyword fallback: 5.7% critical caught, 94.3% to routine | **Numbers cut**; direction stated, marked NOT REPRODUCIBLE (`MODEL_AUDIT` §6 is under the Phase 0 banner) |
| 60 of 61 concepts split across the holdout; 42 shared characters | **Kept and marked NOT REPRODUCIBLE** (`docs/phrase-group-closure.md`; no script recomputes it) |
| mixed rows "48% of v1" | **Softened to "nearly half"**, with the document named |
| accuracy 0.7065, macro F1, per-class recall, calibration error, phrase-cluster intervals [0.400, 0.914] and [0.08, 1.00] | **Cut entirely.** Produced by `scratchpad/ml_audit.py`, never committed, no longer on disk |
| latency p50/p95/p99 table | **Cut.** Unsourced target, unnamed machine; replaced by the specification finding |

## Conventions the paper states as conventions, not measurements

0.91 critical recall · <1.0% critical-to-routine · 150/200 ms latency · 10:1 cost ratio ·
1,000,000 rows · G9's surface shares · the near-duplicate, author-concentration and
rows-per-seed thresholds. All are recorded as lacking a derivation, in §Limitations and in
`reports/STATE.md` correction A30.
