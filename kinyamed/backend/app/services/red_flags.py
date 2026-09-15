"""The red-flag rules layer (CLAUDE.md L2): deterministic, escalate-only, run before the model.

Terms load from `data/lexicon/red_flags.csv`, whose columns are the §10.6 clinical
lexicon. The table SHIPS EMPTY: until a clinical lead supplies validated terms
(STATE.md H10) the layer matches nothing, and triage behaves exactly as it did
without it. Adding validated terms is a CSV edit.

Rules:
  * Loading is all-or-nothing. A row missing `source` or `validated_by`, or otherwise
    malformed, rejects the whole file with every problem and its line number, and
    the service refuses to start.
  * Only `red_flag=true` rows match. A match forces CRITICAL, whatever the model
    said. Nothing here can lower urgency, and PostgreSQL enforces the same
    (`ck_triage_results_rules_escalate_only`).
  * Matching is whole-word, case-, accent- and whitespace-insensitive. Inflected or
    colloquial forms are the lexicon's job (`rw_colloquial_variants`), not a stemmer's.
  * The stored reason names concept_ids only, never patient text (L11).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.models.triage_result import UrgencyLevel
from app.services.text_fold import fold

COLUMNS: tuple[str, ...] = (
    "concept_id",
    "icd11_or_snomed",
    "en",
    "fr",
    "sw",
    "rw",
    "rw_colloquial_variants",
    "sw_variant",
    "register",
    "red_flag",
    "source",
    "validated_by",
    "date",
)
TERM_COLUMNS = ("en", "fr", "sw", "rw")
VARIANT_COLUMN = "rw_colloquial_variants"
VARIANT_SEPARATOR = "|"
REQUIRED_PROVENANCE = ("source", "validated_by")
CONCEPT_ID = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")
REASON_PREFIX = "red_flag:"
REASON_MAX_LENGTH = 200  # triage_results.rules_layer_reason is VARCHAR(200)


class RedFlagLexiconError(ValueError):
    """The lexicon cannot be used as written. Nothing is loaded."""


@dataclass(frozen=True)
class RedFlagMatch:
    concept_ids: tuple[str, ...]

    @property
    def triggered(self) -> bool:
        return bool(self.concept_ids)


@dataclass(frozen=True)
class RuleDecision:
    """The urgency to store, and what the rules layer did to get there."""

    urgency: UrgencyLevel
    model_urgency: UrgencyLevel
    triggered: bool
    reason: str | None


@dataclass(frozen=True)
class RedFlagLexicon:
    patterns: tuple[tuple[str, re.Pattern[str]], ...]

    @property
    def is_empty(self) -> bool:
        return not self.patterns

    def match(self, text: str) -> RedFlagMatch:
        folded = fold(text)
        return RedFlagMatch(
            tuple(
                sorted(
                    {
                        concept
                        for concept, pattern in self.patterns
                        if pattern.search(folded)
                    }
                )
            )
        )


def _pattern(terms: list[str]) -> re.Pattern[str]:
    alternation = "|".join(
        r"\s+".join(re.escape(word) for word in fold(term).split()) for term in terms
    )
    return re.compile(rf"(?<!\w)(?:{alternation})(?!\w)", re.IGNORECASE)


def load_lexicon(path: Path) -> RedFlagLexicon:
    """Parse and validate the whole file, or raise with every problem found."""
    if not path.is_file():
        raise RedFlagLexiconError(f"red-flag lexicon not found at {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        if header != COLUMNS:
            raise RedFlagLexiconError(
                f"{path}: header {list(header)} is not the §10.6 lexicon header {list(COLUMNS)}"
            )
        rows = list(reader)

    problems: list[str] = []
    seen: set[str] = set()
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for line, row in enumerate(rows, start=2):
        concept = (row.get("concept_id") or "").strip()
        where = f"line {line} ({concept or 'no concept_id'})"
        if not CONCEPT_ID.match(concept):
            problems.append(f"{where}: concept_id must match {CONCEPT_ID.pattern}")
        elif concept in seen:
            problems.append(f"{where}: duplicate concept_id")
        seen.add(concept)
        missing = [c for c in REQUIRED_PROVENANCE if not (row.get(c) or "").strip()]
        if missing:
            problems.append(f"{where}: missing {' and '.join(missing)}")
        flag = (row.get("red_flag") or "").strip().lower()
        if flag not in ("true", "false"):
            problems.append(f"{where}: red_flag must be true or false")
        try:
            date.fromisoformat((row.get("date") or "").strip())
        except ValueError:
            problems.append(f"{where}: date must be YYYY-MM-DD")
        terms = [(row.get(c) or "").strip() for c in TERM_COLUMNS]
        terms += [
            v.strip() for v in (row.get(VARIANT_COLUMN) or "").split(VARIANT_SEPARATOR)
        ]
        terms = [t for t in terms if t]
        if not terms:
            problems.append(f"{where}: no term in any language column")
        if flag == "true" and terms:
            patterns.append((concept, _pattern(terms)))
    if problems:
        raise RedFlagLexiconError(
            f"{path}: red-flag lexicon refused, nothing loaded:\n  "
            + "\n  ".join(problems)
        )
    return RedFlagLexicon(tuple(patterns))


def format_reason(concept_ids: tuple[str, ...]) -> str | None:
    """`red_flag:ID1,ID2`, cut to the column width with a count of what was left out."""
    if not concept_ids:
        return None
    full = REASON_PREFIX + ",".join(concept_ids)
    if len(full) <= REASON_MAX_LENGTH:
        return full
    kept: list[str] = []
    for k, concept in enumerate(concept_ids):
        rest = len(concept_ids) - k - 1
        candidate = REASON_PREFIX + ",".join([*kept, concept]) + f",+{rest} more"
        if len(candidate) > REASON_MAX_LENGTH:
            break
        kept.append(concept)
    return REASON_PREFIX + ",".join(kept) + f",+{len(concept_ids) - len(kept)} more"


def apply(model_urgency: UrgencyLevel, match: RedFlagMatch) -> RuleDecision:
    """Escalate to CRITICAL on a match; otherwise keep the model's urgency. Never lower."""
    if match.triggered:
        return RuleDecision(
            UrgencyLevel.CRITICAL, model_urgency, True, format_reason(match.concept_ids)
        )
    return RuleDecision(model_urgency, model_urgency, False, None)


@lru_cache(maxsize=1)
def get_lexicon() -> RedFlagLexicon:
    """The configured lexicon, loaded once. Raises if it is invalid, so start-up fails."""
    from app.core.config import settings

    return load_lexicon(Path(settings.RED_FLAG_LEXICON_PATH))
