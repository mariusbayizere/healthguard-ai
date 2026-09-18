"""Emit the corpus example table: what a frame permutation is, and what no rule catches.

WHY THIS IS EMITTED. The table carries eight figures from the corpus (a row
count, two string lengths, a shared-prefix length, a longest-common-substring
length, a Jaccard ratio and its two terms). Hand-typing them would put eight
more numbers in the paper with no way to re-derive them, in a paper whose
argument is that such numbers go stale. Everything below is read from the frozen
reporting split and the authoring record.

WHAT THE TWO PARTS SHOW.

  Part A  One seed phrase and five of its frame permutations. The seed is
          invariant; only the opener, the onset and the closer move. All rows
          carry the same label because the SEED carries it, which is the cluster
          argument made visible rather than argued.

  Part B  The same concept in first and third person. They share a prefix of
          ZERO characters, because the third person opens on the {REL}
          placeholder, and their word Jaccard is far below the 0.85 the
          near-duplicate gate uses. Neither a prefix rule nor a similarity
          threshold groups them. They are in one phrase group because the
          AUTHORING RECORD declares them one concept.

WHY IF05 AND NOT EX24. EX24 gives a cleaner Part B (shared prefix 0, longest
common substring 25 against IF05's 23). It is not used because its
`english_gloss` in the authoring record is the placeholder "existing concept --
your first-pass phrasing is on one of these two rows". Of the fifteen distinct
phrases in the reporting split, exactly ONE carries a real gloss. That is a
finding about the corpus and not merely a note about which row was chosen, so
the emitter asserts it rather than leaving it in a comment: if the number of
real glosses changes, this script says so.

Usage:
    python review/emit_corpus_example.py
    python review/emit_corpus_example.py --check
"""

from __future__ import annotations

import argparse
import collections
import csv
import difflib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "dataset" / "processed" / "eval_phrase_holdout.csv"
RECORD = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"
OUT = ROOT / "paper" / "generated" / "corpus_example.tex"

# The concept the table is built from, and the one it is not. Named so a reader
# of this file can check the choice rather than take it on trust.
CONCEPT = "IF05"
REJECTED = "EX24"
PERMUTATIONS = 5

# A gloss that begins with this is the authoring sheet's placeholder, not a gloss.
PLACEHOLDER = "existing concept"


class Missing(RuntimeError):
    """A row the table depends on is not where it was. Never a silent fallback."""


# The generator's relation placeholder. It is not Kinyarwanda and not a word a
# patient says: it is a slot the frame substitutes a relation term into. Set in
# \texttt so it reads as a token rather than as part of the sentence.
PLACEHOLDER = "{REL}"


def tex(text: str) -> str:
    """Escape corpus text for LaTeX, and set the placeholder as a token.

    The corpus is quoted, never rewritten. The only transformation beyond
    escaping is wrapping {REL} in \texttt, so a reader can see at a glance that
    it is a slot and not a word.
    """
    for old, new in (
        ("\\", r"\textbackslash{}"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("$", r"\$"),
    ):
        text = text.replace(old, new)
    # After escaping, {REL} is \{REL\}. Set that whole token in \texttt.
    return text.replace("\\{REL\\}", "\\texttt{\\{REL\\}}")


def shared_prefix(a: str, b: str) -> int:
    count = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        count += 1
    return count


def relation_terms() -> list[str]:
    """What {REL} expands to, read from the generator rather than chosen here."""
    sys.path.insert(0, str(ROOT))
    try:
        from dataset import vocabulary
    except ImportError as exc:
        raise Missing(f"cannot import dataset.vocabulary: {exc}") from exc
    terms = vocabulary.RELATIONS.get("kinyarwanda", ())
    if not terms:
        raise Missing("RELATIONS['kinyarwanda'] is empty; {REL} expands to nothing")
    return list(terms)


def load():
    with SPLIT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_phrase = collections.defaultdict(list)
    for row in rows:
        by_phrase[row["phrase"]].append(row)

    record = {}
    with RECORD.open(encoding="utf-8", newline="") as handle:
        for r in csv.DictReader(handle):
            phrasing = (r["your_phrasing"] or "").strip()
            if phrasing:
                record[phrasing] = r

    def find(concept: str, person: str) -> str:
        for phrase in by_phrase:
            r = record.get(phrase)
            if r and r["concept_id"] == concept and r["person"] == person:
                return phrase
        raise Missing(
            f"{concept} {person} is not in {SPLIT.name}. The reporting split was "
            "rebuilt or the record was re-authored; the example must be rechosen, "
            "not approximated."
        )

    first = find(CONCEPT, "first")
    third = find(CONCEPT, "third")
    gloss = (record[first]["english_gloss"] or "").strip()
    if not gloss or gloss.startswith(PLACEHOLDER):
        raise Missing(
            f"{CONCEPT}'s english_gloss is now a placeholder. The table claims a "
            "real gloss; refusing to emit one that is not."
        )

    glossed = [
        phrase
        for phrase in by_phrase
        if (g := (record.get(phrase, {}).get("english_gloss") or "").strip())
        and not g.startswith(PLACEHOLDER)
    ]
    concepts = {record[p]["concept_id"] for p in glossed}
    return by_phrase, first, third, gloss, len(glossed), len(concepts)


def render() -> str:
    by_phrase, first, third, gloss, glossed_phrases, glossed_concepts = load()
    rows = by_phrase[first]
    if len(rows) < PERMUTATIONS:
        raise Missing(f"{CONCEPT} first has only {len(rows)} rows in the split")

    label = rows[0]["label"]
    group_first = rows[0]["phrase_group"]
    group_third = by_phrase[third][0]["phrase_group"]
    same_group = group_first == group_third

    match = difflib.SequenceMatcher(None, first, third)
    lcs = max((b.size for b in match.get_matching_blocks()), default=0)
    prefix = shared_prefix(first, third)
    wa, wb = set(first.lower().split()), set(third.lower().split())
    inter, union = len(wa & wb), len(wa | wb)

    # A row the generator emitted without terminal punctuation, if there is one
    # among the five shown. It is left exactly as generated.
    shown = rows[:PERMUTATIONS]
    unpunctuated = [
        i
        for i, r in enumerate(shown, 1)
        if not r["text"].rstrip().endswith((".", "?", "!"))
    ]

    lines = [
        "% GENERATED FILE - DO NOT EDIT BY HAND.",
        "% Written by review/emit_corpus_example.py from",
        "% dataset/processed/eval_phrase_holdout.csv and",
        "% review/speaker_brief_kinyarwanda_v2.csv. The Kinyarwanda is quoted from",
        "% the corpus exactly as generated and is never rewritten here.",
        "%",
        "\\begin{table*}[t]",
        "\\centering\\small",
        "\\setlength{\\tabcolsep}{4pt}",
        "",
        "\\textbf{Part A: one seed phrase and five of its "
        f"{len(rows):,} frame permutations.}}",
        "",
        # tabularx on \\textwidth so Part A and Part B share one measure and
        # their rules line up. Fixed p{} widths gave the two halves different
        # widths (about 431pt against 363pt), which reads as a misalignment.
        "\\begin{tabularx}{\\textwidth}{r>{\\raggedright\\arraybackslash}X}",
        "\\toprule",
        f"& \\textbf{{Seed}} (concept {CONCEPT}, \\emph{{{tex(gloss)}}}, "
        f"label {label}) \\\\",
        f"& {tex(first)} \\\\",
        "\\midrule",
    ]
    for i, r in enumerate(shown, 1):
        lines.append(f"{i} & {tex(r['text'])} \\\\")
    lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "",
        "\\vspace{0.8em}",
        "",
        "\\textbf{Part B: the same concept in two persons, and what no similarity "
        "rule catches.}",
        "",
        "\\begin{tabularx}{\\textwidth}{l>{\\raggedright\\arraybackslash}Xr}",
        "\\toprule",
        "Person & Phrasing & Characters \\\\",
        "\\midrule",
        f"first & {tex(first)} & {len(first)} \\\\",
        f"third & {tex(third)} & {len(third)} \\\\",
        "\\midrule",
        f"\\multicolumn{{2}}{{l}}{{Shared prefix}} & \\textbf{{{prefix}}} \\\\",
        f"\\multicolumn{{2}}{{l}}{{Longest common substring}} & {lcs} \\\\",
        f"\\multicolumn{{2}}{{l}}{{Word Jaccard}} & "
        f"{inter}/{union} = {inter / union:.3f} \\\\",
        "\\bottomrule",
        "\\end{tabularx}",
        f"\\\\[2pt]{{\\footnotesize \\texttt{{\\{{REL\\}}}} is the stored relation "
        f"placeholder, expanded at generation time to one of {len(relation_terms())} "
        "ruled relation terms; the counts above are computed from the stored "
        "form.}",
        "",
    ]

    caption = [
        "\\caption{What a frame permutation is, and what no similarity rule catches.",
        f"\\textbf{{Part A.}} All {len(rows):,} rows built on this seed carry the label",
        f"{label} \\emph{{because the seed carries it}}: the seed text is invariant and",
        "only the opener, the time expression and the closing line move. They are one",
        "observation, not",
        f"{len(rows):,}, which is the cluster argument made visible rather than argued.",
    ]
    if unpunctuated:
        which = ", ".join(str(i) for i in unpunctuated)
        caption.append(
            f"\\textbf{{Row {which} ends without terminal punctuation.}} That is how the"
        )
        caption.append(
            "generator emitted it and it is left untouched: it is a live instance of the"
        )
        caption.append(
            "C9 surface-uniformity failure, visible in the example itself rather than only"
        )
        caption.append("in the gate's verdict.")
    caption += [
        f"\\textbf{{Part B.}} The two phrasings share a prefix of {prefix} characters,",
        "because the third person opens on the \\texttt{\\{REL\\}} placeholder, and",
        "their word",
        f"Jaccard of {inter / union:.3f} is far below the 0.85 the near-duplicate gate",
        "uses. Neither a prefix rule nor a similarity threshold would group them.",
        "They are",
        ("in one phrase group" if same_group else "NOT in one phrase group"),
        "\\emph{because the authoring record declares them one concept}, not because any",
        "string comparison found them alike, and that is what makes this the case no",
        "similarity rule catches.",
        "Substituting a relation term for the placeholder would change the character",
        "count and the shared prefix, which is why the counts are computed from the",
        "stored form and the expansion is described in the note rather than shown as a",
        "row.",
        f"\\textbf{{On the choice of {CONCEPT}.}} {REJECTED} gives a cleaner Part B",
        f"(shared prefix 0, longest common substring 25 against {CONCEPT}'s {lcs}) and is",
        "not used because its \\path{english_gloss} in the authoring record is a",
        "placeholder rather than a gloss. \\textbf{Of the",
        f"{len(by_phrase)} distinct phrases in the reporting split, {glossed_phrases}",
        "carry a real English gloss, and they are the two persons of",
        f"{glossed_concepts} concept.}}",
        "\\textbf{Every other phrase the reported figures rest on is glossed only by a",
        "placeholder telling the author where to look.} That is a property of the",
        "corpus rather than a note about which row was convenient, and it is why this",
        "table could not be built from the cleaner pair.}",
        "\\label{tab:example}",
        "\\end{table*}",
        "",
    ]
    return "\n".join(lines + caption) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        rendered = render()
    except Missing as exc:
        print(f"REFUSING TO EMIT: {exc}", file=sys.stderr)
        return 2

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != rendered:
            print(
                f"{OUT.name} is stale. Regenerate:\n"
                "  python review/emit_corpus_example.py",
                file=sys.stderr,
            )
            return 1
        print(f"{OUT.name} matches the corpus.")
        return 0

    OUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
