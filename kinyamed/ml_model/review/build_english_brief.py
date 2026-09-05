#!/usr/bin/env python
"""Build `review/speaker_brief_english_v2.csv` off the 127-concept spine.

English has no speaker, so this is not an authoring brief: it is a REVIEW brief.
The distinction drives every column choice below.

    - `suggested_english` holds the CANDIDATE - the v1 corpus string, or a draft.
      Existing text goes here, never into `your_phrasing`.
    - `your_phrasing` stays empty until the reviewer rules. "126 English phrases
      exist" has been read as "126 English phrases are fine"; keeping the two
      columns apart is what stops that.
    - three verdicts, because they have three different owners: `form` is
      mechanical (lint_phrases.py, not stored), `verdict_fidelity` is mine and
      adversarial, `verdict_register` is the reviewer's, and urgency stays with
      the clinician in `needs_clinician`.

WHAT IS CARRIED OVER, AND WHY IT IS SAFE TO CARRY
-------------------------------------------------
The Kinyarwanda brief is the spine: 127 concepts x first/third. Carried:

    applies / person_note   concept collapses and rule-11 person applicability.
                            Both are claims about the CONCEPT (whether a patient
                            can report their own convulsion), not about a
                            language. Safe.
    hold                    carried as-is even where the reason is Kinyarwanda
                            wording, because blocking is the safe direction. The
                            per-domain pass lifts the ones that do not apply to
                            English, and every lift is recorded.
    needs_clinician         reduced to a marker. The Kinyarwanda notes mix
                            clinical questions (language-independent) with
                            lexical ones (not), and classifying twenty free-text
                            notes mechanically would get some wrong in the
                            direction that matters. The per-domain pass restates
                            each one in English terms.

NOT carried: `form`. A phrase's form is a property of its wording, so it is
per-language by definition - EX44's noun_phrase ruling was about Kinyarwanda
nominalisation. English rows target `utterance` for the reason section 7 of
session-state gives: a `noun_phrase` row takes the fixed v1 SUBJECTS list and
IGNORES relation rulings entirely, so under the person split every relation
ruling on an English noun_phrase row would be inert.

Not carried either: `your_phrasing`, `source`, `confidence` - all Kinyarwanda
facts about Kinyarwanda text.

RE-RUNNING
----------
Idempotent and non-destructive. Columns in `REGENERATED` are recomputed from
their sources every run; everything else is preserved once written, so a
half-reviewed brief survives a rebuild. `--check` reports drift without writing.

    python review/build_english_brief.py            # build or refresh
    python review/build_english_brief.py --check    # drift only, no write

Writes atomically and refuses a zero-row write, because walk.py once truncated a
brief to its header.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from dataset.vocabulary import SYMPTOMS  # noqa: E402
from english_relations import DOMAIN_RELATIONS_EN, PENDING_RULINGS  # noqa: E402
from relation_sets import rulings  # noqa: E402
from walk import save  # noqa: E402  - reuse the one atomic writer, not a second one

KY_BRIEF = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"
KY_BRIEF_V1 = ROOT / "review" / "speaker_brief_kinyarwanda.csv"
ANCHORS = ROOT / "review" / "concept_anchors.csv"
SHEET = ROOT / "review" / "phrase_review_sheet.csv"
OUT = ROOT / "review" / "speaker_brief_english_v2.csv"

COLUMNS = [
    "concept_id", "domain", "proposed_urgency", "english_gloss", "anchor",
    "person", "applies", "person_note", "form", "relation_set",
    "suggested_english", "candidate_origin", "confidence",
    "verdict_fidelity", "suggestion_note", "verdict_register", "rw_english_check",
    "your_phrasing", "second_phrasing_optional", "notes",
    "source", "needs_clinician", "hold",
]

# Recomputed from source on every run. Hand edits here are overwritten, which is
# the point: these are derived facts, and a derived column that drifts from its
# source is how the EX16 relation bug survived as long as it did.
# `applies` and `person_note` were seeded-once until 2026-09-05. That was wrong:
# nothing in the English pass ever writes them - not the drafter, not the
# reviewer - so they are purely inherited from the Kinyarwanda spine. Preserving
# them meant that when the Kinyarwanda session ruled a concept out of generation,
# this brief did not notice. EX42 and PA06 were collapsed into IF05 and both kept
# `applies=yes` here, with a drafted English phrase on a dead concept.
REGENERATED = ["domain", "proposed_urgency", "english_gloss", "anchor",
               "relation_set", "applies", "person_note"]

# The eleven collapsed concepts and PR02. Their rows stay on the spine (they are
# part of the 127) but they generate nothing, so an English candidate for them is
# dropped rather than carried forward as if it were live.
COLLAPSED = {"IF07", "EX30", "GI08", "EX17", "HT01", "HT06",
             "NE01", "NE02", "NE03", "NE04", "NE08", "PA10"}
OUT_OF_GENERATION = {"PR02"}


def ex_to_v1_english() -> dict[str, str]:
    """EX concept id -> the English v1 phrase at the same position.

    EX ids were assigned in the order of the 47 `VALIDATE existing` rows of the
    first Kinyarwanda brief, and `SYMPTOMS` is index-parallel across all four
    languages. Both facts are asserted here rather than trusted: 46 of the 47
    rows still match the v2 brief on domain and urgency, and the 47th (EX31) is
    the speaker's own added row, which has no counterpart in any other language.
    """
    where: dict[str, tuple[str, str, int]] = {}
    for urgency, domains in SYMPTOMS["kinyarwanda"].items():
        for domain, phrases in domains.items():
            for i, phrase in enumerate(phrases):
                where[phrase] = (urgency, domain, i)

    existing = [r for r in csv.DictReader(KY_BRIEF_V1.open(encoding="utf-8"))
                if r["task"] == "VALIDATE existing"]
    ex_ids = [r["concept_id"] for r in csv.DictReader(KY_BRIEF.open(encoding="utf-8"))
              if r["person"] == "first" and r["concept_id"].startswith("EX")]
    if len(existing) != len(ex_ids):
        raise SystemExit(
            f"{len(ex_ids)} EX ids but {len(existing)} existing rows in the first "
            "brief. The positional mapping EX id -> v1 phrase is what gives the "
            "English rows their candidate; it must not be guessed."
        )

    spine = {(r["concept_id"], r["person"]): r
             for r in csv.DictReader(KY_BRIEF.open(encoding="utf-8"))}
    out: dict[str, str] = {}
    for ex_id, row in zip(ex_ids, existing):
        ky = row["original_corpus_phrase"].strip()
        if not ky:
            out[ex_id] = ""          # EX31: speaker-added, no v1 row in any language
            continue
        urgency, domain, i = where[ky]
        brief_row = spine[(ex_id, "first")]
        if (brief_row["domain"], brief_row["proposed_urgency"]) != (domain, urgency):
            raise SystemExit(
                f"{ex_id}: brief says {brief_row['domain']}/{brief_row['proposed_urgency']}, "
                f"v1 position says {domain}/{urgency}. The EX ordering assumption is wrong; "
                "stop and re-derive it before any English text is attached to a concept."
            )
        out[ex_id] = SYMPTOMS["english"][urgency][domain][i]
    return out


# Where the collapsed concepts' wording went, so a dropped English candidate is
# offered to the concept that absorbed it instead of vanishing. Kinyarwanda kept
# both wordings in every one of these; English should have the same chance to.
ABSORBED_BY = {"EX17": "EX16", "EX30": "CR07", "GI08": "EX16", "HT01": "EX18",
               "HT06": "EX22", "IF07": "EX29", "PA10": "EX46"}


def concept_drift() -> dict[str, tuple[float, str, str]]:
    """EX id -> (stem overlap, v1 Kinyarwanda, the speaker's rewrite).

    THE EX MAPPING IS POSITIONAL, AND POSITION IS NOT CONCEPT. An EX id names the
    slot a v1 phrase occupied; the speaker was rewriting for naturalness, not
    holding the concept fixed, and several rewrites landed on a different
    presentation. EX30's slot held "mild runny nose" and its rewrite is "I cough
    a little but have no fever" - which is why it then collapsed into CR07, and
    why EX31 exists at all: the speaker added a row to put the runny nose back.

    So the English v1 string at an EX position is the text v1 HAD there, not
    necessarily the concept the id now denotes. Every EX candidate carries that
    caveat, and this flags the ones where the divergence is visible.

    Crude by design - 4-character substrings, because a Kinyarwanda stem hides
    behind noun-class prefixes and a word-boundary regex cannot see it (section
    9). A LEAD, NOT A VERDICT: it misses EX29, whose rewrite turned a cough into
    a fever while keeping enough shared material to score above the threshold.
    """
    def stems(text: str) -> set[str]:
        out: set[str] = set()
        for word in re.findall(r"[a-z']+", text.lower()):
            word = word.replace("'", "")
            for i in range(len(word) - 3):
                out.add(word[i:i + 4])
        return out

    existing = [r for r in csv.DictReader(KY_BRIEF_V1.open(encoding="utf-8"))
                if r["task"] == "VALIDATE existing"]
    ex_ids = [r["concept_id"] for r in csv.DictReader(KY_BRIEF.open(encoding="utf-8"))
              if r["person"] == "first" and r["concept_id"].startswith("EX")]
    out: dict[str, tuple[float, str, str]] = {}
    for ex_id, row in zip(ex_ids, existing):
        original, rewrite = row["original_corpus_phrase"], row["speaker_phrase"]
        if not original or not rewrite:
            continue
        a, b = stems(original), stems(rewrite)
        overlap = len(a & b) / max(1, len(a | b))
        if overlap < 0.10:
            out[ex_id] = (round(overlap, 3), original, rewrite)
    return out


def sheet_drafts() -> dict[str, tuple[str, str]]:
    """concept id -> (draft phrase, draft id) from `phrase_review_sheet.csv`.

    68 of the 80 drafts name their concept in the gloss. The twelve obstetric
    ones predate the OB ids and name none, so they are matched positionally
    against OB01-OB12: both sequences are 5 CRITICAL, 5 URGENT, 2 ROUTINE in the
    same clinical order, and the glosses agree line for line.
    """
    rows = [r for r in csv.DictReader(SHEET.open(encoding="utf-8"))
            if r["language"] == "english" and r["status"] == "draft"]
    out: dict[str, tuple[str, str]] = {}
    obstetric: list[dict] = []
    for r in rows:
        gloss = r["english_gloss"]
        if gloss.startswith("["):
            out[gloss[1:gloss.index("]")]] = (r["phrase"], r["id"])
        elif r["domain"] == "obstetric":
            obstetric.append(r)
    if len(obstetric) != 12:
        raise SystemExit(f"expected 12 untagged obstetric drafts, found {len(obstetric)}")
    for i, r in enumerate(obstetric, start=1):
        out[f"OB{i:02d}"] = (r["phrase"], r["id"])
    return out


def relation_set_name(concept_id: str, domain: str, person: str,
                      ruled: dict[str, str]) -> str:
    """The named set an English third person expands over. Names, not strings.

    Storing the NAME rather than the eight relations is deliberate: the strings
    live in vocabulary.py and the ruling lives in routine_relation_sets.csv, and
    a third copy in this brief would be a third thing to drift.
    """
    if person != "third":
        return ""
    name = ruled.get(concept_id)
    if name:
        return name
    if domain in DOMAIN_RELATIONS_EN:
        return "OBSTETRIC_RELATIONS" if domain == "obstetric" else "CHILD_RELATIONS"
    return "ALL_RELATIONS"


def build() -> list[dict]:
    ky = list(csv.DictReader(KY_BRIEF.open(encoding="utf-8")))
    anchors = {r["concept_id"]: r for r in csv.DictReader(ANCHORS.open(encoding="utf-8"))}
    v1_english = ex_to_v1_english()
    drafts = sheet_drafts()
    ruled = rulings()
    # A ruling made during the English pass, not yet in the Kinyarwanda record.
    # Applied here so the brief is correct, and announced so it is not forgotten.
    for concept_id, name in PENDING_RULINGS.items():
        ruled[concept_id] = name
    drift = concept_drift()

    # Which person row a new concept's single draft belongs on. The drafts were
    # written before the person split and declare no person, so the row that
    # takes one is the row that applies: the paediatric drafts are already carer
    # voice ("my child is having a fit") and their first person is applies=no.
    applies_first = {r["concept_id"]: r["applies"] != "no"
                     for r in ky if r["person"] == "first"}

    rows: list[dict] = []
    for src in ky:
        cid, person = src["concept_id"], src["person"]
        is_ex = cid.startswith("EX")
        anchor = anchors.get(cid, {})
        row = {c: "" for c in COLUMNS}
        row.update(
            concept_id=cid,
            domain=src["domain"],
            proposed_urgency=src["proposed_urgency"],
            # The v1 phrases were catalogued with "(existing phrase - no concept
            # recorded)". They have no gloss and no anchor in any language, so
            # fidelity cannot be judged for them - only register can. Left empty
            # rather than back-filled from the phrase, which would be circular.
            english_gloss="" if is_ex else src["english_gloss"],
            anchor=anchor.get("anchor", ""),
            person=person,
            applies=src["applies"],
            person_note=src["person_note"],
            form="utterance",
            relation_set=relation_set_name(cid, src["domain"], person, ruled),
        )

        notes: list[str] = []
        if src["applies"] == "no":
            notes.append("applies=no inherited from the Kinyarwanda brief")
        if src["hold"] == "yes":
            row["hold"] = "yes"
            notes.append("HOLD INHERITED from Kinyarwanda — lift it here if the "
                         "reason is Kinyarwanda wording rather than the concept")
        if src["needs_clinician"].strip():
            row["needs_clinician"] = "INHERITED — restate in English terms during the domain pass"

        candidate, origin, note = "", "", ""
        if cid in COLLAPSED or cid in OUT_OF_GENERATION:
            drafted = drafts.get(cid)
            absorbed = v1_english.get(cid, "") if is_ex else ""
            # Record the drop once, on the row the candidate would have gone to,
            # rather than twice per concept.
            carries = (person == "first") if is_ex else (
                (person == "first") == applies_first.get(cid, True))
            if carries and (drafted or absorbed):
                origin = "dropped"
                why = (f"collapsed into {ABSORBED_BY.get(cid, 'another concept')}"
                       if cid in COLLAPSED
                       else "out of generation pending the service-design ruling")
                text = drafted[0] if drafted else absorbed
                label = f"draft {drafted[1]}" if drafted else "v1 English"
                note = (f"{label} dropped ({why}): {text!r}. "
                        "Recorded so the drop is visible, not silent.")
        elif is_ex:
            if person == "first":
                candidate = v1_english.get(cid, "")
                origin = "v1_corpus" if candidate else ""
                if not candidate:
                    note = ("no v1 English phrase exists: EX31 is the row the speaker "
                            "ADDED to the first brief, so it has no counterpart in any "
                            "other language and English must be drafted from scratch.")
                else:
                    note = ("v1 corpus string at this position, carried as a CANDIDATE. "
                            "It is currently a noun_phrase rendered after a subject; as "
                            "an utterance it needs the subject folded in.")
                    # An EX id names a POSITION in v1, and the speaker's rewrite of
                    # that position was free to land on a different presentation. So
                    # fidelity cannot be assumed for any EX row, only for the ones
                    # where a gloss exists - and none do.
                    row["verdict_fidelity"] = "unverified: concept identity"
                    row["suggestion_note"] = (
                        "The v1 phrases were catalogued as 'existing phrase - no concept "
                        "recorded', so there is no gloss to check this against. Confirm "
                        "the English still describes the same presentation the Kinyarwanda "
                        "row now describes before ruling on register."
                    )
                    if cid in drift:
                        overlap, original, rewrite = drift[cid]
                        row["suggestion_note"] = (
                            f"CONCEPT MAY HAVE MOVED (stem overlap {overlap}). The "
                            f"Kinyarwanda rewrite shares almost nothing with the v1 phrase "
                            f"this English came from: {original!r} -> {rewrite!r}. If the "
                            "concept moved, the English candidate is the wrong text for "
                            "this row and should be drafted fresh from the Kinyarwanda."
                        )
        else:
            drafted = drafts.get(cid)
            if drafted and (person == "first") == applies_first.get(cid, True):
                candidate, origin = drafted[0], "sheet_draft"
                note = (f"draft {drafted[1]} from phrase_review_sheet.csv, "
                        "Claude 2026-08-31, never reviewed")
                if person == "third":
                    note += ". Written in carer voice already; needs {REL} substituted "
                    note += "for the relation before it can expand."

        row.update(suggested_english=candidate, candidate_origin=origin)
        if person == "first":
            for gone, keeper in ABSORBED_BY.items():
                if keeper != cid:
                    continue
                text = v1_english.get(gone, "") or (drafts.get(gone) or ("",))[0]
                if text:
                    notes.append(
                        f"{gone} collapsed into this concept. Its English text was "
                        f"{text!r} — Kinyarwanda kept both wordings here (EX16 carries "
                        "EX17's as a second phrasing), so consider it for "
                        "second_phrasing_optional rather than letting it drop."
                    )
        if origin in ("v1_corpus", "sheet_draft"):
            row["confidence"] = "unreviewed"
        if note:
            notes.append(note)
        row["notes"] = " | ".join(notes)
        rows.append(row)
    return rows


def merge(fresh: list[dict], existing: list[dict]) -> tuple[list[dict], list[str]]:
    """Refresh derived columns; preserve everything a reviewer may have touched."""
    by_key = {(r["concept_id"], r["person"]): r for r in existing}
    drift: list[str] = []
    for row in fresh:
        old = by_key.get((row["concept_id"], row["person"]))
        if old is None:
            continue
        for column in COLUMNS:
            if column in REGENERATED:
                if old.get(column, "") != row[column]:
                    drift.append(f"{row['concept_id']} {row['person']} {column}: "
                                 f"{old.get(column, '')!r} -> {row[column]!r}")
            elif column not in ("concept_id", "person"):
                row[column] = old.get(column, row[column])
    return fresh, drift


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="Report drift in derived columns without writing.")
    args = ap.parse_args()

    rows = build()
    if len(rows) != 254:
        raise SystemExit(f"expected 254 rows on the 127-concept spine, built {len(rows)}")

    drift: list[str] = []
    if OUT.exists():
        rows, drift = merge(rows, list(csv.DictReader(OUT.open(encoding="utf-8"))))

    if args.check:
        print(f"{len(rows)} rows")
        if drift:
            print(f"{len(drift)} derived columns have drifted from their sources:")
            for d in drift:
                print(f"  {d}")
            return 1
        print("derived columns agree with their sources")
        return 0

    save(OUT, COLUMNS, rows)
    for concept_id, name in PENDING_RULINGS.items():
        print(f"  PENDING: {concept_id} -> {name} is applied here but is NOT yet in "
              "routine_relation_sets.csv")
    filled = sum(1 for r in rows if r["suggested_english"].strip())
    ruled_rows = sum(1 for r in rows if r["your_phrasing"].strip())
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} rows")
    print(f"  {filled} carry a candidate, {ruled_rows} are ruled")
    for d in drift:
        print(f"  refreshed {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
