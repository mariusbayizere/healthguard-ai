# PRELIMINARY — first training run on the labelled Kinyarwanda corpus

**Run:** `ml_model/review/runs/kw_v1_prelim`, seed 42, 2026-09-23.
**Split:** `ml_model/dataset/splits/kw_v1`, frozen at seed 20260920, corpus SHA-256
`d7e1b314…2264f`. Hold-out unit is the source sentence.

> **PROVENANCE, attached to every figure below.** Single non-clinician annotator (the
> paper's author). No second rater. No agreement statistic. **These labels are not
> clinical ground truth.** Nothing here is a gate verdict and none of it belongs in the
> paper.

## 1. The refusal is the headline

`training/pipeline.py`, unmodified, **refused this split at step 1 and exited 2 before
reading a training row.** Sixteen gate cells are INSUFFICIENT DATA. The tightest:

| Gate | Metric | Have | Need |
|---|---|---|---|
| 7 | CRITICAL → ROUTINE rate | 35 | 720 |
| 5 | CRITICAL recall, Kinyarwanda | 35 | 365 |
| 3 | macro F1 | 35 | 570 |
| 8 | URGENT recall | 164 | 570 |
| 1 | overall accuracy | 447 | 710 |
| 9 | Kinyarwanda accuracy | 447 | 780 |
| X-ECE | expected calibration error | 447 | 2,000 |

174 CRITICAL sentences exist across all three splits. **No split of this corpus funds any
safety gate**; reaching gate 7 needs roughly four times the corpus, not a different
slice. Gate 4 reports NOT KNOWN rather than insufficient — its denominator is the model's
own predictions. Gates 10–13 refuse at n=0: this arm is Kinyarwanda only.

A **second, independent refusal** came from `training/thresholds.py`:

```
ThresholdsRefused: no gold CRITICAL rows in the calibration split for
english, french, swahili: CRITICAL recall cannot be constrained there
```

Gate 5 is a per-pure-language constraint and three of the four languages are absent, so
**no thresholds were tuned and no thresholded decision exists.** Relaxing the constraint
to the languages that happen to be present would be re-slicing a requirement to fit the
corpus. Argmax over calibrated probabilities is reported instead.

## 2. The model does not beat always-ROUTINE

**Accuracy 0.3870 [0.3400, 0.4295] against a majority baseline of 0.5548 [0.5101,
0.5996], n = 447 distinct sentences. The intervals do not overlap: the model is
significantly worse than predicting ROUTINE for everything.**

| | Baseline (always-ROUTINE) | Model |
|---|---|---|
| accuracy | 0.5548 [0.5101, 0.5996] | **0.3870 [0.3400, 0.4295]** |
| CRITICAL → ROUTINE rate | 1.0000 | 0.0000 |

The one number the model wins is an artefact of where it collapsed, not of learning: it
sent all 35 CRITICAL cases to URGENT, so none reached ROUTINE.

## 3. Per class, cluster-bootstrap intervals resampling the sentence

2,000 resamples of the sentence, never the row. `nan` where the class is never predicted.

| Class | n (sent.) | Precision | Recall | F1 |
|---|---|---|---|---|
| CRITICAL | 35 | nan (never predicted) | 0.0000 [0.0000, 0.0000] | nan |
| URGENT | 164 | 0.3727 [0.3271, 0.4165] | 0.9817 [0.9588, 1.0000] | 0.5403 [0.4898, 0.5850] |
| ROUTINE | 248 | 0.8000 [0.5625, 1.0000] | 0.0484 [0.0229, 0.0772] | 0.0913 [0.0444, 0.1418] |

Confusion, rows gold and columns predicted, order CRITICAL / URGENT / ROUTINE:

```
CRITICAL [  0,  35,   0]
URGENT   [  0, 161,   3]
ROUTINE  [  0, 236,  12]
```

**The CRITICAL column is empty. The model never predicted CRITICAL once in 447 items.**

### Weighting, calibration

Weighting as committed: **no class-frequency weights.** Cross-entropy is unweighted and
the mechanism is the cost matrix in `training/cost_loss.py`, `cost_weight` 1.0:

```
            pred C   pred U   pred R
gold C        0.0      1.0     10.0
gold U        1.0      0.0      1.0
gold R        1.0      1.0      0.0
```

Temperature fitted on the 223-sentence calibration split: **0.1659** — a sharpening, not
a softening. **It made calibration worse on test:** ECE 0.0199 [0.0018, 0.0691] before,
**0.0984 [0.0611, 0.1469] after.** With 223 calibration sentences against the 2,000 the
X-ECE gate asks for, the honest reading is that the temperature is fitted to noise.

## 4. Probe suite on the checkpoint

| Check | This run | v2d |
|---|---|---|
| capitalisation flip | 24.0% | 31.5% |
| typos flip | 5.5% | 21.0% |
| punctuation flip | 6.0% | 5.0% |
| whitespace flip | 0.0% | 0.0% |
| predicted classes | CRITICAL 0, URGENT 196, ROUTINE 4 | CRITICAL 102, URGENT 33, ROUTINE 65 |
| mean p per class | C 0.27, U 0.37, R 0.36 | C 0.36, U 0.33, R 0.31 |
| highest p(CRITICAL) | 0.28 | 0.55 |
| determinism / validity / encoding / label order / length | all pass | all pass |

`id2label` is `{0: CRITICAL, 1: URGENT, 2: ROUTINE}` — no off-by-one.

**The flip-rate comparison is not like for like and should not be read as an
improvement.** v2d was probed on 200 texts drawn from the v2 phrase holdout, which holds
34,425 rows from **15 distinct source sentences**; this run was probed on 200 texts from
a split of **447 distinct sentences**. The v2d figure measures surface sensitivity over
15 sentences. Two malfunction signals fire here: surface invariance, and **class collapse
— URGENT is 98% of predictions.**

## 5. One epoch, or the labels?

**Not distinguishable, and nothing here should be attributed to the labels.**

The budget is 1,566 rows at batch 16 for 1 epoch — **98 optimisation steps**, of which
~6 are warmup, at a peak learning rate of 1e-5, onto a **randomly initialised**
classification head (`classifier.*` MISSING in the load report). Mean probabilities
C 0.27 / U 0.37 / R 0.36 and a maximum p(CRITICAL) of 0.28 are what a barely-moved head
looks like: near-uniform, with the cost term's preference already visible and nothing
else.

The collapse target is the tell. An undertrained model drifts to the **majority** class,
which here is ROUTINE at 55%. This one collapsed to **URGENT at 37%** — the class that
the cost matrix makes safest, costing 1 against a true CRITICAL and 1 against a true
ROUTINE, never the 10 that CRITICAL → ROUTINE costs. That is the objective behaving
exactly as designed on a model with no signal to override it.

So the observation is jointly explained by an untrained head and a correctly-working cost
term. **The labels are not implicated, and they are not exonerated either** — this run
carries no information about them, because the model never trained far enough to express
whatever signal they do or do not contain. Any statement about label quality would need a
budget where the model demonstrably fits the training set first.

## Machine

Two threads, as committed. Free memory 3,972 MB before training, 3,473 MB after the
single epoch; training took 417.9 s. No OOM. Leakage check **clean** — the check the
pipeline never reached, run here on the same word-3-gram Jaccard ≥ 0.85 comparison.

## Local gates (local, not CI)

`ruff check` clean, `ruff format --check` clean across 179 files, `pytest ml_model/tests`
**493 passed, 3 skipped**. CI is unverified: `gh` is not authenticated in this session.
