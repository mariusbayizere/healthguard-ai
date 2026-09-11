#!/usr/bin/env python
"""B4 — code-switched row generation, matrix-language framed.

ADDITIVE AND INERT. Nothing in the existing pipeline imports this module, so v1
and v2 keep reproducing byte-for-byte (`make verify-full`, charter rule 7). It
generates nothing until a speaker has ruled the worksheet.

WHY THIS DOES NOT DO WHAT v1 DID
--------------------------------
v1 produced mixed rows by swapping a whole phrase at one syntactic seam: frame
in one language, entire clause in the other, every time. That was 48% of the v1
corpus. `docs/code-switching-design.md` records why it is the wrong model:

    Real Kinyarwanda-English speech is typically MATRIX-LANGUAGE FRAMED.
    Kinyarwanda supplies morphosyntax and word order, and English contributes
    single content morphemes - most often a noun. The generator does the
    opposite: it swaps a whole multi-word clause.

So this module inserts ONE content term into an otherwise intact matrix-language
utterance, and integrates it morphologically, which is what the design document
asks for and what v1 never did.

THE REFUSAL IS THE FEATURE
--------------------------
Three things must come from a speaker and cannot be inferred:

  1. whether a term is SWITCHED or merely BORROWED (a borrowed term appears in
     otherwise monolingual speech and must not be labelled mixed at all);
  2. the NOUN CLASS an inserted noun takes;
  3. the AGREEMENT that class triggers on the surrounding verb or possessive.

The design document calls (2) "the item most likely to expose the design as
wrong, and the one where a speaker's judgement cannot be substituted for".

With an unruled worksheet this module RAISES. It does not fall back to v1's
alternation, does not guess a noun class, and does not emit an unintegrated bare
string. A fallback here would regenerate the exact defect the module exists to
replace, and it would do so silently, under a provenance label claiming the
model had been applied.

PROVENANCE
----------
Every row is `machine_generated` and says so. A code-switched row is not
speaker-authored even when the inserted term came from a speaker's worksheet:
the speaker ruled the TERM, not the SENTENCE it was inserted into.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSHEET = ROOT / "review" / "code_switching_worksheet.csv"

# The six ordered pairs v1 shipped, carried forward unchanged so the gap is
# visible. FLAGGED, NOT ADOPTED: there is no kinyarwanda<->swahili and no
# english<->french, and docs/blocked.md question 4 records that nobody has
# established these six reflect Rwandan usage. Do not add a pair here on
# plausibility; a speaker answers it.
MIXED_PAIRS: tuple[tuple[str, str], ...] = (
    ("kinyarwanda", "english"),
    ("english", "kinyarwanda"),
    ("kinyarwanda", "french"),
    ("french", "kinyarwanda"),
    ("swahili", "english"),
    ("english", "swahili"),
)

SWITCHED = "switched"
BORROWED = "borrowed"

# RULED 2026-09-08 by the maintainer, in their words: "a corpus in the KW-EN row
# of my own document with only five nouns and no verbs isn't the mixed language
# it claims. I'd rather ship five combinations honestly than one badly."
#
# So a pair does not generate merely because SOME terms are ruled. It generates
# when the inventory is rich enough to be what the corpus label says it is.
#
# THE VALUE IS DELIBERATELY UNSET. What counts as enough is a judgement about
# language, not arithmetic, and picking a number here would be the same error as
# picking a noun class. `None` means "not yet decided", and the gate refuses --
# which is the correct state, not a broken one.
MINIMUM_SWITCHABLE_TERMS: int | None = None


@dataclass(frozen=True)
class InsertableTerm:
    """One speaker-ruled term. Every field below was ruled, not inferred."""

    term: str
    matrix_language: str
    source_language: str
    disposition: str  # SWITCHED or BORROWED
    noun_class: str
    agreement_example: str

    @property
    def is_switchable(self) -> bool:
        return self.disposition == SWITCHED


def _normalise(value: str) -> str:
    return (value or "").strip().lower()


def load_worksheet(path: Path = WORKSHEET) -> tuple[list[InsertableTerm], list[str]]:
    """Return (ruled terms, reasons the worksheet is not yet usable).

    A term counts as ruled only when its disposition is one of the two allowed
    values AND, if switched, it carries a noun class and an agreement example.
    A half-filled row is not a ruling: inserting a noun whose class nobody
    recorded is exactly the unintegrated bare string this module exists to
    avoid.
    """
    if not path.exists():
        return [], [f"{path} does not exist"]

    ruled: list[InsertableTerm] = []
    problems: list[str] = []
    unresolved: list[str] = []
    seen = 0
    for row in csv.DictReader(path.open(encoding="utf-8")):
        term = (row.get("term") or "").strip()
        if not term:
            continue
        seen += 1
        disposition = _normalise(row.get("is_it_switched_or_borrowed"))
        if not disposition:
            continue  # simply unruled; reported in aggregate
        if disposition not in (SWITCHED, BORROWED):
            # "switched/borrowed" is the speaker saying BOTH, which is a real
            # linguistic answer and not a malformed one -- but the two send a
            # term to different places (mixed rows vs monolingual rows), so it
            # is UNRESOLVED rather than an error. Unresolved terms are reported
            # and skipped; they do not block terms that are cleanly ruled.
            unresolved.append(
                f"{term!r}: ruled {disposition!r}. Switched and borrowed route "
                "the term differently, so one context must be chosen."
            )
            continue
        noun_class = (row.get("noun_class") or "").strip()
        agreement = (row.get("agreement_example") or "").strip()
        if disposition == SWITCHED and " OR " in noun_class.upper():
            unresolved.append(
                f"{term!r}: two candidate noun classes ({noun_class}). The class "
                "determines the agreement, so it cannot be picked by us."
            )
            continue
        if disposition == SWITCHED and not noun_class:
            problems.append(
                f"{term!r}: ruled {SWITCHED} but no noun class recorded. Inserting "
                "it would produce the unintegrated bare string the design "
                "document identifies as defect 2."
            )
            continue
        if disposition == SWITCHED and not agreement:
            problems.append(
                f"{term!r}: ruled {SWITCHED} with a noun class but no agreement "
                "example. The class alone does not say what it triggers."
            )
            continue
        ruled.append(
            InsertableTerm(
                term,
                (row.get("matrix_language") or "").strip(),
                (row.get("source_language") or "").strip(),
                disposition,
                noun_class,
                agreement,
            )
        )

    if seen and not ruled and not problems and not unresolved:
        problems.append(
            f"none of the {seen} terms in {path.name} has been ruled. The "
            "worksheet is with a speaker; see docs/blocked.md question 4."
        )
    return ruled, problems + [f"UNRESOLVED {u}" for u in unresolved]


def switchable_terms(path: Path = WORKSHEET) -> list[InsertableTerm]:
    """Terms a speaker ruled SWITCHED. Borrowed terms are deliberately excluded.

    A borrowed term belongs in MONOLINGUAL rows -- that is defect 3 in the
    design document, and it affects the 52% of the corpus not labelled mixed.
    Emitting a borrowing as a code-switch would mislabel ordinary speech.
    """
    ruled, _ = load_worksheet(path)
    return [t for t in ruled if t.is_switchable]


def generate(
    matrix: str, embedded: str, phrases: list[str], path: Path = WORKSHEET
) -> list[dict]:
    """Emit code-switched rows, or refuse.

    Refusal is not an error condition to be handled around. It is the correct
    output for an unruled worksheet, and the message says what would unblock it.
    """
    if (matrix, embedded) not in MIXED_PAIRS:
        raise SystemExit(
            f"({matrix}, {embedded}) is not one of the six declared pairs. "
            f"Adding a pair is a speaker's ruling, not a configuration change: "
            f"see docs/blocked.md question 4."
        )

    ruled, problems = load_worksheet(path)
    # THE MATRIX LANGUAGE MUST MATCH TOO. The noun class and agreement in the
    # worksheet are facts about the MATRIX language's morphology -- Kinyarwanda
    # Class 9 (i-) is not Swahili's class system, and no Swahili speaker has
    # ruled anything. Filtering only on the embedded language silently inserted
    # Kinyarwanda-classed terms into a Swahili frame, which is the unintegrated
    # bare insertion this module exists to prevent, wearing a concord that
    # belongs to another language.
    terms = [
        t
        for t in ruled
        if t.is_switchable
        and t.matrix_language == matrix
        and t.source_language in (embedded[:2], embedded)
    ]

    blocking = [p for p in problems if not p.startswith("UNRESOLVED ")]

    if terms and not blocking and MINIMUM_SWITCHABLE_TERMS is None:
        raise SystemExit(
            f"REFUSING: {len(terms)} switchable term(s) ruled for "
            f"{matrix}->{embedded} ({', '.join(t.term for t in terms)}), all "
            "nouns.\n"
            "  Enough to generate rows; NOT enough to be the mixed language the "
            "corpus label claims. Ruled 2026-09-08: ship fewer combinations "
            "honestly rather than one badly.\n"
            "  Set MINIMUM_SWITCHABLE_TERMS once someone has decided what a "
            "credible insertion inventory looks like for this pair."
        )
    if terms and not blocking and len(terms) < MINIMUM_SWITCHABLE_TERMS:
        raise SystemExit(
            f"REFUSING: {len(terms)} switchable terms for {matrix}->{embedded}, "
            f"below the declared minimum of {MINIMUM_SWITCHABLE_TERMS}."
        )
    if blocking or not terms:
        detail = (
            "\n  ".join(blocking)
            if blocking
            else (
                f"no term is ruled {SWITCHED} with {matrix} as its MATRIX language "
                f"and {embedded} as its source. The worksheet records noun class and "
                f"agreement for one matrix language only; {matrix} needs its own, "
                f"ruled by a {matrix} speaker."
            )
        )
        raise SystemExit(
            "REFUSING TO GENERATE CODE-SWITCHED ROWS.\n"
            f"  {detail}\n\n"
            "  This is the designed behaviour, not a bug. The alternative is "
            "v1's whole-phrase alternation, which docs/code-switching-design.md "
            "records as the wrong linguistic model, or an unintegrated bare "
            "insertion, which is its defect 2. Either would be emitted under a "
            "label claiming the matrix-language model had been applied.\n"
            f"  Unblock by having a speaker complete {path.name}: disposition "
            "for every term, plus noun class and agreement for each switched one."
        )

    rows: list[dict] = []
    for phrase in phrases:
        for term in terms:
            rows.append(
                {
                    "matrix_language": matrix,
                    "embedded_language": embedded,
                    "phrase": phrase,
                    "inserted_term": term.term,
                    "noun_class": term.noun_class,
                    "agreement": term.agreement_example,
                    # Not speaker-authored. The speaker ruled the TERM; nobody
                    # approved this sentence.
                    "provenance": "machine_generated",
                }
            )
    return rows


def status(path: Path = WORKSHEET) -> str:
    ruled, problems = load_worksheet(path)
    switched = [t for t in ruled if t.is_switchable]
    borrowed = [t for t in ruled if not t.is_switchable]
    lines = [
        f"worksheet : {path}",
        f"ruled     : {len(ruled)} ({len(switched)} switched, "
        f"{len(borrowed)} borrowed)",
        f"pairs     : {len(MIXED_PAIRS)} declared",
    ]
    if problems:
        lines.append("BLOCKED   :")
        lines.extend(f"  - {p}" for p in problems)
    else:
        lines.append("ready     : yes")
    return "\n".join(lines)


if __name__ == "__main__":
    print(status())
