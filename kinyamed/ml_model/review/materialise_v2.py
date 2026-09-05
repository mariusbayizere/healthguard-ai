#!/usr/bin/env python
"""Materialise every v2 ruling from the briefs into dataset/vocabulary.py.

Run once at the freeze. Re-runnable: it rewrites whole assignments rather than
patching them, so running it twice gives the same file.

    python review/materialise_v2.py --check     # report, change nothing
    python review/materialise_v2.py --write     # rewrite vocabulary.py

WHAT IT MATERIALISES, and where each ruling comes from:

    SYMPTOMS['kinyarwanda']  the authored, applies=yes, NOT HELD phrases of
                             speaker_brief_kinyarwanda_v2.csv, keyed
                             urgency -> domain as v1 was
    PHRASE_FORMS             the brief's `form` column. Every v2 phrase is an
                             utterance; a blank would silently default to
                             noun_phrase and prefix a subject onto a complete
                             sentence, which is the defect lint rule caught
    CONCEPT_RELATIONS        review/relation_sets.py --materialise, which
                             resolves routine_relation_sets.csv through the
                             same resolver render_third_person.py uses
    PHRASE_VARIANTS          second phrasings declared in the brief
    PHRASE_CONCEPTS          phrase -> concept id, so a concept's two persons
                             land in one phrase group
    OPENERS/CONTEXTS/CLOSERS the 17 written fragments of
                             frame_fragments_brief.csv are appended to the v1
                             slots. Six remain unwritten and are NOT invented
    CLOSERS_BY_URGENCY       V2_CRITICAL_CLOSER_EXCLUSIONS, plus '. Urakoze.'
                             now that it exists - the same sign-off as
                             '. Murakoze.' and excluded for the same reason
    LANGUAGES / MIXED_PAIRS  Kinyarwanda only, ruled 2026-09-05. English is
                             not speaker-reviewed and Swahili has no authored
                             content; both are future work

HELD ROWS DO NOT GENERATE. That is the point of `hold`, and it is checked here
rather than assumed: a held row with a phrase is excluded and counted, so the
number that stays out of the corpus is reported rather than discovered later.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEF = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"
FRAGMENTS = ROOT / "review" / "frame_fragments_brief.csv"
VOCAB = ROOT / "dataset" / "vocabulary.py"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "review"))


def rows() -> list[dict]:
    return list(csv.DictReader(BRIEF.open(encoding="utf-8")))


def generating(rs: list[dict]) -> list[dict]:
    """Rows that produce corpus phrases: authored, applicable, not held."""
    return [
        r for r in rs
        if (r["applies"] or "yes").strip().lower() != "no"
        and r["your_phrasing"].strip()
        and r["hold"].strip().lower() != "yes"
    ]


def symptoms_block(gen: list[dict]) -> tuple[str, dict]:
    by: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    seen: dict[str, str] = {}
    for r in gen:
        phrase = r["your_phrasing"].strip()
        if phrase in seen:
            raise SystemExit(
                f"duplicate phrase {phrase!r} on {r['concept_id']} {r['person']} "
                f"and {seen[phrase]} - assert_slots_are_distinct would fail, and a "
                "duplicate silently inflates one family's share"
            )
        seen[phrase] = f"{r['concept_id']} {r['person']}"
        by[r["proposed_urgency"].strip()][r["domain"].strip()].append(phrase)
        # A declared second phrasing is a CORPUS PHRASE of the same concept, not
        # metadata about one. Two ways of saying the same thing is what the
        # corpus wants; PHRASE_VARIANTS is what keeps them in one phrase group
        # so the holdout cannot train on one and evaluate on the other.
        second = (r.get("second_phrasing_optional") or "").strip()
        if second and second not in seen:
            seen[second] = f"{r['concept_id']} {r['person']} (second phrasing)"
            by[r["proposed_urgency"].strip()][r["domain"].strip()].append(second)
    out = ["SYMPTOMS: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {",
           '    "kinyarwanda": {']
    for urgency in ("CRITICAL", "URGENT", "ROUTINE"):
        out.append(f'        "{urgency}": {{')
        for domain in sorted(by.get(urgency, {})):
            out.append(f'            "{domain}": (')
            for phrase in by[urgency][domain]:
                out.append(f"                {phrase!r},")
            out.append("            ),")
        out.append("        },")
    out.append("    },")
    out.append("}")
    counts = {u: {d: len(p) for d, p in ds.items()} for u, ds in by.items()}
    return "\n".join(out), counts


def fragments() -> dict[str, list[str]]:
    """The written fragments of the brief, by slot. Empty ones are skipped."""
    add: dict[str, list[str]] = defaultdict(list)
    for r in csv.DictReader(FRAGMENTS.open(encoding="utf-8")):
        if r["status"].strip() != "TO WRITE":
            continue
        # DO NOT STRIP. The brief carries each fragment WITH its separator - a
        # trailing space on an opener, a leading space or ". " on a context or
        # closer - because the renderer concatenates slots without adding one.
        # Stripping produced "ku kubokobiragenda bikagaruka" and the attribution
        # sweep caught it immediately.
        text = r["kinyarwanda"]
        if text.strip():
            add[r["slot"].strip()].append(text)
    return add


def emit(name: str, values: list[str]) -> str:
    body = "\n".join(f"        {v!r}," for v in values)
    return f'{name}: dict[str, tuple[str, ...]] = {{\n    "kinyarwanda": (\n{body}\n    ),\n}}'


def replace_assignment(src: str, name: str, new: str) -> str:
    """Replace a whole top-level assignment, however many lines it spans."""
    pattern = re.compile(rf"^{re.escape(name)}\b[^\n]*=.*?(?=\n[A-Z_]+\s*[:=]|\n# ---|\Z)",
                         re.S | re.M)
    if not pattern.search(src):
        raise SystemExit(f"could not find the assignment for {name}")
    return pattern.sub(lambda _: new + "\n\n", src, count=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="rewrite vocabulary.py")
    args = ap.parse_args()

    rs = rows()
    gen = generating(rs)
    held = [r for r in rs if r["hold"].strip().lower() == "yes"]
    held_authored = [r for r in held if r["your_phrasing"].strip()]

    print(f"brief                     {len(rs)} rows")
    print(f"generating phrases        {len(gen)}")
    print(f"held (excluded)           {len(held)}  of which authored {len(held_authored)}")
    for r in held_authored:
        print(f"    OUT: {r['concept_id']} {r['person']}  {r['your_phrasing'][:52]}")

    sym, counts = symptoms_block(gen)
    for urgency in ("CRITICAL", "URGENT", "ROUTINE"):
        total = sum(counts.get(urgency, {}).values())
        print(f"  {urgency:8} {total:3} phrases across {len(counts.get(urgency, {}))} domains")

    forms = {}
    for r in gen:
        form = r["form"].strip() or "utterance"
        forms[r["your_phrasing"].strip()] = form
        second = (r.get("second_phrasing_optional") or "").strip()
        if second:
            # A second phrasing is a corpus phrase and needs its own form, or it
            # defaults to noun_phrase and gets a subject prefixed onto a complete
            # sentence. It is the same concept in the same shape as its primary.
            forms[second] = form
    blank = [p for p, f in forms.items() if f != "utterance"]
    print(f"PHRASE_FORMS              {len(forms)} entries"
          + (f"  WARNING non-utterance: {blank}" if blank else "  all utterance"))

    rel = subprocess.run([sys.executable, str(ROOT / "review" / "relation_sets.py"),
                          "--materialise"], capture_output=True, text=True)
    concept_relations = rel.stdout.strip()
    print(f"CONCEPT_RELATIONS         {concept_relations.count(':')} phrase mappings")

    var = subprocess.run([sys.executable, str(ROOT / "review" / "second_phrasings.py"),
                          str(BRIEF)], capture_output=True, text=True)
    print("PHRASE_VARIANTS/CONCEPTS  " + var.stdout.strip().splitlines()[0])

    add = fragments()
    print("frame fragments written   " + ", ".join(f"{k}+{len(v)}" for k, v in sorted(add.items())))

    if not args.write:
        print("\n--check only; nothing written. Re-run with --write.")
        return 0

    # PHRASE_CONCEPTS and PHRASE_VARIANTS are built HERE, from the generating
    # set, not taken from second_phrasings.py. That tool reads the whole brief
    # including held rows, and phrase_components RAISES when a declaration names
    # a phrase that is not in the inventory - correctly, because a declaration
    # pointing at nothing leaves the leak it exists to close. Held phrases are
    # not in the inventory, so they must not be declared.
    phrase_concepts = {}
    variants = {}
    for r in gen:
        primary = r["your_phrasing"].strip()
        phrase_concepts[primary] = r["concept_id"].strip()
        second = (r.get("second_phrasing_optional") or "").strip()
        if second:
            phrase_concepts[second] = r["concept_id"].strip()
            variants[second] = primary
    live = set(phrase_concepts)
    print(f"PHRASE_CONCEPTS           {len(phrase_concepts)} phrases across "
          f"{len(set(phrase_concepts.values()))} concepts  (held rows excluded)")
    print(f"PHRASE_VARIANTS           {len(variants)}")

    # CONCEPT_RELATIONS: keep only mappings whose phrase actually generates.
    # Built by CALLING the resolver rather than parsing its output, so this
    # cannot drift from what render_third_person.py showed the speaker.
    from relation_sets import resolve
    from dataset.vocabulary import DOMAIN_RELATIONS, RELATIONS
    rel_map = {}
    for r in gen:
        if r["person"] != "third" or "{REL}" not in r["your_phrasing"]:
            continue
        allowed = resolve(r["concept_id"].strip(), r["domain"].strip())
        default = DOMAIN_RELATIONS.get(r["domain"].strip(), RELATIONS["kinyarwanda"])
        # Only NARROWINGS are written. A phrase whose ruling equals its domain
        # default is left out, because absence already means the default - and
        # writing it in would hide which entries are real rulings.
        if allowed is not None and tuple(allowed) != tuple(default):
            rel_map[r["your_phrasing"].strip()] = tuple(allowed)
    print(f"CONCEPT_RELATIONS         {len(rel_map)} phrases carry a NARROWING "
          f"(the rest take their domain default)")
    for ph, al in sorted(rel_map.items()):
        print(f"    {len(al)} relations  {ph[:56]}")

    src = VOCAB.read_text(encoding="utf-8")
    src = replace_assignment(src, "SYMPTOMS", sym)
    src = replace_assignment(src, "LANGUAGES", 'LANGUAGES = ("kinyarwanda",)')
    src = replace_assignment(src, "MIXED_PAIRS",
                             "MIXED_PAIRS: tuple[tuple[str, str], ...] = ()")

    def as_dict(name, mapping, note):
        body = "\n".join(f"    {k!r}:\n        {v!r}," for k, v in sorted(mapping.items()))
        return f"# {note}\n{name}: dict[str, str] = {{\n{body}\n}}" if mapping else \
               f"# {note}\n{name}: dict[str, str] = {{}}"

    src = replace_assignment(src, "PHRASE_FORMS", as_dict(
        "PHRASE_FORMS", forms,
        "Materialised at the v2 freeze from the brief's form column. Every v2 phrase "
        "is an utterance; a blank here defaults to noun_phrase and prefixes a subject "
        "onto a complete sentence."))
    src = replace_assignment(src, "PHRASE_VARIANTS", as_dict(
        "PHRASE_VARIANTS", variants,
        "Materialised at the v2 freeze. A concept's second phrasing joins its primary."))
    body = "\n".join(f"    {k!r}:\n        {v!r}," for k, v in sorted(rel_map.items()))
    src = replace_assignment(src, "CONCEPT_RELATIONS",
        "# Materialised at the v2 freeze from routine_relation_sets.csv, through the same\n"
        "# resolver render_third_person.py used to show the speaker each rendering. A\n"
        "# phrase absent here takes its domain default.\n"
        "CONCEPT_RELATIONS: dict[str, tuple[str, ...]] = {\n" + body + "\n}"
        if rel_map else "CONCEPT_RELATIONS: dict[str, tuple[str, ...]] = {}")
    src = replace_assignment(src, "PHRASE_CONCEPTS", as_dict(
        "PHRASE_CONCEPTS", phrase_concepts,
        "Materialised at the v2 freeze, from the GENERATING set only - held phrases are "
        "not in the inventory and declaring one would make phrase_components raise."))

    # frame fragments: append the written ones to the v1 slots
    from dataset import vocabulary as V
    for slot, name in (("opener", "OPENERS"), ("context", "CONTEXTS"), ("closer", "CLOSERS")):
        existing = list(getattr(V, name)["kinyarwanda"])
        merged = existing + [f for f in add.get(slot, []) if f not in existing]
        src = replace_assignment(src, name, emit(name, merged))
        print(f"  {name}: {len(existing)} -> {len(merged)}")

    # CRITICAL loses its two sign-offs; '. Urakoze.' now exists and is the same closer
    closers = list(V.CLOSERS["kinyarwanda"]) + [f for f in add.get("closer", [])
                                                if f not in V.CLOSERS["kinyarwanda"]]
    excluded = tuple(c for c in closers if c.strip() in (". Murakoze.", ". Urakoze.")
                     or c.strip().lower().lstrip(". ").rstrip(".") in ("murakoze", "urakoze"))
    critical = tuple(c for c in closers if c not in excluded)
    src = replace_assignment(src, "CLOSERS_BY_URGENCY",
        "# Materialised at the v2 freeze. CRITICAL loses the pure sign-offs: thanking\n"
        "# someone trivialises an emergency. '. Nkora iki?' stays - asking what to do is\n"
        "# a real question in one. URGENT and ROUTINE are deliberately unrestricted.\n"
        "CLOSERS_BY_URGENCY: dict[str, dict[str, tuple[str, ...]]] = {\n"
        '    "CRITICAL": {\n        "kinyarwanda": (\n'
        + "".join(f"            {c!r},\n" for c in critical)
        + "        ),\n    },\n}")
    # replace_assignment swallows whatever follows a block until the next
    # top-level name, and the first run of this script silently DELETED
    # V2_CRITICAL_CLOSER_EXCLUSIONS that way. Re-emit it explicitly: it is the
    # record of why CLOSERS_BY_URGENCY looks as it does, and a materialiser that
    # can lose a ruling is worse than no materialiser.
    if "V2_CRITICAL_CLOSER_EXCLUSIONS" not in src:
        src += ("\n\n# Restored by materialise_v2.py - the ruled CRITICAL closer exclusions.\n"
                "V2_CRITICAL_CLOSER_EXCLUSIONS: tuple[str, ...] = "
                + repr(tuple(e for e in excluded)) + "\n")
    print(f"  CLOSERS_BY_URGENCY: CRITICAL keeps {len(critical)} of {len(closers)}, "
          f"excluding {[e for e in excluded]}")

    VOCAB.write_text(src, encoding="utf-8")
    print(f"\nwrote {VOCAB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
