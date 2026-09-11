"""Emit the D2 clinician review pack from the record.

The pack was hand-typed until 2026-09-11 and said "the 20 `needs_clinician`
rows" while the spine carried 25. `CLAUDE.md` says it in the general case --
no number is typed into prose -- and a count of rows going to a clinician is
exactly a number that must not drift from the record it describes. So the pack
is emitted, and the only numbers in it are counted here.

Two sheets, because the rows are not one kind of ask:

  Sheet 1  the clinical questions. This is what is actually being requested,
           and a clinician can answer every row on it without a Kinyarwanda
           speaker in the room.

  Sheet 2  the word questions, marked optional. A clinician may happen to know
           the register a patient uses, and if they do it is worth capturing --
           but these rows are blocked on a SPEAKER, and presenting them as part
           of the ask would misrepresent what a signature on sheet 1 means.

The split between the two is a judgement and therefore declared, not inferred:
see VOCABULARY_SHEET below. Everything else -- which rows carry the flag, how
many, over how many concepts, the anchor counts -- is read off disk.

Usage:  python review/build_clinician_pack.py [--check]

`--check` emits to memory and compares, so CI can fail on a pack that has
drifted from the spine rather than discovering it at the clinician's desk.
"""

from __future__ import annotations

import argparse
import csv
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPINE = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"
ANCHORS = ROOT / "review" / "concept_anchors.csv"
OUT = ROOT / "docs" / "protocols" / "d2-clinician-review-pack.md"
CSV_DIR = ROOT / "review" / "clinician_pack"

# One CSV per sheet. They are the workbook's source of truth, and
# `csv_to_xlsx.verify()` reads the saved workbook back and asserts every
# cell still equals the CSV it came from -- so a sheet cannot quietly lose
# a row or coerce a concept id into a date on the way to a clinician.
SHEET_FILES = {
    "clinical": CSV_DIR / "sheet1_clinical.csv",
    "vocabulary": CSV_DIR / "sheet2_vocabulary.csv",
    "questions": CSV_DIR / "sheet3_questions.csv",
}

# ── the one judgement in this file ──────────────────────────────────────────
#
# Concepts whose flagged rows go to the OPTIONAL sheet instead of the ask.
#
# The test is not "does the note mention a Kinyarwanda word" -- most of them do.
# It is whether the row names a CLINICAL stake that a clinician could settle.
# `IF01` names a danger sign ("fever with stiff neck is a specific danger
# sign"); `IF03` names one ("IMCI general danger sign (unable to drink);
# precision matters"); `CR05` asks a clinician to confirm a mapping in so many
# words. Those stay on the ask. `IF04` and `IF06` name no clinical question at
# all -- what is unresolved is one word for sweating and the register of a
# phrase for painful urination, and `docs/blocked.md` 1a independently reads
# both as WORD blocks, lifted by the English and French arms on the grounds
# that a block on a Kinyarwanda word cannot bind a language that has the word.
#
# Both persons of a concept move together. A third person here is held only
# because its first person is, so splitting a concept across the two sheets
# would put the question on one and its consequence on the other.
VOCABULARY_SHEET: dict[str, str] = {
    "IF04": (
        "'nkabira ibyuya' for sweating is unvalidated. Nothing clinical is open "
        "about fever with chills and sweats — the missing piece is one word."
    ),
    "IF06": (
        "'iyo nihagarika' for painful urination is unvalidated and may be the "
        "wrong register. Again a word and a register, not a clinical question."
    ),
}

# Rows blocked on a word that never carried `needs_clinician`, so they are not
# subtracted from the ask. Listed on sheet 2 because a clinician who knows the
# word can close them, and because leaving them off would make sheet 2 look
# like a smaller problem than it is.
EXTRA_VOCABULARY: list[tuple[str, str, str]] = [
    (
        "GI03",
        "black tarry stool",
        "Both persons are blocked on a noun for stool. ASKED 2026-09-04: is "
        "'umusarane' the word here, or only the latrine? It heads RBC's "
        "danger-sign line 'Kwituma umusarane uvanze n'amaraso'; the alternative "
        "'amabyi' has one attestation. Already out with a speaker.",
    ),
]

FIVE_QUESTIONS = """\
1. **Does fetal demise belong in a triage taxonomy at all?** `OB06` describes a
   presentation where no intervention follows, unlike every other CRITICAL.
2. **Is `OB13` (reduced fetal movement) a concept worth having** when the
   speaker reports no natural Kinyarwanda phrase expresses it?
3. **Is high fever with refusal to eat URGENT or CRITICAL?** Inability to drink
   is an IMCI general danger sign; refusal to eat in a febrile child sits
   beside it. `EX43`.
4. **Can a patient who accurately reports their own new confusion be**
   **meaningfully confused?** `NE06`. Two language arms hold this row.
5. **Which description of lower chest indrawing is correct** — the chest
   sinking, or the area under the ribs pulling in? `CR04`.
"""


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _cell(text: str, limit: int = 300) -> str:
    """One table cell: no pipes, no newlines, and truncated honestly."""
    flat = " ".join(text.split()).replace("|", "/")
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"


@dataclass(frozen=True)
class Derived:
    """Everything read off disk, derived once.

    The Markdown pack and the three CSV sheets are two renderings of the same
    facts. Deriving them separately would be a second place for the split to
    be wrong -- the exact failure AUDIT 1.3 is about, and the reason the count
    in this pack was wrong to begin with.
    """

    spine: list[dict[str, str]]
    flagged: list[dict[str, str]]
    ask: list[dict[str, str]]
    words: list[dict[str, str]]
    held: list[dict[str, str]]
    concepts: set[str]
    flagged_concepts: set[str]
    ask_concepts: set[str]
    anchors: list[dict[str, str]]
    by_source: Counter
    anchored: int
    anchored_ids: set[str]
    word_entries: int


def derive() -> Derived:
    spine = _rows(SPINE)
    flagged = [r for r in spine if r["needs_clinician"].strip()]
    ask = [r for r in flagged if r["concept_id"] not in VOCABULARY_SHEET]
    anchors = _rows(ANCHORS)
    anchored_ids = {r["concept_id"] for r in anchors}
    return Derived(
        spine=spine,
        flagged=flagged,
        ask=ask,
        words=[r for r in flagged if r["concept_id"] in VOCABULARY_SHEET],
        held=[r for r in spine if r["hold"].strip().lower() == "yes"],
        concepts={r["concept_id"] for r in spine},
        flagged_concepts={r["concept_id"] for r in flagged},
        ask_concepts={r["concept_id"] for r in ask},
        anchors=anchors,
        by_source=Counter(r["source"].strip() for r in anchors),
        anchored=len(anchored_ids),
        anchored_ids=anchored_ids,
        # One entry per CONCEPT, not per row: both persons of a word block wait
        # on the same word, and asking twice would read as two questions.
        word_entries=len(VOCABULARY_SHEET) + len(EXTRA_VOCABULARY),
    )


def build() -> str:
    d = derive()
    ask, words = d.ask, d.words
    flagged_concepts, ask_concepts = d.flagged_concepts, d.ask_concepts
    held, concepts = d.held, d.concepts
    by_source, anchored = d.by_source, d.anchored
    word_entries = d.word_entries

    out: list[str] = []
    w = out.append

    def para(text: str) -> None:
        """A wrapped paragraph, then a blank line.

        Written as one string and wrapped here rather than emitted pre-broken,
        because interpolated counts change width and hand-broken lines go
        ragged the moment a number gains a digit.
        """
        w(textwrap.fill(" ".join(text.split()), width=78))
        w("")

    w("# D2 — Clinician review pack")
    w("")
    w("**STATUS: NOT EXECUTED.** No clinician has reviewed this taxonomy. The")
    w("project document's claim of approval by a nurse at CHUK has no source, and")
    w("nothing in this repository may supply one.")
    w("")
    w("*Generated by `review/build_clinician_pack.py` from")
    w("`review/speaker_brief_kinyarwanda_v2.csv`. Every count below is read off")
    w("that file. Do not edit this document by hand — edit the record.*")
    w("")

    # ── covering note ───────────────────────────────────────────────────────
    w("## Covering note — please read this first")
    w("")
    para(f"**You are being asked about {len(ask)} rows, not {len(flagged_concepts)}.**")
    para(
        f"The figure {len(flagged_concepts)} appears in this project's own "
        "planning documents and was never a count of rows. It is the number of "
        "*concepts* carrying a flag, and the unit of review is a *row*: most "
        "concepts here carry a first-person and a third-person phrasing, and "
        "the two can fail differently — a wording can be right in one person's "
        "mouth and wrong in the other's, which is most of why this pack exists."
    )
    para(
        "Two things also changed on 2026-09-11. Four third-person rows were "
        "filed under `hold` alone while their first persons were flagged for "
        "you, so every pack built before that date showed you one half of "
        "those concepts and dropped the other; they now carry the flag. And "
        f"{len(VOCABULARY_SHEET)} concepts whose only open question is a "
        "Kinyarwanda word moved to the optional sheet, because asking a "
        "clinician to supply a speaker's word is not a clinical review."
    )
    para(
        f"So: {len(ask)} rows over {len(ask_concepts)} concepts. You are "
        "getting the real number rather than the round one because the "
        "difference is roughly two hours of your time, and because a pack "
        "that understates its own size is not a pack you should be asked to "
        "sign."
    )
    para("**There are two sheets, and only the first is the ask.**")
    para(
        f"- **Sheet 1 — {len(ask)} rows.** Clinical questions. This is the "
        "request. Every row can be answered without a Kinyarwanda speaker "
        "present."
    )
    para(
        f"- **Sheet 2 — {word_entries} entries, optional.** Questions about "
        "which Kinyarwanda *word* a patient uses. These are blocked on a "
        "native speaker, not on you. Answer any you happen to know; skipping "
        "the sheet entirely costs this project nothing it was expecting."
    )
    para(
        "The sign-off at the end of sheet 1 covers sheet 1. Nothing on sheet "
        "2 is part of what you are signing."
    )

    # ── sheet 1 ─────────────────────────────────────────────────────────────
    w("---")
    w("")
    w(f"# Sheet 1 — the ask: {len(ask)} rows over {len(ask_concepts)} concepts")
    w("")
    w("Approval, rejection or amendment of the urgency taxonomy, and rulings on")
    w("the rows below. A signature at the end of this sheet is the record.")
    w("")
    w("| concept | person | urgency | gloss | the question |")
    w("|---|---|---|---|---|")
    for r in sorted(ask, key=lambda r: (r["concept_id"], r["person"])):
        w(
            f"| `{r['concept_id']}` | {r['person']} | {r['proposed_urgency']} "
            f"| {_cell(r['english_gloss'], 60)} | {_cell(r['needs_clinician'])} |"
        )
    w("")

    w("## The five questions that are not about one row")
    w("")
    w(FIVE_QUESTIONS.rstrip())
    w("")

    w("## The taxonomy mapping to approve")
    w("")
    para(
        f"{anchored} of {len(concepts)} concepts carry a published anchor: "
        + ", ".join(
            f"{source} ({count})"
            for source, count in sorted(by_source.items(), key=lambda kv: -kv[1])
        )
        + "."
    )
    para(
        f"**{len(concepts) - anchored} concepts carry no anchor at all** — they "
        "are positions inherited from the v1 corpus, catalogued without recorded "
        f"concepts. Those {len(concepts) - anchored} are the ones most in need "
        "of a clinician's eye."
    )

    w(f"## Rows generating nothing until ruled — {len(held)} held")
    w("")
    para(
        "Context, not a second ask: these are already covered by the rows above "
        "or by sheet 2. Listed so that nothing is generating quietly while you "
        "read."
    )
    w("| concept | person | why held |")
    w("|---|---|---|")
    for r in sorted(held, key=lambda r: (r["concept_id"], r["person"])):
        # `notes` first, not `needs_clinician`. This column answers "why is it
        # held", which is what `notes` records; `needs_clinician` answers "what
        # is being asked", and it is already the last column of sheet 1. Taking
        # the flag first put the same 2026-09-11 reclassification paragraph into
        # four consecutive rows here and buried the actual reason under it.
        why = r["notes"].strip() or r["needs_clinician"].strip() or "held"
        w(f"| `{r['concept_id']}` | {r['person']} | {_cell(why, 160)} |")
    w("")

    w("## Sign-off — sheet 1 only")
    w("")
    w(f"> I have reviewed the taxonomy and the {len(ask)} rows on sheet 1.")
    w("")
    w("> Name / role / facility: ______________________")
    w("")
    w("> Approved / approved with the amendments recorded above / not approved")
    w("> (delete as applicable)")
    w("")
    w("> Signature: ______________________   Date: ____________")
    w("")
    w("**Until this sheet is signed, no claim of clinical approval may appear")
    w("anywhere.**")
    w("")

    # ── sheet 2 ─────────────────────────────────────────────────────────────
    w("---")
    w("")
    w(f"# Sheet 2 — OPTIONAL. Not part of the ask. {word_entries} entries")
    w("")
    w("**Skip this sheet freely.** These rows are blocked on a Kinyarwanda word,")
    w("which is a native speaker's call and not a clinical one. They are here")
    w("only because a clinician who works in Kinyarwanda every day may know the")
    w("word a patient actually uses, and that is worth more than another round")
    w("with a speaker. An unanswered entry blocks nothing that sheet 1 unblocks.")
    w("")
    w("| concept | gloss | the word that is missing |")
    w("|---|---|---|")
    seen: set[str] = set()
    for r in sorted(words, key=lambda r: r["concept_id"]):
        if r["concept_id"] in seen:
            continue
        seen.add(r["concept_id"])
        w(
            f"| `{r['concept_id']}` | {_cell(r['english_gloss'], 60)} "
            f"| {_cell(VOCABULARY_SHEET[r['concept_id']], 400)} |"
        )
    for cid, gloss, note in EXTRA_VOCABULARY:
        w(f"| `{cid}` | {_cell(gloss, 60)} | {_cell(note, 400)} |")
    w("")
    for cid in list(VOCABULARY_SHEET) + [c for c, _, _ in EXTRA_VOCABULARY]:
        w(f"> `{cid}` — your word, if you have one: ______________________")
        w("")
    para(
        "Leave any of them blank if you would rather a speaker ruled it. That "
        "is the expected answer and it is not a failure."
    )
    w("")

    return "\n".join(out) + "\n"


# ── the three sheets ────────────────────────────────────────────────────────
#
# The workbook is the thing a clinician actually fills in; the Markdown is the
# thing a reviewer reads in the repository. Both are rendered from `derive()`,
# so they cannot disagree about which rows are being asked about.
#
# Answer columns are empty by design and are tinted by csv_to_xlsx.AUTHOR_COLUMNS
# so "where do I type" needs no explanation. Text is NOT truncated here the way
# the Markdown tables truncate it -- a cell holds the whole question, and a
# clinician ruling on a row should see all of it.


def sheet_clinical(d: Derived) -> tuple[list[str], list[dict[str, str]]]:
    """Sheet 1 -- the ask. One row per flagged row, both persons."""
    columns = [
        "concept_id",
        "person",
        "urgency",
        "english_gloss",
        "the_question",
        "your_ruling",
        "your_notes",
    ]
    rows = [
        {
            "concept_id": r["concept_id"],
            "person": r["person"],
            "urgency": r["proposed_urgency"],
            "english_gloss": r["english_gloss"],
            "the_question": " ".join(r["needs_clinician"].split()),
            "your_ruling": "",
            "your_notes": "",
        }
        for r in sorted(d.ask, key=lambda r: (r["concept_id"], r["person"]))
    ]
    return columns, rows


def sheet_vocabulary(d: Derived) -> tuple[list[str], list[dict[str, str]]]:
    """Sheet 2 -- optional. One row per CONCEPT, not per person."""
    columns = ["concept_id", "english_gloss", "the_word_that_is_missing", "your_word"]
    gloss = {r["concept_id"]: r["english_gloss"] for r in d.spine}

    rows: list[dict[str, str]] = []
    for cid in sorted(VOCABULARY_SHEET):
        rows.append(
            {
                "concept_id": cid,
                "english_gloss": gloss.get(cid, ""),
                "the_word_that_is_missing": " ".join(VOCABULARY_SHEET[cid].split()),
                "your_word": "",
            }
        )
    for cid, cid_gloss, note in EXTRA_VOCABULARY:
        rows.append(
            {
                "concept_id": cid,
                "english_gloss": cid_gloss,
                "the_word_that_is_missing": " ".join(note.split()),
                "your_word": "",
            }
        )
    return columns, rows


def sheet_questions(d: Derived) -> tuple[list[str], list[dict[str, str]]]:
    """Sheet 3 -- the five cross-cutting questions, then the taxonomy check.

    The taxonomy half is not a restatement of the counts. It lists the
    concepts carrying NO published anchor one per row, because the pack's own
    claim is that those are the ones most in need of a clinician's eye -- and a
    claim like that is only actionable if the reader can tick them off.
    """
    columns = ["item", "kind", "detail", "your_answer"]
    rows: list[dict[str, str]] = []

    for number, text in enumerate(_five_questions(), start=1):
        rows.append(
            {
                "item": f"Q{number}",
                "kind": "open question",
                "detail": text,
                "your_answer": "",
            }
        )

    for source, count in sorted(d.by_source.items(), key=lambda kv: -kv[1]):
        rows.append(
            {
                "item": source,
                "kind": "taxonomy: anchored concepts",
                "detail": f"{count} concepts carry this anchor.",
                "your_answer": "",
            }
        )

    # One row per unanchored concept, first person taken as the representative
    # because every concept has one and the gloss is identical across persons.
    seen: set[str] = set()
    for r in d.spine:
        cid = r["concept_id"]
        if cid in d.anchored_ids or cid in seen:
            continue
        seen.add(cid)
        rows.append(
            {
                "item": cid,
                "kind": "taxonomy: NO anchor",
                "detail": (
                    f"{r['domain']} / {r['proposed_urgency']} / "
                    f"{r['english_gloss']} -- inherited from the v1 corpus with "
                    "no published anchor. Is the concept real and is the urgency "
                    "right?"
                ),
                "your_answer": "",
            }
        )
    return columns, rows


def _five_questions() -> list[str]:
    """The five questions as plain sentences, parsed from the Markdown block.

    Parsed rather than duplicated: FIVE_QUESTIONS is the single copy, and a
    second hand-written list would be one more place for the wording to drift.
    """
    out: list[str] = []
    for chunk in FIVE_QUESTIONS.strip().split("\n")[0:]:
        stripped = chunk.strip()
        if stripped and stripped[0].isdigit() and "." in stripped[:3]:
            out.append(stripped.split(".", 1)[1].strip())
        elif out:
            out[-1] += " " + stripped
    return [" ".join(q.replace("**", "").split()) for q in out]


SHEET_BUILDERS = {
    "clinical": sheet_clinical,
    "vocabulary": sheet_vocabulary,
    "questions": sheet_questions,
}


def write_csvs(d: Derived) -> list[Path]:
    """Write one CSV per sheet. Returns the paths actually written."""
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, builder in SHEET_BUILDERS.items():
        columns, rows = builder(d)
        path = SHEET_FILES[name]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare against the committed pack instead of writing it",
    )
    args = parser.parse_args()

    d = derive()
    rendered = build()

    if args.check:
        stale: list[str] = []
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != rendered:
            stale.append(str(OUT.relative_to(ROOT)))
        # The CSVs are checked too. A stale sheet is worse than a stale
        # document: the document is read in the repository, the sheet is what
        # goes to the clinician.
        for name, builder in SHEET_BUILDERS.items():
            path = SHEET_FILES[name]
            if not path.exists():
                stale.append(f"{path.relative_to(ROOT)} (missing)")
                continue
            columns, rows = builder(d)
            on_disk = _rows(path)
            header = list(on_disk[0]) if on_disk else []
            if header != columns or on_disk != rows:
                stale.append(str(path.relative_to(ROOT)))
        if stale:
            print(
                "stale, regenerate with `python review/build_clinician_pack.py`:\n  "
                + "\n  ".join(stale),
                file=sys.stderr,
            )
            return 1
        print("pack and all three sheets match the record.")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rendered.splitlines())} lines)")
    for path in write_csvs(d):
        print(f"wrote {path.relative_to(ROOT)} ({len(_rows(path))} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
