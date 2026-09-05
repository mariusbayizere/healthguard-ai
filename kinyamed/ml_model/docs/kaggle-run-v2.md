# Kaggle run: v2, phrase split, manifest v2

Cells to paste in order. **Read the four warnings at the bottom before you gate on
anything** — three of them change what the resulting numbers mean, and warning 3
is new in v2 and reverses what the v1 playbook said.

Supersedes `docs/kaggle-run-v1.md`, which stays as the record of the v1 run and
whose numbers do not carry over. **v2 is a different corpus, not a newer version
of the same one:** monolingual Kinyarwanda, 330,000 rows from 165 speaker-authored
phrases, against v1's four languages, 1,000,000 rows and 184 template-drafted
phrases. A v1 number and a v2 number do not belong in one table.

## Cell 1 — GPU assertion, before anything else

```python
import torch, subprocess
print(subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv"],
                     capture_output=True, text=True).stdout)
assert torch.cuda.is_available(), "No GPU. Settings -> Accelerator -> GPU, then restart."
print("torch", torch.__version__, "| cuda", torch.version.cuda)
```

## Cell 2 — clone, install only what is missing

```python
!git clone -q https://github.com/mariusbayizere/healthguard-ai.git
%cd healthguard-ai/kinyamed/ml_model
# NOT -r requirements.txt: it pins torch==2.12.0+cpu and would replace the CUDA build.
!pip install -q transformers==5.8.1 scikit-learn==1.8.0 pandas==2.3.3
import torch; assert torch.cuda.is_available(), "CUDA lost during install — stop here."
print("cuda still available after install:", torch.cuda.is_available())
```

## Cell 3 — rebuild the data and verify it against the committed manifests

```python
# 330,000, not 1,000,000: v2's target is 165 phrases x 2,000 rows. Passing v1's
# number here would produce a corpus no manifest describes.
!python dataset/generate_large_dataset.py --target 330000 --seed 42
!python dataset/split_dataset.py --strategy phrase
!python dataset/split_dataset.py --strategy family
!python dataset/freeze_eval.py --strategy phrase --verify
!python dataset/freeze_eval.py --strategy family --verify
```

Both verifies must print `Eval set matches the frozen manifest.` If either does
not, **stop**: the rows on this machine are not the rows the manifest describes,
and nothing produced from them compares to anything produced elsewhere.

`--corpus-version` defaults to 2 and does not need passing. Pass
`--corpus-version 1` only to re-derive the v1 corpus, which is a separate
experiment with separate manifests.

**Optional, and worth the two minutes if anything looks wrong:**

```python
!python verify.py --scope full     # 14 checks: v1 AND v2 both re-derive from seed 42
```

## Cell 4 — persistent checkpoint directory

```python
import os
CKPT = "/kaggle/working/checkpoints"; os.makedirs(CKPT, exist_ok=True)
SAVE  = "/kaggle/working/saved_model_holdout"
TEX   = "/kaggle/working/generated"
```

`/kaggle/working` survives as notebook output. Commit the notebook version before
the session times out, or the checkpoint is lost with the session.

## Cell 5 — train

```python
!python training/train_holdout.py \
    --manifest dataset/processed/eval_manifest_phrase_v2.json \
    --epochs 20 \
    --batch-size 96 \
    --max-length 64 \
    --no-freeze-embeddings \
    --checkpoint-every 500 \
    --checkpoint-path {CKPT}/train_state.pt \
    --save-path {SAVE} \
    --log-every 100
```

**`_v2`, not `_v1`.** The trainer fingerprints the split digests, so pointing it
at the v1 manifest trains on a corpus that is not on this machine and fails
loudly — but check the filename anyway, because a stale copy of the v1 manifest
would let it start.

**20 epochs on v2 is a third of the steps v1 took.** 295,575 training rows at
batch 96 is 3,079 steps per epoch, 61,580 in total, against v1's 187,500. Wall
clock falls roughly in proportion. Whether 20 remains the right number for a
smaller corpus is an open question — start here for comparability of *protocol*,
not of result, and read the loss curve rather than assuming.

Re-running this identical command after a disconnect resumes from the last
checkpoint. The fingerprint covers the split digests and every hyperparameter, so
changing any flag correctly starts over rather than resuming into a model no
manifest describes.

## Cell 6 — the primary number

```python
!python training/evaluate.py \
    --model {SAVE} \
    --manifest dataset/processed/eval_manifest_phrase_v2.json \
    --tex-out {TEX}
```

`evaluate.py` verifies every digest in the manifest before it trusts a row, so a
mismatched split fails here rather than producing a number quietly. **Its
`--manifest` default still points at `_v1`** — pass `_v2` explicitly, as above.

Prints per-class **precision, recall and F1** plus the confusion matrix. Read
precision alongside recall: the v1 smoke run reached 0.876 CRITICAL recall purely
by predicting CRITICAL for 86% of rows, at 0.34 precision. High recall with low
precision is the degenerate failure, not a result.

The phrase holdout is the primary number: 34,425 eval rows, **0 of them sharing a
phrase with training**, `substring_violations: 0`,
`eval_rows_leaked_fraction: 0.0`. That is the claim the corpus exists to support.

## Cell 7 — bring back exactly three files

```python
!cp {TEX}/results_macros.tex {TEX}/results_table.tex training/last_run.json /kaggle/working/
```

Download those three. Put the two `.tex` files in
`kinyamed/ml_model/paper/generated/`, replacing the TBD placeholders, and commit.
Check the header of `results_macros.tex` carries a `% source_sha256:` line
matching **v2's** committed manifest — `make test` fails if a macros file carries
concrete numbers without that provenance block, and the v1 digest will no longer
match.

---

## Warning 1 — three of the four gate values have no source

Unchanged from v1 and still true: if you are gating a release on accuracy,
macro-F1, per-class recall and calibration, only one of those four thresholds was
derived from anything. The others were chosen because they sounded right. Decide
them before you see the numbers, or you are choosing a threshold to fit a result.

## Warning 2 — tuning the threshold on the frozen eval destroys the frozen eval

Unchanged from v1. The eval set is frozen so that a number computed on it means
something. Selecting a decision threshold by trying several and keeping the best
turns it into a validation set, and the frozen digest then certifies a number that
has been fitted. Doing it properly needs a validation split that does not exist
yet.

## Warning 3 — NEW IN v2, and it reverses the v1 playbook

**The v1 playbook said the family holdout was 89.2% contaminated and not a valid
secondary number. In v2 it is 0.0% contaminated — and that is a loss, not a fix.**

```
                          v1                      v2
phrase-eval / train       0% overlap              0% overlap
family-eval / train       89.2%  (101,945 rows)   0.0%  (0 of 24,900)
```

In v1 one phrase fed up to ten families — four languages plus six mixed pairs —
so holding out a family left that phrase's other rows in training. **v2 is
monolingual, so each phrase belongs to exactly one family**, and holding out a
family removes its phrases entirely.

**What this means for the run:** you may now train a second model on
`train_family_holdout.csv` and evaluate it on `eval_family_holdout.csv` and get an
honest number — but it will measure almost the same thing as the phrase run.
**v2 does not have two difficulty levels.** It has one strictness at two sampling
ratios, 10.43% and 7.55%. Reporting the two as easy and hard would be false.

**Never quote 89.2% in a v2 context.** It is a v1 measurement of a v1 property.

## Warning 4 — NEW IN v2: 23 held rows are out of the corpus by design

Four of them are authored phrases the speaker wrote and then held: `CR04` both
persons and `OB06` both persons. They are excluded because they are unresolved,
not because they are bad — `CR04` has two rival clinical descriptions and neither
was chosen, and `OB06`'s wording turned out to mean fetal demise while its label
said URGENT.

That is roughly 9% of the brief absent from training and from both eval sets. It
is documented in `docs/session-state.md` with a reason per row, and it is a
limitation to disclose rather than a gap to explain away: the corpus covers what
a Kinyarwanda speaker was willing to sign off, which is not the same as covering
the clinical space.
