# Urgency probe — empty on purpose

`urgency_probe.csv` ships with its header and **no rows**.

An item asserting that a given text is CRITICAL, URGENT or ROUTINE is a clinical claim.
Each row therefore needs:

- `source`: the document and page it comes from (`docs/clinical/`), and
- `validated_by`: the clinician who validated it (never `PENDING`).

`training/probe.py` refuses the file otherwise, and refuses to score it in any case: the
probe prints the model's answer per item and never a rate. It is **NOT A GATE METRIC**.
The deployment gate is `training/evaluate.py` on a set meeting `reports/EVAL_SET_SPEC.md`.
