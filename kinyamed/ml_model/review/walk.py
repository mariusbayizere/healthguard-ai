#!/usr/bin/env python
"""Work through a brief one row at a time: accept, edit, rewrite, skip, or N/A.

Writes after every decision, so quitting mid-session loses nothing and the next
run resumes where you stopped.

Records provenance on every row, because the paper needs the distinction:

    speaker           you wrote it
    machine_approved  I drafted it, you accepted it unchanged
    machine_edited    I drafted it, you changed it
    not_applicable    this concept does not need this person

    python review/walk.py review/speaker_brief_kinyarwanda_v2.csv
    python review/walk.py review/frame_fragments_brief.csv --phrase-col kinyarwanda \
        --suggest-col suggested_kinyarwanda
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HELP = """
  [enter] accept the suggestion as-is        -> machine_approved
  e       edit it (opens the text to change) -> machine_edited
  r       rewrite from scratch               -> speaker
  n       not applicable for this person     -> not_applicable
  s       skip for now
  q       save and quit
"""


def save(path: Path, fields: list[str], rows: list[dict]) -> None:
    """Write via a temp file and rename, and never write an empty file.

    An earlier version wrote directly to the brief and truncated it to a bare
    header. A brief holds hours of a speaker's work; it does not get written
    non-atomically, and a zero-row write is treated as a bug rather than as an
    instruction to erase the file.
    """
    if not rows:
        raise SystemExit(f"refusing to write {path}: no rows in memory")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dataset.atomicio import atomic_write

    with atomic_write(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", type=Path)
    ap.add_argument("--phrase-col", default="your_phrasing")
    ap.add_argument("--suggest-col", default="suggested_kinyarwanda")
    ap.add_argument("--domain", help="Work through one domain only.")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.brief.open(encoding="utf-8")))
    fields = list(rows[0])
    for extra in (args.phrase_col, args.suggest_col, "source", "confidence", "suggestion_note"):
        if extra not in fields:
            fields.append(extra)
            for r in rows:
                r.setdefault(extra, "")

    todo = [r for r in rows
            if not (r.get(args.phrase_col) or "").strip()
            and (r.get("applies") or "yes").strip().lower() != "no"
            # rows already in the corpus are legitimately empty (the no-opener
            # variant is an empty string) and are not outstanding work
            and (r.get("status") or "").strip().lower() != "existing"
            and (not args.domain or r.get("domain") == args.domain)]
    if not todo:
        print("Nothing outstanding.")
        return 0

    print(f"{len(todo)} rows to decide in {args.brief.name}")
    print(HELP)

    for i, r in enumerate(todo, 1):
        print("-" * 72)
        label = r.get("english_gloss") or r.get("slot", "")
        print(f"[{i}/{len(todo)}] {r.get('domain','')} {r.get('proposed_urgency','')} "
              f"{r.get('person','')}")
        print(f"  gloss      : {label}")
        if r.get("person_note"):
            print(f"  note       : {r['person_note']}")
        if r.get("suggestion_note"):
            print(f"  basis      : {r['suggestion_note']}")
        sug = (r.get(args.suggest_col) or "").strip()
        print(f"  suggestion : {sug if sug else '(none — write your own)'}"
              + (f"   [{r.get('confidence')}]" if r.get("confidence") else ""))

        try:
            choice = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  interrupted — saving")
            break

        if choice == "q":
            break
        if choice == "s":
            continue
        def ask(prompt: str) -> str | None:
            try:
                return input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                return None

        if choice == "n":
            r["applies"] = "no"; r["source"] = "not_applicable"
        elif choice == "r" or not sug:
            new = ask("  your phrasing: ")
            if not new:
                continue
            r[args.phrase_col] = new; r["source"] = "speaker"
        elif choice == "e":
            print(f"  current: {sug}")
            new = ask("  edited : ")
            if not new:
                continue
            r[args.phrase_col] = new
            r["source"] = "machine_approved" if new == sug else "machine_edited"
        else:
            r[args.phrase_col] = sug; r["source"] = "machine_approved"

        save(args.brief, fields, rows)

    save(args.brief, fields, rows)
    done = sum(1 for r in rows if (r.get(args.phrase_col) or "").strip()
               or (r.get("applies") or "yes").lower() == "no")
    print(f"\nSaved. {done}/{len(rows)} resolved.")
    import collections
    c = collections.Counter(r.get("source") or "(none)" for r in rows)
    print("Provenance:", {k: v for k, v in c.items() if k != "(none)"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
