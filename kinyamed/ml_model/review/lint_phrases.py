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


def check(phrase: str, language: str) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    if not phrase.strip():
        return problems, warnings

    if phrase != phrase.strip():
        problems.append("leading or trailing whitespace")
    # Capitalisation is handled by the renderer, which lowercases after a comma
    # opener and capitalises at a sentence start, so either stored form is fine.
    # Trailing sentence punctuation used to be an error, when a phrase was a
    # noun phrase spliced mid-sentence. Utterances are complete sentences and the
    # renderer collapses duplicate punctuation, so a full stop is now correct.
    # A trailing comma or semicolon still is not.
    if phrase.rstrip()[-1:] in ",;:":
        problems.append("ends with a comma or colon: the following slot continues the sentence")
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
    # Connective collision. This is a WARNING, not an error: a natural patient
    # utterance often chains "kandi", and forbidding it would push the speaker
    # back toward the stilted phrasing this whole exercise is correcting. The
    # real fix is context fragments that do not open with the same connective.
    context_heads = {c.strip().split()[0].lower() for c in CONTEXTS[language] if c.strip()}
    for head in context_heads:
        if f" {head} " in f" {phrase.lower()} ":
            warnings.append(f"contains {head!r}, which a context clause also opens with. "
                            f"Fine if it reads naturally; the context slot needs "
                            f"non-{head!r} variants")
            break

    # Standing rule: {REL} should be the grammatical subject. A weak positional
    # check only - it cannot parse Kinyarwanda - so it warns rather than errors.
    if "{REL}" in phrase:
        head = phrase.split()
        if head and not (head[0] == "{REL}" or (len(head) > 1 and head[1] == "{REL}")):
            warnings.append("{REL} is not at the head of the phrase; check it is the "
                            "grammatical subject rather than an object")

    # Length. Written for noun phrases, where anything long was carrying its own
    # onset or context. An utterance is a whole sentence and is legitimately
    # longer - the speaker's own approved phrases run to 14 words - so this is a
    # warning at a higher threshold, not an error.
    if len(phrase.split()) > 16:
        warnings.append(f"{len(phrase.split())} words: check it is not carrying its own "
                        "onset or context, which the slots also supply")
    return problems, warnings


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
    flagged = checked = warned = 0
    for i, row in enumerate(rows, 2):
        if (row.get("applies") or "yes").strip().lower() == "no":
            continue
        phrase = (row.get(col) or "").strip()
        if not phrase:
            continue
        checked += 1
        problems, warns = check(phrase, args.language)
        if phrase.lower() in seen:
            problems.append(f"duplicate of line {seen[phrase.lower()]}")
        seen.setdefault(phrase.lower(), i)
        if problems or warns:
            if problems:
                flagged += 1
            else:
                warned += 1
            print(f"  line {i}: {phrase}")
            for p in problems:
                print(f"      ERROR   {p}")
            for w in warns:
                print(f"      warning {w}")

    total = len(rows)
    print(f"\n{checked} of {total} rows filled; {flagged} errors, {warned} warnings.")
    if checked < total:
        print(f"{total - checked} still blank — this is a partial run, which is fine.")
    print("\nNot checked here, and not checkable here: whether a patient would say it,")
    print("whether the register is right, and whether it works after a third-person")
    print("subject such as 'Umugabo wanjye afite'. Those are the speaker's call.")
    # Exit non-zero only when something is actually wrong, so this can be run
    # repeatedly during a session without a blank file looking like a failure.
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
