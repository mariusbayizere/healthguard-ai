# Model audit — Phase 0 (CLAUDE.md §3.5)

> **NOT REPRODUCIBLE — read this first** (marked 2026-09-15, CLAUDE.md L6). The measurements in this report were produced by `scratchpad/ml_audit.py` and `scratchpad/latency_audit.py`. Neither was committed, and neither exists on disk (§9), so no measured figure below can be re-run. Each section says so. What the repository *can* reproduce today:
> - token lengths: `reports/TOKENIZER_STUDY.md`, which supersedes §2.1;
> - the reporting set's composition, 17,942 rows from 9 sentences: DATASET_AUDIT §10;
> - the gate's refusal on that set: `evaluate.py --check-gold`;
> - the label-order parity test: `ml_model/tests/test_label_parity.py`.

Audit date 2026-09-14. Every number below was produced in this session by
`scratchpad/ml_audit.py` and `scratchpad/latency_audit.py` (kept outside the repo; see §9 for how to re-run).
Nothing here is copied from `last_run.json`, the README or the paper. Where my measurement matches a
recorded figure, I say so.

**Verdict in one line.** The only credible checkpoint (v2d) is a genuinely fine-tuned Kinyarwanda-only
classifier that **fails every quality threshold it can be measured against**, cannot be measured at all on 4 of the 15
gate metrics (and on 3 of 4 languages for CRITICAL recall) because the data does not exist, is badly **uncalibrated** (ECE 0.18), and **sends 11 of 20 hand-picked
emergency inputs to ROUTINE** — including "sinshobora guhumeka" ("I can't breathe") and every English, French
and Swahili emergency phrase tried. It must not triage a patient. The checkpoint committed at `ml_model/saved_model/`
is a different, near-chance model that the backend would refuse to load.

---

## 1. Provenance

### 1.1 Checkpoints found

| | `ml_model/saved_model/` (in repo tree, git-ignored) | v2d `~/kinyamed-runs/model_v2d_freeze8_lr1e-5/` (**outside the repo**) |
|---|---|---|
| Date | 2026-05-19 | 2026-09-07 |
| `model.safetensors` SHA-256 | `0f6a5ebb33222cea97f710015dacfb810473e7d520ce1e122b8790801b7cff7f` | `f2cc6194236d4027ecc23ee8d1d5c0e7499653ba31617ff92fcf3ef1029663ea` |
| `config.id2label` | `LABEL_0/LABEL_1/LABEL_2` (no names) | `CRITICAL/URGENT/ROUTINE` |
| Training data | `dataset/processed/train.csv` — **179 rows** (`wc -l` = 180 incl. header), mixed languages, random split, no leakage control | `train_phrase_holdout.csv`, 295,575 rows, Kinyarwanda only, frozen manifest `eval_manifest_phrase_v2.json` |
| Training script / log | `training/train.py`; no run log | `training/train_holdout.py`; `training/run_records/train.sh`, `run-v2d-freeze8-lr1e-5.log`, `last_run_v2d_freeze8_lr1e-5.json`, `protocol.json` |
| Backend would load it? | **No** — `ModelClassifier` refuses because `id2label` ≠ `(CRITICAL, URGENT, ROUTINE)` (`backend/app/services/model_classifier.py:98-107`), then falls back to the keyword baseline outside production | Yes |
| Status | **INCORRECT** (unreproducible, near-chance, unloadable) | **Reproducible from the machine it was trained on; not from a clean clone** (weights unpublished, not in repo) |

Also present outside the repo: `model_v2b_freeze10_lr1e-5`, `model_v2c_freeze6_lr1.5e-5_DO_NOT_SHIP`, `smoke_model`.

### 1.2 Base model

- HF repo `Davlan/afro-xlmr-mini`. Local cache snapshot revision **`bc04038b969667884bd83cdd37bed9559c2c3d9c`**,
  weights SHA-256 `9a3b2df1add028a576a0ee36b4643eba9cbd4f4df20db3fa57b619a66d0a10c2`.
- **The revision is not pinned in code** (`training/config.py` `MODEL_NAME = "Davlan/afro-xlmr-mini"`,
  `from_pretrained(MODEL_NAME)` with no `revision=`). A retrain after an upstream push would silently use
  different weights. `docs/SOURCES.md` (§10.1 of the spec) does not exist.

### 1.3 Fine-tuned or base model with an untrained head? — measured

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this section was produced by `scratchpad/ml_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.

Per-tensor max |Δ| between each checkpoint and the base snapshot:

| Checkpoint | Embeddings | Layers 0–7 | Layers 8–11 | Classifier head |
|---|---|---|---|---|
| v2d | **identical** (Δ = 0) | **identical** (Δ = 0) | changed, max Δ 0.0055–0.0081 | present (not in base); `dense.weight` ‖·‖ 7.88, `out_proj.weight` ‖·‖ 0.77 |
| saved_model | changed, max Δ 0.0006 | changed, Δ 0.0007 | changed, Δ 0.0008–0.0009 | present; ‖·‖ 7.70 / 0.69 |

**v2d is genuinely fine-tuned**, exactly as its log says: embeddings + bottom 8 layers frozen, top 4 layers +
head trained (7,246,851 of 117,641,859 parameters, 6.2%). The head's `out_proj.weight` norm is comparable to
the `saved_model` head; the behavioural evidence below (97% CRITICAL→CRITICAL on training rows) rules out an
untrained head. The training log shows the head was **newly initialised** (`classifier.* MISSING` in the load
report) and loss descended from 1.0989 to 0.53.

**saved_model** moved every layer by < 0.001 — consistent with a few steps on 179 rows. Its predictions are
near chance on the v2 evaluation set (accuracy 0.414, §4.3).

### 1.4 Reproducibility of the recorded v2d result — measured

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this section was produced by `scratchpad/ml_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.

Re-running inference on the frozen reporting subset reproduced `training/last_run.json` **exactly**: accuracy
0.706499, macro F1 0.772399, CRITICAL recall 0.850368, identical confusion matrix `[[7621,1341,0],[3869,3868,56],[0,0,1187]]`.
Eval file SHA-256 `b8cddf0d…23af5` matches the manifest. This is a strength of the project and should be kept.

**Verdict: PROVENANCE PARTIAL.** Seed (42), config (`train.sh`), manifest digests, run log and code are
recorded. Missing: pinned base revision, published weights (the SRS names `mariusbayizere/kinyamed-afro-xlmr`
— not verified to exist; not checked, no network call made), code commit of the training run in the run record
(the manifest carries `git_commit eb5dce0`, the run record does not), environment lockfile.

---

## 2. Correctness

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this table, except the label-parity test (`tests/test_label_parity.py`, committed) was produced by `scratchpad/ml_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.

| Check | Result | Evidence |
|---|---|---|
| Thread-safe singleton (100 concurrent) | **FAIL** | `get_classifier()` is `@lru_cache`. With a stub builder that sleeps 0.5 s, 100 threads released by a barrier on a cold cache invoked the builder **100 times** and received 2 distinct objects. Production is protected only because `main.py` lifespan calls it once before serving. With the real model this would be 100 × 470 MB loads. |
| InferenceResult has 7 fields, no nulls (FR-04-02) | **FAIL** | `Classification` has 4 fields: `urgency, possible_conditions, confidence, advice_rw`. Absent: per-class probabilities, detected language + confidence, model version, duration. `triage_results` has no `model_version` column, so no stored decision can be tied to a model. |
| Probabilities sum to 1; softmax once | **PASS** | max \|Σp − 1\| = 1.8e-7 over 17,942 rows. `ModelClassifier.classify` applies one `torch.softmax` to raw logits; `XLMRobertaForSequenceClassification` returns logits. |
| Token truncation per language | **PASS at 96 and at 128** (see §2.1) | 0.0% of rows exceed 96 tokens in any language measured |
| Label order (silent killer #2) | **PASS for v2d; guarded** | `config.id2label` = `{0:CRITICAL,1:URGENT,2:ROUTINE}` = `dataset/labels.py` `LABEL_MAP`; backend refuses mismatch (`model_classifier.py:98-107`); cross-package parity test `ml_model/tests/test_label_parity.py` ran and passed. Behavioural check on 3,000 **training** rows: true CRITICAL → predicted CRITICAL 1,422 / 1,466 (97.0%), no CRITICAL→ROUTINE — an inverted head would show the opposite. |
| Serving max_length vs training | **Mismatch, currently harmless** | Trained at `max_length=96`; backend `.env` / `.env.example` set `MODEL_MAX_LENGTH=512`. On 300 tripled-length texts (~150 tokens) predictions at 96 vs 512 disagreed on **0.0%**. Harmless on this corpus because nothing is long; a real patient narrative would be scored on a length the model never saw. |
| Fail-safe when model unavailable (L4) | **FAIL** | Outside `ENVIRONMENT=production` the service silently serves the keyword baseline (measured CRITICAL recall 0.057, §6.2). A runtime exception inside `classify()` surfaces as HTTP 500; there is no PENDING/human-review path. `/ready` imports the non-existent `app.ml.model_loader` and always reports `ml_model: "not_installed"`, even with v2d loaded (§3.2) — so an orchestrator can never gate traffic on the model. |

### 2.1 Token-length distribution (tokenizer from v2d, XLM-R SentencePiece)

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this section was produced by `scratchpad/ml_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.
> **Superseded by `reports/TOKENIZER_STUDY.md`** (committed `training/tokenizer_study.py`), which measures all 330,000 v2 rows rather than a sample. **The longest Kinyarwanda row is 94 tokens, not 88.** 88 was the maximum of the random 20,000-row sample below. The committed study's v1 figures agree with this table (p95 54, p99 59, max 68 for Kinyarwanda).

| Text source | n | p50 | p95 | p99 | max | % > 96 | % > 128 | chars/token |
|---|---|---|---|---|---|---|---|---|
| **v2 corpus, Kinyarwanda** full utterances (random 20k of 330k) | 20,000 | 50 | 66 | 74 | ~~88~~ **superseded: 94 over all 330,000 rows (TOKENIZER_STUDY)** | 0.00 | 0.00 | **2.66** |
| v1 corpus (regenerated to scratch), Kinyarwanda | 5,000 | 43 | 54 | 59 | 68 | 0.00 | 0.00 | 2.65 |
| v1 corpus, English | 5,000 | 26 | 32 | 34 | 38 | 0.00 | 0.00 | 3.89 |
| v1 corpus, French | 5,000 | 33 | 42 | 45 | 50 | 0.00 | 0.00 | 3.47 |
| v1 corpus, Swahili | 5,000 | 27 | 34 | 37 | 42 | 0.00 | 0.00 | 3.40 |
| v1 corpus, mixed | 5,000 | 32 | 47 | 52 | 59 | 0.00 | 0.00 | 3.21 |
| v2 English brief, machine-drafted phrases (bare) | 207 | 15 | 21 | 23 | 24 | 0.00 | 0.00 | 3.05 |
| v2 French brief, machine-drafted phrases (bare) | 205 | 17 | 26 | 27 | 30 | 0.00 | 0.00 | 2.96 |

**Finding.** Kinyarwanda does tokenise ~1.5× longer per character than English (2.66 vs 3.89 chars/token),
as the spec warns — but **truncation is not the silent killer here, because the corpus is short and
templated**: the longest Kinyarwanda row is ~~88~~ **94** tokens (superseded; see the note above). That is itself a warning: real patient narratives are
longer than template rows, and the absence of truncation in evaluation says nothing about field inputs.
(A per-language row for v1 bare seed phrases was also computed and **discarded** — my script iterated the wrong
level of `SYMPTOMS` and produced identical numbers for all four languages.)

---

## 3. Performance (CPU)

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this section was produced by `scratchpad/latency_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.

**Hardware:** Intel Core i5-6200U (2 cores / 4 threads, 2015 laptop part), 7.6 GiB RAM, Linux 7.0, Python 3.11.9,
torch 2.12.0+cpu, transformers 5.8.1, `torch.set_num_threads(2)`. **Conditions were not clean:** Firefox and
Chrome held ~3 GB, and 2–3 GB of swap was in use throughout. Latency below is therefore an upper bound for
this CPU, not a best case. The spec's "target CPU spec" is not defined anywhere in the repo — **BLOCKED on you
naming it.**

### 3.1 In-process inference (`ModelClassifier.classify`, the class the API serves; max_length 96)

| Measure | Result | Target | Verdict |
|---|---|---|---|
| Model load (`from_pretrained`, under swap) | 66.2 s | — | — |
| Cold: first inference after load | 649.7 ms | — | — |
| Concurrency 1 (n=300) | p50 **132.3** · p95 **216.6** · p99 258.1 · max 383.7 ms | p50 < 150 · p95 < 200 · p99 < 300 | p50 MET · **p95 NOT MET** · p99 MET |
| Concurrency 10 (n=500) | p50 **1,566** · p95 2,929 · p99 3,859 ms | same | **NOT MET** |
| Concurrency 50 (n=500) | p50 **7,939** · p95 8,834 · p99 16,279 ms | same | **NOT MET** |
| Peak RSS of process | **1,431 MB** | < 2 GB | MET (single process) |

The repo's own record (`training/latency_v2d.json`, 2026-09-08, same CPU, batch 1) is warm p50 66 ms / p95 103 ms,
cold 1,341 ms. My concurrency-1 numbers are ~2× slower, consistent with the swap pressure noted above; I cannot
claim either is the machine's true figure. **Concurrency is the real problem:** `ModelClassifier` serialises
every forward pass behind one `threading.Lock` (`model_classifier.py:124`), so latency grows linearly with
queue depth — ~160 ms × N.

### 3.2 End-to-end HTTP (`POST /api/v1/triage`, uvicorn 1 worker, PostgreSQL 16 local, v2d loaded, rate limiter off, SMS stubbed)

| Measure | Result | NFR target | Verdict |
|---|---|---|---|
| Server start → `/health` 200 | 77.0 s | — | — |
| `/ready` with v2d loaded | `{"status":"ready","database":"ok","ml_model":"not_installed"}` | truthful | **WRONG** |
| Concurrency 1 (n=100) | p50 **363** · p95 **1,501** · p99 2,646 ms, all 201 | p50 < 200 · p95 < 350 · p99 < 500 | **NOT MET** |
| Concurrency 10 (n=200) | p50 **3,083** · p95 7,189 · p99 7,665 ms, all 201 | same | **NOT MET** |
| Concurrency 50 (n=200) | p50 **34,067** · p95 58,770 · p99 59,546 ms; **136 of 200 × HTTP 503** | same; error < 0.1% | **NOT MET** |
| Server RSS high-water mark | **1,416 MB** | < 2 GB @ 50 concurrent | MET |
| Server log lines containing a full E.164 phone | **336** (from `sms_stubbed … to=`) | 0 (L11) | **FAIL** |
| `GET /queue` `patient_phone` | `+250788000111` unmasked | masked | **FAIL** |

**Why 503 at 50:** `database_error … QueuePool limit of size 10 overflow 5 reached, connection timed out,
timeout 30.00`. Each request checks out a DB connection (patient lookup) *before* waiting on the model lock, so
15 requests hold all connections while queued for inference and the rest time out after 30 s. The model lock and
the connection pool compound each other. Fix belongs to R1/R5 (release the session across inference, or run
inference in a bounded worker pool with back-pressure), not to a bigger pool.

**The single triage probe run through the real API with v2d loaded** (`symptoms_input: "sinshobora guhumeka"`):

```json
{"urgency_level": "ROUTINE", "confidence_score": 0.598, "language_detected": "kinyarwanda",
 "patient_response": "Fata gahunda yo kureba muganga igihe ukabonera umwanya.", "response_pending": false,
 "estimated_wait": 0, "queue_position": 1}
```

The returned sentence is the speaker-authored ROUTINE template whose brief
(`ml_model/review/speaker_brief_kinyarwanda_v2_responses.csv`) glosses it as *"Not urgent — make an appointment …
it is safe to wait for a normal appointment."* The ROUTINE SMS template was also rendered for dispatch
(`sms_stubbed message_length=142`). **End to end, the running system tells a patient who types the backend's own
listed red-flag phrase for "cannot breathe" that it is safe to wait.** Nothing flags it for review.

---

### 3.3 Reproducible measurement after micro-batching (2026-09-15) — supersedes §3.1 for the served path

**Reproducible.**
- Script: `backend/scripts/benchmark_inference.py`. Output: `reports/measurements/inference_benchmark/`
  (`results.json`, and gate-ready `latency_batch*.json` / `memory_batch*.json`).
- Root-cause check: `backend/scripts/diagnose_inference_path.py`, output `path_diagnosis.txt`.

**Method**
- The backend's own `ModelClassifier`, in-process: v2d at `max_length` 96, 2 torch threads.
- 1,000 corpus texts (seed 42); closed loop with 1,000 timed requests per level.
- p50/p95/p99 nearest-rank, each with a 95% bootstrap interval over requests.
- "Serialised" is the same engine at `max_batch_size=1`: one worker, one forward pass at a time, exactly what the
  removed lock did. "Micro-batched" is `max_batch_size=16`, with a 5 ms window.

**Machine: not the target.** No target hardware is named (STATE.md H15).
- **CPU:** Intel Core i5-6200U, **2 physical cores, 4 logical** (2 threads per core); 7,825 MB RAM.
- **Memory state:** 3,870 MB available before model load, about 820 MB of swap already in use; 2,761–3,478 MB
  available across the levels; lowest 1,585 MB (during load).
- **The machine was not idle.** Load average was 2.7–4.2 on 2 cores, with Chrome running, during the runs and the
  diagnosis. **These are upper bounds on a loaded laptop, not best cases.**

**Cold start:** model load 31.5 s; first inference 705 ms; peak RSS 1,283 MB.

**Equivalence.** Batching does not change what the model says: 200 texts, **0 argmax disagreements** between single
and padded-batch inference; largest probability difference 2.4 × 10⁻⁷.

| Concurrent | Serialised p50 (ms) | p95 | p99 | req/s | Micro-batched p50 (ms) | p95 | p99 | req/s |
|---|---|---|---|---|---|---|---|---|
| 1 | 162 [157, 167] | 305 [289, 326] | 451 [388, 532] | 5.58 | 171 [166, 177] | 366 [344, 385] | 560 [478, 608] | 5.03 |
| 10 | 1,548 [1,516, 1,576] | 2,552 [2,421, 2,616] | 3,036 [2,808, 3,220] | 5.98 | 1,015 [998, 1,026] | 1,697 [1,681, 1,955] | 2,268 [2,257, 2,561] | 9.04 |
| 50 | 9,851 [9,715, 9,921] | 13,223 [13,098, 13,309] | 14,479 [14,189, 14,535] | 5.03 | **3,694 [3,685, 3,724]** | **4,988 [4,911, 5,101]** | 5,511 [5,400, 5,548] | **12.8** |

Peak RSS at 50 concurrent: 1,334 MB serialised, 1,382 MB micro-batched. Gate 15's < 2 GB holds on this machine, but
the gate cannot record MET until H15 names the target hardware.

**Findings**
1. **The serialisation defect is real and reproduced:** serialised p50 at 50 concurrent is 9.9 s (§3.1's
   unreproducible 7.9 s was the same defect). Micro-batching cuts it to 3.7 s and raises throughput from 5.0 to
   12.8 requests per second, 2.5×.
2. **The ceiling is CPU, not the lock.**
   - Serialised throughput is flat at 5.0–6.0 requests per second at every concurrency level. That is one worker
     saturating the CPU.
   - With batching, latency at 50 concurrent is about concurrency ÷ throughput (50 / 12.8 = 3.9 s, measured
     3.7 s). The engine adds about 7 ms: direct forward p50 158 ms against 165 ms through the engine, same process,
     interleaved.
3. **The older 66 ms record** (`training/latency_v2d.json`, 2026-09-08, same CPU, same work) **is not
   contradicted by the code.** The difference is machine state: two diagnosis runs minutes apart gave direct p50 133
   and 158 ms as load rose. A clean, idle re-run is needed before any figure represents this CPU.
4. **The latency NFR cannot be met on this hardware, at any concurrency, batched or not.** See SRS correction A29 in
   STATE.md.
   - At 1 concurrent the p50 interval [157, 167] ms lies wholly above 150 ms, and p95 is 305 ms against 200.
   - Even the repository's cleanest record (66 / 103 ms, one request at a time) fails at 50 concurrent. Holding p50
     at 150 ms with 50 requests in flight needs about 50 / 0.15 ≈ 333 requests per second. Measured capacity is 12.8
     (about 26× short); even on the cleaner record with the measured 2.5× batching gain it would be about 38 (about
     9× short).

## 4. Quality — held-out test set

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this section was produced by `scratchpad/ml_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.
> The set's composition (17,942 rows from 9 sentences, 4 CRITICAL) **is** reproducible: DATASET_AUDIT §10. The metrics and intervals are not.

### 4.1 What the test set actually is

- Manifest `dataset/processed/eval_manifest_phrase_v2.json`: 34,425 eval rows, **Kinyarwanda only**, 8 held-out
  phrase groups / 15 phrases, leakage `exact_text_overlap 0, phrase_overlap 0, substring_violations 0`
  (re-checked in DATASET_AUDIT §4).
- Training split these into **stopping** groups (3 groups, 6 phrases, 16,483 rows; 900 sampled for early
  stopping) and **reporting** groups (5 groups, **9 distinct phrases, 17,942 rows, 4 CRITICAL phrases**). The
  reporting subset is the only data no training decision touched, so it is the test set used below.
- **17,942 rows are 9 sentences** surrounded by frame text. The spec's n=100,000 and ≥10,000 per language do
  not exist. English, French, Swahili and all 6 mixed combinations have **zero** evaluation rows.

### 4.2 The 15 gate metrics (v2d, reporting set) with 95% bootstrap CIs

Two CIs are reported because they answer different questions. **Row-level** (1,000 resamples of rows) treats
17,942 rows as independent — they are not. **Phrase-cluster** (1,000 resamples of the 9 phrases) is the honest
one: it asks how the number would move with a different draw of sentences. Use the cluster CI.

| # | Metric | Threshold | Measured | Row-level 95% CI | **Phrase-cluster 95% CI** | Verdict |
|---|---|---|---|---|---|---|
| 1 | Overall accuracy | ≥ 0.82 | **0.7065** | [0.700, 0.713] | **[0.400, 0.914]** | NOT MET |
| 2 | Weighted F1 | ≥ 0.83 | **0.6953** | [0.689, 0.702] | [0.412, 0.927] | NOT MET |
| 3 | Macro F1 | ≥ 0.80 | **0.7724** | [0.767, 0.778] | [0.269, 0.908] | NOT MET |
| 4 | CRITICAL precision | ≥ 0.88 | **0.6633** | [0.655, 0.672] | [0.021, 0.989] | NOT MET |
| 5 | CRITICAL recall (each pure language) | ≥ 0.91 | **0.8504** (KW) | [0.843, 0.858] | **[0.077, 1.000]** | NOT MET (KW); NOT MEASURABLE (EN/FR/SW — no data) |
| 6 | CRITICAL F1 | ≥ 0.89 | **0.7453** | — | — | NOT MET |
| 7 | CRITICAL→ROUTINE FNR | < 1.0% | **0.00%** (0 / 8,962) | [0, 0] | [0, 0] | **NOT DEFENSIBLY MET** — 4 CRITICAL sentences; §6.1 probe contradicts it |
| 8 | URGENT recall | ≥ 0.86 | **0.4963** | [0.486, 0.507] | [0.155, 0.850] | NOT MET |
| 9 | Kinyarwanda accuracy | ≥ 0.80 | **0.7065** | as #1 | as #1 | NOT MET |
| 10 | English accuracy | ≥ 0.86 | — | — | — | NOT MEASURABLE: no English eval rows; model never saw English |
| 11 | French accuracy | ≥ 0.84 | — | — | — | NOT MEASURABLE |
| 12 | Swahili accuracy | ≥ 0.80 | — | — | — | NOT MEASURABLE |
| 13 | Mixed-language accuracy | ≥ 0.82 | — | — | — | NOT MEASURABLE: 0 mixed rows in v2 |
| 14 | Latency p50 / p95 | < 150 / < 200 ms | see §3 | — | — | see §3 |
| 15 | Memory @ 50 concurrent | < 2 GB | see §3 | — | — | see §3 |

The phrase-cluster CI for CRITICAL recall spans **0.08 to 1.00**. With four CRITICAL sentences the evaluation
cannot distinguish a safe model from a dangerous one. **No amount of retraining changes that; only more
distinct, validated sentences do.**

### 4.3 Confusion matrices (rows = true, columns = predicted; order CRITICAL, URGENT, ROUTINE)

**v2d, overall = Kinyarwanda (the only language):**

```
              CRIT   URG   ROUT
CRITICAL      7621  1341      0
URGENT        3869  3868     56
ROUTINE          0     0   1187
```

The model over-triages URGENT to CRITICAL (49.6% of URGENT) — the safer direction — and never predicts ROUTINE
for a CRITICAL row *in this set*. Predicted distribution: CRITICAL 11,490 / URGENT 5,209 / ROUTINE 1,243.

**saved_model (for completeness):**

```
              CRIT   URG   ROUT
CRITICAL      4749  2392   1821
URGENT        4027  2613   1153
ROUTINE        289   832     66
```

accuracy 0.414, macro F1 0.314, CRITICAL recall 0.530, **CRITICAL→ROUTINE 20.3%**.

Per-language confusion matrices for EN/FR/SW/mixed: **NOT MEASURABLE** (no data).

### 4.4 The model underfits its own training data

On 3,000 rows sampled from the **training** file (first 200,000 rows, so ROUTINE is under-represented): accuracy
**0.743**, URGENT correctly predicted on only 794 / 1,502. A model that gets a quarter of *seen* sentences wrong
is capacity- or schedule-limited (8 of 12 layers frozen, lr 1e-5, early-stopped at step 900 of 2,000 on a
900-row, 6-phrase stopping set), not merely failing to generalise.

---

## 5. Calibration

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this section was produced by `scratchpad/ml_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.

| | ECE (15 equal-width bins) |
|---|---|
| Reporting set, raw softmax | **0.188** |
| Stopping split (the only validation-like split), raw | **0.179** |
| Reporting set after temperature scaling fitted on stopping split (T = 0.45, grid 0.25–5.0 on NLL) | 0.127 |
| Threshold | ≤ 0.05 |

**Reliability table, v2d reporting set (raw):**

| confidence bin | n | mean confidence | accuracy |
|---|---|---|---|
| (0.33, 0.40] | 30 | 0.378 | 0.600 |
| (0.40, 0.47] | 185 | 0.452 | 0.578 |
| **(0.47, 0.53]** | **15,852** | **0.497** | **0.689** |
| (0.53, 0.60] | 662 | 0.541 | 0.668 |
| (0.60, 0.67] | 6 | 0.645 | 0.000 |
| (0.67, 0.73] | 12 | 0.700 | 0.167 |
| (0.73, 0.80] | 260 | 0.786 | 0.969 |
| (0.80, 0.87] | 935 | 0.817 | 0.998 |

(A PNG reliability diagram was not produced; the table is the diagram's data.)

**Findings.**
1. **88% of predictions sit in a single confidence bin around 0.50**; the model is under-confident and its
   score carries almost no ranking information in that bin. Temperature scaling (T < 1, sharpening) reduces ECE
   to 0.127 but cannot reach 0.05 because the problem is concentration, not scale.
2. **93.4% of predictions have confidence < 0.75.** If FR-04-03 were implemented today with the default
   threshold, **93% of patients would be flagged for human review** — the threshold would be meaningless, as
   the spec anticipated. The frontend already labels the score "uncalibrated softmax value, not a probability"
   (`frontend/src/routes/Triage.tsx`), which is correct.
3. Calibration fitted on a 6-phrase stopping split will not transfer; it needs a validation set of many
   distinct sentences.

**Verdict: ECE ≤ 0.05 NOT MET.**

---

## 6. Safety

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this section was produced by `scratchpad/ml_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.

### 6.1 Red-flag probe — v2d (**illustrative, not a validated suite**)

Twenty inputs: the Kinyarwanda, English, French and Swahili terms in the backend's own `CRITICAL_TERMS`
list (`backend/app/services/triage_service.py:92`) plus short sentences built from them. These terms are
**unsourced** (L5) and I cannot vouch for the Kinyarwanda or Swahili as a clinician or native speaker would;
this is a probe, not a gold set.

| Input | Predicted | p(CRIT, URG, ROUT) |
|---|---|---|
| guhumeka nabi | **ROUTINE** | .288 .260 .452 |
| sinshobora guhumeka | **ROUTINE** | .217 .185 .598 |
| kuva amaraso | URGENT | .401 .411 .188 |
| amaraso menshi | URGENT | .434 .448 .118 |
| ububabare bw'igituza | URGENT | .432 .469 .099 |
| igituza kirababara | URGENT | .440 .472 .088 |
| yataye ubwenge | CRITICAL | .479 .444 .077 |
| kugagara | **ROUTINE** | .132 .133 .735 |
| umutima urahagarara | CRITICAL | .521 .422 .057 |
| Mfite ububabare bw'igituza kandi sinshobora guhumeka | CRITICAL | .503 .443 .054 |
| Umwana wanjye yataye ubwenge | CRITICAL | .493 .441 .066 |
| I have chest pain and cannot breathe | **ROUTINE** | .197 .240 .563 |
| He is unconscious | **ROUTINE** | .186 .229 .585 |
| heavy bleeding after delivery | **ROUTINE** | .286 .313 .402 |
| douleur thoracique, je ne peux pas respirer | **ROUTINE** | .094 .128 .779 |
| il a perdu connaissance | **ROUTINE** | .167 .195 .638 |
| nina maumivu ya kifua na siwezi kupumua | **ROUTINE** | .132 .159 .708 |
| amezimia | **ROUTINE** | .174 .211 .615 |
| kutokwa damu nyingi | **ROUTINE** | .137 .160 .703 |
| Mfite chest pain kandi sinshobora guhumeka | CRITICAL | .554 .383 .063 |

**11 / 20 → ROUTINE; 5 / 20 CRITICAL.** Every non-Kinyarwanda emergency input and every short Kinyarwanda
fragment went to ROUTINE — and several with the model's *highest* confidences in the whole probe (0.78 for the
French chest-pain sentence). The learned shortcut appears to be "unfamiliar or short text → ROUTINE". The API
accepts any text of ≥ 3 characters in any language (`backend/app/schemas/triage.py:19`), and no rules layer
runs first. **This is the single most dangerous behaviour found in the audit.**

### 6.2 The keyword "red-flag" list as a classifier — measured

The only red-flag logic in the codebase is `KeywordClassifier`, which the API serves **instead of** the model
whenever `TRIAGE_MODEL_PATH` is unset (the default) outside production.

| Set | n | accuracy | CRITICAL recall | CRITICAL→ROUTINE |
|---|---|---|---|---|
| v2 reporting set (Kinyarwanda, patient-voice) | 17,942 | 0.315 | **0.057** | **94.3%** |
| v1 regenerated, Kinyarwanda | 3,000 | 0.740 | 0.544 | 33.2% |
| v1 English | 3,000 | 0.644 | 0.526 | 47.4% |
| v1 French | 3,000 | 0.630 | 0.434 | 56.6% |
| v1 Swahili | 3,000 | 0.647 | 0.360 | 51.9% |
| v1 mixed | 3,000 | 0.675 | 0.473 | 47.9% |

The term list catches textbook phrasings ("sinshobora guhumeka") and misses how the corpus's patients describe
the same presentations. **It cannot be promoted to the L2 layer as is**; an L2 layer needs the §10.6 lexicon
with colloquial variants and a T1 validator. Every backend integration test that asserts a triage outcome
(`test_full_triage_path.py`, `test_triage_routes.py`) runs this baseline, not the model.

### 6.3 Language detection — measured (FR-04-08)

`detect_language()` (marker-word counts) on the regenerated v1 corpus (machine-drafted text; 3,000 rows each):
English 1.000, French 1.000, **Kinyarwanda 0.877** (12.3% → `unknown`), **Swahili 0.883**, **mixed 0.330**.
No language confidence is produced. Threshold ≥ 0.92 pure / ≥ 0.85 mixed: **NOT MET** for KW, SW, mixed.
No dedicated language-ID evaluation set exists.

---

## 7. Error analysis

> **NOT REPRODUCIBLE** (marked 2026-09-15): every measured figure in this section was produced by `scratchpad/ml_audit.py`, which was never committed and is no longer on disk (§9). Do not quote it. Not re-derived.

The spec asks for 100 sampled errors clustered. With 9 distinct sentences the clusters *are* the sentences.
100 errors sampled at random (seed 7) from 5,266 errors:

| True → Pred | Phrase (template) | Domain | n / 100 |
|---|---|---|---|
| URGENT → CRITICAL | {REL} afite umuriro wa dogere 39. *(relative has a 39° fever)* | infectious_fever | 57 |
| CRITICAL → URGENT | {REL} arimo kuva imyuna mu mazuru kandi ntahagarara. *(unstoppable nosebleed, third person)* | haemorrhage_trauma | 19 |
| CRITICAL → URGENT | Amazuru yanjye arimo ariva imyuna myinshi kandi ntahagarara. *(first person)* | haemorrhage_trauma | 10 |
| URGENT → CRITICAL | {REL} afite umuvuduko w'amaraso wazamutse cyane. *(high blood pressure)* | chronic_care | 9 |
| URGENT → CRITICAL | mfite umuriro wa dogere 39 | infectious_fever | 3 |
| URGENT → ROUTINE | fever 39°, both persons | infectious_fever | 2 |

Per-sentence accuracy (all rows): the first-person nosebleed sentence is **7.7%** correct (455 of 493 → URGENT),
the third-person fever sentence **13.8%**. Chest-pain + breathlessness sentences are 99.98–100%.

**What the model is bad at:**
1. **Third-person reports** ("my relative…") shift predictions toward CRITICAL: the same fever sentence is 42%
   correct in first person and 14% in third. Likely learned from a correlation between `{REL}` frames and
   CRITICAL in the templates (see DATASET_AUDIT §5).
2. **Haemorrhage not phrased as "amaraso" (blood).** "imyuna" (nosebleed) is missed as CRITICAL — the model
   keys on lexical tokens, not the presentation.
3. **Out-of-distribution input** (§6.1): other languages and short fragments collapse to ROUTINE.
4. Whether "unstoppable nosebleed" *should* be CRITICAL is a clinical question; the taxonomy is unapproved
   (`ml_model/docs/protocols/d2-clinician-review-pack.md`).

---

## 8. Verdict per threshold and recommendation

> **Rests on NOT REPRODUCIBLE measurements** (§1.3–§7). The deployment gate, which is reproducible, reaches the same end by refusal: 0 of 45 gate cells can be measured on the current set (DATASET_AUDIT §10).

| Gate | Verdict |
|---|---|
| Metrics 1–4, 6, 8, 9 | **NOT MET** |
| Metric 5 CRITICAL recall | **NOT MET** (KW); **NOT MEASURABLE** (EN/FR/SW) |
| Metric 7 CRITICAL→ROUTINE | **NOT DEFENSIBLY MET** (0% on 4 sentences; 55% on the probe) |
| Metrics 10–13 | **NOT MEASURABLE** — no data |
| Metrics 14–15 | see §3 |
| Red-flag suite 100% | **MISSING** |
| ECE ≤ 0.05 | **NOT MET** (0.179) |
| Language ID | **NOT MET** |
| Leakage | **MET** (phrase split) |

**The thresholds cannot be met by retraining on the current data**, and I will not propose lowering any. The
binding constraint is the evaluation base, not the optimiser. Proposed order (detail in REMEDIATION_PLAN):

1. **Stop the bleeding in the service first** (independent of any model): pre-model escalate-only rules layer
   with an out-of-distribution guard — unknown language, very short input, or low calibrated confidence →
   `requires_human_review=True`, never ROUTINE.
2. **Lexicon + a real test set before any retraining** (§10.6 / §10.7): the evaluation must contain hundreds of
   distinct, clinician-labelled CRITICAL sentences per language before a recall number means anything.
3. Then retrain with: base revision pinned; unfreeze more layers (the model underfits its training set);
   explicit cost matrix (CRITICAL→ROUTINE ≫ adjacent errors) instead of inverse-frequency weights that are
   ≈ 1.0 on balanced data; an OOD "none of the above" signal; calibration on a many-sentence validation split;
   baselines (AfriBERTa, XLM-R, Serengeti) per §10.8.

---

## 9. Re-running these measurements

The scripts are in the session scratchpad, deliberately not committed during a read-only audit. If you approve,
they belong under `ml_model/audit/` with a `make audit-model` target.

```
backend/venv/bin/python ml_audit.py <outdir>          # provenance, tokens, metrics, CIs, ECE, probes (~2 h on this laptop under swap)
backend/venv/bin/python latency_audit.py <outdir> inproc
backend/venv/bin/python latency_audit.py <outdir> http
```
