#!/usr/bin/env python
"""Build `review/speaker_brief_french_v2.csv` off the 128-concept spine.

French has no speaker, so this is not an authoring brief: it is a REVIEW brief.
Same shape as `build_english_brief.py`, and deliberately so — where the two
differ, the difference is recorded here rather than absorbed.

    - `suggested_french` holds the CANDIDATE - a v1 corpus string, or a draft.
      Existing text goes here, never into `your_phrasing`.
    - `your_phrasing` stays empty until a reviewer rules. NO FRENCH SPEAKER HAS
      SEEN ANY OF THIS.
    - `agreement_check` is DERIVED, not asserted - see FR-1 below.

FOUR DIFFERENCES FROM THE ENGLISH BUILDER, ALL DELIBERATE
---------------------------------------------------------
1. **128 concepts, not 127.** `OB13` was added to the spine 2026-09-05. The
   English brief is still 254/127 and is the one out of step; this is built
   against the spine as it stands today.

2. **v1 is read from the FROZEN COMMIT, not the working tree.** `dataset/
   vocabulary.py` is mid-rewrite for the v2 Kinyarwanda work: `LANGUAGES` is
   down to `("kinyarwanda",)` and the Kinyarwanda phrase list has been
   rewritten, so there is no `SYMPTOMS["french"]` to read and the v1 positional
   mapping no longer resolves against it. `build_english_brief.py` crashes on
   exactly this today.

   Reading HEAD is not a workaround, it is the correct source. **v1 is frozen
   and must stay byte-identical**; a positional mapping into v1 is a fact about
   the frozen corpus, so a working tree being edited for v2 is the wrong place
   to ask. The frozen file is used read-only and `dataset/` is never touched.

3. **The collapse list is DERIVED from the spine**, not hardcoded. A concept
   whose both persons are `applies=no` is out of generation. The English
   builder hardcodes twelve ids and the spine now has fifteen — `EX42`, `PA06`
   and `PA01` collapsed after that list was written, and nothing told it. A
   derived list cannot go stale, which is the same argument that moved
   `applies` and `person_note` into REGENERATED on 2026-09-05.

4. **`agreement_check` exists and has no English counterpart.** English needed
   no such column because an English relation takes no agreement. See FR-1 in
   `french_relations.py`.

NOT carried, for the reasons `build_english_brief.py` gives: `form` (a property
of wording, so per-language), `your_phrasing`, `source`, `confidence`.

RE-RUNNING
----------
Idempotent and non-destructive. Columns in `REGENERATED` are recomputed every
run; everything else is preserved once written, so a half-reviewed brief
survives a rebuild. `--check` reports drift without writing.

    python review/build_french_brief.py            # build or refresh
    python review/build_french_brief.py --check    # drift only, no write
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from french_relations import (DOMAIN_RELATIONS_FR, PENDING_RULINGS,  # noqa: E402
                               agreement_risks, obstetric_scope)  # noqa: E402
from relation_sets import rulings  # noqa: E402
from walk import save  # noqa: E402  - reuse the one atomic writer, not a second one

KY_BRIEF = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"
KY_BRIEF_V1 = ROOT / "review" / "speaker_brief_kinyarwanda.csv"
ANCHORS = ROOT / "review" / "concept_anchors.csv"
SHEET = ROOT / "review" / "phrase_review_sheet.csv"
OUT = ROOT / "review" / "speaker_brief_french_v2.csv"

# The frozen v1 vocabulary, addressed by commit rather than by path. `HEAD` is
# right only because v1 has not been re-frozen since; if it ever is, pin the tag.
V1_REF = "HEAD"
V1_PATH = "kinyamed/ml_model/dataset/vocabulary.py"

COLUMNS = [
    "concept_id", "domain", "proposed_urgency", "english_gloss", "anchor",
    "person", "applies", "person_note", "form", "relation_set",
    "suggested_french", "candidate_origin", "confidence",
    "verdict_fidelity", "suggestion_note", "verdict_register",
    "rw_french_check", "agreement_check",
    "your_phrasing", "second_phrasing_optional", "notes",
    "source", "needs_clinician", "hold",
]

# Recomputed from source on every run. Hand edits here are overwritten, which is
# the point. `agreement_check` is in the list because it is a pure function of
# the phrase and the relation set: if a draft is reworded, the risk must move
# with it, and a stored verdict that outlives its phrase is the EX16 bug again.
REGENERATED = ["domain", "proposed_urgency", "english_gloss", "anchor",
               "relation_set", "applies", "person_note", "agreement_check"]

# Collapse targets the spine's own notes do not spell out. Everything else is
# parsed from the notes; this map exists so the one gap is visible rather than
# silently absent, and `collapse_targets()` raises if it grows one.
ABSORBED_BY_DECLARED = {
    "IF07": "EX29",   # "collapse of IF07 into EX29 completed" - phrasing the regex misses
}


def v1_vocabulary():
    """Import the FROZEN v1 `vocabulary.py` from git, read-only.

    Not `from dataset.vocabulary import SYMPTOMS`: the working tree copy is
    mid-rewrite for v2 and has neither a `french` key nor the v1 Kinyarwanda
    phrase list the positional mapping keys on.
    """
    blob = subprocess.run(
        ["git", "show", f"{V1_REF}:{V1_PATH}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as handle:
        handle.write(blob)
        path = handle.name
    spec = importlib.util.spec_from_file_location("_v1_vocabulary", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    Path(path).unlink(missing_ok=True)
    if "french" not in module.SYMPTOMS:
        raise SystemExit(
            f"{V1_REF}:{V1_PATH} has no French symptoms. The frozen v1 is the only "
            "source of the v1 French strings; if it has lost them, stop and find "
            "the commit that still has them rather than drafting over the gap."
        )
    return module


def ex_to_v1_french(v1) -> dict[str, str]:
    """EX concept id -> the French v1 phrase at the same position.

    EX ids were assigned in the order of the 47 `VALIDATE existing` rows of the
    first Kinyarwanda brief, and `SYMPTOMS` is index-parallel across all four
    languages. Both facts are asserted here rather than trusted, exactly as
    `build_english_brief.ex_to_v1_english` does.
    """
    where: dict[str, tuple[str, str, int]] = {}
    for urgency, domains in v1.SYMPTOMS["kinyarwanda"].items():
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
            "French rows their candidate; it must not be guessed."
        )

    spine = {(r["concept_id"], r["person"]): r
             for r in csv.DictReader(KY_BRIEF.open(encoding="utf-8"))}
    out: dict[str, str] = {}
    for ex_id, row in zip(ex_ids, existing):
        ky = row["original_corpus_phrase"].strip()
        if not ky:
            out[ex_id] = ""          # EX31: speaker-added, no v1 row in any language
            continue
        if ky not in where:
            raise SystemExit(
                f"{ex_id}: v1 phrase {ky!r} is not in {V1_REF}:{V1_PATH}. The frozen "
                "v1 is supposed to be byte-identical; if it is not, that outranks "
                "anything this brief is doing."
            )
        urgency, domain, i = where[ky]
        brief_row = spine[(ex_id, "first")]
        if (brief_row["domain"], brief_row["proposed_urgency"]) != (domain, urgency):
            raise SystemExit(
                f"{ex_id}: brief says {brief_row['domain']}/{brief_row['proposed_urgency']}, "
                f"v1 position says {domain}/{urgency}. The EX ordering assumption is wrong; "
                "stop and re-derive it before any French text is attached to a concept."
            )
        out[ex_id] = v1.SYMPTOMS["french"][urgency][domain][i]
    return out


def collapsed_concepts(ky: list[dict]) -> set[str]:
    """Concepts out of generation: both persons `applies=no`.

    Derived, not listed. The English builder's hardcoded set was three short by
    the time it was read.
    """
    persons: dict[str, list[dict]] = defaultdict(list)
    for row in ky:
        persons[row["concept_id"]].append(row)
    return {cid for cid, rows in persons.items()
            if all(r["applies"] == "no" for r in rows)}


_COLLAPSE = re.compile(r"collapse\w*[^.]{0,80}?\binto\s+([A-Z]{2}\d{2})", re.IGNORECASE)


def collapse_targets(ky: list[dict], collapsed: set[str]) -> dict[str, str]:
    """Collapsed concept -> the concept that absorbed it, from the spine's notes.

    Where a collapsed concept's wording went, so a dropped French candidate is
    offered to the concept that absorbed it instead of vanishing. Kinyarwanda
    kept both wordings in most of these; French should have the same chance to.

    Parsed rather than transcribed. `ABSORBED_BY_DECLARED` covers the one note
    that states the collapse in a form the pattern cannot read, and a collapsed
    concept matching neither raises - a silent gap here is a dropped candidate
    nobody is told about.
    """
    blobs: dict[str, list[str]] = defaultdict(list)
    for row in ky:
        blobs[row["concept_id"]].extend(
            [row.get("notes", ""), row.get("person_note", ""),
             row.get("suggestion_note", "")])

    out: dict[str, str] = {}
    unresolved: list[str] = []
    for cid in sorted(collapsed):
        if cid in ABSORBED_BY_DECLARED:
            out[cid] = ABSORBED_BY_DECLARED[cid]
            continue
        match = _COLLAPSE.search(" ".join(blobs[cid]))
        if match:
            out[cid] = match.group(1).upper()
        else:
            unresolved.append(cid)
    if unresolved:
        raise SystemExit(
            f"no collapse target recoverable for {unresolved}. Their French candidates "
            "would be dropped with no record of where the concept went. Add the id to "
            "ABSORBED_BY_DECLARED with the ruling that names the target."
        )
    return out


def concept_drift() -> dict[str, tuple[float, str, str]]:
    """EX id -> (stem overlap, v1 Kinyarwanda, the speaker's rewrite).

    THE EX MAPPING IS POSITIONAL, AND POSITION IS NOT CONCEPT. An EX id names the
    slot a v1 phrase occupied; the speaker was rewriting for naturalness, not
    holding the concept fixed. So the French v1 string at an EX position is the
    text v1 HAD there, not necessarily the concept the id now denotes.

    Crude by design, and A LEAD, NOT A VERDICT - identical to the English
    arm's, so the two flag the same rows.
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

    68 of the 80 French drafts name their concept in the gloss. The twelve
    obstetric ones predate the OB ids and name none, so they are matched
    positionally against OB01-OB12: both sequences are 5 CRITICAL, 5 URGENT, 2
    ROUTINE in the same clinical order, and the glosses agree line for line.

    OB13 has no draft in any language - it was opened after the sheet was
    written, and the speaker reports Kinyarwanda has no phrase for it. Do not
    draft one here either.
    """
    rows = [r for r in csv.DictReader(SHEET.open(encoding="utf-8"))
            if r["language"] == "french" and r["status"] == "draft"]
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
    """The named set a French third person expands over. Names, not strings."""
    if person != "third":
        return ""
    name = ruled.get(concept_id)
    if name:
        return name
    if domain in DOMAIN_RELATIONS_FR:
        return "OBSTETRIC_RELATIONS" if domain == "obstetric" else "CHILD_RELATIONS"
    return "ALL_RELATIONS"


def build() -> list[dict]:
    ky = list(csv.DictReader(KY_BRIEF.open(encoding="utf-8")))
    anchors = {r["concept_id"]: r for r in csv.DictReader(ANCHORS.open(encoding="utf-8"))}
    v1 = v1_vocabulary()
    v1_french = ex_to_v1_french(v1)
    drafts = sheet_drafts()
    ruled = rulings()
    # A ruling made during a per-language pass, not yet in the Kinyarwanda
    # record. Applied here so the brief is correct, announced so it is not
    # forgotten. Same entry the English arm carries.
    for concept_id, name in PENDING_RULINGS.items():
        ruled[concept_id] = name
    drift = concept_drift()

    collapsed = collapsed_concepts(ky)
    absorbed_by = collapse_targets(ky, collapsed)
    out_of_generation = {"PR02", "OB13"}

    # Which person row a new concept's single draft belongs on. The drafts were
    # written before the person split and declare no person, so the row that
    # takes one is the row that applies.
    applies_first = {r["concept_id"]: r["applies"] != "no"
                     for r in ky if r["person"] == "first"}

    rows: list[dict] = []
    for src in ky:
        cid, person = src["concept_id"], src["person"]
        is_ex = cid.startswith("EX")
        anchor = anchors.get(cid, {})
        relation_set = relation_set_name(cid, src["domain"], person, ruled)
        row = {c: "" for c in COLUMNS}
        row.update(
            concept_id=cid,
            domain=src["domain"],
            proposed_urgency=src["proposed_urgency"],
            # The v1 phrases were catalogued with "(existing phrase - no concept
            # recorded)". They have no gloss and no anchor in any language, so
            # fidelity cannot be judged for them - only register can.
            english_gloss="" if is_ex else src["english_gloss"],
            anchor=anchor.get("anchor", ""),
            person=person,
            applies=src["applies"],
            person_note=src["person_note"],
            form="utterance",
            relation_set=relation_set,
        )

        notes: list[str] = []
        if src["applies"] == "no":
            notes.append("applies=no inherited from the Kinyarwanda brief")
        if src["hold"] == "yes":
            row["hold"] = "yes"
            notes.append("HOLD INHERITED from Kinyarwanda — lift it here if the "
                         "reason is Kinyarwanda wording rather than the concept")
        if src["needs_clinician"].strip():
            row["needs_clinician"] = "INHERITED — restate in French terms during the domain pass"

        candidate, origin, note = "", "", ""
        if cid in collapsed or cid in out_of_generation:
            drafted = drafts.get(cid)
            absorbed = v1_french.get(cid, "") if is_ex else ""
            # Record the drop once, on the row the candidate would have gone to,
            # rather than twice per concept.
            carries = (person == "first") if is_ex else (
                (person == "first") == applies_first.get(cid, True))
            if carries and (drafted or absorbed):
                origin = "dropped"
                why = (f"collapsed into {absorbed_by.get(cid, 'another concept')}"
                       if cid in collapsed
                       else "out of generation")
                text = drafted[0] if drafted else absorbed
                label = f"draft {drafted[1]}" if drafted else "v1 French"
                note = (f"{label} dropped ({why}): {text!r}. "
                        "Recorded so the drop is visible, not silent.")
        elif is_ex:
            if person == "first":
                candidate = v1_french.get(cid, "")
                origin = "v1_corpus" if candidate else ""
                if not candidate:
                    note = ("no v1 French phrase exists: EX31 is the row the speaker "
                            "ADDED to the first brief, so it has no counterpart in any "
                            "other language and French must be drafted from scratch.")
                else:
                    note = ("v1 corpus string at this position, carried as a CANDIDATE. "
                            "It is currently a noun_phrase rendered after a subject; as "
                            "an utterance it needs the subject folded in.")
                    row["verdict_fidelity"] = "unverified: concept identity"
                    row["suggestion_note"] = (
                        "The v1 phrases were catalogued as 'existing phrase - no concept "
                        "recorded', so there is no gloss to check this against. Confirm "
                        "the French still describes the same presentation the Kinyarwanda "
                        "row now describes before ruling on register."
                    )
                    if cid in drift:
                        overlap, original, rewrite = drift[cid]
                        row["suggestion_note"] = (
                            f"CONCEPT MAY HAVE MOVED (stem overlap {overlap}). The "
                            f"Kinyarwanda rewrite shares almost nothing with the v1 phrase "
                            f"this French came from: {original!r} -> {rewrite!r}. If the "
                            "concept moved, the French candidate is the wrong text for "
                            "this row and should be drafted fresh from the Kinyarwanda."
                        )
        else:
            drafted = drafts.get(cid)
            if drafted and (person == "first") == applies_first.get(cid, True):
                candidate, origin = drafted[0], "sheet_draft"
                note = (f"draft {drafted[1]} from phrase_review_sheet.csv, "
                        "Claude 2026-08-31, never reviewed")
                if person == "third":
                    note += (". Written in carer voice already; needs {REL} substituted "
                             "for the relation before it can expand.")

        row.update(suggested_french=candidate, candidate_origin=origin)
        if person == "first":
            for gone, keeper in sorted(absorbed_by.items()):
                if keeper != cid:
                    continue
                text = v1_french.get(gone, "") or (drafts.get(gone) or ("",))[0]
                if text:
                    notes.append(
                        f"{gone} collapsed into this concept. Its French text was "
                        f"{text!r} — consider it for second_phrasing_optional rather "
                        "than letting it drop, where the Kinyarwanda kept both wordings."
                    )
        if origin in ("v1_corpus", "sheet_draft"):
            row["confidence"] = "unreviewed"
        if note:
            notes.append(note)
        row["notes"] = " | ".join(notes)
        rows.append(row)
    scope = obstetric_scope(rows)
    for row in rows:
        row["agreement_check"] = " ; ".join(
            agreement_risks(row["suggested_french"], scope[row["concept_id"]]))
    return rows


def merge(fresh: list[dict], existing: list[dict]) -> tuple[list[dict], list[str]]:
    """Refresh derived columns; preserve everything a reviewer may have touched."""
    by_key = {(r["concept_id"], r["person"]): r for r in existing}
    scope = obstetric_scope(fresh)
    drift: list[str] = []
    for row in fresh:
        old = by_key.get((row["concept_id"], row["person"]))
        if old is None:
            continue
        for column in COLUMNS:
            # `agreement_check` is derived from `suggested_french`, which is a
            # PRESERVED column, so it cannot be compared against the fresh build
            # here: the fresh build still holds the sheet-draft candidate the
            # reviewer has since replaced, and comparing to that reports drift on
            # every redrafted row. Handled after the copy instead.
            if column == "agreement_check":
                continue
            if column in REGENERATED:
                if old.get(column, "") != row[column]:
                    drift.append(f"{row['concept_id']} {row['person']} {column}: "
                                 f"{old.get(column, '')!r} -> {row[column]!r}")
            elif column not in ("concept_id", "person"):
                row[column] = old.get(column, row[column])
        expected = " ; ".join(
            agreement_risks(row["suggested_french"], scope[row["concept_id"]]))
        if old.get("agreement_check", "") != expected:
            drift.append(f"{row['concept_id']} {row['person']} agreement_check: "
                         f"{old.get('agreement_check', '')!r} -> {expected!r}")
        row["agreement_check"] = expected
    return fresh, drift


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="Report drift in derived columns without writing.")
    args = ap.parse_args()

    rows = build()
    concepts = len({r["concept_id"] for r in rows})
    if (len(rows), concepts) != (256, 128):
        raise SystemExit(
            f"expected 256 rows on the 128-concept spine, built {len(rows)} rows "
            f"over {concepts} concepts. The spine moved; re-read it before writing."
        )

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
    filled = sum(1 for r in rows if r["suggested_french"].strip())
    ruled_rows = sum(1 for r in rows if r["your_phrasing"].strip())
    risky = sum(1 for r in rows if r["agreement_check"].strip())
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} rows over {concepts} concepts")
    print(f"  {filled} carry a candidate, {ruled_rows} are ruled")
    print(f"  {risky} carry an FR-1 agreement risk")
    for d in drift:
        print(f"  refreshed {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
