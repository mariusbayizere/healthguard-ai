#!/usr/bin/env python
"""The pilot authoring instrument: the sheet native authors fill in, and the gates it
enforces while they do (EVAL_SET_SPEC §7 and §8, CORPUS_REBUILD §3, ENGINEERING_SPEC §10.2).

    python -m annotation.authoring --language kinyarwanda --items 2354 --out sheet.csv
    python -m annotation.authoring --check returned_sheet.csv
    python -m annotation.authoring --report --language kinyarwanda --items 2354 --authors 5

WHAT THIS FILE DOES NOT CONTAIN
-------------------------------
No vignette text and no urgency label, by design.
  * The text is written by native Kinyarwanda-speaking clinicians. Machine-authored or
    machine-translated Kinyarwanda is not admissible (ENGINEERING_SPEC §10.2 T1/T3).
  * The label is the annotator's, twice over, with adjudication (EVAL_SET_SPEC §9).
    A label in the authoring sheet would anchor the annotator, so `annotation/store.py`
    refuses an urgency column at import and `check_rows` refuses one here.

WHAT IS STILL BLOCKED (the sheet writes BLOCKED, it never guesses)
-----------------------------------------------------------------
See BLOCKED_AXES: the clinical domain axis, the clinical presentation types, and the
urgency definitions themselves. Each names the document or person that must supply it.

THE GATES, AT AUTHORING TIME RATHER THAN AFTER
----------------------------------------------
CORPUS_REBUILD §3 defines G1-G8 for the corpus. The ones that can be judged from a
sheet are enforced here, so an author learns about a collapse while there is still time
to write differently:
  G1 rows per seed         G4 near-duplicate seeds      G5 machine person-transformation
  G7 provenance complete   G8 author concentration
G2 (distinct seeds per language, and per non-empty cell) is a property of the finished
corpus, so `check_rows` reports it only in corpus scope; `capacity()` says where it
binds, and it cannot be computed per cell while the domain axis is BLOCKED.
G3 (lexical diversity floor) is deliberately absent: its floor is defined as a fraction
of the natively authored pilot's own MATTR, so it cannot be computed until this pilot
exists (CORPUS_REBUILD §3).
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BLOCKED = "BLOCKED"

#: Axis -> what must supply it. The sheet writes BLOCKED in these columns.
BLOCKED_AXES: dict[str, str] = {
    "domain": (
        "docs/clinical/ national triage protocol, with its own organisation of domains "
        "(EVAL_SET_SPEC §7; register H4). The repository's 9 corpus domains are an "
        "unratified placeholder and must not define the grid."
    ),
    "clinical_presentation_type": (
        "docs/clinical/ (register D2/D3): atypical presentation of a time-critical "
        "condition, paediatric, obstetric, and near-boundary pairs (EVAL_SET_SPEC §7)."
    ),
    "urgency_definition": (
        "the lead clinician (register H6), through protocol §3: the category definitions "
        "and worked examples. Authors do not label, and the definitions are not needed "
        "to author."
    ),
}

SHEET_COLUMNS: tuple[str, ...] = (
    "item_id",
    "text",  # written by the author; empty in the issued sheet
    "language",
    "split",
    "scenario_id",
    "seed_id",
    "reporter",
    "patient_age_group",
    "domain",
    "voice",
    "length",
    "negation",
    "multiple_complaints",
    "register",
    "author_code",
    "generation_method",
    "validated_by",
    "date",
)

#: Columns an author must fill for provenance to be complete (G7). `text` is filled at
#: authoring time; `domain` may be BLOCKED until H4.
PROVENANCE_COLUMNS = (
    "item_id",
    "language",
    "split",
    "scenario_id",
    "seed_id",
    "reporter",
    "patient_age_group",
    "author_code",
    "generation_method",
    "validated_by",
    "date",
)

FORBIDDEN_COLUMNS = ("urgency", "gold_label", "label", "urgency_level")

#: G5: the only admissible origins. Anything else fails the build.
ALLOWED_GENERATION_METHODS = {
    "native_author": "written by a native speaker (any split)",
    "native_author_variant": "a paraphrase by a native speaker (calibration split only)",
}

MAX_ROWS_PER_SEED = 50  # G1
MAX_SEED_SHARE = 0.001  # G1: no seed above 0.1% of rows
MIN_SEEDS_PER_LANGUAGE = 3000  # G2
MIN_SEEDS_PER_CELL = 30  # G2
NEAR_DUPLICATE_JACCARD = 0.85  # G4 (ENGINEERING_SPEC §3.6)
MAX_NEAR_DUPLICATE_SEED_RATE = 0.02  # G4
MAX_AUTHOR_SHARE = 0.20  # G8
SHINGLE_WORDS = 3

LINGUISTIC_TYPES = {
    "voice": ("first_person", "reported"),
    "length": ("fragment", "sentence", "narrative"),
    "negation": ("yes", "no"),
    "multiple_complaints": ("yes", "no"),
    "register": ("everyday", "formal"),
}
REPORTERS = ("self", "relative_or_carer")
AGE_GROUPS = (
    BLOCKED,
)  # E6 is undecided: the scope (paediatric / adult / both) is yours


class AuthoringError(ValueError):
    """The sheet cannot be issued or read as given."""


# ── Issuing a sheet ───────────────────────────────────────────────────────────
def _read_domains(path: Path) -> list[str]:
    with Path(path).open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not {"domain", "source"} <= rows[0].keys():
        raise AuthoringError("the domain list needs columns domain,source")
    for row in rows:
        if not (row.get("source") or "").strip():
            raise AuthoringError(
                f"domain {row['domain']!r} has no source. Every domain cites the "
                "document and page it comes from (EVAL_SET_SPEC §7)"
            )
    return [row["domain"].strip() for row in rows]


def write_sheet(
    path: Path,
    *,
    language: str,
    items: int,
    domains: Path | None = None,
    split: str = "test",
    start: int = 1,
) -> Path:
    """Write an empty authoring sheet: one row per item, text blank, no urgency column."""
    if items < 1:
        raise AuthoringError("an authoring sheet needs at least one row")
    names = _read_domains(domains) if domains is not None else [BLOCKED]
    prefix = language[:2].lower()
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for k in range(items):
            seed = f"{prefix}-seed-{start + k:05d}"
            writer.writerow(
                {
                    "item_id": f"{prefix}-{start + k:05d}",
                    "text": "",
                    "language": language,
                    "split": split,
                    "scenario_id": seed,
                    "seed_id": seed,
                    "reporter": "",
                    "patient_age_group": BLOCKED,
                    "domain": names[k % len(names)],
                    "voice": "",
                    "length": "",
                    "negation": "",
                    "multiple_complaints": "",
                    "register": "",
                    "author_code": "",
                    "generation_method": "native_author",
                    "validated_by": "PENDING",
                    "date": "",
                }
            )
    return Path(path)


# ── Checking a returned sheet ─────────────────────────────────────────────────
def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _shingles(text: str) -> frozenset[str]:
    words = _normalise(text).split(" ")
    if len(words) < SHINGLE_WORDS:
        return frozenset({" ".join(words)})
    return frozenset(
        " ".join(words[i : i + SHINGLE_WORDS])
        for i in range(len(words) - SHINGLE_WORDS + 1)
    )


def _content_words(text: str) -> frozenset[str]:
    return frozenset(_normalise(text).split(" "))


#: Columns that, if present in a RETURNED sheet, carry the English SITUATION
#: PROMPT for the item -- not a translation of it.
#:
#: The issued sheet has none of these: `write_sheet` emits one `text` column and
#: the author fills it in Kinyarwanda. Prompts are produced outside the
#: repository and handed to authors alongside the sheet (CORPUS_REBUILD.md R3).
#:
#: The distinction governs what may be checked. The prompt describes a
#: situation; the author writes what the person would SAY. Divergent wording is
#: the intended outcome and the reason authored sentences carry twice the
#: vocabulary of generated ones -- so nothing here diffs strings. A divergent
#: EVENT is the defect: one returned pair described a monkey bite in the prompt
#: and a snake bite in the authored text.
ENGLISH_COLUMNS = ("english", "english_gloss", "english_text", "gloss")

_DIGITS = re.compile(r"\d+")


def _numeric_disagreement(english: str, authored: str) -> str | None:
    """A numeral in one column and not the other, or different numerals.

    THE ONLY PART OF R2 THAT CAN BE AUTOMATED HERE. Numerals are the one thing
    both columns spell identically regardless of language, so "for 3 days"
    against a sentence containing no 3 is detectable without knowing either
    language. Everything else about R2 -- whether the animal, the body part or
    the mechanism agree -- is not, and this function deliberately does not
    pretend otherwise.
    """
    left, right = set(_DIGITS.findall(english)), set(_DIGITS.findall(authored))
    if left == right:
        return None
    only_english = sorted(left - right)
    only_authored = sorted(right - left)
    parts = []
    if only_english:
        parts.append(f"{only_english} appears only in the English")
    if only_authored:
        parts.append(f"{only_authored} appears only in the authored text")
    return "; ".join(parts)


def check_rows(rows: Sequence[Mapping[str, str]], *, scope: str = "pilot") -> list[str]:
    """Every gate violation and rule violation in a returned sheet. Empty means it may be
    imported for annotation. `scope='corpus'` additionally enforces G2."""
    problems: list[str] = []
    if not rows:
        return ["the sheet has no rows"]

    for column in FORBIDDEN_COLUMNS:
        if any(column in row for row in rows):
            problems.append(
                f"the sheet carries a {column!r} column: an authoring sheet never carries an "
                "urgency label, because it would anchor the annotator (EVAL_SET_SPEC §9)"
            )

    # G7 provenance completeness
    for row in rows:
        missing = [c for c in PROVENANCE_COLUMNS if not (row.get(c) or "").strip()]
        if missing:
            problems.append(
                f"G7 provenance: item {row.get('item_id', '?')!r} is missing {', '.join(missing)}"
            )
        if not (row.get("text") or "").strip():
            problems.append(
                f"G7 provenance: item {row.get('item_id', '?')!r} has no text"
            )

    # G5 machine person-transformation
    for row in rows:
        method = (row.get("generation_method") or "").strip()
        if method not in ALLOWED_GENERATION_METHODS:
            problems.append(
                f"G5 machine person-transformation: item {row.get('item_id', '?')!r} has "
                f"generation_method {method!r}; allowed: {sorted(ALLOWED_GENERATION_METHODS)}"
            )
        if (
            method == "native_author_variant"
            and (row.get("split") or "").strip() != "calibration"
        ):
            problems.append(
                f"G5: item {row.get('item_id', '?')!r} is a variant outside the calibration "
                "split (EVAL_SET_SPEC §8: one item per scenario in the test split)"
            )
    by_seed_author: dict[tuple[str, str, frozenset[str]], set[str]] = defaultdict(set)
    for row in rows:
        key = (
            (row.get("seed_id") or "").strip(),
            (row.get("author_code") or "").strip(),
            _content_words(row.get("text", "")),
        )
        by_seed_author[key].add((row.get("voice") or "").strip())
    for (seed, author, _), voices in by_seed_author.items():
        if len(voices) > 1 and author:
            problems.append(
                f"G5 machine person-transformation: author {author!r} wrote seed {seed!r} in "
                f"{sorted(voices)} with the same content words. A first/third pair needs two "
                "different authors (CORPUS_REBUILD §3 G5)"
            )

    # G1 rows per seed
    per_seed = Counter((row.get("seed_id") or "").strip() for row in rows)
    for seed, count in per_seed.items():
        if count > MAX_ROWS_PER_SEED:
            problems.append(
                f"G1 rows per seed: seed {seed!r} has {count} rows, max {MAX_ROWS_PER_SEED}"
            )
        if len(rows) >= 1000 and count > MAX_SEED_SHARE * len(rows):
            problems.append(
                f"G1 seed share: seed {seed!r} is {count / len(rows):.2%} of rows, max "
                f"{MAX_SEED_SHARE:.1%}"
            )

    # One item per scenario in the test split (EVAL_SET_SPEC §8)
    test_scenarios = Counter(
        (row.get("scenario_id") or "").strip()
        for row in rows
        if (row.get("split") or "").strip() == "test"
    )
    for scenario, count in test_scenarios.items():
        if count > 1:
            problems.append(
                f"scenario {scenario!r} has {count} items in the test split; the test split "
                "holds one item per scenario, variants belong to calibration"
            )

    # G8 author concentration, per language x domain
    per_cell: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in rows:
        cell = ((row.get("language") or "").strip(), (row.get("domain") or "").strip())
        per_cell[cell][(row.get("author_code") or "").strip()] += 1
    for (language, domain), authors in per_cell.items():
        total = sum(authors.values())
        for author, count in authors.items():
            if author and count > MAX_AUTHOR_SHARE * total:
                problems.append(
                    f"G8 author concentration: {author!r} wrote {count}/{total} "
                    f"({count / total:.0%}) of {language} x {domain}, max {MAX_AUTHOR_SHARE:.0%}"
                )

    # G4 near-duplicate seeds, one row per seed
    first_by_seed: dict[str, str] = {}
    for row in rows:
        seed = (row.get("seed_id") or "").strip()
        first_by_seed.setdefault(seed, row.get("text", ""))
    texts = {s: t for s, t in first_by_seed.items() if _normalise(t)}
    exact: Counter = Counter(_normalise(t) for t in texts.values())
    duplicated = [t for t, n in exact.items() if n > 1]
    if duplicated:
        problems.append(
            f"G4 exact duplicates: {len(duplicated)} text(s) appear on more than one seed"
        )
    shingles = {s: _shingles(t) for s, t in texts.items()}
    seeds = sorted(shingles)
    near = set()
    for i, left in enumerate(seeds):
        for right in seeds[i + 1 :]:
            a, b = shingles[left], shingles[right]
            if len(a | b) and len(a & b) / len(a | b) >= NEAR_DUPLICATE_JACCARD:
                near.update({left, right})
    if texts and len(near) / len(texts) > MAX_NEAR_DUPLICATE_SEED_RATE:
        problems.append(
            f"G4 near-duplicate seeds: {len(near)}/{len(texts)} ({len(near) / len(texts):.1%}) of "
            f"seeds have a neighbour at Jaccard >= {NEAR_DUPLICATE_JACCARD}, max "
            f"{MAX_NEAR_DUPLICATE_SEED_RATE:.0%}"
        )

    if scope == "corpus":
        per_language = defaultdict(set)
        for row in rows:
            per_language[(row.get("language") or "").strip()].add(
                (row.get("seed_id") or "").strip()
            )
        for language, found in per_language.items():
            if len(found) < MIN_SEEDS_PER_LANGUAGE:
                problems.append(
                    f"G2 distinct seeds: {language} has {len(found)}, needs "
                    f"{MIN_SEEDS_PER_LANGUAGE} (corpus scope)"
                )
    # R2: a row carrying BOTH a prompt column and authored text asserts that the
    # two describe the same EVENT. One returned pair did not -- a monkey bite in
    # the prompt, a snake bite in the authored column -- and it would have entered
    # the corpus as a matched pair.
    #
    # Wording is NOT compared and must not be: the prompt is a situation, not a
    # source text, and an author who tracked its wording would be translating
    # (CORPUS_REBUILD.md R3).
    #
    # This CANNOT decide the question. Deciding it needs a reader with both
    # languages, and this module is deliberately language-agnostic. So it does two
    # things it can do honestly: report the numeric disagreements it can see, and
    # route every remaining pair to a human. The message says "confirm", never
    # "verified", because nothing here has verified anything.
    for row in rows:
        english_column = next(
            (c for c in ENGLISH_COLUMNS if (row.get(c) or "").strip()), None
        )
        if english_column is None:
            continue
        english = (row.get(english_column) or "").strip()
        authored = (row.get("text") or "").strip()
        if not authored:
            continue

        item = row.get("item_id", "?")
        mismatch = _numeric_disagreement(english, authored)
        if mismatch is not None:
            problems.append(
                f"R2 numerals: item {item!r} disagrees between prompt {english_column!r} and "
                f"'text' -- {mismatch}. One column describes something the other does "
                "not."
            )
        problems.append(
            f"R2 REVIEW REQUIRED: item {item!r} carries both {english_column!r} and "
            "'text'. A human who reads both languages must confirm they describe the "
            "same event -- same mechanism, body part, actor and number of complaints. "
            "This check cannot decide it (CORPUS_REBUILD.md R2)."
        )

    return problems


# ── Capacity: where each gate binds ───────────────────────────────────────────
def minimum_authors(items_in_language_and_domain: int) -> int:
    """G8: no author above 20% of a language x domain, so at least 5 authors per cell."""
    needed = math.ceil(1 / MAX_AUTHOR_SHARE)
    return min(needed, max(1, items_in_language_and_domain))


def capacity(
    *, language: str, items: int, authors: int, domains: Path | None = None
) -> list[dict[str, Any]]:
    """For each gate: where it binds for a set of this size, or why it cannot be computed."""
    names = _read_domains(domains) if domains is not None else None
    cells_unknown = names is None
    rows: list[dict[str, Any]] = [
        {
            "gate": "G1",
            "rule": f"<= {MAX_ROWS_PER_SEED} rows per seed, and no seed above {MAX_SEED_SHARE:.1%} of rows",
            "binds_at_items": None,
            "note": (
                "The test split holds one item per scenario (EVAL_SET_SPEC §8), so each item is "
                "its own seed and G1 cannot bind. It binds only if calibration variants are "
                f"written: {MAX_ROWS_PER_SEED} variants per seed, and above 1,000 items the "
                f"{MAX_SEED_SHARE:.1%} share is the tighter limit"
            ),
        },
        {
            "gate": "G2",
            "rule": f">= {MIN_SEEDS_PER_LANGUAGE} distinct seeds per language, and >= {MIN_SEEDS_PER_CELL} per non-empty cell",
            "binds_at_items": MIN_SEEDS_PER_LANGUAGE,
            "cells_unknown": cells_unknown,
            "blocked_by": "domain axis" if cells_unknown else "",
            "note": (
                f"A {items}-item pilot has at most {items} seeds, below the corpus floor of "
                f"{MIN_SEEDS_PER_LANGUAGE}: G2 is a corpus gate and is NOT applied to the pilot. "
                "The per-cell floor cannot be computed at all while the domain axis is BLOCKED, "
                "so the minimum viable set size is unknown"
            ),
        },
        {
            "gate": "G3",
            "rule": "MATTR >= 80% of the natively authored pilot's own MATTR",
            "binds_at_items": None,
            "note": "Cannot bind on the pilot: the pilot is what defines the floor",
        },
        {
            "gate": "G4",
            "rule": f"<= {MAX_NEAR_DUPLICATE_SEED_RATE:.0%} of seeds with a neighbour at Jaccard >= {NEAR_DUPLICATE_JACCARD}",
            "binds_at_items": math.ceil(1 / MAX_NEAR_DUPLICATE_SEED_RATE),
            "note": (
                f"From {math.ceil(1 / MAX_NEAR_DUPLICATE_SEED_RATE)} items, a single near-duplicate "
                "pair exceeds the rate. This is the gate most likely to bind in practice, because "
                "authors writing to a grid converge on phrasings"
            ),
        },
        {
            "gate": "G5",
            "rule": "generation_method in the allowed set; a first/third pair needs two authors",
            "binds_at_items": None,
            "note": "Per item, not per size. It binds the moment machine transformation is used",
        },
        {
            "gate": "G7",
            "rule": "100% provenance",
            "binds_at_items": None,
            "note": "Per item",
        },
        {
            "gate": "G8",
            "rule": f"no author above {MAX_AUTHOR_SHARE:.0%} of a language x domain",
            "binds_at_items": authors * math.ceil(1 / MAX_AUTHOR_SHARE)
            if authors
            else None,
            "minimum_authors": minimum_authors(items),
            "note": (
                f"With {authors} author(s), the cell cannot exceed "
                f"{authors * math.ceil(1 / MAX_AUTHOR_SHARE)} items before one author passes "
                f"{MAX_AUTHOR_SHARE:.0%}. At least {minimum_authors(items)} authors are needed "
                "per language x domain, and the cell count itself is BLOCKED"
            ),
        },
    ]
    return rows


def report(
    *, language: str, items: int, authors: int, domains: Path | None = None
) -> str:
    lines = [
        f"Authoring instrument — {language}, {items} items, {authors} author(s)",
        "",
        "The sheet carries no urgency label (the annotator's job) and no text (the author's).",
        "",
        "Gate                                                        Binds at        Note",
    ]
    for entry in capacity(
        language=language, items=items, authors=authors, domains=domains
    ):
        binds = entry["binds_at_items"]
        lines.append(
            f"{entry['gate']:<4} {entry['rule']:<54} {binds or '-'!s:<15} {entry['note']}"
        )
    lines += [
        "",
        "BLOCKED axes — the sheet writes BLOCKED and names what must supply each:",
    ]
    for axis, source in BLOCKED_AXES.items():
        lines.append(f"  {axis}: {source}")
    lines += [
        "",
        "H4 (national triage protocol) is the one that blocks the grid itself: without a ratified",
        "domain list the number of non-empty cells is unknown, so G2's per-cell floor, and with it",
        "the minimum viable set size, cannot be computed.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--language", default="kinyarwanda")
    parser.add_argument("--items", type=int, default=2354)
    parser.add_argument("--authors", type=int, default=5)
    parser.add_argument("--domains", type=Path, default=None)
    parser.add_argument("--split", default="test")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--scope", choices=("pilot", "corpus"), default="pilot")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.check:
        with args.check.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        problems = check_rows(rows, scope=args.scope)
        for problem in problems:
            print(f"REFUSED: {problem}", file=sys.stderr)
        print(f"{len(rows)} rows, {len(problems)} problem(s)")
        return 2 if problems else 0
    if args.out:
        path = write_sheet(
            args.out,
            language=args.language,
            items=args.items,
            domains=args.domains,
            split=args.split,
        )
        print(f"{args.items} empty rows -> {path}")
        return 0
    print(
        report(
            language=args.language,
            items=args.items,
            authors=args.authors,
            domains=args.domains,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
