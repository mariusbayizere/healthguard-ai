#!/usr/bin/env python
"""Check authored phrases against the constraints the generator imposes.

These are structural checks only. Whether a phrase is what a patient would
actually say is not checkable here and is the speaker's judgement; this catches
the mechanical failures that would otherwise surface as broken sentences in a
million rows.

Usage:
    python review/lint_phrases.py review/speaker_brief_kinyarwanda.csv --language kinyarwanda
"""

from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.vocabulary import CLOSERS, CONTEXTS, ONSETS, SUBJECTS  # noqa: E402


def check(phrase: str, language: str) -> list[str]:
    problems: list[str] = []
    if not phrase.strip():
        return problems

    if phrase != phrase.strip():
        problems.append("leading or trailing whitespace")
    if phrase[:1].isupper():
        problems.append("starts with a capital: a subject precedes it, so it is mid-sentence")
    if phrase.rstrip()[-1:] in ".!?,;:":
        problems.append("ends with punctuation: the closer supplies it")
    if unicodedata.normalize("NFC", phrase) != phrase:
        problems.append("not NFC-normalised (breaks substring leakage detection)")
    if "’" in phrase or "‘" in phrase:
        problems.append("curly apostrophe: use a straight ' for consistency")
    if "  " in phrase:
        problems.append("double space")

    # An ONSET is appended directly. If the phrase already ends with a word that
    # an onset starts with, the result reads as a stutter.
    onset_heads = {o.strip().split()[0].lower() for o in ONSETS[language] if o.strip()}
    last = phrase.split()[-1].lower().strip(",.")
    if last in onset_heads:
        problems.append(f"ends with {last!r}, which also begins an onset -> '{phrase} {last} ...'")

    # A CONTEXT is appended and begins with a connective. A phrase that already
    # carries its own connective clause will produce two in a row.
    context_heads = {c.strip().split()[0].lower() for c in CONTEXTS[language] if c.strip()}
    for head in context_heads:
        if f" {head} " in f" {phrase.lower()} ":
            problems.append(f"contains {head!r}, which a context clause also adds "
                            f"-> '... {head} ... {head} ...'")
            break

    if len(phrase.split()) > 12:
        problems.append(f"{len(phrase.split())} words: long enough that it is probably "
                        "carrying its own onset or context")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--language", required=True, choices=list(SUBJECTS))
    ap.add_argument("--column", default=None, help="Column holding the phrase.")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.csv_path.open(encoding="utf-8")))
    col = args.column or next(
        (c for c in ("your_phrasing", f"current_{args.language}_phrase", "phrase")
         if c in rows[0]), None)
    if col is None:
        raise SystemExit(f"no phrase column found in {args.csv_path}")

    print(f"Linting {col!r} in {args.csv_path} ({args.language})\n")
    seen: dict[str, int] = {}
    flagged = checked = 0
    for i, row in enumerate(rows, 2):
        phrase = (row.get(col) or "").strip()
        if not phrase:
            continue
        checked += 1
        problems = check(phrase, args.language)
        if phrase.lower() in seen:
            problems.append(f"duplicate of line {seen[phrase.lower()]}")
        seen.setdefault(phrase.lower(), i)
        if problems:
            flagged += 1
            print(f"  line {i}: {phrase}")
            for p in problems:
                print(f"      - {p}")

    print(f"\n{checked} phrases checked, {flagged} flagged.")
    print("\nNot checked here, and not checkable here: whether a patient would say it,")
    print("whether the register is right, and whether it works after a third-person")
    print("subject such as 'Umugabo wanjye afite'. Those are the speaker's call.")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
