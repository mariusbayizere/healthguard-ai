#!/usr/bin/env bash
# The exact training command the systemd unit runs. Edit the flags here, not in
# the unit file — the unit deliberately holds no hyperparameters, so this file
# is the whole record of what was run.
#
# Every flag below except --threads is part of the run fingerprint, so changing
# any of them makes train_holdout.py REJECT an existing checkpoint and start
# fresh. That is intended: a checkpoint is only resumable by the config that
# made it. The step-2000 checkpoint from the 2026-09-05 run fingerprints as
# b887790b9f5762b8 and cannot be resumed into this one.
#
# WHY THESE NUMBERS: see ~/kinyamed-runs/protocol.json, section
# "v2b_config_provenance". They were read off the 2026-09-05 loss curve, not
# tuned against the eval set.
set -euo pipefail
cd /home/marius/healthguard-ai/kinyamed/ml_model

# ABSOLUTE INTERPRETER, NOT `python3`. A systemd user unit gets a PATH with no
# pyenv in it, so `python3` resolves to /usr/bin/python3, which has neither
# numpy nor torch. The 2026-09-05 run did not hit this because it was launched
# from an interactive shell where the pyenv shim was on PATH. Pinning the
# interpreter also records exactly which one produced the model.
PYTHON=/home/marius/.pyenv/versions/3.11.9/bin/python3
"$PYTHON" -c 'import torch, numpy, transformers' || {
  echo "FATAL: $PYTHON is missing torch/numpy/transformers — refusing to start" >&2
  exit 1
}

exec "$PYTHON" training/train_holdout.py \
  --manifest dataset/processed/eval_manifest_phrase_v2.json \
  --train-fraction 1.0 \
  --max-steps 2000 \
  --batch-size 16 \
  --max-length 96 \
  --learning-rate 1e-5 \
  --warmup-ratio 0.06 \
  --weight-decay 0.01 \
  --freeze-layers 8 \
  --stop-groups 3 \
  --patience 5 \
  --min-delta 0.002 \
  --eval-every 50 \
  --eval-limit 900 \
  --log-every 25 \
  --checkpoint-every 100 \
  --checkpoint-path /home/marius/kinyamed-runs/checkpoints/train_state.pt \
  --save-path /home/marius/kinyamed-runs/model_v2 \
  --report training/last_run.json \
  --threads 2 \
  --seed 42
