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
    python dataset/generate_large_dataset.py --target 1008000
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
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
    PHRASE_FORMS,
    REL_PLACEHOLDER,
    RELATIONS,
    DOMAIN_RELATIONS,
    CONCEPT_RELATIONS,
    CONTEXTS_BY_URGENCY,
    CLOSERS_BY_URGENCY,
    ONSETS,
    SENTENCE_END,
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
# v2 target. 504 phrase strings x 2,000 rows per phrase = 1,008,000. Chosen so
# that median rows-per-phrase lands on 2,000: raising the row count without adding
# phrases only makes each phrase repeat more often, which is the opposite of the
# diversity the vocabulary expansion buys. See docs/v2-sizing.md.
#
# v1 is 1,000,000 rows and stays that way; every v1 path passes --target explicitly.
TARGET_ROWS_V2 = 1_008_000

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


# A phrase is either a noun phrase, which takes a subject ("afite <phrase>"), or a
# complete patient utterance, which does not ("ndakorora cyane"). v1 declares
# nothing and every phrase defaults to NOUN_PHRASE, so v1 output is unchanged.
NOUN_PHRASE = "noun_phrase"
UTTERANCE = "utterance"
DEFAULT_FORM = NOUN_PHRASE


@dataclass(frozen=True)
class Family:
    """One template family: a fixed (language, urgency, domain) slot product."""

    language: str          # label written to the dataset
    urgency: str
    domain: str
    frame_language: str    # supplies opener/subject/onset/context/closer
    phrase_language: str   # supplies the clinical phrase
    slots: tuple[tuple[str, ...], ...] = field(repr=False)
    form: str = DEFAULT_FORM

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
        # An opener ending in sentence punctuation starts a new sentence, so what
        # follows keeps its capital; one ending in a comma continues, so it does not.
        continues = bool(opener) and opener.rstrip()[-1:] not in _SENTENCE_END
        if subject:
            if continues:
                subject = subject[0].lower() + subject[1:]
            phrase = _drop_terminal_stop(phrase, f"{onset}{context}")
            return _tidy(f"{opener}{subject} {phrase}{onset}{context}{closer}")
        # Utterance form: the phrase is a complete clause and takes no subject.
        # After a greeting it continues mid-sentence ("Muganga, ndakorora...");
        # with no greeting it starts the sentence and is capitalised, which is
        # what the subject slot did in the noun-phrase form.
        if continues:
            phrase = phrase[0].lower() + phrase[1:]
        else:
            phrase = phrase[0].upper() + phrase[1:]
        phrase = _drop_terminal_stop(phrase, f"{onset}{context}")
        return _tidy(f"{opener}{phrase}{onset}{context}{closer}")


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


_SENTENCE_END = SENTENCE_END


def _tidy(text: str) -> str:
    """Normalise punctuation where slots meet.

    Slot fragments are written as natural speech, so a context or opener may be
    a complete sentence rather than a mid-sentence continuation. Concatenating
    those raw produces "gitunguranye.. Nkora iki?" or a lowercase word after a
    full stop. Rather than constrain how the speaker writes, the join is made
    punctuation-aware: duplicate sentence punctuation collapses, a sentence
    always starts with a capital, and spacing is regular.

    For v1, where every opener ends ", " and every closer is the last element,
    this is a no-op.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _SENTENCE_END:
            # collapse a run of sentence punctuation to the first mark
            out.append(ch)
            while i + 1 < len(text) and text[i + 1] in _SENTENCE_END:
                i += 1
            i += 1
            continue
        out.append(ch)
        i += 1
    text = "".join(out)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.!?,])", r"\1", text)
    text = re.sub(r"([.!?])(?=[^\s])", r"\1 ", text)
    # capitalise the first letter, and any letter opening a new sentence
    text = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text


def _drop_terminal_stop(phrase: str, tail: str) -> str:
    """Remove a phrase's final full stop when the next slot continues the sentence.

    An utterance is authored as a complete sentence, but onsets and contexts are
    mid-sentence continuations: " kuva ejo", " kandi ndahangayitse". Left alone,
    "Ndakorora cyane." followed by " kandi..." becomes two sentences and the
    connective is promoted to a sentence opener - "Kandi birushaho kuba bibi." -
    which reads wrong. Dropping the stop restores the intended single sentence.

    A tail that is itself a new sentence (". Byatangiye...") keeps the stop.
    """
    stripped = tail.lstrip()
    if not stripped or stripped[0] in _SENTENCE_END:
        return phrase
    if phrase.rstrip()[-1:] in _SENTENCE_END:
        return phrase.rstrip()[:-1]
    return phrase


def phrase_form(phrase: str) -> str:
    """The form a phrase takes, from the vocabulary's declaration.

    Phrases that declare nothing are noun phrases, which is what every v1 phrase
    is. The declaration lives in vocabulary.PHRASE_FORMS so that v1's SYMPTOMS
    structure is untouched and v1 output is bit-identical.
    """
    return PHRASE_FORMS.get(phrase, DEFAULT_FORM)


def build_families() -> list[Family]:
    """Every template family, pure and code-switched."""
    assert_slots_are_distinct()
    families: list[Family] = []

    def add(label_language: str, frame: str, phrase_lang: str, urgency: str, domain: str,
            phrases: tuple[str, ...]) -> None:
        # Phrases in one cell may declare different forms. Each form becomes its
        # own family, because they take different slot sets and therefore have
        # different combination counts. With nothing declared this is a single
        # NOUN_PHRASE family and identical to the previous behaviour.
        for form in (NOUN_PHRASE, UTTERANCE):
            in_form = tuple(p for p in phrases if phrase_form(p) == form)
            if not in_form:
                continue
            subjects = SUBJECTS[frame] if form == NOUN_PHRASE else ("",)
            # A {REL} phrase is one phrase for holdout purposes but renders as
            # every relation, so the expansion happens here and the canonical
            # form stays in the phrase inventory.
            expanded: list[str] = []
            for phrase in in_form:
                if REL_PLACEHOLDER in phrase:
                    # A concept-level set wins over its domain's.
                    allowed = CONCEPT_RELATIONS.get(phrase, DOMAIN_RELATIONS.get(domain))
                    pool = RELATIONS.get(phrase_lang, ("",))
                    if allowed is not None:
                        if len(allowed) == 0:
                            # Deliberately empty: this concept has no third-person
                            # form, because nobody presents on another's behalf for
                            # it. The phrase contributes no rows and that is correct.
                            continue
                        pool = tuple(r for r in pool if r in allowed)
                        if not pool:
                            raise SystemExit(
                                f"{domain!r} allows {allowed!r}, none of which is in "
                                f"RELATIONS[{phrase_lang!r}]. That is a misconfiguration; "
                                "an intentionally empty set must be NO_RELATIONS."
                            )
                    # A relation is a proper-noun-shaped phrase and is written
                    # capitalised, but mid-sentence it is not a sentence start:
                    # "Iyo umwana wanjye ahumeka", not "Iyo Umwana wanjye".
                    head = phrase.startswith(REL_PLACEHOLDER)
                    expanded.extend(
                        phrase.replace(REL_PLACEHOLDER,
                                       rel if head else rel[0].lower() + rel[1:])
                        for rel in pool
                    )
                else:
                    expanded.append(phrase)
            in_form = tuple(expanded)
            families.append(
                Family(
                    language=label_language,
                    urgency=urgency,
                    domain=domain,
                    frame_language=frame,
                    phrase_language=phrase_lang,
                    slots=(
                        OPENERS[frame],
                        subjects,
                        in_form,
                        ONSETS[frame],
                        # A class may narrow its contexts/closers where the frame
                        # would contradict the label. Empty maps mean no
                        # narrowing, which is v1's behaviour exactly.
                        CONTEXTS_BY_URGENCY.get(urgency, {}).get(frame, CONTEXTS[frame]),
                        CLOSERS_BY_URGENCY.get(urgency, {}).get(frame, CLOSERS[frame]),
                    ),
                    form=form,
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
    parser.add_argument(
        "--target", type=int, default=TARGET_ROWS_V2,
        help="Examples to generate (default: the v2 target of 1,008,000).",
    )
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
