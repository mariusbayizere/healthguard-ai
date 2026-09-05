# Kaggle run: 20 epochs, phrase split, manifest v1

> **SUPERSEDED for new runs by `docs/kaggle-run-v2.md`.** Kept as the record of
> the v1 run. Everything below describes the v1 corpus — four languages,
> 1,000,000 rows, 184 template-drafted phrases — and **none of its numbers carry
> over to v2**, which is monolingual Kinyarwanda, 330,000 rows, 165
> speaker-authored phrases. A v1 result and a v2 result are not the same
> experiment and do not belong in one table.
>
> **Warning 3 below is NOT reversed in v2 — it is stronger.** Its subject is
> CROSS-SPLIT contamination: evaluating the *phrase*-trained model on
> *family*-eval. That was 89.2% in v1 and is **100.0% in v2** (24,900 of 24,900),
> because the two v2 eval sets are disjoint, so everything one holds out the other
> trains on. What v2 fixed is the different, WITHIN-split question — family-eval
> against family-train is 0.0%. Do not read the 0.0% as licence to take the
> shortcut this warning forbids. Do not carry the 89.2% figure into any v2 context
> either; the v2 number for the same comparison is 100%. See `docs/v2-sizing.md`.

Cells to paste in order. Read the three warnings at the bottom before you gate on
anything — two of them change what the resulting numbers mean.

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
!python dataset/generate_large_dataset.py --target 1000000 --seed 42
!python dataset/split_dataset.py --strategy phrase
!python dataset/split_dataset.py --strategy family
!python dataset/freeze_eval.py --strategy phrase --verify
!python dataset/freeze_eval.py --strategy family --verify
```

Both verifies must print `Eval set matches the frozen manifest.` If either does
not, **stop**: the rows on this machine are not the rows the manifest describes,
and nothing produced from them compares to anything produced elsewhere.

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
    --manifest dataset/processed/eval_manifest_phrase_v1.json \
    --epochs 20 \
    --batch-size 96 \
    --max-length 64 \
    --no-freeze-embeddings \
    --checkpoint-every 500 \
    --checkpoint-path {CKPT}/train_state.pt \
    --save-path {SAVE} \
    --log-every 100
```

Re-running this identical command after a disconnect resumes from the last
checkpoint. The fingerprint covers the split digests and every hyperparameter, so
changing any flag correctly starts over rather than resuming into a model no
manifest describes.

## Cell 6 — the primary number

```python
!python training/evaluate.py \
    --model {SAVE} \
    --manifest dataset/processed/eval_manifest_phrase_v1.json \
    --tex-out {TEX}
```

Prints per-class **precision, recall and F1** plus the confusion matrix. Read
precision alongside recall: the smoke run reached 0.876 CRITICAL recall purely by
predicting CRITICAL for 86% of rows, at 0.34 precision. High recall with low
precision is the degenerate failure, not a result.

## Cell 7 — bring back exactly three files

```python
!cp {TEX}/results_macros.tex {TEX}/results_table.tex training/last_run.json /kaggle/working/
```

Download those three. Put the two `.tex` files in
`kinyamed/ml_model/paper/generated/`, replacing the TBD placeholders, and commit.
Check the header of `results_macros.tex` reads

    % source_sha256: 751b8f57c195183ffc392959a58e2e6cbb0beb9c63caa3c15b7fb28530f4edec

matching the committed manifest. `make test` fails if a macros file carries
concrete numbers without that provenance block.

---

## Warning 1 — three of the four gate values have no source

`MINIMUM_CRITICAL_RECALL = 0.95` exists in the code. **`accuracy >= 0.82`,
`critical_f1 >= 0.88` and `weighted_f1 >= 0.83` appear nowhere** — not in this
repository, not in `docs/remote-training.md`, not in the project documentation.
They are targets someone chose before anything was trained, not thresholds
derived from a requirement. Record them as aspirations; do not present a run as
"passing" against them as though they were external criteria.

## Warning 2 — tuning the threshold on the frozen eval destroys the frozen eval

The instruction "if critical_recall falls short, apply class weights first, then
CRITICAL threshold adjustment" has a problem in its second half.

Class weighting is **already on and is not a lever here**. The loss is weighted by
inverse class frequency, but the corpus is deliberately balanced
(CRITICAL 33.0%, URGENT 34.0%, ROUTINE 33.0%), so the weights come out at
0.984 / 0.972 / 1.044 — within 5% of unity. Turning a knob already at 1.0 will not
move recall.

Adjusting the decision threshold until CRITICAL recall reaches 0.95 **on the eval
set, then reporting that eval set**, is fitting to the test data. The reported
number stops being a held-out estimate, and the whole frozen-manifest apparatus
stops meaning anything.

The correct procedure, if you want a tuned threshold:

1. carve a validation slice out of **train** (e.g. `--train-fraction 0.9`, holding
   the remaining 10% aside);
2. choose the threshold on that slice;
3. evaluate **once** on the frozen eval with the threshold fixed;
4. report the threshold and the slice it came from alongside the number.

I have not implemented threshold tuning, because doing it against the frozen eval
is the wrong thing and doing it properly needs a validation split that does not
exist yet. Say the word and I will add it.

## Warning 3 — v1 ONLY: the family holdout is not a valid secondary number for this model

**This warning applies to v2 as well, and more strongly — 100% rather than
89.2%.** What changed in v2 is a *different* measurement: family-eval against its
own family-train is now 0.0%, where the two splits' mutual contamination went to
its ceiling. See `docs/kaggle-run-v2.md` warning 3 and `docs/v2-sizing.md`.

**89.2% of family-eval rows (101,945 of 114,321) appear verbatim in the phrase
split's training set.** Both splits partition the same corpus on different axes,
so a model trained on `train_phrase_holdout` has already seen nearly all of
`eval_family_holdout`.

Evaluating this model there measures memorisation and will look flattering.

To get a real family-holdout number, train a **second** model on
`train_family_holdout.csv` and evaluate it on `eval_family_holdout.csv`. That is a
second 20-epoch run. If you want the number without the second run, report it
explicitly as contaminated — 89.2% seen during training — or omit it.
