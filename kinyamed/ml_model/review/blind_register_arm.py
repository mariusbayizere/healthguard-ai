#!/usr/bin/env python
"""Blind register rating: the frozen v1 English against the machine drafts.

The question is narrow and worth measuring: **can the reviewer tell the 46
phrases that are already in the shipped corpus from the ones a model drafted?**

    - If they cannot, that is a real result about the drafts, and it is also the
      first time the 46 have been reviewed by anyone at all. They entered v1 as
      "original corpus" with no author, no gloss and no verdict.
    - If they can, the interesting number is which direction it goes.

DESIGN, AND WHERE THE BLIND IS IMPERFECT
----------------------------------------
Balanced 46/46, so base rate carries no information. Shuffled under a fixed
seed. Origin lives only in the key file, which the rater does not open until the
ratings are in.

Three honest limitations, stated because a blind arm that oversells itself is
worse than none:

1. **Form is a partial tell.** All 46 v1 phrases are noun phrases; the drafts
   are a mix of noun phrases and complete clauses. A rater who notices that is
   no longer fully blind. Rendering both through the frame was the alternative
   and it is worse - a clause rendered after "I have" reads as broken English,
   which leaks origin far more loudly than the bare phrase does.
2. **Anything quoted in review/ is excluded, computed not listed.** A phrase the
   rater has read in a note cannot be rated blind, and there is no way to un-see
   one. This is recomputed on every build, because the seen set grows with every
   batch drafted.
3. **This measures register, not correctness.** A phrase can read perfectly and
   still be the wrong phrase for its concept. That is what `verdict_fidelity` in
   the brief is for, and the two must not be collapsed.

    python review/blind_register_arm.py --build
    python review/blind_register_arm.py --score

Build refuses to overwrite an items file that already carries ratings.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from dataset.vocabulary import SYMPTOMS  # noqa: E402
sys.path.insert(0, str(HERE))
from walk import save  # noqa: E402

SHEET = ROOT / "review" / "phrase_review_sheet.csv"
ITEMS = ROOT / "review" / "blind" / "register_arm_items.csv"
KEY = ROOT / "review" / "blind" / "register_arm_key.csv"

SEED = 42

# A SEEN ITEM IS NOT A BLIND ITEM, and the set of seen items grows every time a
# batch is drafted: a note reading "replaces sheet draft 'X'" tells the reviewer
# that X is a draft, and one reading "v1 English was 'Y'" tells them Y is not.
#
# The first version of this file hardcoded seventeen ids. By the time the arm was
# actually run, 37 of its 92 items had been quoted somewhere - 40% of the arm,
# with the origin recoverable for every one. Hardcoding could not have kept up.
#
# So exclusion is computed instead: any phrase whose text appears anywhere in the
# drafts files or the review documents is out. Conservative on purpose - it will
# drop a phrase that appears coincidentally, which costs a few items and cannot
# leak an answer.
CONTAMINATION_SOURCES = ("review/drafts/*.csv", "review/*.md")


def written_this_session() -> str:
    """Everything written into review/ that the reviewer has read."""
    text = []
    for pattern in CONTAMINATION_SOURCES:
        for path in sorted(ROOT.glob(pattern)):
            text.append(path.read_text(errors="ignore").lower())
    return "\n".join(text)

ITEM_COLUMNS = ["item_id", "phrase", "domain", "proposed_urgency", "register", "note"]
KEY_COLUMNS = ["item_id", "origin", "source_id", "phrase"]

SCALE = {
    "4": "natural - someone would say this",
    "3": "understandable but slightly off",
    "2": "clearly not how someone would put it",
    "1": "not English a patient would use here",
}


def v1_items() -> list[dict]:
    """The 46 frozen English phrases, with the domain and class they carry in v1."""
    out = []
    for urgency, domains in SYMPTOMS["english"].items():
        for domain, phrases in domains.items():
            for i, phrase in enumerate(phrases):
                out.append({"phrase": phrase, "domain": domain,
                            "proposed_urgency": urgency, "origin": "v1_corpus",
                            "source_id": f"v1[{urgency}/{domain}/{i}]"})
    return out


def draft_items() -> list[dict]:
    return [{"phrase": r["phrase"], "domain": r["domain"],
             "proposed_urgency": r["proposed_urgency"], "origin": "machine_draft",
             "source_id": r["id"]}
            for r in csv.DictReader(SHEET.open(encoding="utf-8"))
            if r["language"] == "english" and r["status"] == "draft"]


def build() -> int:
    if ITEMS.exists():
        rated = [r for r in csv.DictReader(ITEMS.open(encoding="utf-8"))
                 if r["register"].strip()]
        if rated:
            raise SystemExit(
                f"refusing to rebuild: {ITEMS.name} already carries {len(rated)} "
                "ratings. Score it, or move it aside deliberately."
            )

    seen = written_this_session()
    v1 = [i for i in v1_items() if i["phrase"].lower() not in seen]
    drafts = [i for i in draft_items() if i["phrase"].lower() not in seen]
    n = min(len(v1), len(drafts))
    if n < 20:
        raise SystemExit(
            f"only {n} clean items per side; an arm this small decides nothing. "
            "Both populations have been quoted too heavily to blind."
        )

    rng = random.Random(SEED)
    pool = rng.sample(v1, n) + rng.sample(drafts, n)
    rng.shuffle(pool)

    items, key = [], []
    for index, entry in enumerate(pool, start=1):
        item_id = f"R{index:03d}"
        items.append({"item_id": item_id, "phrase": entry["phrase"],
                      "domain": entry["domain"],
                      "proposed_urgency": entry["proposed_urgency"],
                      "register": "", "note": ""})
        key.append({"item_id": item_id, "origin": entry["origin"],
                    "source_id": entry["source_id"], "phrase": entry["phrase"]})

    ITEMS.parent.mkdir(parents=True, exist_ok=True)
    save(ITEMS, ITEM_COLUMNS, items)
    save(KEY, KEY_COLUMNS, key)
    print(f"wrote {ITEMS.relative_to(ROOT)}: {len(items)} items "
          f"({n} v1, {n} drafts), seed {SEED}")
    print(f"  excluded as already quoted in review/: "
          f"{46 - len(v1)} v1, {80 - len(drafts)} drafts")
    print(f"wrote {KEY.relative_to(ROOT)} — do not open it until the ratings are in")
    print("\nRate the `register` column 1-4:")
    for score, meaning in sorted(SCALE.items(), reverse=True):
        print(f"  {score}  {meaning}")
    print("\nOne question only: would someone say this to a health worker, in "
          "English, in Rwanda?\nNot whether it is the right phrase for its "
          "concept — that is the brief's job.")
    return 0


def score() -> int:
    items = {r["item_id"]: r for r in csv.DictReader(ITEMS.open(encoding="utf-8"))}
    key = list(csv.DictReader(KEY.open(encoding="utf-8")))

    rated = [(k, items[k["item_id"]]) for k in key
             if items[k["item_id"]]["register"].strip()]
    if not rated:
        raise SystemExit(f"no ratings in {ITEMS.name} yet")

    by_origin: dict[str, list[int]] = {}
    for k, item in rated:
        try:
            by_origin.setdefault(k["origin"], []).append(int(item["register"]))
        except ValueError:
            raise SystemExit(f"{k['item_id']}: register {item['register']!r} is not 1-4")

    print(f"{len(rated)} of {len(key)} items rated\n")
    for origin, scores in sorted(by_origin.items()):
        mean = statistics.mean(scores)
        low = sum(1 for s in scores if s <= 2)
        print(f"  {origin:15s} n={len(scores):3d}  mean {mean:.2f}  "
              f"{low} rated 2 or below")

    if len(by_origin) == 2:
        (a, sa), (b, sb) = sorted(by_origin.items())
        gap = statistics.mean(sa) - statistics.mean(sb)
        print(f"\n  gap ({a} - {b}): {gap:+.2f}")
        print("  A gap near zero means the rater could not separate the shipped "
              "corpus\n  from the drafts. It does NOT mean either population is "
              "good — both\n  can be rated low together, and that is its own "
              "result.")

    worst = sorted(rated, key=lambda p: int(p[1]["register"]))[:10]
    print("\nlowest rated:")
    for k, item in worst:
        print(f"  {item['register']}  [{k['origin']}] {item['phrase']!r}")
        if item["note"].strip():
            print(f"       {item['note']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--score", action="store_true")
    args = ap.parse_args()
    return build() if args.build else score()


if __name__ == "__main__":
    raise SystemExit(main())
