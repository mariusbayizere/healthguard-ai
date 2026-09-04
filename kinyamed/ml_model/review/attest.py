#!/usr/bin/env python
"""Is this Kinyarwanda word attested? Check every substantiation source at once.

Run before writing a phrase that uses a word you are not certain of. Standing
rules 5 to 8 say a word must exist in language a Rwandan has actually produced
before it goes into a phrase; this is the check that makes that cheap.

    python review/attest.py ugutwi
    python review/attest.py kwituma amabyi umwanda      # several at once
    python review/attest.py impiswi --context           # show surrounding text
    python review/attest.py nda --whole-word            # opt in to word boundaries

Sources, in descending authority:

    speaker      phrases the Kinyarwanda speaker authored or accepted
    approved     v1 vocabulary in dataset/vocabulary.py — already in the corpus
    review_sheet review/phrase_review_sheet.csv, including unapproved drafts
    chw          review/attestation/ — 524 real CHW questions and clinician
                 answers, CC BY 4.0, see that directory's SOURCE.md
    rbc          review/attestation/ — 2.5M characters of Rwanda Biomedical
                 Centre health and CHW training curriculum, CC BY 2.0

A hit in `speaker` or `approved` settles it. A hit in `chw` or `rbc` means the
word is real Rwandan health Kinyarwanda but nobody on this project has authored
with it — it is a lead to put to the speaker, never a licence to write the
phrase yourself. A hit only in `review_sheet` with status `draft` is not
evidence at all: that is my own unapproved drafting coming back around.

`chw` and `rbc` are separate tiers because they fail differently. `chw` is
CHW-to-clinician case reports that passed through speech-to-text, so a lone odd
hit may be a transcription artefact and the count of distinct CHWs is what
matters. `rbc` is written, edited curriculum with no ASR layer, so a single
clean hit is worth more — but it is instructional register throughout ("teach
the mother to..."), so it attests a TERM and says nothing about how a patient
would phrase it. Neither corpus is patient speech.

MATCHING IS SUBSTRING BY DEFAULT, deliberately. A Kinyarwanda stem hides behind
noun-class prefixes and verbal morphology, so a word-boundary regex misses
`igituza` when looking for `gituza`. The cost is false positives — `nda` matches
`ndakorora` — so read the contexts before believing a hit. `--whole-word` is
available when you know you want it.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

csv.field_size_limit(10**9)

BRIEF = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"
SHEET = ROOT / "review" / "phrase_review_sheet.csv"
CHW = ROOT / "review" / "attestation" / "chw_questions_kinyarwanda.csv"
RBC = ROOT / "review" / "attestation" / "rbc_kinyarwanda_health.txt"


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(path.open(encoding="utf-8")))


def speaker_texts() -> list[tuple[str, str]]:
    """(label, text) for every phrase the speaker authored or accepted."""
    out = []
    for r in _rows(BRIEF):
        if (r.get("applies") or "yes").strip().lower() == "no":
            continue
        phrase = (r.get("your_phrasing") or "").strip()
        if phrase:
            out.append((f"{r['concept_id']} {r['person']} [{r.get('source','')}]", phrase))
    return out


def approved_texts() -> list[tuple[str, str]]:
    """(label, text) for v1 vocabulary already shipping in the corpus."""
    from dataset.vocabulary import (CLOSERS, CONTEXTS, ONSETS, OPENERS,
                                    SUBJECTS, SYMPTOMS)
    out = []
    for urgency, domains in SYMPTOMS.get("kinyarwanda", {}).items():
        for domain, phrases in domains.items():
            for p in phrases:
                out.append((f"v1 {domain} {urgency}", p))
    for name, table in (("opener", OPENERS), ("subject", SUBJECTS),
                        ("onset", ONSETS), ("context", CONTEXTS),
                        ("closer", CLOSERS)):
        for frag in table.get("kinyarwanda", ()):
            if frag.strip():
                out.append((f"v1 {name}", frag))
    return out


def review_sheet_texts() -> list[tuple[str, str]]:
    out = []
    for r in _rows(SHEET):
        if (r.get("language") or "").strip() != "kinyarwanda":
            continue
        for col in ("phrase", "speaker_corrected_phrase"):
            t = (r.get(col) or "").strip()
            if t:
                out.append((f"{r.get('id','')} {r.get('status','')}", t))
    return out


def chw_texts() -> list[tuple[str, str]]:
    out = []
    for r in _rows(CHW):
        for col in ("question_kinyarwanda", "answer_clinician_kinyarwanda"):
            t = (r.get(col) or "").strip()
            if t:
                kind = "Q" if col.startswith("question") else "A"
                out.append((f"chw:{r.get('chw_id','?')} {kind}", t))
    return out


def rbc_texts() -> list[tuple[str, str]]:
    """(label, text) per line of the RBC training corpus.

    Plain text, one sentence or heading per line. The line number is the label
    so a hit can be found again in the file.
    """
    if not RBC.exists():
        return []
    out = []
    for n, line in enumerate(RBC.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if line:
            out.append((f"rbc:{n}", line))
    return out


SOURCES = [
    ("speaker", "the speaker authored or accepted it", speaker_texts),
    ("approved", "v1 vocabulary, already in the corpus", approved_texts),
    ("review_sheet", "phrase review sheet (includes unapproved drafts)", review_sheet_texts),
    ("chw", "real CHW/clinician Kinyarwanda, CC BY 4.0 — ASR transcript", chw_texts),
    ("rbc", "RBC health/CHW training curriculum, CC BY 2.0 — written, instructional", rbc_texts),
]

# Corpora of real Kinyarwanda that this project has not authored with. A hit
# here is a lead for the speaker, never permission to write the phrase.
LEAD_SOURCES = ("chw", "rbc")


def find(term: str, pairs: list[tuple[str, str]], whole: bool) -> list[tuple[str, str]]:
    if whole:
        pat = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        return [(l, t) for l, t in pairs if pat.search(t)]
    low = term.lower()
    return [(l, t) for l, t in pairs if low in t.lower()]


def excerpt(text: str, term: str, width: int = 90) -> str:
    i = text.lower().find(term.lower())
    if i < 0:
        return text[:width]
    start = max(0, i - width // 2)
    end = min(len(text), i + len(term) + width // 2)
    return ("..." if start else "") + text[start:end].strip() + ("..." if end < len(text) else "")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("terms", nargs="+", help="Kinyarwanda word or stem to look for.")
    ap.add_argument("--whole-word", action="store_true",
                    help="Require word boundaries. Off by default: a stem hides "
                         "behind noun-class prefixes.")
    ap.add_argument("--context", action="store_true",
                    help="Show every match, not just the first few.")
    ap.add_argument("--max", type=int, default=3, help="Excerpts per source (default 3).")
    args = ap.parse_args()

    loaded = [(name, why, fn()) for name, why, fn in SOURCES]
    missing = [name for name, _, pairs in loaded if not pairs]
    if missing:
        print(f"note: no data loaded for {', '.join(missing)}\n", file=sys.stderr)

    exit_code = 1
    for term in args.terms:
        print("=" * 72)
        print(f"  {term}")
        print("=" * 72)
        verdict = []
        for name, why, pairs in loaded:
            hits = find(term, pairs, args.whole_word)
            if not hits:
                print(f"  {name:13} —")
                continue
            verdict.append(name)
            extra = ""
            if name == "chw":
                # How many distinct CHWs used it. One speaker could be an ASR
                # artefact; several is a real term.
                who = {l.split()[0] for l, _ in hits}
                extra = f", {len(who)} distinct CHW/clinician record(s)"
            elif name == "rbc":
                # No ASR layer here, so the useful count is how many distinct
                # lines carry it — a term repeated across the curriculum is
                # settled vocabulary, one hit in a heading may be incidental.
                extra = f", {len({t for _, t in hits})} distinct line(s)"
            print(f"  {name:13} {len(hits)} hit(s){extra}   ({why})")
            shown = hits if args.context else hits[:args.max]
            for label, text in shown:
                print(f"      [{label}] {excerpt(text, term)}")
            if not args.context and len(hits) > args.max:
                print(f"      ... {len(hits) - args.max} more; --context for all")
        print()
        if "speaker" in verdict or "approved" in verdict:
            print("  VERDICT: attested in project-approved language. Safe to use.")
            exit_code = 0
        elif any(s in verdict for s in LEAD_SOURCES):
            where = " and ".join(s for s in LEAD_SOURCES if s in verdict)
            print(f"  VERDICT: attested in real Rwandan health Kinyarwanda ({where}), but")
            print("           NOT in any phrase this project has approved. This is a lead")
            print("           for the speaker — it does not authorise writing the phrase.")
            if "rbc" in verdict and "chw" not in verdict:
                print("           rbc only: instructional register, so this attests the term")
                print("           and says nothing about how a patient would phrase it.")
            exit_code = 0
        elif "review_sheet" in verdict:
            print("  VERDICT: only in the review sheet. If those rows are drafts, this")
            print("           is my own unapproved drafting and is NOT evidence.")
        else:
            print("  VERDICT: NOT ATTESTED anywhere. Do not invent it — ask the speaker.")
        print()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
