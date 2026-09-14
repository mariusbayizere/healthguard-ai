# D6 — Deployment runbook

**STATUS: NOT EXECUTED. NOT DEPLOYED. NOT CLEARED FOR PATIENT USE.**

The project document describes deployment at health centres in Rwanda. Nothing
is deployed, no clinician has cleared this system, and the model does not meet
its own acceptance gate. This runbook exists so that a deployment, if one is
ever authorised, is executed rather than improvised.

## Preconditions — every one must hold

| # | Precondition | Status today |
|---|---|---|
| 1 | Model meets the acceptance gate (all three conditions) | **FAILS G1**: CRITICAL recall 0.8504 against 0.95 |
| 2 | D2 clinician sign-off obtained | not executed |
| 3 | Response templates authored by a speaker, all languages and channels | 0 of 24 authored |
| 4 | SMS templates authored | included in the 24 above |
| 5 | D1 second-annotator κ computed and reported | not executed |
| 6 | D4 nurse baseline run | not executed |
| 7 | Evaluation base large enough to support the recall claim | 4 CRITICAL sentences |

**Precondition 7 is not closable by deployment work.** It needs more authored
phrases, and it bounds every safety claim regardless of how the other six go.

## Runbook — only once the preconditions hold

1. `alembic upgrade head`. The schema is Alembic's; the application never
   creates it.
2. Set `TRIAGE_MODEL_PATH` and install the ML extras.
3. Confirm at start-up: the log line `classifier_selected` names the model.
4. SMS stays behind its feature flag, disabled, in dry-run, until a clinician
   has approved the authored SMS text.
5. Warm start is verified: the first request must not pay the cold cost
   (measured at 1341 ms against a warm median of 66 ms).

## Rollback

Unset `TRIAGE_MODEL_PATH` and restart. Rollback means taking the service out of
clinical use.

## What this runbook cannot do

It cannot make the system safe. It sequences a deployment; the preconditions
decide whether one should happen.
