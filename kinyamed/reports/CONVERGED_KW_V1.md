# PRELIMINARY — encoder-only run trained to convergence, Kinyarwanda

**Run:** `ml_model/review/runs/kw_v1_converged`, seed 42, 2026-09-23.
**Split:** `ml_model/dataset/splits/kw_v1`, frozen at seed 20260920.

> **PROVENANCE, attached to every figure below.** Single non-clinician annotator (the
> paper's author). No second rater. No agreement statistic. **These labels are not
> clinical ground truth.** Nothing here is a gate verdict and none of it belongs in the
> paper. The gate refusals in `reports/PRELIMINARY_KW_V1.md` stand unchanged.

## Scope change — read this before any number

**This run fits the twelve encoder layers and the classification head only.** The
embedding matrix is frozen, so **the model cannot adapt its Kinyarwanda subword
representations**: whatever AfroXLMR already believes a Kinyarwanda wordpiece means is
what it still believes at the end. Only 21,442,563 of 117,641,859 parameters — 18.2% —
were trainable.

**This is a different experiment from the one-epoch run, not the same experiment given a
longer budget.** No figure here should be compared with that run as though only the
budget changed.

The reason is memory: full fine-tuning at this budget needs ~3.9 GiB because gradients
and Adam state scale with trainable parameters, and 96.2M of 117.6M parameters (81.8%)
are one 250,002-row vocabulary matrix. This machine has ~3.2 GiB. Two arguments say the
freeze is defensible rather than a dodge, and both would hold with memory to spare:

1. **117M parameters fitted on 1,332 rows is over-parameterised by any reading.**
   Freezing 82% of them is regularisation one would plausibly choose anyway.
2. **Layer freezing is this project's existing precedent, not an invention for a memory
   problem.** The v2d checkpoint is `model_v2d_freeze8_lr1e-5`.

## The budget was fixed before evaluation, and the chain is auditable

`budget.json` was written at **2026-09-23T05:13:33+0200**, before the first attempt read
anything. That attempt was killed under memory pressure having produced only that file,
so it never read the test split. **This run reused that file byte for byte rather than
rewriting it**, and recorded the two memory changes in a sibling `budget_amendment.json`.
The pre-commitment therefore predates every number below, and the ordering is evidenced
by the files rather than asserted.

Max 20 epochs, patience 3, early stopping on validation loss over a slice of the
**training** split carved by source sentence and stratified by class (fit 1,332 rows /
1,331 sentences; validation 234 rows / 234 sentences; zero scenario overlap; leakage
check clean). Checkpoint selected by lowest validation loss, never by test. Learning rate
left at the committed 1e-5, deliberately not tuned alongside the budget. **Test read
once, after training finished and the checkpoint was already chosen.**

## 1. Loss curve

| ep | train | val | val_acc | s | free MB |
|---|---|---|---|---|---|
| 1 | 1.99164 | 1.95270 | 0.4615 | 155 | 1953 |
| 2 | 1.90845 | 1.86293 | 0.3675 | 129 | 2016 |
| 3 | 1.85814 | 1.83409 | 0.3718 | 279 | 2190 |
| 4 | 1.83697 | 1.81498 | 0.4060 | 229 | 2284 |
| 5 | 1.80985 | 1.76367 | 0.4957 | 294 | 1801 |
| 6 | 1.72912 | 1.72102 | 0.5983 | 224 | 2286 |
| 7 | 1.63113 | 1.60050 | 0.6453 | 303 | 2810 |
| 8 | 1.52759 | 1.54531 | 0.6496 | 237 | 2775 |
| 9 | 1.43728 | 1.50437 | 0.6325 | 284 | 3128 |
| 10 | 1.37013 | 1.46141 | 0.6496 | 231 | 3361 |
| 11 | 1.29633 | 1.51359 | 0.6752 | 162 | 3117 |
| 12 | 1.23493 | 1.40577 | 0.6538 | 128 | 2653 |
| 13 | 1.20643 | 1.43797 | 0.6667 | 186 | 2765 |
| 14 | 1.16533 | 1.44453 | 0.6709 | 94 | 2743 |
| **15** | **1.13869** | **1.35737** | **0.6667** | 91 | 2775 |
| 16 | 1.09421 | 1.36173 | 0.6624 | 203 | 2629 |
| 17 | 1.06883 | 1.39801 | 0.6624 | 264 | 2397 |
| 18 | 1.06988 | 1.39141 | 0.6624 | 101 | 2492 |

**It fit.** Train loss fell monotonically 1.9916 -> 1.0699, and validation followed it
down to epoch 15 before turning. Train crossed below validation at epoch 8 and the gap
widened from there. This is the question the one-epoch run could not answer: the model
does learn the training data.

## 2. The epoch kept

**Epoch 15, validation loss 1.35737.** Early stop fired at epoch 18 after three epochs
without improvement (16, 17, 18) — it stopped on its own rather than reaching the cap.
Eighteen epochs in 3,764 s (62.7 min).

Selection used validation loss only. Note epoch 11 had the highest validation
*accuracy* (0.6752) and was not selected, which is the pre-committed rule doing its job
rather than being overridden after the fact.

## 3. The single test evaluation

n = 447 distinct source sentences. 2,000 cluster-bootstrap resamples of the sentence.

**The model beats always-ROUTINE.**

| | Baseline | Model (epoch 15) |
|---|---|---|
| accuracy | 0.5548 [0.5101, 0.5996] | **0.6398 [0.5951, 0.6846]** |

Those marginal intervals overlap by 0.0045, which settles nothing either way —
overlapping marginal intervals are a well-known trap, since non-overlap implies a
difference but overlap does not imply its absence. The correct test is paired, on the
same items, computed from the one saved prediction set (no second inference, no second
model):

**difference +0.0850, 95% interval [+0.0291, +0.1432], excluding zero; the model wins in
99.9% of resamples.**

| Class | n | Precision | Recall | F1 |
|---|---|---|---|---|
| CRITICAL | 35 | 1.0000 [1.0000, 1.0000] (n=2 predicted) | **0.0571 [0.0000, 0.1481]** | 0.1081 [0.0465, 0.2667] |
| URGENT | 164 | 0.5149 [0.4466, 0.5833] | 0.6341 [0.5576, 0.7066] | 0.5683 [0.5060, 0.6257] |
| ROUTINE | 248 | 0.7407 [0.6882, 0.7952] | 0.7258 [0.6735, 0.7818] | 0.7332 [0.6907, 0.7765] |

```
              pred C  pred U  pred R
gold CRITICAL      2      30       3
gold URGENT        0     104      60
gold ROUTINE       0      68     180
```

**The safety picture is bad, and it is the part that matters.** The model found 2 of 35
CRITICAL cases. CRITICAL precision of 1.0000 is not a strength — it is two predictions,
both right, and the interval is degenerate because there is nothing to resample.
**CRITICAL -> ROUTINE ran at 0.0857 [0.0000, 0.1944]**, three cases of thirty-five,
against gate 7's threshold of below 0.01. Even taking the interval's floor seriously, the
point estimate is 8.6x the limit. A model that fits its training data and still misses
94% of CRITICAL cases has said something, and it is not encouraging.

Calibration: ECE 0.0801 [0.0521, 0.1263] before temperature scaling, **0.0578 [0.0326,
0.1038] after**, temperature 1.1305. Scaling helped this time, unlike the one-epoch run
where a 0.1659 sharpening made it worse. It remains above the 0.05 gate, on 447 sentences
against the 2,000 that gate wants.

**Thresholds refused again**, same structural reason: gate 5 constrains CRITICAL recall
in each pure language and this arm is Kinyarwanda only, so three of four languages have
no CRITICAL rows to constrain. Argmax reported; refusal recorded.

## 4. What this run does and does not license

It answers the question the first run could not: **the model fits the training set and
still generalises only weakly, and it fails the safety class outright.** That is a result
about the corpus and the label set, where the first run's collapse was a result about the
budget.

It does **not** license a statement about label quality on its own. The embeddings are
frozen, so a plausible competing explanation survives: AfroXLMR's pretrained Kinyarwanda
subword representations may simply not separate CRITICAL from URGENT, and no amount of
encoder fitting would fix that. Distinguishing "the labels are noisy" from "the frozen
representations cannot express the distinction" needs a full fine-tune, which this machine
cannot fund at this budget.

## Machine

| | |
|---|---|
| peak RSS (VmHWM at exit) | **2,208 MB** |
| projected before the run | 1,710 MB |
| training | 3,764 s, 18 epochs, 2 threads |

**My projection was 498 MB low** — the estimate omitted the transient cost of
`save_pretrained` overlapping live optimiser state, and allocator fragmentation across a
62-minute run. It fit with ~1 GiB to spare, but the margin was smaller than advertised.

### Hardware finding

**This machine does not fund twenty epochs of full fine-tuning, at about 3.9 GiB, and
does fund twenty epochs of encoder-only fine-tuning, measured at 2.21 GiB peak.** The
constraint bounds *what* can be trained rather than ruling the experiment out. It belongs
beside the 43-hour sweep measurement as a fact about the hardware.

Rejected alternatives, with reasons: gradient accumulation with a smaller batch saves
~50 MB for 4x the step count, because weights, gradients and optimiser state are all
batch-independent; fp16/bf16 is unavailable, the CPU reporting AVX2 with no
`avx512_bf16` and no `amx_bf16`, and Adam state stays fp32 under autocast regardless.
Neither change alone clears the margin: all-trainable with weights streamed to disk still
peaks at ~2.74 GiB against a 3.0 GiB ceiling.
