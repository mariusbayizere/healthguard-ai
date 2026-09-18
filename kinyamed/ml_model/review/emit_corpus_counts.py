"""Emit the corpus row counts the paper quotes, from the record that holds them.

EXTERNAL REVIEW D2. The paper carried these counts hand-typed, and they went
stale: commit `934433a` reclassified four third-person rows into
`needs_clinician`, the record moved from 25 flagged to 29, and the paper did not
follow. The reviewer read the resulting arithmetic as two errors (B2 and B3)
when it was drift.

It is the same shape as B6, where an URGENT *support* figure was reused where a
confusion-matrix cell belonged. Both are a number copied from a source that
later moved. A paper whose argument is that numbers need traceable sources
should not carry hand-typed counts at all, so these are derived here and
`\\input` by the paper.

TWO SEPARATE THINGS, AND AN EARLIER VERSION OF THIS FILE CONFUSED THEM.

  1. `needs_clinician` and `hold` overlap: 19 rows carry both. That matters for
     the flagged/held figures and nothing else.
  2. `256 - 50 - 23 = 183` does NOT reach the 165-phrase inventory, and the
     overlap above is not why. `applies=no` and `hold=yes` are disjoint (0 rows
     carry both, measured). The subtraction is short one term: 19 rows are
     applicable and unheld but carry no phrase yet, and one row contributes a
     second phrasing as an extra corpus phrase. 256 - 50 - 23 - 19 + 1 = 165.

The second reading was stated wrongly here and in the paper, blaming the
flagged/held overlap for a gap it has no bearing on. The two 19s are a
coincidence: 19 rows are flagged-and-held, and a different 19 are unauthored.
Every term of the reconciliation is therefore emitted, so the appendix can show
the subtraction reaching the inventory instead of asserting a number near it.

The selection rule is `review/materialise_v2.py::generating`, which is what
actually writes `dataset/vocabulary.py`; this file counts the same predicate.
`--check` compares the emitted total against `vocabulary.py` itself, so the two
cannot drift apart silently.

Usage:
    python review/emit_corpus_counts.py            # write
    python review/emit_corpus_counts.py --check    # fail if stale
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPINE = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"
OUT = ROOT / "paper" / "generated" / "corpus_counts.tex"


def derive() -> dict[str, int]:
    """Count the record. One pass, no judgement."""
    with SPINE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    def inapplicable(r: dict) -> bool:
        return (r["applies"] or "yes").strip().lower() == "no"

    def held_row(r: dict) -> bool:
        return (r["hold"] or "").strip().lower() == "yes"

    def authored(r: dict) -> bool:
        return bool((r["your_phrasing"] or "").strip())

    flagged = [r for r in rows if (r["needs_clinician"] or "").strip()]
    held = [r for r in rows if held_row(r)]
    both = [r for r in rows if (r["needs_clinician"] or "").strip() and held_row(r)]

    # The predicate that materialise_v2.py applies when it writes vocabulary.py.
    inapplicable_rows = [r for r in rows if inapplicable(r)]
    generating = [
        r for r in rows if not inapplicable(r) and authored(r) and not held_row(r)
    ]
    unauthored = [
        r for r in rows if not inapplicable(r) and not held_row(r) and not authored(r)
    ]
    # A second phrasing is an additional corpus phrase, not an additional row.
    primary = {(r["your_phrasing"] or "").strip() for r in generating}
    seconds = {
        (r.get("second_phrasing_optional") or "").strip()
        for r in generating
        if (r.get("second_phrasing_optional") or "").strip()
    }
    extra = seconds - primary
    # Flagged AND generating. Not the same as flagged-and-not-held: two rows
    # carry a flag without a hold yet still generate nothing, one ruled
    # inapplicable and one not yet written. Section 3.2 quotes this one.
    flagged_generating = [r for r in generating if (r["needs_clinician"] or "").strip()]

    return {
        "rows": len(rows),
        "flagged": len(flagged),
        "held": len(held),
        "both": len(both),
        "held_only": len(held) - len(both),
        "flagged_only": len(flagged) - len(both),
        "inapplicable": len(inapplicable_rows),
        "unauthored": len(unauthored),
        "second_phrasings": len(extra),
        "inventory": len(generating) + len(extra),
        "flagged_generating": len(flagged_generating),
    }


def render() -> str:
    c = derive()
    return f"""% GENERATED FILE - DO NOT EDIT BY HAND.
% Written by review/emit_corpus_counts.py from
% review/speaker_brief_kinyarwanda_v2.csv.
% Editing this file to change a reported count is fabrication; change the
% record and re-run the emitter.
%
% source: review/speaker_brief_kinyarwanda_v2.csv
%
\\newcommand{{\\CorpusRows}}{{{c["rows"]:,}}}
\\newcommand{{\\CorpusFlagged}}{{{c["flagged"]:,}}}
\\newcommand{{\\CorpusHeld}}{{{c["held"]:,}}}
\\newcommand{{\\CorpusFlaggedAndHeld}}{{{c["both"]:,}}}
\\newcommand{{\\CorpusHeldOnly}}{{{c["held_only"]:,}}}
\\newcommand{{\\CorpusFlaggedOnly}}{{{c["flagged_only"]:,}}}
%
% The reconciliation to the generating inventory. Every term, so the appendix
% can show the subtraction arriving rather than assert a number near it:
%   rows - inapplicable - held - unauthored + second phrasings = inventory
\\newcommand{{\\CorpusInapplicable}}{{{c["inapplicable"]:,}}}
\\newcommand{{\\CorpusUnauthored}}{{{c["unauthored"]:,}}}
\\newcommand{{\\CorpusSecondPhrasings}}{{{c["second_phrasings"]:,}}}
\\newcommand{{\\CorpusInventory}}{{{c["inventory"]:,}}}
\\newcommand{{\\CorpusFlaggedInInventory}}{{{c["flagged_generating"]:,}}}
%
% NO SENTENCE MACRO HERE, DELIBERATELY. An earlier version defined one
% containing \\textbf{{...}}; `paper/render_plain.py::macros()` parses
% \\newcommand with [^}}]* and cannot capture nested braces, so the macro would
% have survived into the plain-text reading copy verbatim. The prose that uses
% these values lives in sections/appendix.tex, where an author would look for
% it; only plain values are defined here.

"""


def inventory_on_disk() -> int | None:
    """Distinct phrases actually in dataset/vocabulary.py, or None if unreadable.

    The reconciliation is only worth printing if it lands on the inventory the
    generator really has. This reads that inventory rather than trusting the
    arithmetic, so the record and the generated vocabulary cannot drift apart
    without the emitter saying so.
    """
    sys.path.insert(0, str(ROOT))
    try:
        from dataset import vocabulary
    except ImportError:
        return None

    def walk(obj: object):
        if isinstance(obj, dict):
            for value in obj.values():
                yield from walk(value)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                yield from walk(value)
        else:
            yield obj

    return len(set(walk(vocabulary.SYMPTOMS)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    counts = derive()
    on_disk = inventory_on_disk()
    if on_disk is not None and on_disk != counts["inventory"]:
        print(
            f"the record reconciles to {counts['inventory']:,} phrases but "
            f"dataset/vocabulary.py holds {on_disk:,}. One of them has moved; "
            "re-run review/materialise_v2.py --write, or fix the record.",
            file=sys.stderr,
        )
        return 1

    rendered = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != rendered:
            print(
                f"{OUT.name} is stale. Regenerate:\n"
                "  python review/emit_corpus_counts.py",
                file=sys.stderr,
            )
            return 1
        print(f"{OUT.name} matches the record.")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for key, value in counts.items():
        print(f"  {key:14} {value:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
