#!/usr/bin/env python
"""Run `lint_phrases.check` over the French brief, against the FROZEN v1 frames.

`lint_phrases.py` takes `--language` and reads `ONSETS`, `CONTEXTS` and
`SUBJECTS` from `dataset/vocabulary.py`. That no longer works for French: the
working tree copy is mid-rewrite for the v2 Kinyarwanda work and `LANGUAGES` is
down to `("kinyarwanda",)`, so `ONSETS["french"]` raises a KeyError before a
single phrase is checked.

The frames are read from the frozen v1 commit instead, for the same reason
`build_french_brief.py` reads the v1 phrases there: **v1 is frozen and must stay
byte-identical**, so the French frame slots a v2 phrase will be rendered into are
a fact about the frozen file, not about a tree being edited.

THE REAL `check()` IS REUSED, not reimplemented - the frame dicts are bound into
its module before it runs. A second copy of the rules would drift from the first,
which is the failure this project keeps finding.

    python review/lint_french.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import lint_phrases  # noqa: E402
from build_french_brief import OUT, v1_vocabulary  # noqa: E402

FRENCH = "french"


def main() -> int:
    v1 = v1_vocabulary()
    # Bind the frozen French frames into the linter's module globals. Only the
    # three names `check()` reads are replaced, and only for French.
    for name in ("ONSETS", "CONTEXTS", "SUBJECTS", "CLOSERS"):
        setattr(lint_phrases, name, getattr(v1, name))

    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    checked = errors = warnings = 0
    seen: dict[str, str] = {}
    for row in rows:
        if row["applies"] == "no":
            continue
        phrase = row["suggested_french"].strip()
        if not phrase:
            continue
        key = f"{row['concept_id']}/{row['person']}"
        checked += 1
        problems, warns = lint_phrases.check(phrase, FRENCH)
        if not (row.get("form") or "").strip():
            problems.append(
                "no form declared; the build defaults to noun_phrase and will "
                "prefix a subject. Declare 'utterance' or 'noun_phrase'.")
        if phrase.lower() in seen:
            problems.append(f"duplicate of {seen[phrase.lower()]}")
        seen.setdefault(phrase.lower(), key)
        if problems or warns:
            errors += bool(problems)
            warnings += bool(warns and not problems)
            print(f"  {key}: {phrase}")
            for p in problems:
                print(f"      ERROR   {p}")
            for w in warns:
                print(f"      warning {w}")

    print(f"\n{checked} French candidates checked; {errors} with errors, "
          f"{warnings} with warnings only.")
    print("Not checked here, and not checkable here: whether a francophone Rwandan")
    print("patient would say it. That is review/rwandan-french-questions.md.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
