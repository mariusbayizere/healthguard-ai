"""Write decision_rule_cases.json from the ML implementation (calibration.softmax, thresholds.decide).

    cd kinyamed/ml_model && python tests/fixtures/make_decision_rule_cases.py

The inputs are hand-chosen to hit every branch of the rule. Each threshold case keeps
a margin from its boundary, so no case depends on floating-point rounding that two
implementations could legitimately do differently. Synthetic logits; no model.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ML_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ML_ROOT))

from training import calibration as cal  # noqa: E402
from training import thresholds as th  # noqa: E402

OUT = Path(__file__).resolve().parent / "decision_rule_cases.json"
MARGIN = 1e-6

INPUTS = [
    ("argmax picks CRITICAL", [2.0, 1.0, 0.0], 1.0, None),
    ("argmax picks ROUTINE", [0.0, 0.5, 2.0], 1.0, None),
    ("argmax tie goes to the more urgent class", [1.0, 1.0, 0.0], 1.0, None),
    ("argmax after a temperature", [3.0, 0.0, -1.0], 2.0, None),
    (
        "thresholds serve CRITICAL where argmax says ROUTINE",
        [math.log(0.25), math.log(0.15), math.log(0.60)],
        1.0,
        [0.2, 0.55],
    ),
    (
        "thresholds serve URGENT",
        [math.log(0.10), math.log(0.50), math.log(0.40)],
        1.0,
        [0.2, 0.55],
    ),
    (
        "thresholds serve ROUTINE",
        [math.log(0.10), math.log(0.30), math.log(0.60)],
        1.0,
        [0.2, 0.55],
    ),
    (
        "the temperature alone turns ROUTINE into CRITICAL",
        [0.5, 0.0, 2.5],
        3.0,
        [0.2, 0.55],
    ),
    ("a sharpening temperature below 1", [1.0, 0.8, 0.0], 0.5, [0.5, 0.9]),
]


def main() -> int:
    cases = []
    for name, logits, temperature, thresholds in INPUTS:
        probs = cal.softmax(np.array([logits]) / temperature)[0]
        if thresholds is None:
            decision = int(np.argmax(probs))
        else:
            for value, bound in (
                (probs[0], thresholds[0]),
                (probs[0] + probs[1], thresholds[1]),
            ):
                if abs(value - bound) < MARGIN:
                    raise SystemExit(f"{name}: within {MARGIN} of a threshold")
            decision = int(th.decide(np.array([probs]), *thresholds)[0])
        cases.append(
            {
                "name": name,
                "logits": logits,
                "temperature": temperature,
                "thresholds": thresholds,
                "probabilities": probs.tolist(),
                "decision": decision,
            }
        )
    OUT.write_text(
        json.dumps(
            {
                "generated_by": "tests/fixtures/make_decision_rule_cases.py",
                "decision_order": ["CRITICAL", "URGENT", "ROUTINE"],
                "cases": cases,
            },
            indent=2,
        )
        + "\n"
    )
    for case in cases:
        print(f"{case['decision']}  {case['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
