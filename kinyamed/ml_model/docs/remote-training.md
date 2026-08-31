# Running the real training on a free GPU

20 epochs costs **~35 days** on the development laptop (2-core i5-6200U, measured
0.33 steps/s at batch 16, 0.37 with dynamic padding) and roughly **14–19 hours**
on a free Kaggle P100 or Colab T4. This is how to move the run without breaking
the chain that makes a reported number traceable.

## The key idea: ship the manifests, not the data

Do **not** upload the corpus. The pipeline is deterministic and pure standard
library, so the GPU machine regenerates it from seed 42 in about a minute
(measured: 15 s to generate, ~40 s to split) and checks the result against the SHA-256 digests already committed in
`eval_manifest_phrase_v1.json`.

That is stronger than uploading the CSVs. An upload proves only that some bytes
arrived; regenerating and verifying proves the remote machine holds *exactly* the
rows the manifest describes. The repository is 0.42 MB; the corpus and splits are
430 MB that never need to move.

    dataset/raw/symptoms_large.csv          181 MB   regenerated, never uploaded
    dataset/processed/*_holdout.csv         450 MB   regenerated, never uploaded
    dataset/processed/eval_manifest_*.json  10 KB    committed — this is the payload

## Kaggle

Enable the GPU accelerator, then:

```python
!git clone https://github.com/mariusbayizere/healthguard-ai.git
%cd healthguard-ai/kinyamed/ml_model
```

**Do not `pip install -r requirements.txt` there.** It pins `torch==2.12.0+cpu`,
which will replace the host's CUDA build with a CPU one and silently cost you the
entire speedup. Install everything except torch:

```python
!pip install -q transformers==5.8.1 scikit-learn==1.8.0 pandas==2.3.3
import torch; print(torch.__version__, torch.cuda.is_available())   # expect True
```

Rebuild the data and verify it against the committed manifest:

```python
!python dataset/generate_large_dataset.py --target 1000000 --seed 42
!python dataset/split_dataset.py --strategy phrase
!python dataset/freeze_eval.py --strategy phrase --verify
```

**That last command is the provenance gate.** It must print
`Eval set matches the frozen manifest.` If it does not, stop: the remote data is
not the data the manifest describes, and nothing produced from it is comparable
to anything produced here.

Train, writing checkpoints and the model to persistent storage:

```python
!python training/train_holdout.py \
    --manifest dataset/processed/eval_manifest_phrase_v1.json \
    --epochs 20 --batch-size 64 --max-length 64 \
    --checkpoint-every 500 \
    --checkpoint-path /kaggle/working/checkpoints/train_state.pt \
    --save-path /kaggle/working/saved_model_holdout
```

Then produce the paper's numbers:

```python
!python training/evaluate.py \
    --model /kaggle/working/saved_model_holdout \
    --manifest dataset/processed/eval_manifest_phrase_v1.json \
    --tex-out /kaggle/working/generated
```

## Colab

Identical, except mount Drive first and point `--checkpoint-path` and
`--save-path` inside it, so a disconnect does not lose the run:

```python
from google.colab import drive; drive.mount('/content/drive')
# --checkpoint-path /content/drive/MyDrive/healthguard/checkpoints/train_state.pt
```

## What to change for a GPU

| setting | laptop | GPU | why |
|---|---|---|---|
| `--batch-size` | 16 | 64–128 | the laptop is core-bound, not memory-bound |
| `--checkpoint-every` | 100–200 | 500–1000 | steps are far cheaper; checkpoints are not |
| `--freeze-embeddings` | on | **consider off** | 1.15 GB of optimiser state is affordable on a GPU, and fine-tuning the embeddings is likely worth more than the speed |
| `--threads` | 2 | leave unset | irrelevant on GPU |

Leave `--max-length 64` alone. Token lengths measured over 10,000 rows run 18–63
with a median of 43, so 64 truncates nothing and anything lower does.

## Session limits and resume

A free Kaggle session caps at about 9 hours, which 20 epochs may exceed. The
checkpoint is fingerprint-gated, so resuming is safe *and* refuses to resume into
a different configuration: re-run the identical command and it picks up at the
last checkpoint. The checkpoint must be on storage that survives the session —
`/kaggle/working` saved as output, or Drive on Colab.

Note the fingerprint covers the split digests, model name, seed, epochs,
max-steps, batch size, max-length, learning rate, weight decay, warmup ratio,
train fraction, eval limit and the freeze flag. Change any of them and the run
correctly starts over rather than resuming into a model no manifest describes.

## Bringing results back

Download exactly two files from `generated/`, plus the run report:

    generated/results_macros.tex     the numbers the paper quotes
    generated/results_table.tex      the results table
    training/last_run.json           full metrics and the loss history

Drop the two `.tex` files into `kinyamed/ml_model/paper/generated/`, replacing the
committed TBD placeholders, and commit them. The paper `\input`s them, so the
figures in the document come from the run and cannot be typed by hand.

Each file carries a provenance header written by `evaluate.py`:

    % generated_at:   2026-..-..T..:..:..+00:00
    % git_commit:     <short sha of the code that produced it>
    % manifest:       dataset/processed/eval_manifest_phrase_v1.json
    % strategy:       phrase
    % split_seed:     42
    % source_sha256:  751b8f57c195183ffc392959a58e2e6cbb0beb9c63caa3c15b7fb28530f4edec
    % eval_sha256:    564398202d54afc9e3cdc5c2fcd2694b506e635e2e492856e45867647a886e0c

That is what survives the trip. `source_sha256` and `eval_sha256` must match the
values in the committed manifest — if they do, the number in the paper is tied to
the exact million rows this repository can rebuild from seed 42 on any machine.
The test suite enforces the other half: a macros file containing concrete numbers
without that provenance block fails `make test`.

## Checklist

- [ ] `torch.cuda.is_available()` is True *after* installing dependencies
- [ ] `freeze_eval.py --verify` prints `Eval set matches the frozen manifest.`
- [ ] checkpoint path is on storage that survives a disconnect
- [ ] `evaluate.py` ran against the same manifest that training used
- [ ] the two `.tex` files' `source_sha256` matches the committed manifest
- [ ] `make test` passes locally after dropping the files in
