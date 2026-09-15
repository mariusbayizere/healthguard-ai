# Dataset audit — Phase 0 (docs/ENGINEERING_SPEC.md §3.6)

Audit date 2026-09-14. Measurements by `scratchpad/dataset_audit.py` and `scratchpad/ml_audit.py` in this
session unless a line says otherwise. The corpus files are git-ignored derived artefacts; their SHA-256 digests
were checked against the committed manifests.

**Verdict in one line.** The corpus the model was trained on is **330,000 rows of Kinyarwanda generated from
165 phrases and 360 distinct word types**. It is admirably reproducible and leakage-controlled, but it is not the
1,000,000-row, four-language, ten-combination, clinician-validated dataset the specification requires. It carries
**no per-row provenance**, **no validation by a clinician**, and **no inter-rater agreement**. Three of the four
languages have no rows at all. It is not publishable as specified.

---

## 1. Which dataset?

There are two corpora, and the repository's own documents disagree about them.

| | **v1** | **v2** (trained on) |
|---|---|---|
| Generator | `dataset/generate_large_dataset.py --corpus-version 1` from `dataset/vocabulary_v1.py` (frozen) | `--corpus-version 2` (default) from `dataset/vocabulary.py` |
| On disk? | No (regenerable; I regenerated a 100,000-row sample into scratch) | Yes: `dataset/raw/symptoms_large.csv`, SHA-256 `0c9c3a39…aef152` = manifest `source.sha256` ✓ |
| Rows | 1,000,000 (per README / manifests v1) | **330,000** |
| Languages | kinyarwanda, english, french, swahili, mixed | **kinyarwanda only** |
| Seed phrases | 184 (README) | **165 distinct** (measured) |
| Origin | machine-drafted slot fill | speaker-authored + machine-derived Kinyarwanda phrases × generated frames (see §6) |
| Frozen manifests | `eval_manifest_{phrase,family}_v1.json` | `eval_manifest_{phrase,family}_v2.json` |

**Documentation conflict (L6).** The root `README.md` describes v1 ("1,000,000 rows generated from 184 seed
phrases … across 5 languages", "make test — 41 tests", "No model has been trained on the leakage-controlled splits
yet") and, in the same file, reports v2 figures ("330,000 rows … 165 distinct phrases", "Macro F1 0.7724"). The
committed `dataset/sample/sample_manifest.json` still describes itself as a sample "of the full corpus, for running
the pipeline … without generating 1M rows", but the committed 1,000-row sample is **100% Kinyarwanda** (v2).
`ml_model/docs/STATUS.md` (2026-09-09) is the only document consistent with disk.

Full-corpus reproducibility (`verify.py --scope full`): see §8.

---

## 2. Size, origin, generation method

- **330,000 rows**, 5 columns `text, language, label, domain, family` (processed splits add `phrase, phrase_group`).
- Generation: each row = one of 165 symptom phrases (first person or third person with a `{REL}` relation slot)
  embedded in a frame drawn from Kinyarwanda slot inventories: **OPENERS 12, CONTEXTS 10, CLOSERS 11**, plus
  onsets and relation terms (`dataset/vocabulary.py`, counted by import). The allocation targets ~2,000 rows per
  phrase ("size follows content", the old charter's rule 4).
- Seed 42; deterministic; every write atomic (`dataset/atomicio.py`).

## 3. Standards from §9.1, measured

| Standard | Spec | v2 measured | v1 (100k regenerated sample) | Verdict (v2) |
|---|---|---|---|---|
| Total size | ≥ 1,000,000 unique after dedup | **330,000** | 1,000,000 by design | **NOT MET** |
| Language balance | each pure 10–15%; mixed 40–60% | **kinyarwanda 100%** | KW 13.0 · EN 13.0 · FR 13.0 · SW 13.0 · mixed 48.0% | **NOT MET** (v1 meets it) |
| Class balance | CRIT 28–38 · URG 32–42 · ROUT 28–38% | CRIT 33.0 · URG 34.0 · ROUT 33.0% | 33.0 · 34.0 · 33.0% | **MET** |
| Domain coverage | 80+ domains, ≥ 500 per domain | **9 domains** (smallest domain 11,441 rows; smallest domain×label family 432 rows) | 9 domains | **NOT MET** |
| Exact duplicates (MD5 of lowercased, whitespace-collapsed text) | < 2% | **0 / 330,000 (0.000%)** | 0 / 100,000 | MET — by construction (distinct combination index), so uninformative |
| Near-duplicates, MinHash Jaccard ≥ 0.85 (word 3-grams, 64 perm / 16 bands, exact Jaccard verified on candidates) | report | **2.77%** of 3,000 probe rows have a ≥ 0.85 neighbour within a 40,000-row train sample — a *lower bound*; the repo's own scan (`symptoms_large.neardup.json`, threshold 0.80, 60k sample) reports 8.71% | not run | reported; population rate higher than both |
| Length | 20–512 chars | min **31**, median 132, max **272**; 0 outside bounds | 32 / 105 / 178 | MET |
| Token length | fits 128 | max 88 tokens, 0.00% > 96 (MODEL_AUDIT §2.1) | max 68 (KW) | MET — but see §5: short, regular text is a warning, not a comfort |
| Clinical validation | 1,500 rows, 2 RNs, κ ≥ 0.80 | **none**; protocol only (`docs/protocols/d1-annotation-protocol.md`) | none | **BLOCKED** (no clinician) |
| Code-switch naturalness | ≥ 3.5/5, all 6 pairs | **0 mixed rows** in v2; generator refuses (`dataset/code_switching.py`, `docs/blocked.md` §4) | 48% mixed rows, machine-interleaved, never rated | **NOT MET / BLOCKED** |
| Release | CSV + Parquet, CC BY 4.0, datasheet | no Parquet, no datasheet, no per-row licence | — | **MISSING** |

## 4. Leakage across splits (L8)

Phrase-holdout split v2 (`eval_manifest_phrase_v2.json`), re-checked independently:

| Check | Manifest says | Re-measured |
|---|---|---|
| Exact text overlap (normalised) eval ↔ train | 0 | **0** of 34,425 eval rows |
| Phrase overlap | 0 | **0** (train 150 distinct phrases, eval 15) |
| Phrase-group overlap | — | **0** |
| Substring violations | 0 | not re-derived (the split's substring-closure logic is tested by `tests/test_leakage.py`, 24 tests, ran and passed) |
| Near-duplicate eval → train (Jaccard ≥ 0.85) | — | **0** of 5,000 eval rows vs 40,000 train rows; median best Jaccard 0.27, p95 0.50, **max 0.73** |
| `family_overlap` | 6 | — (expected: families are language:label:domain; the phrase split does not hold them out) |

**Verdict: no split leakage in the phrase holdout. MET.** The max Jaccard of 0.73 is the shared frame text
(openers/closers), which is by design and is the channel for the shortcut in §5.2.

The v1 family manifest records `eval_rows_leaked_fraction: 1.0` by design (it tests category, not wording,
generalisation); the README says so. Do not quote a family-split score as wording generalisation.

## 5. Diversity and template collapse — the flaw a reviewer will find

### 5.1 Effective diversity

| Measure | v2 (330,000 rows) | v1 sample (100,000 rows, 5 languages) |
|---|---|---|
| Distinct symptom phrases | **165** | 184 (README) |
| Rows per phrase | min 386 · median 1,146 · max 8,975 | — |
| Effective phrase count, exp(entropy) of the row-per-phrase distribution | **111.3** | — |
| **Distinct word types (`\w+`, lowercased)** | **360** | 672 total; KW 180 · EN 175 · FR 188 · SW 149 · mixed 672 |
| Tokens | 6,348,608 | 1,791,138 |
| Type–token ratio | **5.7 × 10⁻⁵** | 3.75 × 10⁻⁴ |
| Unigram entropy | 7.29 bits | 8.41 bits (per language 6.36–6.57) |

**Finding.** The entire Kinyarwanda training corpus uses **360 word types** — a closed vocabulary far smaller
than open patient speech would need. 330,000 rows carry roughly the linguistic information of 111–165 sentences.
The repo is candid about this (`README.md` "Row count is not evidence of diversity"); the spec's 1M target would
make it worse, not better. It also explains why no row is longer than 88 tokens, and it is consistent with (not proof of) the model sending
out-of-vocabulary emergency inputs to ROUTINE (MODEL_AUDIT §6.1).

### 5.2 Label shortcuts built into the templates — measured on the train split (295,575 rows)

| Feature | CRITICAL | URGENT | ROUTINE |
|---|---|---|---|
| Row ends with a "thank you" closer (`Murakoze` / `Urakoze`) | **0.00%** | 18.33% | 18.41% |
| Third-person (`{REL}`) phrase | 88.93% | 86.43% | **69.62%** |

The v2 generator deliberately excludes thank-you closers from CRITICAL (`dataset/vocabulary.py:847-870`, "thanking
someone trivialises an emergency"). That rule is reasonable clinically and **fatal statistically**: the closer is a
perfect "not CRITICAL" signal that has nothing to do with symptoms. **Perturbation probe on v2d:** appending
". Murakoze." to 300 held-out CRITICAL rows changed the prediction of **5 of 259** rows the model had called
CRITICAL (net CRITICAL 259 → 258). v2d leans on it only weakly; a stronger model trained on the same data would be
free to exploit it fully. Third person skews away from ROUTINE, consistent with the third-person errors in
MODEL_AUDIT §7.

## 6. Per-row provenance

| Column required by §9.1 | Present in any corpus CSV? |
|---|---|
| `source` | **no** |
| `generation_method` | **no** |
| `validated_by` | **no** |
| `licence` | **no** |
| `variant` (Swahili) | **no** |
| `matrix_language` (code-switched) | **no** |

Provenance exists **per phrase, not per row**, in the review briefs (`review/speaker_brief_kinyarwanda_v2.csv`
column `source`; categories defined in `docs/provenance-categories.md` and derived by `review/provenance.py`,
tested by `tests/test_provenance.py` — ran, passed). From `docs/STATUS.md` (repo figure, not re-derived by me):
82 of 165 phrases (49.7%) directly speaker-authored; the remainder speaker-derived, machine-drafted-speaker-approved
or machine-derived. **Frames (openers/contexts/closers) carry no provenance column at all.**

**Verdict: not publishable as is.** Joining phrase-level provenance onto rows is mechanical (every row has a
`phrase` column in the splits) and should be done before any release; frame provenance must be recorded.

Licence: no dataset licence is declared. Clinical anchors cite WHO IMCI 2014 (All rights reserved — concepts only)
and WHO-ICRC BEC 2018 (CC BY-NC-SA 3.0 IGO) per `docs/clinical-anchors.md`; the **NC-SA terms are incompatible with
the spec's CC BY 4.0 release** if any BEC text were reproduced. The repo states it reproduces no WHO text; I did not
verify that claim.

## 7. Linguistic quality

**BLOCKED — I will not grade Kinyarwanda or Swahili.** §3.6 asks for 200 Kinyarwanda and 200 Swahili rows
reviewed for MT artefacts, calques, noun-class agreement and invented terms. I am not a native speaker of either,
and L16 forbids guessing. There are **no Swahili rows** in v2 to sample (Swahili brief: relation terms authored,
0 phrases — `docs/STATUS.md`). A stratified 200-row Kinyarwanda sample can be produced in one command for a
reviewer once D4 names one.

What can be measured without a speaker, and was:
- Vocabulary is extremely closed (360 types) — any calque or error in one phrase is replicated ~2,000 times.
- The English and French v2 arms are `machine_reviewed` drafts no speaker has seen (`docs/STATUS.md`); the v1
  corpus's EN/FR/SW rows are machine-drafted throughout.

## 8. Reproducibility

| Check | Result |
|---|---|
| `verify.py --scope sample` (committed 1,000-row sample + both splits from seed 42) | **6/6 PASS**, 9 s (executed) |
| `verify.py --scope full` (1M v1 + v2 corpora, every frozen digest) | **14/14 PASS**, 815 s (executed): v1 1,000,000 rows and v2 330,000 rows regenerate from seed 42; all phrase/family train/eval digests match; v2 eval files on disk match manifests |
| Corpus SHA-256 vs v2 manifest | match |
| Eval file SHA-256 vs manifest | match (`b8cddf0d…23af5`) |

## 9. What must change before this is a dataset (summary; details in REMEDIATION_PLAN R4)

1. Build the §10.6 lexicon and a **many-sentence, clinician-labelled evaluation set per language first**; the
   training corpus second.
2. Record provenance per row (join phrase provenance; add frame provenance), plus `variant` / `matrix_language`.
3. Remove label-correlated frame slots, or balance them across classes, and add a shortcut-perturbation test to
   the generator's test suite.
4. Report effective diversity (types, effective phrase count) alongside row count everywhere the row count
   appears.
5. Replace the README's stale v1 narrative; write a Gebru et al. datasheet.
6. Do not raise rows-per-phrase to reach 1M; report the largest defensible size (§10.7).

## 10. The evaluation set shows the same template collapse (added 2026-09-15)

**The only held-out reporting set is 17,942 rows from 9 distinct source sentences:** about 1,994 rows per
sentence. It is the same slot-filling collapse as the training corpus (§5), and it gives n = 9 of information.

Rebuilt with the training code's own splitter: `split_eval_by_group` over `eval_manifest_phrase_v2.json`
(digests verified), 3 stopping groups, seed 42, as the v2d run. Written to the git-ignored
`dataset/processed/gate_n9_gold.csv` (SHA-256 prefix `636b7727e428`) by `scripts/gate_on_current_holdout.py`.

| Population | Rows | Distinct source sentences |
|---|---|---|
| All items | 17,942 | 9 |
| Gold CRITICAL | 8,962 | 4 |
| Gold URGENT | 7,793 | 4 |
| Gold ROUTINE | 1,187 | **1** |
| English, French, Swahili, any mixed pair | 0 | 0 |

**Consequences**
- **0 of 45 gate cells can be measured.**
  `python training/evaluate.py --gold dataset/processed/gate_n9_gold.csv --check-gold` gives 38 INSUFFICIENT
  DATA and 5 NOT KNOWN (the CRITICAL precision rows, whose population the model sets). Output:
  `reports/measurements/gate_n9_check_gold.txt`.
  Example: `CRITICAL recall [kinyarwanda]: INSUFFICIENT DATA (8,962 rows from 4 distinct source sentences; need
  365 distinct)`.
- **The ROUTINE class is one sentence.** Any F1 or macro average on this set rests on a single ROUTINE sentence.
- **No inference was needed to show this.** `evaluate.py --model` now refuses before loading the model when no
  cell is measurable.
- **Row-level intervals on this set are wrong, and point estimates without intervals are worse.**
  - The v2d run record and the paper tables (`train_holdout.py`, `holdout_eval.py`) carry no interval at all.
  - MODEL_AUDIT §4.2's phrase-cluster intervals (e.g. CRITICAL recall 0.08–1.00) came from an uncommitted
    Phase 0 script that is no longer on disk (MODEL_AUDIT §9), so they cannot be re-run (L6).
  - The gate does resample clusters. It prints no interval here because 9 < every minimum.
