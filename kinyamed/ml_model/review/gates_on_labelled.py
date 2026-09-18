"""Run the nine corpus gates against the labelled corpus, per language arm.

THE ADAPTER INVENTS NOTHING. The gates read a schema the generated corpus
carries: `seed_id`, `language`, `generation_method`, `author_code`,
`validated_by`, `domain`. The labelled corpus carries `id`, `cue`, `reporter`,
`age_group`, `text_kw`, `author`, `label`. Where a field exists it is mapped;
where it does not, the cell is left EMPTY and the gate is allowed to fail.

That is the whole point of running this. Filling `generation_method` with
`native_author` because the sentences look authored would convert a missing
record into a passing gate, which is the exact move this project exists to
catch. An empty cell is the truthful statement that the corpus does not record
the fact, and C5 and C7 failing is a finding about the corpus, not a bug here.

WHAT MAPS, AND WHY:

  seed_id   = the row id. In this corpus one row IS one authored sentence, so
              rows and seeds are the same population. In the generated corpus
              one seed produced up to 50 rows; here the expansion factor is 1,
              which is why C1 cannot fail and says nothing.
  text      = text_kw, for rows that have it. The 201 rows with a label and no
              Kinyarwanda are excluded: an empty string is not a short sentence.
  language  = the arm. Kinyarwanda for every row that exists today.
  the rest  = empty, because the corpus does not record them.

PER ARM, INCLUDING EMPTY ARMS. An arm with no authored rows is reported, not
skipped, and it FAILS C2 on zero distinct seeds. An absent arm and a failing
arm look identical in a summary that omits the empty ones, and the four-language
claim is exactly where that matters.

Usage:
    python review/gates_on_labelled.py
    python review/gates_on_labelled.py --arm kinyarwanda
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataset import corpus_gates  # noqa: E402
from dataset import labelled_corpus as lc  # noqa: E402

ARMS = ("kinyarwanda", "english", "french", "swahili")

# The schema the gates read. Order matters only for readability.
GATE_COLUMNS = (
    "seed_id",
    "text",
    "language",
    "domain",
    "generation_method",
    "author_code",
    "validated_by",
    "reporter",
    "age_group",
)


def adapt(rows: list[lc.Row], arm: str) -> list[dict[str, str]]:
    """Map the labelled corpus into the gates' schema for one arm.

    Only Kinyarwanda has rows today. The other three return an empty list, and
    the caller still runs the gates over it so the arm reports a failure rather
    than an absence.
    """
    if arm != "kinyarwanda":
        return []
    return [
        {
            "seed_id": str(r.id),
            "text": r.text,
            "language": arm,
            # Not recorded by this corpus. Left empty deliberately; see docstring.
            "domain": "",
            "generation_method": "",
            "author_code": "",
            "validated_by": "",
            "reporter": r.reporter,
            "age_group": r.age_group,
        }
        for r in lc.measurable(rows)
    ]


def run_arm(rows: list[lc.Row], arm: str) -> tuple[str, int]:
    """Gate report for one arm, and its distinct-seed count."""
    adapted = adapt(rows, arm)
    seeds = len({r["seed_id"] for r in adapted})

    with tempfile.NamedTemporaryFile(
        "w", suffix=f".{arm}.csv", delete=False, encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(GATE_COLUMNS))
        writer.writeheader()
        writer.writerows(adapted)
        path = Path(handle.name)

    try:
        text = corpus_gates.report(path, distinct_seeds=seeds, seed_column="seed_id")
    finally:
        path.unlink(missing_ok=True)
    return text, seeds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARMS, default=None)
    args = parser.parse_args()

    rows = lc.load()
    arms = (args.arm,) if args.arm else ARMS

    print(lc.provenance_line())
    print(f"corpus sha256 {lc.digest()}")
    print(
        "\nThe gates were written for a GENERATED corpus. This is the first time "
        "they meet authored data.\nNo gate is waived. Fields the labelled corpus "
        "does not record are left empty, and a\ngate that fails on an empty field "
        "is reporting a real gap in the record.\n"
    )
    for arm in arms:
        adapted = adapt(rows, arm)
        print("=" * 72)
        print(f"ARM: {arm}    rows: {len(adapted):,}")
        if not adapted:
            print(
                "  No authored rows. The arm is reported rather than skipped: it "
                "FAILS C2\n  (distinct seeds 0 against a floor of "
                f"{corpus_gates.MIN_SEEDS_PER_LANGUAGE:,}) and every other gate is "
                "vacuous\n  on an empty corpus. An absent arm and a failing arm "
                "must not look alike."
            )
            continue
        text, seeds = run_arm(rows, arm)
        print(f"  distinct seeds C2 reads: {seeds:,}")
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
