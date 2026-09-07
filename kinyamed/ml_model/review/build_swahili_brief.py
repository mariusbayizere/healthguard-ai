#!/usr/bin/env python
"""Build `review/speaker_brief_swahili_v2.csv` off the 128-concept spine.

A Kiswahili speaker has agreed to author the Swahili arm, so this is an
**AUTHORING brief, not a review brief** — the one structural difference from
`build_french_brief.py`, and the difference every other decision here follows
from.

NO SWAHILI TEXT IS PRODUCED, CARRIED OR SUGGESTED BY THIS SCRIPT
----------------------------------------------------------------
Not a draft, not the v1 corpus string, not a candidate column. The Kinyarwanda
arm's finding is that a fluent draft anchors a speaker to its errors — it is
why Kinyarwanda came out speaker-authored and English did not — and
`docs/phrasing-guide.md` states the remedy the speaker themselves gave:

    "Write your own, do not edit mine. Editing anchors you to my structure,
     which is the defect. The brief has the English gloss precisely so you can
     work from the clinical meaning rather than from my sentence."

Enforced, not asserted: `assert_no_swahili()` searches every generated cell for
every v1 Swahili string and refuses to write if one appears. "I did not write
any Swahili" is exactly the kind of claim that is true when the code is written
and false three edits later.

`dataset/vocabulary_v1.py` DOES hold 46 machine-translated Swahili strings, and
`review/speaker_brief_swahili.csv` (v1) shows them. They are deliberately not
brought here. They are not lost: v1 is frozen, and they can be compared against
the authored phrases AFTERWARDS, which is the only order in which the comparison
means anything.

FIVE DIFFERENCES FROM THE FRENCH BUILDER, ALL DELIBERATE
--------------------------------------------------------
1. **No candidate column, no verdict columns, no confidence.** A review brief
   rules on text that exists. Nothing exists here yet. `suggested_*`,
   `candidate_origin`, `verdict_fidelity`, `verdict_register`, `rw_*_check` and
   `agreement_check` all have nothing to hold and are not emitted.

2. **`english_gloss` is filled for the 47 EX concepts**, which the French and
   English briefs leave empty. A reviewer with a French candidate in front of
   them can work without a gloss; an author with an empty gloss has nothing to
   write from, and 47 of 128 concepts would be unauthorable. Source and the
   seven declared corrections are in `EX_GLOSS` below.

3. **Every ruling is restated in plain English**, not inherited verbatim. The
   spine's `person_note` and `needs_clinician` cells name Kinyarwanda words,
   `walk.py`, `routine_relation_sets.csv` and dated session rulings. The speaker
   works in a spreadsheet with no repository, so a note they cannot act on is a
   note that is not there. Every restatement is DECLARED in a map below and an
   undeclared value raises — a silent pass-through of repo jargon is the failure
   this guards.

4. **`relation_set_members` spells the set out in English.** A named set is
   meaningless without its members, and the author has to test one sentence
   against all of them (phrasing guide, Part 1 rule 2). The English wording is
   `english_relations.py`'s, which is v1's own SUBJECTS wording, not a fresh
   translation. NOTE THE GAP THIS EXPOSES: `RELATIONS` in `vocabulary_v1.py` has
   a `kinyarwanda` key and nothing else, so no Swahili relation terms exist
   anywhere in the project. They are asked for in the companion sheet — see
   `speaker_brief_swahili_v2_relations.csv`.

5. **`keep_distinct_from` is new.** `review/kinyarwanda-phrase-group-collisions.md`
   measured five phrase groups holding eleven concepts, and the cause was the
   speaker authoring a fuller version of a phrase they had already written. That
   cause is not Kinyarwanda-specific; it will reproduce in Swahili unless the
   author is told which concepts are near neighbours WHILE writing. Cheaper to
   warn than to reword afterwards, which is what the Kinyarwanda arm had to do.

WHAT IS CARRIED FROM THE SPINE UNCHANGED
----------------------------------------
`applies`, the person split, `hold`, `needs_clinician` and the relation-set
rulings are language-independent and are carried, exactly as the French arm
carried them. Eleven holds are lifted — the same eleven the English and French
arms independently lifted, because each is a block on a Kinyarwanda WORD and not
on the concept. See `LIFTED_HOLDS`.

RE-RUNNING
----------
Idempotent and non-destructive. `REGENERATED` columns are recomputed every run;
the author's four columns are preserved once written, so a half-authored brief
survives a rebuild. `--check` reports drift without writing.

    python review/build_swahili_brief.py            # build or refresh
    python review/build_swahili_brief.py --check    # drift only, no write

`dataset/` is read-only here and is never written.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from english_relations import (ALL_RELATIONS, CHILD_RELATIONS_EN,  # noqa: E402
                               HOUSEHOLD_RELATIONS_EN, ADULT_RELATIONS_EN,
                               DOMAIN_RELATIONS_EN, NO_RELATIONS_EN,
                               OBSTETRIC_RELATIONS_NO_MOTHER, PENDING_RULINGS)
from relation_sets import rulings  # noqa: E402
from walk import save  # noqa: E402  - reuse the one atomic writer, not a second one

SPINE = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"
SPINE_V1 = ROOT / "review" / "speaker_brief_kinyarwanda.csv"
ANCHORS = ROOT / "review" / "concept_anchors.csv"
OUT = ROOT / "review" / "speaker_brief_swahili_v2.csv"
RELATIONS_OUT = ROOT / "review" / "speaker_brief_swahili_v2_relations.csv"

# The frozen v1 corpus. Committed at e492890, so it is read as a file rather than
# through `git show` the way `build_french_brief.py` had to: HEAD's
# `dataset/vocabulary.py` is now the v2 Kinyarwanda-only rewrite and no longer
# has an `english` key at all. Read-only, and only its ENGLISH is read.
V1 = ROOT / "dataset" / "vocabulary_v1.py"

COLUMNS = [
    "concept_id", "domain", "proposed_urgency", "english_gloss",
    "person", "person_note", "applies", "action",
    "relation_set", "relation_set_members", "keep_distinct_from",
    "hold", "needs_clinician", "brief_notes",
    "your_phrasing", "second_phrasing_optional", "regional_variant", "your_notes",
]

# The author's four columns. Everything else is derived and is recomputed on
# every run. `your_notes` is theirs and `brief_notes` is mine; the two are named
# apart because the v1 brief's single `notes` column had to serve both and it
# was never clear which cell belonged to whom.
AUTHORED = ["your_phrasing", "second_phrasing_optional", "regional_variant", "your_notes"]
REGENERATED = [c for c in COLUMNS if c not in AUTHORED
               and c not in ("concept_id", "person")]

NAMED_MEMBERS: dict[str, tuple[str, ...]] = {
    "ALL_RELATIONS": ALL_RELATIONS,
    "ADULT_RELATIONS": ADULT_RELATIONS_EN,
    "CHILD_RELATIONS": CHILD_RELATIONS_EN,
    "HOUSEHOLD_RELATIONS": HOUSEHOLD_RELATIONS_EN,
    "OBSTETRIC_RELATIONS": DOMAIN_RELATIONS_EN["obstetric"],
    "OBSTETRIC_RELATIONS_NO_MOTHER": OBSTETRIC_RELATIONS_NO_MOTHER,
    "NO_RELATIONS": NO_RELATIONS_EN,
}


# ---------------------------------------------------------------------------
# DECLARED RESTATEMENTS
#
# Each map below turns a spine cell written for the Kinyarwanda session into
# something a Kiswahili speaker with no repository can act on. Every one of them
# raises on an undeclared value rather than passing the original through: the
# whole point of the brief is that the speaker never has to guess what a note
# means, and a note referring to `walk.py` or to a Kinyarwanda word would fail
# that silently.
# ---------------------------------------------------------------------------

# Spine `person_note` -> what it means for someone writing Swahili.
# Keyed on the exact spine string so a reworded note fails loudly.
PERSON_NOTE = {
    "": "",
    "first = the pregnant woman; third = husband, mother or neighbour reporting":
        "First person is the pregnant woman herself. Third person is someone "
        "else reporting for her — her husband, her mother, a neighbour.",
    "usually third (the parent speaks); write first only if an older child would say it":
        "Usually the parent speaks, so the third person is the main row. Write "
        "the first person only if an older child would plausibly say it about "
        "themselves.",
    "usually third (the parent speaks); an older child would say it; the parent's "
    "version is the third person":
        "Usually the parent speaks. An older child could say the first person "
        "about themselves; the parent's version is the third person.",
    "usually third (the parent speaks); the parent speaks":
        "The parent speaks. The third person is the parent's report.",
    "applies=no 2026-09-03, rule 11: an unconscious patient cannot report. Same "
    "ground on which NE02 first was already applies=no — which was itself part of "
    "the evidence the two were one concept.":
        "No first person: an unconscious patient cannot report their own "
        "unconsciousness. Third person only.",
    "applies=no 2026-09-03, rule 11: a convulsing patient cannot report. Same "
    "ground on which NE01 first was already applies=no — which was itself part of "
    "the evidence the two were one concept.":
        "No first person: a convulsing patient cannot report it while it is "
        "happening. Third person only.",
    "applies=no 2026-09-04. Ruled NO_RELATIONS in routine_relation_sets.csv — "
    "nobody presents on another's behalf for a refill or a routine review — so no "
    "third person exists. Left open it would have been offered for authoring by "
    "walk.py, producing a row that cannot generate: the PR02 failure shape, a "
    "ruling recorded where no code path reads it. The first-person row is "
    "untouched; NO_RELATIONS is a restriction, not a deletion.":
        "No third person: nobody comes in on someone else's behalf to collect a "
        "repeat prescription or attend their own routine review. First person "
        "only — that row is unaffected.",
    "applies=no 2026-09-04. Ruled NO_RELATIONS — adult self-service, nobody "
    "presents on another's behalf. Same principle as the chronic_care five: "
    "leaving it open has walk.py offer a row that cannot generate. PR06 "
    "additionally settled a stale handover line that had said 'adult relations'. "
    "First person untouched.":
        "No third person: an adult asks for this service for themselves and "
        "nobody asks on their behalf. First person only — that row is unaffected.",
}

# Concept -> why one person is `applies=no`, where the spine's reason is a
# per-concept ruling rather than one of the standing rules above.
APPLIES_NO_REASON = {
    ("GI04", "first"):
        "Ruled out: dehydration here is judged by a skin pinch, which is an "
        "examination the health worker performs. A patient cannot report it "
        "about themselves. The third person (a carer describing the child) "
        "stands.",
    ("PA02", "first"):
        "Ruled out: an infant too weak to breastfeed cannot speak at all.",
    ("PA03", "first"):
        "Ruled out: an unconscious or floppy child cannot speak for themselves.",
    ("PA04", "first"):
        "Ruled out: a child in severe respiratory distress cannot speak for "
        "themselves.",
    ("PA05", "first"):
        "Ruled out: sunken eyes is a sign someone else observes, and without it "
        "the concept collapses into ordinary diarrhoea.",
    ("PA07", "first"):
        "Ruled out: 'not gaining weight' is read off a growth chart, not "
        "something a child reports; what is left overlaps the adult weight-loss "
        "concept.",
    ("EX40", "first"): None,   # standing paediatric-duplicate rule, text below
    ("EX41", "first"): None,
    ("EX43", "first"): None,
}

PAEDIATRIC_DUPLICATE = (
    "Ruled out under a standing rule: a child saying 'I have a fever and a rash' "
    "IS the adult concept — the fact that the patient is a child lives only in "
    "the relation word, and the first person has no slot for it. So the "
    "first-person row would duplicate an adult concept and is dropped rather "
    "than written twice."
)

# Holds lifted for this arm. Each is a block on a KINYARWANDA WORD, not on the
# concept, so it cannot bind a language that may simply have the word. The
# English and French arms lifted exactly this set independently of each other;
# two arms agreeing is the strongest evidence available that the lifts are right.
# Verified against `speaker_brief_french_v2.csv` by `check_lifts_match_french()`.
LIFTED_HOLDS = {
    ("CR05", "third"): "the Kinyarwanda hold is on whether 'ijwi ridasanzwe' "
                       "(an unusual sound) maps to wheeze — a question about a "
                       "Kinyarwanda word. See QUESTION 1.",
    ("EX27", "third"): "the Kinyarwanda hold is on inflecting one verb for a "
                       "third person, which is a Kinyarwanda grammar question.",
    ("GI03", "third"): "the Kinyarwanda hold is the missing stool noun. See "
                       "QUESTION 2.",
    ("IF01", "first"): "the Kinyarwanda hold is on one unvalidated word for a "
                       "stiff neck.",
    ("IF01", "third"): "held only because the Kinyarwanda first person was.",
    ("IF03", "first"): "the Kinyarwanda hold is on the wording of 'unable to "
                       "drink', not on the concept.",
    ("IF03", "third"): "held only because the Kinyarwanda first person was.",
    ("IF04", "first"): "the Kinyarwanda hold is on one unvalidated word for "
                       "sweating.",
    ("IF04", "third"): "held only because the Kinyarwanda first person was.",
    ("IF06", "first"): "the Kinyarwanda hold is on the register of one phrase "
                       "for painful urination.",
    ("IF06", "third"): "held only because the Kinyarwanda first person was.",
    ("OB12", "third"): "held on a relation question, which the "
                       "OBSTETRIC_RELATIONS_NO_MOTHER ruling has since settled.",
}

# A hold this arm ADDS that the spine does not carry. Carried across from the
# French arm, which carried it from the English arm, because it is a claim about
# the concept rather than about any language.
ADDED_HOLDS = {
    ("NE06", "first"):
        "Whether a patient who can accurately report their own new confusion is "
        "meaningfully confused is a clinical question, not a language one. Both "
        "the English and French arms hold this row; do not write it.",
}

# Why a held row is held, in terms that do not require the repository. Only the
# rows that stay held after `LIFTED_HOLDS` need an entry.
HOLD_REASON = {
    "CR04": "Held for a clinician: the two available ways of describing lower "
            "chest indrawing are not the same description, and choosing between "
            "them is a clinical call.",
    "CC01": "Held for a clinician: whether a patient in diabetic ketoacidosis "
            "can still report their own drowsiness and deep breathing.",
    "CC02": "Held for a clinician: whether a patient with hypoglycaemic "
            "confusion can report it.",
    "HT03": "Held for a clinician: whether a patient concussed enough to be "
            "confused and vomiting can give this account themselves.",
    "OB06": "Held for a clinician, and the concept itself is open. This is "
            "FETAL DEMISE — the baby has died in the womb — not reduced "
            "movement. Two questions are outstanding: whether it should be "
            "CRITICAL, and whether a presentation where no intervention follows "
            "belongs in a triage taxonomy at all. Do not write a phrase for it.",
    "OB13": "Out of generation, held. This is 'reduced fetal movement', opened "
            "when OB06 was re-ruled to fetal demise. The Kinyarwanda speaker "
            "reports no natural Kinyarwanda phrase says it, and whether the "
            "concept should exist at all is an open clinical question. Do not "
            "write a phrase for it. (If Kiswahili DOES have a natural way to say "
            "it, that is useful evidence — put it in your_notes, not in "
            "your_phrasing.)",
    "PR02": "Out of generation, held: whether men present for family-planning "
            "advice is a Rwandan service-design question nobody has answered. "
            "Do not write a phrase for it.",
    "NE06": ADDED_HOLDS[("NE06", "first")],
}


# Concept -> (does the flag transfer to another language?, the question in plain
# English). A `needs_clinician` flag on the spine is sometimes a clinical
# question about the CONCEPT, which every language inherits, and sometimes a
# doubt about one Kinyarwanda WORD, which no other language inherits. Carrying
# both kinds identically — which is what "INHERITED, restate later" does — asks
# a Kiswahili speaker to worry about a Kinyarwanda word.
CLINICIAN: dict[str, tuple[bool, str]] = {
    "CR04": (True, "For a clinician: lower chest indrawing can be described as "
                   "the chest sinking, or as the area under the ribs being "
                   "pulled in. They are not the same description and the choice "
                   "has not been made. This row is held."),
    # CR05 and PA08 carry their whole question in QUESTIONS, so the note here
    # would only repeat it. Kept in the map because the spine flag still has to
    # be classified: silence and "not classified" must stay distinguishable.
    "CR05": (True, ""),
    "CC01": (True, "For a clinician: can a patient this ill still report their "
                   "own drowsiness and deep breathing? This row is held."),
    "CC02": (True, "For a clinician: can a patient with low blood sugar report "
                   "their own confusion? This row is held."),
    "HT03": (True, "For a clinician: can a patient concussed enough to be "
                   "vomiting and confused give this account? This row is held."),
    "HT05": (True, "AXIS, AND IT MATTERS FOR THE WORDING. The concept is a limb "
                   "that is BENT OR OUT OF SHAPE after a fall — what the patient "
                   "can see — and NOT a fracture, which is a diagnosis. The "
                   "Kinyarwanda arm was blocked here for days because only "
                   "fracture vocabulary was attested; the speaker settled it by "
                   "saying the leg is bent AND adding 'but I do not think it is "
                   "broken' inside the sentence. If Kiswahili has an ordinary "
                   "way to say a limb is bent out of shape, use it. If the only "
                   "natural words are fracture words, say so in your_notes "
                   "rather than writing a phrase that claims a fracture."),
    "EX27": (False, "The Kinyarwanda flag is about inflecting one verb for "
                    "another person. It does not transfer."),
    "IF01": (False, "The Kinyarwanda flag is about one unvalidated word for a "
                    "stiff neck. It does not transfer — but the sign is a "
                    "danger sign, so keep the neck explicit."),
    "IF03": (False, "The Kinyarwanda flag is about wording. It does not "
                    "transfer — but this is an emergency danger sign (unable to "
                    "drink or breastfeed), so keep it precise and do not soften "
                    "it to 'not eating'."),
    "IF04": (False, "The Kinyarwanda flag is about one unvalidated word for "
                    "sweating. It does not transfer."),
    "IF06": (False, "The Kinyarwanda flag is about the register of one phrase "
                    "for painful urination. It does not transfer — though the "
                    "same register question may arise in Kiswahili, and if it "
                    "does, say so."),
    "NE04": (False, "Moot: this concept was collapsed and both persons are "
                    "applies=no."),
    "NE05": (True, "OPEN QUESTION ABOUT THE CONCEPT, not about a language. The "
                   "gloss names vomiting and the Kinyarwanda phrase does not; "
                   "the Kinyarwanda also frames the light as the CAUSE of the "
                   "headache rather than as something that hurts the eyes, and "
                   "the speaker says the causal framing is the natural one. "
                   "Write what is natural in Kiswahili and say in your_notes "
                   "which of the three signs your sentence actually carries."),
    "NE06": (True, "For a clinician: is a patient who can accurately report "
                   "their own new confusion meaningfully confused? This row is "
                   "held."),
    "OB03": (True, "For a clinician: this is a specific obstetric emergency "
                   "(the cord or a hand appearing before the baby). Nothing "
                   "generates from this row until a clinician validates the "
                   "wording, so write it if you can and expect it to be checked."),
    "OB05": (True, "For a clinician: the description of infected discharge "
                   "after delivery needs clinical confirmation."),
    "OB06": (True, HOLD_REASON["OB06"]),
    "OB13": (True, HOLD_REASON["OB13"]),
    "EX43": (True, "For a clinician: is 'high fever and refusing to eat' URGENT, "
                   "or is refusal to eat in a feverish child close enough to the "
                   "'unable to drink' danger sign to be CRITICAL? Nothing about "
                   "the wording changes while that is open — write the URGENT "
                   "version."),
    "PA08": (True, ""),
}

# ---------------------------------------------------------------------------
# THE THREE OPEN QUESTIONS
#
# Named by the requester, and they are the same three in both other arms:
# `review/rwandan-english-questions.md` closes by saying CR05, GI05 and PA08 are
# "the concepts whose vocabulary nobody has been able to settle in either
# language, and they should go to the same person at the same time."
#
# GI03 is included with GI05 because it is the same missing noun and it is the
# one that CANNOT be routed around: GI05 was written using the diarrhoea word,
# and melaena needs the noun itself.
#
# A Kiswahili answer here is EVIDENCE for the other two arms, not a ruling on
# them. Kiswahili having a word does not tell anyone what Kinyarwanda does.
# ---------------------------------------------------------------------------
QUESTIONS: dict[str, str] = {
    "CR05": (
        "QUESTION 1 OF 3 — WHEEZE. Kinyarwanda and English are both stuck on the "
        "same thing. The Kinyarwanda draft says 'an unusual sound', which a "
        "clinician says is not specifically wheeze; the English says 'a "
        "whistling sound', which is the standard lay description in British and "
        "American English and which nobody can confirm a Rwandan patient would "
        "reach for. WHAT WE ARE ASKING: is there an ordinary, non-clinical "
        "Kiswahili way a patient describes the sound of wheeze? If there is no "
        "such expression and patients describe this some other way — the chest "
        "being tight, breathing being hard, imitating the sound — write what "
        "they ACTUALLY say and tell us in your_notes what you had to leave out."
    ),
    "GI03": (
        "QUESTION 2 OF 3 — A WORD FOR STOOL (this row and GI05). The Kinyarwanda "
        "arm is blocked on the NOUN: no word for stool appears in the speaker's "
        "phrases, in the v1 corpus or in any source material found, and the one "
        "candidate is still out with two contacts because it may mean only the "
        "latrine. GI05 (blood in the stool) was routed around by using the "
        "diarrhoea word instead; THIS row cannot be routed around, because black "
        "tarry stool needs the noun. English has the parallel doubt: is 'stool' "
        "a patient's word or a health worker's? WHAT WE ARE ASKING: what does a "
        "patient actually call it in Kiswahili? Is there more than one word, and "
        "does the choice change with politeness, with who is listening, or with "
        "region? And for this row specifically: is there a natural way to say "
        "the stool is black, without medical vocabulary?"
    ),
    "GI05": (
        "QUESTION 2 OF 3 — A WORD FOR STOOL (this row and GI03). See GI03 for "
        "the full question. This is the row the Kinyarwanda arm routed around by "
        "using the word for diarrhoea rather than a noun for stool. If Kiswahili "
        "lets you say it directly, say it directly, and note in your_notes "
        "whether you used a stool word or went around it the same way."
    ),
    "PA08": (
        "QUESTION 3 OF 3 — EAR DISCHARGE. The Kinyarwanda phrase names a "
        "CONDITION and states neither the pain nor the discharge the gloss asks "
        "for, and nobody knows whether that word means acute middle-ear "
        "infection specifically or any ear complaint at all. English has the "
        "same doubt: is the ordinary phrase that the ear is 'discharging', or "
        "that 'water' is coming out? WHAT WE ARE ASKING: how does a parent say "
        "in Kiswahili that a child's ear is running? Is the natural phrase one "
        "that NAMES the illness, or one that DESCRIBES the signs? Both are "
        "useful — write the natural one and tell us in your_notes which kind it "
        "is."
    ),
}


# ---------------------------------------------------------------------------
# EX GLOSSES
#
# The spine's `english_gloss` for the 47 EX concepts is the placeholder
# "existing concept — your first-pass phrasing is on one of these two rows",
# which points at Kinyarwanda text. Useless to a reviewer, and fatal to an
# author: it is 47 of 128 concepts with nothing to write from.
#
# The gloss is taken from the FROZEN v1 ENGLISH at the same corpus position.
# That text is the right register for the job — v1 English is a noun-phrase
# description of a presentation, not a patient utterance, so it says what the
# concept IS without modelling how to say it. It is also frozen, so it cannot
# drift.
#
# THE POSITIONAL MAPPING IS NOT A GUARANTEE OF CONCEPT IDENTITY. An EX id names
# the slot a v1 phrase occupied, and the Kinyarwanda speaker was rewriting for
# naturalness, not holding the concept fixed. `docs/ex-concept-drift.md` records
# three ids whose concepts rotated. Each override below is one of those, with
# the record that establishes it.
# ---------------------------------------------------------------------------
EX_GLOSS_OVERRIDE: dict[str, tuple[str, str]] = {
    "EX04": (
        "difficulty breathing, with the lips changing colour",
        "v1 English says 'lips turning blue'. The speaker's Kinyarwanda now says "
        "the lips changed COLOUR in both persons, and the English arm dropped "
        "'blue' deliberately: CR03 IS the blue-lips concept, and 'blue' was the "
        "only word separating the two.",
    ),
    "EX15": (
        "vomiting a lot and feeling very weak",
        "v1 English says 'signs of dehydration'. The speaker's rewrite says "
        "vomiting and weakness. Dehydration signs belong to GI04, and carrying "
        "the v1 wording here would put a second concept on this id.",
    ),
    "EX27": (
        "fever with chills, and the patient thinks it is malaria",
        "v1 English says 'fever and aching all over', which the speaker's "
        "rewrite does not say — it says fever, chills and a suspicion of "
        "malaria. Recorded in docs/ex-concept-drift.md.",
    ),
    "EX29": (
        "a mild fever for one day, with nothing else wrong",
        "v1 English says 'a mild cough with no fever' — the OPPOSITE sign. Three "
        "concepts rotated across three ids in the rewrite: v1 EX29's cough is "
        "now CR07's, v1 EX30's runny nose is now EX31's, and this id took the "
        "mild-fever-no-danger-sign concept that IF07 used to hold. "
        "docs/ex-concept-drift.md, re-examined 2026-09-04.",
    ),
    "EX31": (
        "a slightly runny nose",
        "This row was ADDED by the Kinyarwanda speaker and has no v1 position in "
        "any language, so there is no v1 English to take. Its concept is the one "
        "that arrived here when three concepts rotated across three ids in the "
        "rewrite — see EX29 and EX30.",
    ),
}

# Collapsed EX ids whose v1 English gloss is kept but is no longer where the
# concept went. Both are `applies=no` in both persons, so nothing is authored
# from them; the note exists so the rotation is visible rather than silent.
EX_ROTATED_AWAY = {
    "EX17": "Its wording was not thrown away: it survives as EX16's second phrasing.",
    "EX30": "Its Kinyarwanda rewrite ('I cough a little but have no fever') is the "
            "phrase CR07 now carries — the concept moved, it was not deleted.",
}

# ---------------------------------------------------------------------------
# NEAR NEIGHBOURS
#
# From `review/kinyarwanda-phrase-group-collisions.md` (five groups, eleven
# concepts, closed 2026-09-05 by one collapse and four rewordings) plus the two
# axes recorded elsewhere in the spine. Every entry names a pair of LIVE
# concepts whose meanings are close enough that one natural sentence could serve
# both — at which point the evaluation can no longer separate them.
#
# The finding the collisions document ends on: three of the five had one cause,
# a short phrase being the opening clause of a longer phrase that specialises
# it. That cause is not Kinyarwanda-specific. Warning while the author writes
# costs nothing; the Kinyarwanda arm had to reword afterwards.
# ---------------------------------------------------------------------------
KEEP_DISTINCT: dict[str, str] = {
    "CR02": "EX02 (serious difficulty breathing — CR02 is worse: cannot finish a sentence)",
    "EX02": "CR02 (too breathless to finish a sentence) and EX04 (which adds the lips)",
    "EX04": "EX02 (breathing trouble alone) and CR03 (which IS the blue-lips concept)",
    "CR03": "EX04 (breathing trouble with lips changing colour)",
    "CR01": "EX05 — CR01 is the JAW (or jaw and arm), EX05 is the ARM only. This is "
            "the one concept pair in the corpus with a recorded axis; keep the two "
            "sentences from containing one another.",
    "EX05": "CR01 — EX05 is the ARM only, CR01 carries the jaw.",
    "EX14": "GI07 (pain that will not settle) and EX38 (pain in pregnancy, with bleeding)",
    "GI07": "EX14 (plain severe belly pain) — the axis is that GI07's does not settle",
    "EX38": "EX14 (plain severe belly pain) — EX38 is in pregnancy and bleeding",
    "EX09": "CC03 (high blood pressure WITH headache) — EX09 is the reading alone",
    "CC03": "EX09 (the high reading alone) — CC03 adds the headache",
    "EX18": "EX20 — EX18 is bleeding that will not stop, EX20 is specifically the NOSE",
    "EX20": "EX18 (heavy bleeding, site unspecified) — EX20 must name the nose",
    "EX10": "CC08 (a blood-pressure medicine refill) — EX10 is any repeat prescription",
    "CC08": "EX10 (any repeat prescription) — CC08 names the blood-pressure medicine",
    "CR07": "EX29 (mild fever, nothing else) and EX31 (a slightly runny nose)",
    "EX29": "CR07 (a mild cough, no fever) and EX31 (a runny nose)",
    "EX31": "CR07 (mild cough) and EX29 (mild fever)",
    "IF02": "EX33 (convulsing, no temperature named) and EX40 (convulsing with a "
            "fever above 40)",
    "EX33": "IF02 (fever with convulsions) and EX40 (fever above 40) — EX33 is the "
            "plain convulsion, and it must NOT be conditioned on a temperature",
    "EX40": "IF02 and EX33 — EX40 is the one that names 40 degrees",
    "EX12": "GI04 (severe diarrhoea WITH dehydration) — EX12 is three days of it",
    "GI04": "EX12 (severe diarrhoea for three days) — GI04 adds the dehydration",
    "PR05": "OB11 — PR05 is a FIRST booking, OB11 is a routine check. These two are "
            "one character from being merged in the Kinyarwanda measurement; keep "
            "the two Kiswahili sentences clearly different from the start.",
    "OB11": "PR05 — OB11 is a routine antenatal check, PR05 is the first booking.",
    "EX26": "EX27 — both are fever with chills, and EX27 adds that the patient "
            "suspects malaria. Whether these are one concept is UNRESOLVED (see "
            "brief_notes on EX27); write them so they do not become one sentence.",
    "EX27": "EX26 (malaria symptoms: fever and chills) — EX27 adds the patient's "
            "own suspicion. Their collapse is unresolved.",
}


# The standing instruction every third-person row needs, and the single most
# common error in the Kinyarwanda arm. Repeated per row on purpose: the author
# works in a spreadsheet, one row at a time, and a rule stated once in a
# covering document is a rule read once.
THIRD_PERSON_RULE = (
    "Write the five characters {REL} where the relation word goes. Make {REL} the "
    "GRAMMATICAL SUBJECT of the sentence, and check your sentence still reads "
    "naturally for every relation listed in relation_set_members. Never mix "
    "first and third person inside one sentence."
)

FIRST_PERSON_RULE = (
    "First person: the patient's own words about themselves. No {REL} in this row."
)


def v1_vocabulary():
    """Import the frozen v1 corpus, read-only. Only its ENGLISH is read here.

    `build_french_brief.py` reads this through `git show` because at the time
    the only copy was in a commit. It is now committed as `vocabulary_v1.py`
    (e492890) and HEAD's `dataset/vocabulary.py` is the v2 Kinyarwanda-only
    rewrite with no `english` key at all, so the file is the source and the git
    detour is gone.
    """
    spec = importlib.util.spec_from_file_location("_v1_vocabulary", V1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for language in ("kinyarwanda", "english"):
        if language not in module.SYMPTOMS:
            raise SystemExit(
                f"{V1} has no {language} symptoms. The frozen v1 is the only source "
                "of the EX glosses; if it has lost a language, stop and find the "
                "commit that still has it rather than writing glosses over the gap."
            )
    return module


def ex_to_v1_english(v1) -> dict[str, str]:
    """EX concept id -> the ENGLISH v1 phrase at the same corpus position.

    EX ids were assigned in the order of the 47 `VALIDATE existing` rows of the
    first Kinyarwanda brief, and `SYMPTOMS` is index-parallel across all four
    languages. Both facts are asserted rather than trusted, exactly as
    `build_french_brief.ex_to_v1_french` does.
    """
    where: dict[str, tuple[str, str, int]] = {}
    for urgency, domains in v1.SYMPTOMS["kinyarwanda"].items():
        for domain, phrases in domains.items():
            for i, phrase in enumerate(phrases):
                where[phrase] = (urgency, domain, i)

    existing = [r for r in csv.DictReader(SPINE_V1.open(encoding="utf-8"))
                if r["task"] == "VALIDATE existing"]
    ex_ids = [r["concept_id"] for r in csv.DictReader(SPINE.open(encoding="utf-8"))
              if r["person"] == "first" and r["concept_id"].startswith("EX")]
    if len(existing) != len(ex_ids):
        raise SystemExit(
            f"{len(ex_ids)} EX ids but {len(existing)} existing rows in the first "
            "brief. The positional mapping EX id -> v1 phrase is what gives 47 "
            "concepts their only English gloss; it must not be guessed."
        )

    spine = {(r["concept_id"], r["person"]): r
             for r in csv.DictReader(SPINE.open(encoding="utf-8"))}
    out: dict[str, str] = {}
    for ex_id, row in zip(ex_ids, existing):
        ky = row["original_corpus_phrase"].strip()
        if not ky:
            out[ex_id] = ""          # EX31: speaker-added, no v1 row in any language
            continue
        if ky not in where:
            raise SystemExit(
                f"{ex_id}: v1 phrase {ky!r} is not in {V1}. The frozen v1 is supposed "
                "to be byte-identical; if it is not, that outranks anything this "
                "brief is doing."
            )
        urgency, domain, i = where[ky]
        brief_row = spine[(ex_id, "first")]
        if (brief_row["domain"], brief_row["proposed_urgency"]) != (domain, urgency):
            raise SystemExit(
                f"{ex_id}: spine says {brief_row['domain']}/{brief_row['proposed_urgency']}, "
                f"v1 position says {domain}/{urgency}. The EX ordering assumption is "
                "wrong; stop and re-derive it before any gloss is attached to a concept."
            )
        out[ex_id] = v1.SYMPTOMS["english"][urgency][domain][i]
    return out


def collapsed_concepts(spine: list[dict]) -> set[str]:
    """Concepts out of generation: both persons `applies=no`. Derived, not listed."""
    persons: dict[str, list[dict]] = defaultdict(list)
    for row in spine:
        persons[row["concept_id"]].append(row)
    return {cid for cid, rows in persons.items()
            if all(r["applies"] == "no" for r in rows)}


_COLLAPSE = re.compile(r"collapse\w*[^.]{0,80}?\binto\s+([A-Z]{2}\d{2})", re.IGNORECASE)

# The one collapse the spine's notes state in a form the pattern cannot read.
ABSORBED_BY_DECLARED = {"IF07": "EX29"}


def collapse_targets(spine: list[dict], collapsed: set[str]) -> dict[str, str]:
    """Collapsed concept -> the concept that absorbed it, from the spine's notes.

    An author looking at an `applies=no` row is entitled to know where the
    concept went, so they can check they have not written the same sentence
    twice. Parsed rather than transcribed; an unresolvable id raises.
    """
    blobs: dict[str, list[str]] = defaultdict(list)
    for row in spine:
        blobs[row["concept_id"]].extend(
            [row.get("notes", ""), row.get("person_note", "")])

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
            f"no collapse target recoverable for {unresolved}. Add the id to "
            "ABSORBED_BY_DECLARED with the ruling that names the target."
        )
    return out


def relation_ruling(concept_id: str, domain: str, ruled: dict[str, str]) -> str:
    """The named set a third person expands over. Names, not strings."""
    name = ruled.get(concept_id)
    if name:
        return name
    if domain in DOMAIN_RELATIONS_EN:
        return "OBSTETRIC_RELATIONS" if domain == "obstetric" else "CHILD_RELATIONS"
    return "ALL_RELATIONS"


def check_lifts_match_french() -> list[str]:
    """Every hold this arm lifts must be one the French arm lifted too.

    The lifts are not this arm's judgement — they are two independent arms
    having already reached the same conclusion, which is the whole reason for
    trusting them. If the French brief stops agreeing, that is a finding, not a
    detail: re-derive the lift rather than keeping it because it is written here.
    """
    french = ROOT / "review" / "speaker_brief_french_v2.csv"
    if not french.exists():
        return [f"{french.name} is missing; the lifts cannot be cross-checked"]
    fr = {(r["concept_id"], r["person"]): r
          for r in csv.DictReader(french.open(encoding="utf-8"))}
    spine = {(r["concept_id"], r["person"]): r
             for r in csv.DictReader(SPINE.open(encoding="utf-8"))}
    problems = []
    for key in sorted(LIFTED_HOLDS):
        if spine.get(key, {}).get("hold") != "yes":
            problems.append(f"{key} is not held on the spine; the lift is stale")
        elif fr.get(key, {}).get("hold") == "yes":
            problems.append(f"{key} is lifted here but still held in the French brief")
    for key, row in sorted(spine.items()):
        if row["hold"] == "yes" and key not in LIFTED_HOLDS \
                and fr.get(key, {}).get("hold") != "yes":
            problems.append(f"{key} is lifted in the French brief but held here")
    return problems


def restate_person_note(raw: str, concept_id: str, person: str) -> str:
    if raw not in PERSON_NOTE:
        raise SystemExit(
            f"{concept_id} {person}: person_note is not one of the declared "
            f"restatements:\n  {raw!r}\n"
            "Passing it through would put Kinyarwanda words and repository "
            "filenames in front of a Kiswahili speaker who has neither. Add the "
            "restatement to PERSON_NOTE."
        )
    return PERSON_NOTE[raw]


def applies_no_reason(concept_id: str, person: str, person_note: str,
                      collapsed: set[str], absorbed_by: dict[str, str]) -> str:
    if concept_id in collapsed:
        return (f"This whole concept is out of generation — it was collapsed into "
                f"{absorbed_by[concept_id]}, which carries the same sign. Nothing "
                "to write on either person's row.")
    if (concept_id, person) in APPLIES_NO_REASON:
        return APPLIES_NO_REASON[(concept_id, person)] or PAEDIATRIC_DUPLICATE
    if person_note:
        return "This person does not apply — see person_note."
    raise SystemExit(
        f"{concept_id} {person}: applies=no with no declared reason and no "
        "person_note to fall back on. An author told to skip a row is owed the "
        "reason; add it to APPLIES_NO_REASON."
    )


def build() -> list[dict]:
    spine = list(csv.DictReader(SPINE.open(encoding="utf-8")))
    anchors = {r["concept_id"]: r for r in csv.DictReader(ANCHORS.open(encoding="utf-8"))}
    v1_english = ex_to_v1_english(v1_vocabulary())

    ruled = rulings()
    # A ruling made during the English pass and applied by the French arm, not
    # yet written into the Kinyarwanda record. Applied so the brief is correct,
    # announced by main() so it is not forgotten.
    ruled.update(PENDING_RULINGS)

    collapsed = collapsed_concepts(spine)
    absorbed_by = collapse_targets(spine, collapsed)

    rows: list[dict] = []
    for src in spine:
        cid, person = src["concept_id"], src["person"]
        is_ex = cid.startswith("EX")
        row = {c: "" for c in COLUMNS}

        # --- gloss ------------------------------------------------------
        note_gloss = ""
        if is_ex and cid in EX_GLOSS_OVERRIDE:
            gloss, note_gloss = EX_GLOSS_OVERRIDE[cid]
            note_gloss = f"GLOSS CORRECTED FROM THE v1 CORPUS: {note_gloss}"
        elif is_ex:
            gloss = v1_english[cid]
            if not gloss:
                raise SystemExit(
                    f"{cid}: no v1 English and no declared override, so this row "
                    "would reach the author with no gloss at all. Add it to "
                    "EX_GLOSS_OVERRIDE."
                )
        else:
            gloss = src["english_gloss"]
            # CR03 was ruled LIPS ONLY on 2026-09-05. The ruling landed in
            # concept_anchors.csv and concepts.py and never in the spine, so every
            # language brief displays a gloss claiming fingertips — see
            # review/cr03-gloss-not-narrowed.md. A REVIEW brief showing the wrong
            # gloss costs a wrong verdict; an AUTHORING brief showing it gets a
            # Kiswahili sentence written about fingertips. The anchor is taken
            # where the two disagree, and the disagreement is reported by main().
            anchor_gloss = anchors.get(cid, {}).get("english_gloss", "")
            if anchor_gloss and anchor_gloss != gloss:
                note_gloss = (
                    f"Gloss taken from concept_anchors.csv, which was narrowed by a "
                    f"ruling the spine never picked up. The spine still says "
                    f"{gloss!r}.")
                gloss = anchor_gloss

        # --- carried rulings --------------------------------------------
        person_note = restate_person_note(src["person_note"], cid, person)
        applies = src["applies"]
        held = ((src["hold"] == "yes" and (cid, person) not in LIFTED_HOLDS)
                or (cid, person) in ADDED_HOLDS)

        relation_set, members = "", ""
        if person == "third":
            relation_set = relation_ruling(cid, src["domain"], ruled)
            if relation_set in NAMED_MEMBERS:
                members = " / ".join(NAMED_MEMBERS[relation_set]) or "(none)"
            else:
                members = "(none — this concept generates no third person)"

        # --- what the author is being asked to do -----------------------
        if applies == "no":
            action = "SKIP — does not apply"
        elif held:
            action = "SKIP — held"
        elif cid in QUESTIONS:
            action = "WRITE — and answer the question in brief_notes"
        else:
            action = "WRITE"

        # --- the note, most important first ------------------------------
        notes: list[str] = []
        if cid in QUESTIONS:
            notes.append(QUESTIONS[cid])
        if applies == "no":
            notes.append(applies_no_reason(cid, person, person_note,
                                           collapsed, absorbed_by))
        elif held:
            notes.append(HOLD_REASON[cid])
        elif src["hold"] == "yes":
            notes.append("The Kinyarwanda row is held; the hold is LIFTED here "
                         f"because {LIFTED_HOLDS[(cid, person)]} Write this row.")

        if src["needs_clinician"].strip():
            if cid not in CLINICIAN:
                raise SystemExit(
                    f"{cid} {person}: needs_clinician is set on the spine but the "
                    "flag is not classified. Every flag is either a question about "
                    "the concept, which this arm inherits, or a doubt about a "
                    "Kinyarwanda word, which it does not. Add it to CLINICIAN."
                )
            transfers, question = CLINICIAN[cid]
            row["needs_clinician"] = "yes" if transfers else ""
            if applies != "no" and question and question not in notes:
                notes.append(question if transfers
                             else f"Not a question for you: {question}")

        if note_gloss:
            notes.append(note_gloss)
        if cid in EX_ROTATED_AWAY:
            notes.append(EX_ROTATED_AWAY[cid])
        if is_ex and cid not in EX_GLOSS_OVERRIDE:
            notes.append("Gloss is the frozen v1 English at this corpus position. "
                         "It describes the presentation; it is not a sentence to "
                         "translate.")
        if applies != "no" and not held:
            notes.append(THIRD_PERSON_RULE if person == "third" else FIRST_PERSON_RULE)

        row.update(
            concept_id=cid,
            domain=src["domain"],
            proposed_urgency=src["proposed_urgency"],
            english_gloss=gloss,
            person=person,
            person_note=person_note,
            applies=applies,
            action=action,
            relation_set=relation_set,
            relation_set_members=members,
            keep_distinct_from=KEEP_DISTINCT.get(cid, ""),
            hold="yes" if held else "",
            brief_notes=" | ".join(notes),
        )
        rows.append(row)
    return rows


def merge(fresh: list[dict], existing: list[dict]) -> tuple[list[dict], list[str]]:
    """Refresh derived columns; preserve everything the author may have written."""
    by_key = {(r["concept_id"], r["person"]): r for r in existing}
    drift: list[str] = []
    for row in fresh:
        old = by_key.get((row["concept_id"], row["person"]))
        if old is None:
            continue
        for column in REGENERATED:
            if old.get(column, "") != row[column]:
                drift.append(f"{row['concept_id']} {row['person']} {column}: "
                             f"{old.get(column, '')!r} -> {row[column]!r}")
        for column in AUTHORED:
            row[column] = old.get(column, "")
    return fresh, drift


# The relation words themselves. `RELATIONS` in `vocabulary_v1.py` has a
# `kinyarwanda` key and nothing else, so no Swahili relation term exists
# anywhere in the project — which means every third-person row in this brief
# has a {REL} with nothing to substitute. Twelve words, asked for on their own
# sheet rather than buried in a 256-row one.
RELATION_SHEET_COLUMNS = ["english", "used_by", "note", "your_swahili",
                          "regional_variant", "your_notes"]

RELATION_NOTE = {
    "My neighbour":
        "OPEN, AND WE WOULD LIKE YOUR VIEW. This word is gender-neutral in both "
        "Kinyarwanda and English, and the Kinyarwanda speaker ruled it INTO the "
        "obstetric set knowingly — which means a language that does not mark "
        "gender on the relation lets a male patient back into a pregnancy "
        "sentence. English resolves it with 'she' later in the sentence. Can "
        "Kiswahili? If not, say so: it may mean the set has to narrow.",
    "My grandmother":
        "The Kinyarwanda word is a general term for an elderly woman rather than "
        "specifically the speaker's grandmother; v1's English chose 'My "
        "grandmother'. If Kiswahili distinguishes the two, tell us which you "
        "wrote and whether the other is also worth having.",
    "My neighbour's child":
        "Used only where a neighbour brings a child in. If that is not a natural "
        "thing to say in Kiswahili, say so rather than forcing it.",
}


def relation_sheet_rows() -> list[dict]:
    used: dict[str, list[str]] = defaultdict(list)
    for name, members in NAMED_MEMBERS.items():
        for member in members:
            used[member].append(name)
    order = list(ALL_RELATIONS) + [m for m in CHILD_RELATIONS_EN
                                   if m not in ALL_RELATIONS]
    return [{"english": member,
             "used_by": ", ".join(sorted(used[member])),
             "note": RELATION_NOTE.get(member, ""),
             "your_swahili": "", "regional_variant": "", "your_notes": ""}
            for member in order]


def assert_no_swahili(rows: list[dict], v1) -> None:
    """No Swahili reaches the author. This is the brief's one hard invariant.

    Checked mechanically rather than trusted, because "I did not write any
    Swahili" is exactly the kind of claim that is true when the code is written
    and false three edits later. Every v1 Swahili string — the 46 in the frozen
    corpus and anything in the v1 Swahili brief — is searched for in every
    generated cell.

    A hit is not a typo to fix in the CSV. It means the builder grew a path that
    carries Swahili, and the anchoring this brief exists to prevent is back.
    """
    swahili = {p.strip() for urgency in v1.SYMPTOMS["swahili"].values()
               for phrases in urgency.values() for p in phrases}
    v1_brief = ROOT / "review" / "speaker_brief_swahili.csv"
    if v1_brief.exists():
        swahili |= {r["current_swahili_phrase"].strip()
                    for r in csv.DictReader(v1_brief.open(encoding="utf-8"))}
    swahili = {s for s in swahili if len(s) > 8}

    for row in rows:
        for column, value in row.items():
            for phrase in swahili:
                if phrase in value:
                    raise SystemExit(
                        f"{row['concept_id']} {row['person']} {column} contains v1 "
                        f"Swahili: {phrase!r}. An authoring brief must not show the "
                        "speaker any Swahili to react to — see the module docstring."
                    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="Report drift in derived columns without writing.")
    args = ap.parse_args()

    lift_problems = check_lifts_match_french()

    rows = build()
    assert_no_swahili(rows, v1_vocabulary())
    concepts = len({r["concept_id"] for r in rows})
    if (len(rows), concepts) != (256, 128):
        raise SystemExit(
            f"expected 256 rows on the 128-concept spine, built {len(rows)} rows "
            f"over {concepts} concepts. The spine moved; re-read it before writing."
        )
    for row in rows:
        if row["action"].startswith("WRITE") and not row["english_gloss"].strip():
            raise SystemExit(
                f"{row['concept_id']} {row['person']} is a row the author is asked "
                "to write and it has no gloss. There is nothing to write from.")
        if "first-pass phrasing" in row["english_gloss"]:
            raise SystemExit(
                f"{row['concept_id']}: the spine's EX gloss placeholder reached the "
                "brief. It points at Kinyarwanda text the author cannot see.")

    # `keep_distinct_from` must name concepts that still exist and still
    # generate. A warning about a collapsed concept is worse than no warning:
    # the author goes looking for a row that is marked SKIP.
    live = {r["concept_id"] for r in rows if r["applies"] == "yes"}
    for row in rows:
        for named in set(re.findall(r"\b([A-Z]{2}\d{2})\b", row["keep_distinct_from"])):
            if named not in live:
                raise SystemExit(
                    f"{row['concept_id']}: keep_distinct_from names {named}, which no "
                    "longer generates. Drop it from KEEP_DISTINCT or name its "
                    "replacement.")

    drift: list[str] = []
    replaced_stale = False
    if OUT.exists():
        existing = list(csv.DictReader(OUT.open(encoding="utf-8")))
        header = list(existing[0]) if existing else []
        if header == COLUMNS:
            rows, drift = merge(rows, existing)
        else:
            # The file on disk is the generator-era brief from 6c3685d: a
            # different column set, 127 concepts, and every author column empty.
            # It is not a half-finished version of this brief, so it is replaced
            # rather than merged — but never silently.
            authored = sum(1 for r in existing
                           if (r.get("your_phrasing") or "").strip())
            if authored:
                raise SystemExit(
                    f"{OUT.name} has a different column set AND {authored} rows "
                    "with a phrase in them. Refusing to overwrite someone's work; "
                    "move the file aside and re-run if that is really what you want."
                )
            replaced_stale = True

    if args.check:
        print(f"{len(rows)} rows over {concepts} concepts")
        for problem in lift_problems:
            print(f"  LIFT: {problem}")
        if drift:
            print(f"{len(drift)} derived columns have drifted from their sources:")
            for d in drift:
                print(f"  {d}")
        if replaced_stale:
            print(f"  {OUT.name} on disk is the pre-spine brief and would be replaced")
        return 1 if (drift or lift_problems) else 0

    save(OUT, COLUMNS, rows)
    save(RELATIONS_OUT, RELATION_SHEET_COLUMNS, relation_sheet_rows())

    if replaced_stale:
        print(f"REPLACED {OUT.name}: the file on disk was the generator-era brief "
              "(127 concepts, different columns, nothing authored in it).")
    for problem in lift_problems:
        print(f"  LIFT PROBLEM: {problem}")
    for concept_id, name in PENDING_RULINGS.items():
        print(f"  PENDING: {concept_id} -> {name} is applied here but is NOT yet in "
              "routine_relation_sets.csv")

    write = sum(1 for r in rows if r["action"].startswith("WRITE"))
    skip_applies = sum(1 for r in rows if r["applies"] == "no")
    skip_held = sum(1 for r in rows if r["hold"] == "yes")
    questions = sorted({r["concept_id"] for r in rows if r["concept_id"] in QUESTIONS})
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} rows over {concepts} concepts")
    print(f"  {write} rows to author, {skip_applies} applies=no, {skip_held} held")
    print(f"  {len(LIFTED_HOLDS)} Kinyarwanda holds lifted, "
          f"{len(ADDED_HOLDS)} added")
    print(f"  open questions carried on {questions}")
    print(f"wrote {RELATIONS_OUT.relative_to(ROOT)}: "
          f"{len(relation_sheet_rows())} relation words to author")
    for d in drift:
        print(f"  refreshed {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
