#!/usr/bin/env python
"""Generate a large multilingual symptom-triage dataset.

Examples are composed from grammatical slots (opener, subject, symptom phrase,
onset, context, closer) drawn from `vocabulary.py`. Every example is produced
from a *distinct* combination index within its template family, so uniqueness
is a property of the construction rather than something rejected afterwards by
a deduplication pass over a million strings.

Class and language balance are allocated up front from the quality targets, not
measured and hoped for. Every row is validated before it is written.

Usage:
    python dataset/generate_large_dataset.py --target 1000000
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from itertools import cycle
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.vocabulary import (  # noqa: E402
    CLOSERS,
    CONTEXTS,
    DOMAINS,
    LANGUAGES,
    MIXED_PAIRS,
    ONSETS,
    OPENERS,
    SUBJECTS,
    SYMPTOMS,
)

URGENCIES = ("CRITICAL", "URGENT", "ROUTINE")
VALID_LANGUAGES = frozenset({*LANGUAGES, "mixed"})

# ── Quality targets (see SENIOR_ENGINEERING_PROMPT.md, Section 5) ─────────
MIN_LENGTH = 20
MAX_LENGTH = 512
MIN_AVG_LENGTH = 30
MAX_DUPLICATE_RATE = 0.02
MIN_EXAMPLES_PER_DOMAIN = 500
# The domain floor above is expressed for a full-size run; below that size it
# is scaled proportionally. An absolute floor would fail every small run for
# the wrong reason — a 1,000-row sample cannot hold 500 rows of nine domains —
# which would make a sample-based CI check permanently red and worthless.
QUALITY_REFERENCE_ROWS = 1_000_000

CLASS_TARGETS = {"CRITICAL": (0.28, 0.38), "URGENT": (0.32, 0.42), "ROUTINE": (0.28, 0.38)}
LANGUAGE_TARGETS = {language: (0.08, 0.15) for language in LANGUAGES}

# Allocation shares. Four pure languages at 13% each leaves 48% code-switched,
# which matches how patients actually write in Rwandan clinics.
PURE_LANGUAGE_SHARE = 0.13
CLASS_SHARES = {"CRITICAL": 0.33, "URGENT": 0.34, "ROUTINE": 0.33}


def validate_example(text: str, language: str, label: str) -> bool:
    """Whether one generated example is fit to train on."""
    stripped = text.strip()
    return all(
        (
            len(stripped) >= MIN_LENGTH,
            len(stripped) <= MAX_LENGTH,
            label in URGENCIES,
            language in VALID_LANGUAGES,
            not stripped[0].isdigit(),
            ":" not in stripped[:20],
            text.count("?") <= 2,
        )
    )


@dataclass(frozen=True)
class Family:
    """One template family: a fixed (language, urgency, domain) slot product."""

    language: str          # label written to the dataset
    urgency: str
    domain: str
    frame_language: str    # supplies opener/subject/onset/context/closer
    phrase_language: str   # supplies the clinical phrase
    slots: tuple[tuple[str, ...], ...] = field(repr=False)

    @property
    def family_id(self) -> str:
        """Stable identifier for this template family.

        Written to every row so that an evaluation split can hold out whole
        families: examples from one family share a slot product and are
        therefore near-duplicates of each other by construction.
        """
        return f"{self.frame_language}->{self.phrase_language}:{self.urgency}:{self.domain}"

    @property
    def combinations(self) -> int:
        total = 1
        for slot in self.slots:
            total *= len(slot)
        return total

    def render(self, index: int) -> str:
        """Decode a combination index into a sentence (mixed-radix decode)."""
        parts: list[str] = []
        for slot in reversed(self.slots):
            index, position = divmod(index, len(slot))
            parts.append(slot[position])
        opener, subject, phrase, onset, context, closer = reversed(parts)
        # After a greeting the sentence continues, so the subject is not a
        # sentence start: "Muganga, umwana wanjye afite..." not "Muganga, Umwana".
        if opener:
            subject = subject[0].lower() + subject[1:]
        return f"{opener}{subject} {phrase}{onset}{context}{closer}".strip()


def assert_slots_are_distinct() -> None:
    """Every slot value must be unique within its list.

    Generation maps distinct combination indices to sentences. A value repeated
    inside one slot breaks that injection, so two indices render identical text
    and the duplicate rate climbs silently. Fail loudly instead.
    """
    for name, table in (
        ("OPENERS", OPENERS), ("SUBJECTS", SUBJECTS), ("ONSETS", ONSETS),
        ("CONTEXTS", CONTEXTS), ("CLOSERS", CLOSERS),
    ):
        for language, values in table.items():
            if len(set(values)) != len(values):
                repeated = [v for v in set(values) if values.count(v) > 1]
                raise ValueError(
                    f"{name}[{language!r}] contains repeated values {repeated!r}; "
                    "slot values must be distinct."
                )
    for language, urgencies in SYMPTOMS.items():
        for urgency, domains in urgencies.items():
            for domain, phrases in domains.items():
                if len(set(phrases)) != len(phrases):
                    raise ValueError(
                        f"SYMPTOMS[{language!r}][{urgency!r}][{domain!r}] has duplicates."
                    )


def build_families() -> list[Family]:
    """Every template family, pure and code-switched."""
    assert_slots_are_distinct()
    families: list[Family] = []

    def add(label_language: str, frame: str, phrase_lang: str, urgency: str, domain: str,
            phrases: tuple[str, ...]) -> None:
        families.append(
            Family(
                language=label_language,
                urgency=urgency,
                domain=domain,
                frame_language=frame,
                phrase_language=phrase_lang,
                slots=(
                    OPENERS[frame],
                    SUBJECTS[frame],
                    phrases,
                    ONSETS[frame],
                    CONTEXTS[frame],
                    CLOSERS[frame],
                ),
            )
        )

    for language in LANGUAGES:
        for urgency, domains in SYMPTOMS[language].items():
            for domain, phrases in domains.items():
                add(language, language, language, urgency, domain, phrases)

    for frame, phrase_lang in MIXED_PAIRS:
        for urgency, domains in SYMPTOMS[phrase_lang].items():
            for domain, phrases in domains.items():
                add("mixed", frame, phrase_lang, urgency, domain, phrases)

    return families


def allocate(families: list[Family], target: int) -> dict[Family, int]:
    """Decide how many examples each family contributes.

    Allocation is by language share, then class share, then split across the
    domains available in that bucket in proportion to how much distinct
    material each has — capped by the combinations a family can actually
    produce without repeating itself.
    """
    quotas: dict[Family, int] = {}
    buckets: dict[tuple[str, str], list[Family]] = {}
    for family in families:
        buckets.setdefault((family.language, family.urgency), []).append(family)

    language_shares = {language: PURE_LANGUAGE_SHARE for language in LANGUAGES}
    language_shares["mixed"] = 1.0 - PURE_LANGUAGE_SHARE * len(LANGUAGES)

    for (language, urgency), members in buckets.items():
        bucket_target = int(target * language_shares[language] * CLASS_SHARES[urgency])
        capacity = sum(member.combinations for member in members)
        if capacity == 0:
            continue
        for member in members:
            share = member.combinations / capacity
            quotas[member] = min(int(bucket_target * share), member.combinations)

    # Distribute the rounding remainder over families that still have headroom.
    shortfall = target - sum(quotas.values())
    headroom = [f for f in quotas if quotas[f] < f.combinations]
    for family in cycle(headroom or list(quotas)):
        if shortfall <= 0:
            break
        if quotas[family] < family.combinations:
            quotas[family] += 1
            shortfall -= 1
    return quotas


def generate(target: int, output: Path, seed: int, report_every: int) -> dict:
    """Generate the dataset, streaming it to `output`, and return its statistics."""
    rng = random.Random(seed)
    families = build_families()
    quotas = allocate(families, target)
    capacity = sum(family.combinations for family in families)

    print(f"Template families      : {len(families)}")
    print(f"Distinct combinations  : {capacity:,}")
    print(f"Target examples        : {target:,}")
    if capacity < target:
        raise SystemExit(
            f"Vocabulary supports {capacity:,} unique examples but {target:,} were "
            "requested. Add symptom phrases to vocabulary.py."
        )
    print(f"Output                 : {output}\n")

    output.parent.mkdir(parents=True, exist_ok=True)
    labels: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    domains: Counter[str] = Counter()
    families: Counter[str] = Counter()
    seen: set[int] = set()
    duplicates = 0
    rejected = 0
    total_length = 0
    written = 0
    started = time.monotonic()

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["text", "language", "label", "domain", "family"])

        for family, quota in quotas.items():
            if quota <= 0:
                continue
            # Distinct indices -> distinct sentences, with no dedup pass needed.
            for index in rng.sample(range(family.combinations), quota):
                text = family.render(index)
                if not validate_example(text, family.language, family.urgency):
                    rejected += 1
                    continue

                fingerprint = hash(text)
                if fingerprint in seen:
                    duplicates += 1
                    continue
                seen.add(fingerprint)

                writer.writerow(
                    [text, family.language, family.urgency, family.domain, family.family_id]
                )
                labels[family.urgency] += 1
                languages[family.language] += 1
                domains[family.domain] += 1
                families[family.family_id] += 1
                total_length += len(text)
                written += 1

                if written % report_every == 0:
                    elapsed = time.monotonic() - started
                    rate = written / elapsed if elapsed else 0
                    print(
                        f"[{written:>9,}/{target:,}] "
                        f"{elapsed:6.1f}s {rate:8,.0f}/s | "
                        + " ".join(f"{k}={v / written:.1%}" for k, v in sorted(labels.items()))
                        + " | "
                        + " ".join(f"{k}={v / written:.1%}" for k, v in sorted(languages.items())),
                        flush=True,
                    )

    elapsed = time.monotonic() - started
    return {
        "total": written,
        "elapsed_seconds": round(elapsed, 1),
        "rejected": rejected,
        "duplicates": duplicates,
        "duplicate_rate": round(duplicates / max(written + duplicates, 1), 5),
        "avg_length": round(total_length / max(written, 1), 1),
        "labels": dict(labels),
        "languages": dict(languages),
        "domains": dict(domains),
        "families": dict(families),
        "output": str(output),
    }


def check_quality(stats: dict) -> list[str]:
    """Return every quality target the generated dataset misses."""
    problems: list[str] = []
    total = stats["total"]

    for label, (low, high) in CLASS_TARGETS.items():
        share = stats["labels"].get(label, 0) / total
        if not low <= share <= high:
            problems.append(f"class {label} at {share:.1%}, target {low:.0%}-{high:.0%}")

    for language, (low, high) in LANGUAGE_TARGETS.items():
        share = stats["languages"].get(language, 0) / total
        if not low <= share <= high:
            problems.append(f"language {language} at {share:.1%}, target {low:.0%}-{high:.0%}")

    floor = max(1, round(MIN_EXAMPLES_PER_DOMAIN * total / QUALITY_REFERENCE_ROWS))
    for domain in DOMAINS:
        count = stats["domains"].get(domain, 0)
        if count < floor:
            problems.append(f"domain {domain} has {count}, minimum {floor}")

    if stats["duplicate_rate"] > MAX_DUPLICATE_RATE:
        problems.append(f"duplicate rate {stats['duplicate_rate']:.2%} exceeds 2%")
    if stats["avg_length"] < MIN_AVG_LENGTH:
        problems.append(f"average length {stats['avg_length']} below {MIN_AVG_LENGTH}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=1_000_000, help="Examples to generate.")
    parser.add_argument(
        "--output", type=Path, default=Path("dataset/raw/symptoms_large.csv"),
        help="Destination CSV.",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility.")
    parser.add_argument("--report-every", type=int, default=10_000, help="Progress interval.")
    args = parser.parse_args()

    stats = generate(args.target, args.output, args.seed, args.report_every)

    print("\n" + "=" * 68)
    print(f"Generated {stats['total']:,} examples in {stats['elapsed_seconds']}s")
    print(f"Average length : {stats['avg_length']} chars")
    print(f"Duplicates     : {stats['duplicates']} ({stats['duplicate_rate']:.3%})")
    print(f"Rejected       : {stats['rejected']}")
    print("\nClass balance:")
    for label, count in sorted(stats["labels"].items()):
        print(f"  {label:<9} {count:>9,}  {count / stats['total']:6.2%}")
    print("\nLanguage balance:")
    for language, count in sorted(stats["languages"].items()):
        print(f"  {language:<12} {count:>9,}  {count / stats['total']:6.2%}")
    print("\nDomain coverage:")
    for domain, count in sorted(stats["domains"].items()):
        print(f"  {domain:<22} {count:>9,}")

    problems = check_quality(stats)
    report = args.output.with_suffix(".stats.json")
    report.write_text(json.dumps({**stats, "quality_problems": problems}, indent=2))
    print(f"\nStatistics written to {report}")

    if problems:
        print("\nQUALITY TARGETS MISSED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nAll quality targets met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
