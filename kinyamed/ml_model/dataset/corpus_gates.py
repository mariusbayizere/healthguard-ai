#!/usr/bin/env python
"""CORPUS_REBUILD §3 gates G1-G9, checked over a generated corpus.

    python dataset/corpus_gates.py --corpus dataset/raw/symptoms_large.csv --seeds 165

No gate is waived, softened, or passed for being close. A gate that cannot be computed
from the data at hand is reported **NOT COMPUTABLE**, with the reason, and never as a
pass: an uncomputable gate is an open question, not a clearance.

Stdlib only, like the rest of the dataset pipeline, so this runs with nothing installed.

WHAT EACH GATE ASKS (CORPUS_REBUILD §3)
  G1 rows per seed          <= 50, and no seed above 0.1% of rows
  G2 distinct seeds         >= 3,000 per language, and >= 30 per non-empty cell
  G3 lexical diversity      MATTR >= 80% of the natively authored pilot's MATTR
  G4 near-duplicate seeds   <= 2% of seeds with a neighbour at Jaccard >= 0.85; 0 exact
  G5 machine transformation generation_method in the allowed set, per row
  G6 frame consistency      the frame matches the row's reporter and age group
  G7 provenance             100% of rows carry the §2 metadata
  G8 author concentration   no author above 20% of a language x domain
  G9 surface variation      real case, punctuation, spacing and typo variety (added
                            2026-09-16 after the probe measured what its absence costs)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MAX_ROWS_PER_SEED = 50  # G1
MAX_SEED_SHARE = 0.001  # G1
MIN_SEEDS_PER_LANGUAGE = 3000  # G2
MIN_SEEDS_PER_CELL = 30  # G2
NEAR_DUPLICATE_JACCARD = 0.85  # G4
MAX_NEAR_DUPLICATE_SEED_RATE = 0.02  # G4
MAX_AUTHOR_SHARE = 0.20  # G8
SHINGLE_WORDS = 3

ALLOWED_GENERATION_METHODS = {"native_author", "native_author_variant"}
PROVENANCE_COLUMNS = ("seed_id", "generation_method", "author_code", "validated_by")

# G9 shares. Engineering defaults (CORPUS_REBUILD §3.1), not clinical values.
MIN_NON_SENTENCE_CASE = 0.15
MIN_WITHOUT_TERMINAL_PUNCTUATION = 0.20


@dataclass(frozen=True)
class GateResult:
    gate: str
    rule: str
    passed: bool | None  # None = NOT COMPUTABLE, never a pass
    detail: str

    @property
    def verdict(self) -> str:
        return {True: "PASS", False: "FAIL", None: "NOT COMPUTABLE"}[self.passed]


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


def _first_text_per_seed(rows: Sequence[Mapping[str, str]]) -> dict[str, str]:
    first: dict[str, str] = {}
    for row in rows:
        seed = (row.get("seed_id") or "").strip()
        if seed:
            first.setdefault(seed, row.get("text", ""))
    return first


def _g1(rows) -> GateResult:
    rule = f"<= {MAX_ROWS_PER_SEED} rows per seed, and no seed above {MAX_SEED_SHARE:.1%} of rows"
    if not any((row.get("seed_id") or "").strip() for row in rows):
        return GateResult(
            "G1", rule, None, "no seed_id column: rows cannot be attributed to a seed"
        )
    counts = Counter((row.get("seed_id") or "").strip() for row in rows)
    over = [(s, n) for s, n in counts.items() if n > MAX_ROWS_PER_SEED]
    share = [
        (s, n)
        for s, n in counts.items()
        if len(rows) >= 1000 and n > MAX_SEED_SHARE * len(rows)
    ]
    if over or share:
        parts = []
        if over:
            worst = max(over, key=lambda kv: kv[1])
            parts.append(
                f"{len(over)} seed(s) above {MAX_ROWS_PER_SEED} rows, worst {worst[0]!r} at {worst[1]:,}"
            )
        if share:
            worst = max(share, key=lambda kv: kv[1])
            parts.append(
                f"{len(share)} seed(s) above {MAX_SEED_SHARE:.1%} of the corpus, worst "
                f"{worst[0]!r} at {worst[1] / len(rows):.2%}"
            )
        return GateResult("G1", rule, False, "; ".join(parts))
    return GateResult(
        "G1",
        rule,
        True,
        f"{len(counts):,} seeds, max {max(counts.values())} rows per seed",
    )


def _g2(rows) -> GateResult:
    rule = f">= {MIN_SEEDS_PER_LANGUAGE:,} distinct seeds per language, and >= {MIN_SEEDS_PER_CELL} per non-empty cell"
    per_language: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        seed = (row.get("seed_id") or "").strip()
        if seed:
            per_language[(row.get("language") or "").strip()].add(seed)
    if not per_language:
        return GateResult(
            "G2", rule, None, "no seed_id column: distinct seeds cannot be counted"
        )
    short = {
        lang: len(seeds)
        for lang, seeds in per_language.items()
        if len(seeds) < MIN_SEEDS_PER_LANGUAGE
    }
    cell_note = (
        " The per-cell floor is NOT COMPUTABLE: a cell is domain x urgency x reporter x age group, and the "
        "domain axis is unratified (H4) while the age axis awaits E6."
    )
    if short:
        worst = ", ".join(f"{lang} {n:,}" for lang, n in sorted(short.items()))
        return GateResult(
            "G2",
            rule,
            False,
            f"{worst} distinct seeds, needs {MIN_SEEDS_PER_LANGUAGE:,}.{cell_note}",
        )
    return GateResult(
        "G2",
        rule,
        None,
        "every language meets the seed floor, but the per-cell floor is NOT COMPUTABLE."
        + cell_note,
    )


def _g3(rows) -> GateResult:
    return GateResult(
        "G3",
        "MATTR >= 80% of the natively authored pilot's MATTR",
        None,
        "the floor is defined as a fraction of the pilot's own diversity, and no pilot exists yet",
    )


def _g4(rows) -> GateResult:
    rule = f"<= {MAX_NEAR_DUPLICATE_SEED_RATE:.0%} of seeds with a neighbour at Jaccard >= {NEAR_DUPLICATE_JACCARD}, 0 exact duplicates"
    texts = _first_text_per_seed(rows)
    if not texts:
        return GateResult(
            "G4", rule, None, "no seed_id column: seeds cannot be compared"
        )
    exact = Counter(_normalise(t) for t in texts.values())
    duplicated = sum(1 for n in exact.values() if n > 1)
    shingles = {seed: _shingles(text) for seed, text in texts.items()}
    seeds = sorted(shingles)
    near: set[str] = set()
    for i, left in enumerate(seeds):
        for right in seeds[i + 1 :]:
            a, b = shingles[left], shingles[right]
            if len(a | b) and len(a & b) / len(a | b) >= NEAR_DUPLICATE_JACCARD:
                near.update({left, right})
    rate = len(near) / len(texts)
    if duplicated or rate > MAX_NEAR_DUPLICATE_SEED_RATE:
        return GateResult(
            "G4",
            rule,
            False,
            f"{duplicated} exact duplicate text(s) across seeds; {len(near):,}/{len(texts):,} seeds "
            f"({rate:.1%}) have a near-duplicate neighbour",
        )
    return GateResult(
        "G4",
        rule,
        True,
        f"{len(near):,}/{len(texts):,} seeds ({rate:.1%}) near-duplicate, 0 exact",
    )


def _g5(rows) -> GateResult:
    rule = "generation_method in the allowed set; machine person-transformation banned"
    if not any("generation_method" in row for row in rows):
        return GateResult(
            "G5",
            rule,
            False,
            "the corpus carries no generation_method column, so the origin of every row is unknown. "
            "An unattributable row is refused, not assumed native",
        )
    bad = Counter(
        (row.get("generation_method") or "").strip()
        for row in rows
        if (row.get("generation_method") or "").strip()
        not in ALLOWED_GENERATION_METHODS
    )
    if bad:
        listed = ", ".join(
            f"{method or 'empty'!r} x{n:,}" for method, n in bad.most_common(5)
        )
        return GateResult(
            "G5",
            rule,
            False,
            f"{sum(bad.values()):,} row(s) with a disallowed origin: {listed}",
        )
    return GateResult(
        "G5", rule, True, f"all {len(rows):,} rows carry an allowed generation_method"
    )


# Reporter x age-group pairs ratified as coherent. EMPTY ON PURPOSE: which
# combinations a corpus may contain is a judgement about who presents on whose
# behalf, and nobody has made it for this project. G6 reports the pairs it
# observes so they can be ratified; it does not invent the ruling, and it does
# not pass a corpus because the pairs look reasonable.
PERMITTED_REPORTER_AGE: frozenset[tuple[str, str]] = frozenset()


def _g6(rows) -> GateResult:
    """Reporter and age group: present, complete, and drawn from a ratified set.

    WRITTEN 2026-09-18. Until then this returned a hardcoded NOT COMPUTABLE
    string and read no column at all, so it could not pass or fail whatever it
    was given, and it reported the same sentence about a corpus that records
    both fields as about one that records neither. A gate that cannot change its
    answer is not a gate. The generated corpus genuinely lacked both columns,
    which is why nobody noticed until a corpus arrived that had them.
    """
    rule = "the frame matches the row's reporter and patient age group"
    has_reporter = any("reporter" in row for row in rows)
    has_age = any("age_group" in row or "patient_age_group" in row for row in rows)

    if not (has_reporter and has_age):
        absent = ", ".join(
            name
            for name, present in (("reporter", has_reporter), ("age_group", has_age))
            if not present
        )
        return GateResult(
            "G6", rule, None, f"the corpus carries no {absent} column per row"
        )

    def age_of(row) -> str:
        return (row.get("age_group") or row.get("patient_age_group") or "").strip()

    incomplete = sum(
        1 for row in rows if not (row.get("reporter") or "").strip() or not age_of(row)
    )
    if incomplete:
        return GateResult(
            "G6",
            rule,
            False,
            f"{incomplete:,}/{len(rows):,} row(s) are missing a reporter or an age "
            "group, so the frame cannot be checked against them",
        )

    observed = Counter((row["reporter"].strip(), age_of(row)) for row in rows)
    if not PERMITTED_REPORTER_AGE:
        listed = ", ".join(f"{r} x {a} ({n:,})" for (r, a), n in observed.most_common())
        return GateResult(
            "G6",
            rule,
            None,
            f"every row carries both fields and {len(observed)} distinct pairs are "
            f"present, but no ratified set of permitted reporter x age-group pairs "
            f"exists to check them against. Observed: {listed}. Ratify these in "
            "PERMITTED_REPORTER_AGE and this gate becomes computable",
        )

    unratified = {
        pair: n for pair, n in observed.items() if pair not in PERMITTED_REPORTER_AGE
    }
    if unratified:
        listed = ", ".join(
            f"{r} x {a} ({n:,})" for (r, a), n in sorted(unratified.items())
        )
        return GateResult(
            "G6",
            rule,
            False,
            f"{sum(unratified.values()):,} row(s) in unratified pairs: {listed}",
        )
    return GateResult(
        "G6",
        rule,
        True,
        f"all {len(rows):,} rows carry a reporter and an age group, in "
        f"{len(observed)} ratified pairs",
    )


def _g7(rows) -> GateResult:
    rule = "100% of rows carry the §2 provenance metadata"
    missing_columns = [
        c for c in PROVENANCE_COLUMNS if not any(c in row for row in rows)
    ]
    if missing_columns:
        return GateResult(
            "G7",
            rule,
            False,
            f"the corpus has no {', '.join(missing_columns)} column(s)",
        )
    incomplete = sum(
        1
        for row in rows
        if any(not (row.get(c) or "").strip() for c in PROVENANCE_COLUMNS)
    )
    if incomplete:
        return GateResult(
            "G7",
            rule,
            False,
            f"{incomplete:,}/{len(rows):,} rows have an empty provenance field",
        )
    return GateResult("G7", rule, True, f"all {len(rows):,} rows complete")


def _g8(rows) -> GateResult:
    rule = f"no author above {MAX_AUTHOR_SHARE:.0%} of a language x domain"
    if not any("author_code" in row for row in rows):
        return GateResult(
            "G8",
            rule,
            False,
            "the corpus has no author_code column: authorship is unrecorded",
        )
    per_cell: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in rows:
        cell = ((row.get("language") or "").strip(), (row.get("domain") or "").strip())
        per_cell[cell][(row.get("author_code") or "").strip()] += 1
    worst = None
    for (language, domain), authors in per_cell.items():
        total = sum(authors.values())
        for author, count in authors.items():
            share = count / total
            if share > MAX_AUTHOR_SHARE and (worst is None or share > worst[3]):
                worst = (author, language, domain, share)
    if worst:
        author, language, domain, share = worst
        return GateResult(
            "G8", rule, False, f"{author!r} wrote {share:.0%} of {language} x {domain}"
        )
    return GateResult(
        "G8",
        rule,
        True,
        f"no author above {MAX_AUTHOR_SHARE:.0%} in any language x domain",
    )


def _g9(rows) -> GateResult:
    rule = (
        f">= {MIN_NON_SENTENCE_CASE:.0%} not sentence-cased, >= {MIN_WITHOUT_TERMINAL_PUNCTUATION:.0%} without "
        "terminal punctuation, stray spacing present, realistic typos present"
    )
    texts = [row.get("text", "") for row in rows]
    if not texts:
        return GateResult("G9", rule, None, "no rows")
    total = len(texts)
    capitals = sum(1 for t in texts if t.strip() and t.strip().isupper())
    sentence_cased = sum(
        1 for t in texts if t.strip()[:1].isupper() and not t.strip().isupper()
    )
    non_sentence = (total - sentence_cased) / total
    no_terminal = sum(1 for t in texts if not re.search(r"[.?!]$", t.strip())) / total
    double_space = sum(1 for t in texts if "  " in t)
    problems = []
    if non_sentence < MIN_NON_SENTENCE_CASE:
        problems.append(
            f"{non_sentence:.1%} not sentence-cased (needs {MIN_NON_SENTENCE_CASE:.0%})"
        )
    if capitals == 0:
        problems.append("0 rows in capitals")
    if no_terminal < MIN_WITHOUT_TERMINAL_PUNCTUATION:
        problems.append(
            f"{no_terminal:.1%} without terminal punctuation (needs {MIN_WITHOUT_TERMINAL_PUNCTUATION:.0%})"
        )
    if double_space == 0:
        problems.append("0 rows with stray spacing")
    detail = (
        f"capitals {capitals:,}, not sentence-cased {non_sentence:.1%}, without terminal punctuation "
        f"{no_terminal:.1%}, stray spacing {double_space:,}. Typo share is NOT measurable from text alone "
        "and must come from the authoring metadata"
    )
    if problems:
        return GateResult(
            "G9", rule, False, "; ".join(problems) + f". Measured: {detail}"
        )
    return GateResult("G9", rule, True, detail)


CHECKS = (_g1, _g2, _g3, _g4, _g5, _g6, _g7, _g8, _g9)


def check(rows: Sequence[Mapping[str, str]]) -> list[GateResult]:
    return [check_fn(list(rows)) for check_fn in CHECKS]


def largest_passing_corpus(*, distinct_seeds: int) -> dict[str, object]:
    """How large a corpus this many seeds can support, and which gate binds first."""
    rows_under_g1 = distinct_seeds * MAX_ROWS_PER_SEED
    passes_g2 = distinct_seeds >= MIN_SEEDS_PER_LANGUAGE
    if not passes_g2:
        return {
            "distinct_seeds": distinct_seeds,
            "rows_under_g1": rows_under_g1,
            "passes_g2": False,
            "largest_passing_rows": 0,
            "binding_gate": (
                f"G2: {distinct_seeds:,} distinct seeds against a floor of {MIN_SEEDS_PER_LANGUAGE:,} per "
                "language. No corpus of any size passes, because the floor is on seeds, not rows"
            ),
        }
    return {
        "distinct_seeds": distinct_seeds,
        "rows_under_g1": rows_under_g1,
        "passes_g2": True,
        "largest_passing_rows": rows_under_g1,
        "binding_gate": f"G1: {MAX_ROWS_PER_SEED} rows per seed x {distinct_seeds:,} seeds",
    }


def report(
    corpus: Path,
    *,
    distinct_seeds: int | None = None,
    limit: int | None = None,
    seed_column: str | None = None,
) -> str:
    """`seed_column` names the column that attributes a row to its seed, when it is not
    called `seed_id` (the split files call it `phrase`)."""
    with Path(corpus).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = (
            [row for _, row in zip(range(limit), reader, strict=False)]
            if limit
            else list(reader)
        )
    if seed_column:
        for row in rows:
            row["seed_id"] = row.get(seed_column, "")
    results = check(rows)
    lines = [
        f"CORPUS_REBUILD §3 gates on {corpus}",
        f"{len(rows):,} rows. No gate was waived, and NOT COMPUTABLE is never a pass.",
        "",
        f"{'Gate':<5} {'Verdict':<15} Detail",
    ]
    for result in results:
        lines.append(f"{result.gate:<5} {result.verdict:<15} {result.detail}")
    failed = [r.gate for r in results if r.passed is False]
    unknown = [r.gate for r in results if r.passed is None]
    lines += [
        "",
        f"{len(failed)} gate(s) FAIL: {', '.join(failed) or 'none'}",
        f"{len(unknown)} gate(s) NOT COMPUTABLE: {', '.join(unknown) or 'none'}",
    ]
    if distinct_seeds is not None:
        ceiling = largest_passing_corpus(distinct_seeds=distinct_seeds)
        lines += [
            "",
            f"Seed inventory: {ceiling['distinct_seeds']:,} distinct seed phrases.",
            f"Largest corpus that passes every size-dependent gate: {ceiling['largest_passing_rows']:,} rows.",
            f"Binding gate: {ceiling['binding_gate']}",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument(
        "--seeds", type=int, default=None, help="size of the seed inventory"
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--seed-column", default=None, help="column attributing a row to its seed"
    )
    args = parser.parse_args(argv)
    text = report(
        args.corpus,
        distinct_seeds=args.seeds,
        limit=args.limit,
        seed_column=args.seed_column,
    )
    print(text)
    return 0 if "FAIL" not in text.split("Gate")[-1] else 1


if __name__ == "__main__":
    raise SystemExit(main())
