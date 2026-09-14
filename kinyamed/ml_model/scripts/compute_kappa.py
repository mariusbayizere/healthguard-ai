#!/usr/bin/env python
"""Cohen's kappa from two independent label files (referenced by D1 and D7).

    python scripts/compute_kappa.py first.csv second.csv

Each file: item_id, label, language. Refuses on a single file, on files that do not
cover exactly the same items, and on per-language counts below the specification
minimum — it never reports a kappa it cannot support.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from annotation.kappa import kappa_report, render


def _read(path: Path) -> dict[str, tuple[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            r["item_id"].strip(): (r["language"].strip(), r["label"].strip())
            for r in csv.DictReader(handle)
        }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "REFUSED: kappa needs exactly two independent label files", file=sys.stderr
        )
        return 2
    first, second = _read(Path(argv[0])), _read(Path(argv[1]))
    if first.keys() != second.keys():
        print(
            f"REFUSED: the files label different items ({len(first.keys() ^ second.keys())} differ)",
            file=sys.stderr,
        )
        return 2
    pairs = []
    for item, (language, label) in sorted(first.items()):
        other_language, other_label = second[item]
        if other_language != language:
            print(
                f"REFUSED: item {item} has different languages in the two files",
                file=sys.stderr,
            )
            return 2
        pairs.append((language, label, other_label))
    print(render(kappa_report(pairs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
