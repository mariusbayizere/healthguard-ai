#!/usr/bin/env python
"""Freeze a train / calibration / test split of the labelled Kinyarwanda corpus.

    python -m dataset.split_labelled --seed 20260920 --out dataset/splits/kw_v1

THE HOLD-OUT UNIT IS THE SOURCE SENTENCE, NEVER THE ROW (docs/ENGINEERING_SPEC.md L8).
A scenario here is a connected component of sentences that are the same text after
normalisation, or near-duplicates at word-3-gram Jaccard >= 0.85 -- the same
comparison `training/pipeline.py` runs as its leakage check. Splitting by row would
let two spellings of one authored sentence sit on both sides of the boundary, which
is the leakage the pipeline would then refuse on. Grouping first means the split is
clean by construction rather than by luck. On this corpus the clustering merges
exactly one pair (ids 247 and 775, identical text, both URGENT).

FROZEN MEANS FROZEN. The script refuses to write into a directory that already
holds a split. A split is created once, hashed, and committed; regenerating it
against a changed corpus is how a held-out set stops being held out.

UNCLASSIFIABLE IS NOT A FOURTH CLASS. Rows labelled `CANNOT CLASSIFY` are a
judgement that the text does not support a triage decision. They are excluded from
every split and listed by id in the manifest, not folded into a class and not
silently dropped. Rows carrying a label but no Kinyarwanda text are excluded the
same way, for the same reason: recorded, not hidden.

THE SPLIT CARRIES NO CLINICAL AUTHORITY. Every label in it came from one
non-clinician annotator with no second rater. The manifest repeats that line and
`labelled_corpus.provenance_line()` is its only wording.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parent.parent
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from dataset import labelled_corpus as lc  # noqa: E402
from dataset.labels import LABEL_MAP  # noqa: E402

LANGUAGE = "kinyarwanda"
UNCLASSIFIABLE_LABEL = "CANNOT CLASSIFY"
SPLIT_NAMES = ("train", "calibration", "test")
#: Share of scenarios per class. Test is the largest hold-out the corpus can fund
#: while leaving a trainable majority; see the manifest for what it actually buys.
SHARES = {"train": 0.70, "calibration": 0.10, "test": 0.20}
FIELDNAMES = ("item_id", "text", "language", "gold_label", "scenario_id", "split")
NEAR_DUPLICATE_JACCARD = 0.85
SHINGLE_WORDS = 3


@dataclass(frozen=True)
class Item:
    item_id: str
    text: str
    gold_label: str
    scenario_id: str


def normalise(text: str) -> str:
    """Whitespace-collapsed lowercase. Identical to pipeline.normalise."""
    return " ".join(text.strip().lower().split())


def shingles(text: str) -> frozenset[str]:
    """Word 3-grams of the normalised text, as pipeline._shingles builds them."""
    words = normalise(text).split(" ")
    if len(words) < SHINGLE_WORDS:
        return frozenset({" ".join(words)})
    return frozenset(
        " ".join(words[i : i + SHINGLE_WORDS])
        for i in range(len(words) - SHINGLE_WORDS + 1)
    )


def scenario_components(texts: list[str]) -> list[int]:
    """Component index per text: exact-equal or Jaccard >= 0.85 joins two texts."""
    parent = list(range(len(texts)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    seen: dict[str, int] = {}
    for index, text in enumerate(texts):
        norm = normalise(text)
        if norm in seen:
            union(seen[norm], index)
        else:
            seen[norm] = index
    grams = [shingles(t) for t in texts]
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if normalise(texts[i]) == normalise(texts[j]):
                continue
            overlap = len(grams[i] & grams[j])
            if not overlap:
                continue
            if overlap / len(grams[i] | grams[j]) >= NEAR_DUPLICATE_JACCARD:
                union(i, j)
    return [find(i) for i in range(len(texts))]


def scenario_id(texts: list[str]) -> str:
    """Content-addressed, so the same sentences always yield the same id."""
    joined = "\u001f".join(sorted(normalise(t) for t in texts))
    return "s" + hashlib.sha256(joined.encode()).hexdigest()[:12]


def build_items() -> tuple[list[Item], dict[str, list[int]]]:
    """Trainable items grouped into scenarios, plus what was excluded and why."""
    rows = lc.load()
    excluded = {
        "no_text": sorted(r.id for r in rows if not r.has_text),
        "unclassifiable": sorted(
            r.id for r in rows if r.has_text and r.label == UNCLASSIFIABLE_LABEL
        ),
    }
    usable = [r for r in rows if r.has_text and r.label in LABEL_MAP]
    components = scenario_components([r.text for r in usable])
    grouped: dict[int, list[int]] = defaultdict(list)
    for index, component in enumerate(components):
        grouped[component].append(index)
    items = []
    for members in grouped.values():
        sid = scenario_id([usable[i].text for i in members])
        for i in members:
            row = usable[i]
            items.append(Item(f"kw-{row.id:06d}", row.text, row.label, sid))
    return sorted(items, key=lambda it: it.item_id), excluded


def assign(items: list[Item], seed: int) -> dict[str, str]:
    """Scenario id -> split name. Stratified by class, allocated by scenario.

    A scenario is one unit whatever its row count, so its label is the label of
    its rows; the clustering never merges two labels on this corpus, and a mixed
    component would be a defect worth failing on rather than resolving silently.
    """
    by_scenario: dict[str, set[str]] = defaultdict(set)
    for item in items:
        by_scenario[item.scenario_id].add(item.gold_label)
    mixed = sorted(s for s, labels in by_scenario.items() if len(labels) > 1)
    if mixed:
        raise ValueError(f"scenarios spanning more than one label: {mixed[:5]}")

    per_class: dict[str, list[str]] = defaultdict(list)
    for scenario, labels in by_scenario.items():
        per_class[next(iter(labels))].append(scenario)

    rng = random.Random(seed)
    out: dict[str, str] = {}
    for label in sorted(per_class):
        scenarios = sorted(per_class[label])
        rng.shuffle(scenarios)
        total = len(scenarios)
        n_test = round(total * SHARES["test"])
        n_calibration = round(total * SHARES["calibration"])
        for position, scenario in enumerate(scenarios):
            if position < n_test:
                out[scenario] = "test"
            elif position < n_test + n_calibration:
                out[scenario] = "calibration"
            else:
                out[scenario] = "train"
    return out


def counts(items: list[Item], assignment: dict[str, str]) -> dict[str, dict[str, int]]:
    """Distinct scenarios and rows per split per class. Scenarios are the honest n."""
    table: dict[str, dict[str, int]] = {}
    for split in SPLIT_NAMES:
        chosen = [i for i in items if assignment[i.scenario_id] == split]
        rows = Counter(i.gold_label for i in chosen)
        scenarios = {
            label: len({i.scenario_id for i in chosen if i.gold_label == label})
            for label in LABEL_MAP
        }
        table[split] = {
            **{f"rows_{k}": rows.get(k, 0) for k in LABEL_MAP},
            **{f"scenarios_{k}": scenarios[k] for k in LABEL_MAP},
            "rows_total": len(chosen),
            "scenarios_total": len({i.scenario_id for i in chosen}),
        }
    return table


def write(out: Path, items: list[Item], assignment: dict[str, str], seed: int) -> None:
    if out.exists() and any(out.iterdir()):
        raise SystemExit(
            f"REFUSED: {out} already holds a split. A split is frozen once "
            "(docs/ENGINEERING_SPEC.md L8); delete it deliberately or choose another path."
        )
    out.mkdir(parents=True, exist_ok=True)
    digests = {}
    for split in SPLIT_NAMES:
        path = out / f"{split}.csv"
        chosen = [i for i in items if assignment[i.scenario_id] == split]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()
            for item in chosen:
                writer.writerow(
                    {
                        "item_id": item.item_id,
                        "text": item.text,
                        "language": LANGUAGE,
                        "gold_label": item.gold_label,
                        "scenario_id": item.scenario_id,
                        "split": split,
                    }
                )
        digests[f"{split}.csv"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _, excluded = build_items()
    manifest = {
        "corpus": str(lc.CORPUS.relative_to(ML_ROOT)),
        "corpus_sha256": lc.digest(),
        "seed": seed,
        "language": LANGUAGE,
        "hold_out_unit": "source sentence (near-duplicate component)",
        "near_duplicate_jaccard": NEAR_DUPLICATE_JACCARD,
        "shares": SHARES,
        "counts": counts(items, assignment),
        "excluded": {k: {"n": len(v), "ids": v} for k, v in excluded.items()},
        "file_sha256": digests,
        "provenance": lc.provenance_line(),
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    items, _ = build_items()
    assignment = assign(items, args.seed)
    write(args.out, items, assignment, args.seed)
    print(lc.provenance_line())
    print(json.dumps(counts(items, assignment), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
