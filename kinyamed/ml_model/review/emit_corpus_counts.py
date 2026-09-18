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

THE OVERLAP IS THE POINT. `needs_clinician` and `hold` are not disjoint: 19 rows
carry both. The paper's `256 - 50 - 23 = 183` subtraction assumed they were, and
a reader will repeat it unless the emitted text says otherwise. So this states
all six figures and says in words that the two sets overlap.

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

    flagged = [r for r in rows if (r["needs_clinician"] or "").strip()]
    held = [r for r in rows if (r["hold"] or "").strip().lower() == "yes"]
    both = [
        r
        for r in rows
        if (r["needs_clinician"] or "").strip()
        and (r["hold"] or "").strip().lower() == "yes"
    ]
    return {
        "rows": len(rows),
        "flagged": len(flagged),
        "held": len(held),
        "both": len(both),
        "held_only": len(held) - len(both),
        "flagged_only": len(flagged) - len(both),
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
% NO SENTENCE MACRO HERE, DELIBERATELY. An earlier version defined one
% containing \\textbf{{...}}; `paper/render_plain.py::macros()` parses
% \\newcommand with [^}}]* and cannot capture nested braces, so the macro would
% have survived into the plain-text reading copy verbatim. The prose that uses
% these values lives in sections/appendix.tex, where an author would look for
% it; only plain values are defined here.

"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

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
    counts = derive()
    print(f"wrote {OUT.relative_to(ROOT)}")
    for key, value in counts.items():
        print(f"  {key:14} {value:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
