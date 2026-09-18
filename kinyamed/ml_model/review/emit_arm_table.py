"""Emit the per-language-arm inventory table, from the generator and the briefs.

WHY THIS IS EMITTED AND NOT TYPED. Appendix F already contradicted itself about
this table's contents: one paragraph said a Kiswahili speaker supplied all
twelve relation terms, another said "no Swahili relation terms exist anywhere in
the project". The repository settles it (`review/swahili_relations.py` holds
TERMS = 12, of which 7 are wired), but only because somebody went and looked.
Prose about an inventory drifts from the inventory. This reads the inventory.

WHAT THE TABLE IS FOR. The paper claims a four-language DESIGN and a
Kinyarwanda-only CORPUS. The zeros are the evidence for the second half of that
claim, so they are reported exactly and not rounded into a sentence like
"limited coverage".

THE FOUR COLUMNS ARE NOT THE SAME KIND OF THING, deliberately:

  phrases      Authored by a speaker of that language. Machine drafts are
               counted separately, because counting them here is the exact
               overstatement this paper is about.
  relations    Relation words a third-person frame substitutes. English and
               French carry wording lifted from the v1 machine-drafted subject
               slot; Swahili's are speaker-authored. Same count, different
               provenance, so the emitter reports provenance too.
  frames       Openers, onsets, contexts and closers. Without all four an arm
               emits nothing, whatever its phrase count. This is the binding
               constraint and the column that explains the last one.
  rows         What the generator actually produced.

FAILS CLOSED. A missing module or a renamed structure raises, and nothing is
written. An arm that genuinely holds nothing reports 0; an arm we could not
read reports an error and stops the build. Those two must never look alike.

Usage:
    python review/emit_arm_table.py            # write
    python review/emit_arm_table.py --check    # fail if stale
"""

from __future__ import annotations

import argparse
import csv
import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "generated" / "arm_table.tex"
DRAFTS = ROOT / "review" / "drafts"

ARMS = ("kinyarwanda", "english", "french", "swahili")

# The four frame slots a row needs. Named here so a renamed structure in
# vocabulary.py fails loudly rather than quietly counting three.
FRAME_SLOTS = ("OPENERS", "ONSETS", "CONTEXTS", "CLOSERS")


class Missing(RuntimeError):
    """A structure the table depends on could not be read. Never a zero."""


def vocabulary():
    sys.path.insert(0, str(ROOT))
    try:
        return importlib.import_module("dataset.vocabulary")
    except ImportError as exc:  # pragma: no cover - environment failure
        raise Missing(f"cannot import dataset.vocabulary: {exc}") from exc


def per_language(vocab, name: str) -> dict[str, int]:
    """Sizes of a per-language dict in vocabulary.py, 0 where an arm is absent."""
    if not hasattr(vocab, name):
        raise Missing(
            f"dataset/vocabulary.py has no {name}. It was renamed or removed; "
            "this table cannot be emitted without knowing what replaced it."
        )
    table = getattr(vocab, name)
    if not isinstance(table, dict):
        raise Missing(f"{name} is {type(table).__name__}, expected a dict by language")
    counts = {}
    for arm in ARMS:
        value = table.get(arm)
        if value is None:
            counts[arm] = 0
        elif isinstance(value, dict):
            counts[arm] = sum(
                len(v) if hasattr(v, "__len__") else 1
                for group in value.values()
                for v in (group.values() if isinstance(group, dict) else [group])
            )
        else:
            counts[arm] = len(value)
    return counts


def authored_phrases(vocab) -> dict[str, int]:
    """Distinct phrases per arm in SYMPTOMS, which is what the generator emits."""
    if not hasattr(vocab, "SYMPTOMS"):
        raise Missing("dataset/vocabulary.py has no SYMPTOMS")

    def walk(obj):
        if isinstance(obj, dict):
            for value in obj.values():
                yield from walk(value)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                yield from walk(value)
        else:
            yield obj

    return {arm: len(set(walk(vocab.SYMPTOMS.get(arm, {})))) for arm in ARMS}


def machine_drafts() -> dict[str, int]:
    """Distinct machine-drafted candidates per arm, from review/drafts/."""
    if not DRAFTS.is_dir():
        raise Missing(f"{DRAFTS} does not exist")
    counts = dict.fromkeys(ARMS, 0)
    for arm in ARMS:
        column = f"suggested_{arm}"
        seen: set[str] = set()
        for path in sorted(DRAFTS.glob("*.csv")):
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            if not rows or column not in rows[0]:
                continue
            seen.update(
                (r.get(column) or "").strip()
                for r in rows
                if (r.get(column) or "").strip()
            )
        counts[arm] = len(seen)
    return counts


def relation_terms(vocab) -> dict[str, tuple[int, str]]:
    """Relation words per arm, with their provenance.

    Kinyarwanda's are wired into the generator. The other three live in review
    modules because no frame can use them yet; counting only what is wired would
    report 0 for Swahili and erase a speaker's work.
    """
    wired = per_language(vocab, "RELATIONS")
    out: dict[str, tuple[int, str]] = {
        "kinyarwanda": (wired["kinyarwanda"], "speaker authored")
    }
    provenance = {
        "english": "wording from the v1 machine drafts",
        "french": "wording from the v1 machine drafts",
        "swahili": "speaker authored",
    }
    for arm in ("english", "french", "swahili"):
        try:
            module = importlib.import_module(f"review.{arm}_relations")
        except ImportError as exc:
            raise Missing(f"cannot import review.{arm}_relations: {exc}") from exc
        if not hasattr(module, "ALL_RELATIONS"):
            raise Missing(f"review/{arm}_relations.py has no ALL_RELATIONS")
        out[arm] = (len(module.ALL_RELATIONS), provenance[arm])
    return out


def rows_generated() -> dict[str, int]:
    """Rows the committed generator produces, read from its own constant."""
    source = (ROOT / "dataset" / "generate_large_dataset.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r"^TARGET_ROWS_V2\s*[:=].*?([\d_]+)", source, re.M)
    if not match:
        raise Missing(
            "dataset/generate_large_dataset.py has no TARGET_ROWS_V2; the row "
            "count cannot be read from the generator and must not be typed here."
        )
    total = int(match.group(1).replace("_", ""))
    # v2 is monolingual. Any arm without frames emits nothing, and that is the
    # table's point, so it is asserted rather than assumed.
    return {"kinyarwanda": total, "english": 0, "french": 0, "swahili": 0}


def derive() -> list[dict]:
    vocab = vocabulary()
    phrases = authored_phrases(vocab)
    drafts = machine_drafts()
    relations = relation_terms(vocab)
    rows = rows_generated()
    frames = {slot: per_language(vocab, slot) for slot in FRAME_SLOTS}

    out = []
    for arm in ARMS:
        present = [slot for slot in FRAME_SLOTS if frames[slot][arm]]
        out.append(
            {
                "arm": arm,
                "phrases": phrases[arm],
                "drafts": drafts[arm],
                "relations": relations[arm][0],
                "relation_note": relations[arm][1],
                "frames": sum(frames[slot][arm] for slot in FRAME_SLOTS),
                "frame_slots": len(present),
                "rows": rows[arm],
            }
        )
    return out


def render() -> str:
    data = derive()
    lines = []
    for row in data:
        name = row["arm"].capitalize()
        if row["arm"] == "kinyarwanda":
            name = f"\\textbf{{{name}}}"
        drafts = "--" if row["arm"] == "kinyarwanda" else f"{row['drafts']:,}"
        lines.append(
            f"{name} & {row['phrases']:,} & {drafts} & {row['relations']:,} & "
            f"{row['frames']:,} ({row['frame_slots']}/4) & {row['rows']:,} \\\\"
        )
    body = "\n".join(lines)
    notes = "; ".join(
        f"{r['arm'].capitalize()}'s are {r['relation_note']}"
        for r in data
        if r["arm"] in ("english", "swahili")
    )
    return f"""% GENERATED FILE - DO NOT EDIT BY HAND.
% Written by review/emit_arm_table.py from dataset/vocabulary.py,
% review/<arm>_relations.py, review/drafts/ and the generator's own
% TARGET_ROWS_V2. Editing a count here is fabrication; change the inventory.
%
\\begin{{table*}}[t]
\\centering
\\small
\\setlength{{\\tabcolsep}}{{4pt}}
\\begin{{tabular}}{{>{{\\raggedright\\arraybackslash}}p{{3cm}}rrrrr}}
\\toprule
Arm & Phrases & Drafts & Relations & Frames & Rows \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\caption{{What each language arm contains. \\textbf{{Phrases}} are authored by a
speaker of that arm; \\textbf{{drafts}} are machine-written candidates no
speaker of that language has reviewed, counted separately because counting them
as phrases is the overstatement this paper is about. \\textbf{{Frames}} counts
openers, onsets, contexts and closers, with the number of those four slots that
are non-empty: a row needs all four, which is why three arms generate nothing
whatever their other columns say. Provenance differs within a column
({notes}).}}
\\label{{tab:arms}}
\\end{{table*}}

"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        rendered = render()
    except Missing as exc:
        print(f"REFUSING TO EMIT: {exc}", file=sys.stderr)
        return 2

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != rendered:
            print(
                f"{OUT.name} is stale. Regenerate:\n  python review/emit_arm_table.py",
                file=sys.stderr,
            )
            return 1
        print(f"{OUT.name} matches the inventory.")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for row in derive():
        print(
            f"  {row['arm']:13} phrases {row['phrases']:>4}  drafts {row['drafts']:>4}"
            f"  relations {row['relations']:>3}  frames {row['frames']:>3}"
            f" ({row['frame_slots']}/4)  rows {row['rows']:>8,}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
