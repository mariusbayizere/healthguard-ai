"""Emit the plain-text abstract arXiv's submission form takes, from the paper.

WHY THIS EXISTS. arXiv's abstract field caps at 1,920 characters and truncates
without asking. The compiled v2 abstract ran to 2,768, so whatever was pasted
into that form would have been the paper's opening argument with its last third
missing, and nobody would have seen the cut until the listing was live.

The abstract is also the one piece of prose that would otherwise be maintained
in two places: once in `sections/abstract.tex` for the PDF, once in a text file
for the submission. Two copies of the same paragraph drift, which is the failure
this repository keeps finding in its own numbers. So there is one source, the
LaTeX, and this renders it.

It reuses `render_plain` rather than stripping LaTeX again, so the abstract is
expanded exactly as the reading copy expands it: macros resolved to the values
the emitters wrote, no markup left behind.

Usage:
    python paper/emit_arxiv_abstract.py            # write
    python paper/emit_arxiv_abstract.py --check    # fail if stale or too long
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
SOURCE = PAPER / "sections" / "abstract.tex"
# The reports directory is kinyamed/reports, beside ml_model rather than
# inside it: that is where PAPER_NUMBERS.md and the audits the paper cites
# already live.
OUT = ROOT.parent / "reports" / "ARXIV_ABSTRACT.txt"

# arXiv's own limit on the abstract field. Anything longer is silently cut.
ARXIV_LIMIT = 1920


def render() -> str:
    """The abstract as arXiv would receive it: plain text, macros expanded."""
    sys.path.insert(0, str(PAPER))
    import render_plain

    text = render_plain.strip(
        SOURCE.read_text(encoding="utf-8"),
        render_plain.macros(),
        render_plain.numbering(),
    )
    return text.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render()
    length = len(rendered.rstrip("\n"))

    if length > ARXIV_LIMIT:
        print(
            f"the abstract is {length:,} characters and arXiv accepts "
            f"{ARXIV_LIMIT:,}. It would be truncated on submission. Shorten "
            f"{SOURCE.relative_to(ROOT)} by {length - ARXIV_LIMIT:,} characters.",
            file=sys.stderr,
        )
        return 1

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != rendered:
            print(
                f"{OUT.name} is stale. Regenerate:\n"
                "  python paper/emit_arxiv_abstract.py",
                file=sys.stderr,
            )
            return 1
        print(f"{OUT.name} matches the paper ({length:,} of {ARXIV_LIMIT:,}).")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(rendered, encoding="utf-8")
    print(
        f"wrote {OUT.relative_to(ROOT.parent)} "
        f"({length:,} characters, {ARXIV_LIMIT - length:,} to spare)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
