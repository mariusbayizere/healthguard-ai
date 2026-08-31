#!/usr/bin/env python
"""Validate a generated symptom-triage dataset.

Reports the things that decide whether a benchmark built on this data is
trustworthy: balance, duplication, malformed records and text-encoding
integrity. Nothing here is sampled unless it says so.

Usage:
    python dataset/validate_dataset.py --input dataset/raw/symptoms_large.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.vocabulary import DOMAINS, LANGUAGES, SYMPTOMS  # noqa: E402

URGENCIES = ("CRITICAL", "URGENT", "ROUTINE")
VALID_LANGUAGES = frozenset({*LANGUAGES, "mixed"})

MIN_LENGTH = 20
MAX_LENGTH = 512
MIN_AVG_LENGTH = 30
MAX_DUPLICATE_RATE = 0.02
MIN_EXAMPLES_PER_DOMAIN = 500

CLASS_TARGETS = {"CRITICAL": (0.28, 0.38), "URGENT": (0.32, 0.42), "ROUTINE": (0.28, 0.38)}
LANGUAGE_TARGETS = {language: (0.08, 0.15) for language in LANGUAGES}

# Byte sequences that appear when UTF-8 has been decoded as Latin-1 somewhere
# in the pipeline. Kinyarwanda and French text is where this would surface.
MOJIBAKE_MARKERS = ("Ã", "â€", "Â", "ï»¿", "�")
_PUNCTUATION = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WHITESPACE = re.compile(r"\s+")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def fold(text: str) -> str:
    """Accent-insensitive, case-insensitive, punctuation-free normal form."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _WHITESPACE.sub(" ", _PUNCTUATION.sub("", stripped.casefold())).strip()


def all_symptom_phrases() -> dict[str, list[str]]:
    """Every seed phrase, indexed by language, longest first.

    Longest-first matters: some phrases contain others ("umuriro" inside
    "umuriro mwinshi"). Matching in set order would attribute a row to whichever
    phrase happened to come out of the set first, so phrase attribution — and
    therefore the leakage analysis built on it — would not be reproducible.
    """
    phrases: dict[str, set[str]] = defaultdict(set)
    for language, urgencies in SYMPTOMS.items():
        for domains in urgencies.values():
            for values in domains.values():
                phrases[language].update(values)
    return {
        language: sorted(values, key=lambda phrase: (-len(phrase), phrase))
        for language, values in phrases.items()
    }


def overlapping_phrases() -> list[tuple[str, str]]:
    """Seed phrases that contain another seed phrase of the same language."""
    overlaps: list[tuple[str, str]] = []
    for values in all_symptom_phrases().values():
        for outer in values:
            for inner in values:
                if inner != outer and inner in outer:
                    overlaps.append((inner, outer))
    return overlaps


@dataclass
class Findings:
    """Every problem found, with a bounded sample of offending rows."""

    counts: Counter = field(default_factory=Counter)
    samples: dict[str, list] = field(default_factory=lambda: defaultdict(list))

    def record(self, kind: str, line: int, text: str) -> None:
        self.counts[kind] += 1
        if len(self.samples[kind]) < 5:
            self.samples[kind].append({"line": line, "text": text[:120]})


def check_encoding(path: Path) -> dict:
    """Verify the file is well-formed UTF-8 and free of mojibake."""
    raw = path.read_bytes()
    report: dict = {"bytes": len(raw), "has_bom": raw.startswith(b"\xef\xbb\xbf")}
    try:
        raw.decode("utf-8", errors="strict")
        report["strict_utf8"] = True
    except UnicodeDecodeError as exc:
        report["strict_utf8"] = False
        report["decode_error"] = str(exc)
    return report


def validate(path: Path) -> dict:
    """Run every check over the dataset and return a structured report."""
    encoding = check_encoding(path)
    findings = Findings()

    labels: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    domains: Counter[str] = Counter()
    families: Counter[str] = Counter()
    family_labels: dict[str, str] = {}
    family_languages: dict[str, str] = {}
    phrase_counts: Counter[str] = Counter()
    phrase_families: dict[str, set[str]] = defaultdict(set)

    exact_seen: set[int] = set()
    folded_seen: set[int] = set()
    exact_duplicates = 0
    folded_duplicates = 0

    total = 0
    total_length = 0
    lengths: list[int] = []
    apostrophe_straight = 0
    apostrophe_curly = 0
    non_nfc = 0
    phrase_index = all_symptom_phrases()

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"text", "language", "label", "domain", "family"}
        if set(reader.fieldnames or []) != expected:
            raise SystemExit(f"Unexpected columns: {reader.fieldnames}")

        for line, row in enumerate(reader, start=2):
            text = row["text"]
            language, label = row["language"], row["label"]
            domain, family = row["domain"], row["family"]
            total += 1

            # ── Field validity ────────────────────────────────────────────
            if label not in URGENCIES:
                findings.record("invalid_label", line, text)
            if language not in VALID_LANGUAGES:
                findings.record("invalid_language", line, text)
            if domain not in DOMAINS:
                findings.record("invalid_domain", line, text)
            if not family or family.count(":") != 2:
                findings.record("invalid_family", line, text)

            # ── Malformed / truncated ─────────────────────────────────────
            stripped = text.strip()
            length = len(stripped)
            if not stripped:
                findings.record("empty", line, text)
            if length < MIN_LENGTH:
                findings.record("too_short", line, text)
            if length > MAX_LENGTH:
                findings.record("too_long", line, text)
            if text != stripped:
                findings.record("untrimmed_whitespace", line, text)
            if "  " in text:
                findings.record("double_space", line, text)
            if stripped and stripped[0].isdigit():
                findings.record("starts_with_digit", line, text)
            if ":" in stripped[:20]:
                findings.record("label_leaked_in_prefix", line, text)
            if text.count("?") > 2:
                findings.record("excess_question_marks", line, text)
            if stripped.endswith(("-", "'", ",", "’")):
                findings.record("truncated_ending", line, text)
            if _CONTROL.search(text):
                findings.record("control_characters", line, text)
            if any(marker in text for marker in MOJIBAKE_MARKERS):
                findings.record("mojibake", line, text)
            if text.count('"') % 2:
                findings.record("unbalanced_quotes", line, text)

            # ── Kinyarwanda / Unicode integrity ───────────────────────────
            apostrophe_straight += text.count("'")
            apostrophe_curly += text.count("’")
            if unicodedata.normalize("NFC", text) != text:
                non_nfc += 1
                findings.record("not_nfc_normalised", line, text)

            # ── Duplication ───────────────────────────────────────────────
            exact = hash(text)
            if exact in exact_seen:
                exact_duplicates += 1
                findings.record("exact_duplicate", line, text)
            else:
                exact_seen.add(exact)

            folded_hash = hash(fold(text))
            if folded_hash in folded_seen:
                folded_duplicates += 1
            else:
                folded_seen.add(folded_hash)

            # ── Content core: which seed phrase this row carries ──────────
            frame_language = family.split("->", 1)[0] if "->" in family else language
            phrase_language = (
                family.split("->", 1)[1].split(":", 1)[0] if "->" in family else language
            )
            matched = None
            for phrase in phrase_index.get(phrase_language, ()):
                if phrase in text:
                    matched = phrase
                    break
            if matched is None:
                findings.record("no_seed_phrase_found", line, text)
            else:
                phrase_counts[matched] += 1
                phrase_families[matched].add(family)

            labels[label] += 1
            languages[language] += 1
            domains[domain] += 1
            families[family] += 1
            family_labels[family] = label
            family_languages[family] = language
            total_length += length
            if len(lengths) < 200_000:
                lengths.append(length)

    lengths.sort()

    def percentile(fraction: float) -> int:
        if not lengths:
            return 0
        return lengths[min(int(len(lengths) * fraction), len(lengths) - 1)]

    # Phrases appearing in more than one family are the only way a
    # family-level split could still leak identical clinical content.
    cross_family_phrases = {
        phrase: sorted(owners)
        for phrase, owners in phrase_families.items()
        if len(owners) > 1
    }

    return {
        "input": str(path),
        "encoding": encoding,
        "total": total,
        "families": dict(families),
        "family_count": len(families),
        "family_labels": family_labels,
        "family_languages": family_languages,
        "labels": dict(labels),
        "languages": dict(languages),
        "domains": dict(domains),
        "avg_length": round(total_length / max(total, 1), 1),
        "length_p05": percentile(0.05),
        "length_p50": percentile(0.50),
        "length_p95": percentile(0.95),
        "min_length": lengths[0] if lengths else 0,
        "max_length": lengths[-1] if lengths else 0,
        "exact_duplicates": exact_duplicates,
        "exact_duplicate_rate": round(exact_duplicates / max(total, 1), 6),
        "normalised_duplicates": folded_duplicates,
        "normalised_duplicate_rate": round(folded_duplicates / max(total, 1), 6),
        "distinct_seed_phrases": len(phrase_counts),
        "cross_family_phrases": cross_family_phrases,
        "overlapping_phrases": overlapping_phrases(),
        "apostrophes_straight": apostrophe_straight,
        "apostrophes_curly": apostrophe_curly,
        "non_nfc_rows": non_nfc,
        "problem_counts": dict(findings.counts),
        "problem_samples": {k: v for k, v in findings.samples.items()},
    }


def check_targets(report: dict) -> list[str]:
    """Return every quality target the dataset misses."""
    problems: list[str] = []
    total = report["total"]

    for label, (low, high) in CLASS_TARGETS.items():
        share = report["labels"].get(label, 0) / total
        if not low <= share <= high:
            problems.append(f"class {label} at {share:.1%}, target {low:.0%}-{high:.0%}")
    for language, (low, high) in LANGUAGE_TARGETS.items():
        share = report["languages"].get(language, 0) / total
        if not low <= share <= high:
            problems.append(f"language {language} at {share:.1%}, target {low:.0%}-{high:.0%}")
    for domain in DOMAINS:
        count = report["domains"].get(domain, 0)
        if count < MIN_EXAMPLES_PER_DOMAIN:
            problems.append(f"domain {domain} has {count}, minimum {MIN_EXAMPLES_PER_DOMAIN}")
    if report["exact_duplicate_rate"] > MAX_DUPLICATE_RATE:
        problems.append(f"exact duplicate rate {report['exact_duplicate_rate']:.2%} exceeds 2%")
    if report["normalised_duplicate_rate"] > MAX_DUPLICATE_RATE:
        problems.append(
            f"normalised duplicate rate {report['normalised_duplicate_rate']:.2%} exceeds 2%"
        )
    if report["avg_length"] < MIN_AVG_LENGTH:
        problems.append(f"average length {report['avg_length']} below {MIN_AVG_LENGTH}")
    if not report["encoding"]["strict_utf8"]:
        problems.append("file is not valid UTF-8")
    if report["encoding"]["has_bom"]:
        problems.append("file starts with a UTF-8 BOM")
    for kind in ("mojibake", "control_characters", "empty", "invalid_label", "invalid_language"):
        if report["problem_counts"].get(kind):
            problems.append(f"{report['problem_counts'][kind]} rows with {kind}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("dataset/raw/symptoms_large.csv"))
    parser.add_argument("--report", type=Path, default=None, help="Where to write the JSON report.")
    parser.add_argument("--top-families", type=int, default=10)
    args = parser.parse_args()

    report = validate(args.input)
    problems = check_targets(report)
    report["quality_problems"] = problems

    total = report["total"]
    print(f"Dataset            : {report['input']}")
    print(f"Total examples     : {total:,}")
    print(f"Template families  : {report['family_count']}")
    print(f"Distinct phrases   : {report['distinct_seed_phrases']} "
          f"({len(report['overlapping_phrases'])} contained inside another phrase)")
    print(
        f"Length             : min {report['min_length']} / p05 {report['length_p05']} / "
        f"p50 {report['length_p50']} / p95 {report['length_p95']} / max {report['max_length']} "
        f"(avg {report['avg_length']})"
    )

    print("\nClass balance:")
    for label, count in sorted(report["labels"].items()):
        print(f"  {label:<9} {count:>9,}  {count / total:6.2%}")
    print("\nLanguage balance:")
    for language, count in sorted(report["languages"].items()):
        print(f"  {language:<12} {count:>9,}  {count / total:6.2%}")
    print("\nDomain coverage:")
    for domain, count in sorted(report["domains"].items()):
        print(f"  {domain:<22} {count:>9,}  {count / total:6.2%}")

    print("\nDuplication:")
    print(f"  exact            {report['exact_duplicates']:>9,}  {report['exact_duplicate_rate']:.4%}")
    print(
        f"  normalised       {report['normalised_duplicates']:>9,}  "
        f"{report['normalised_duplicate_rate']:.4%}   (casefold + accent-fold + punctuation strip)"
    )
    print(f"  phrases in >1 family: {len(report['cross_family_phrases'])}")

    print("\nEncoding:")
    enc = report["encoding"]
    print(f"  strict UTF-8     {enc['strict_utf8']}")
    print(f"  BOM              {enc['has_bom']}")
    print(f"  NFC-normalised   {total - report['non_nfc_rows']:,}/{total:,}")
    print(
        f"  apostrophes      {report['apostrophes_straight']:,} straight (U+0027), "
        f"{report['apostrophes_curly']:,} curly (U+2019)"
    )

    print("\nMalformed / truncated:")
    if report["problem_counts"]:
        for kind, count in sorted(report["problem_counts"].items(), key=lambda kv: -kv[1]):
            print(f"  {kind:<26} {count:>9,}")
            for sample in report["problem_samples"][kind][:2]:
                print(f"      line {sample['line']}: {sample['text']}")
    else:
        print("  none")

    print(f"\nFamily sizes (largest {args.top_families}):")
    for family, count in sorted(report["families"].items(), key=lambda kv: -kv[1])[: args.top_families]:
        print(f"  {family:<48} {count:>8,}")
    smallest = sorted(report["families"].items(), key=lambda kv: kv[1])[:3]
    print("Family sizes (smallest 3):")
    for family, count in smallest:
        print(f"  {family:<48} {count:>8,}")

    destination = args.report or args.input.with_suffix(".validation.json")
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport written to {destination}")

    if problems:
        print("\nQUALITY TARGETS MISSED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nAll quality targets met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
