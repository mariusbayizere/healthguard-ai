"""Grammatical person of the v2 corpus: who has the symptom, the speaker or someone else?

    cd kinyamed/ml_model && python ../reports/measurements/grammatical_person.py > ../reports/measurements/grammatical_person.txt

Measurement only. Nothing here is a clinical judgement and nothing is written to the corpus.

TWO LABELS PER ROW
1. REFERENCE (what the generator built):
   - a `{REL}` phrase is third person by construction, and the relation rendered into
     the row is recovered exactly;
   - the 88 non-`{REL}` phrases are labelled by hand in `PHRASE_PERSON` from their
     Kinyarwanda concord morphology. That hand reading is mine, not a speaker's, and
     the uncertain ones are listed in `UNCERTAIN`.
2. AUTOMATIC: a rule classifier over Kinyarwanda subject/object concord and possessive
   morphology (`classify`). It never sees the phrase column or the `{REL}` marker.
   Its disagreement with the reference is its error rate on this corpus.

The unit classified is the SYMPTOM CLAUSE (the rendered phrase), not the whole row:
openers and closers ("Ndakeneye ubufasha", "Nzanye umwana wanjye") put first-person
SPEAKER morphology into rows about someone else. The whole-row variant is also reported,
to show how wrong a whole-text count would be.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, ".")
from dataset import vocabulary as V  # noqa: E402

FILES = {
    "train": Path("dataset/processed/train_phrase_holdout.csv"),
    "eval": Path("dataset/processed/eval_phrase_holdout.csv"),
}
REPORTING_GROUPS = {  # training/run_records/last_run_v2d_freeze8_lr1e-5.json eval_split
    "Amazuru yanjye arimo ariva imyuna myinshi kandi ntahagarara.",
    "Mfite umuvuduko w'amaraso wazamutse cyane.",
    "Ndashaka ko bapima amaraso.",
    "mfite umuriro wa dogere 39",
    "mu gituza harandya cyane kandi sinshobora guhumeka neza",
}

# ── Reference labels for the 88 phrases without {REL} (hand reading, not a speaker) ─
SELF, OTHER, CARER, UNMARKED = "self-report", "third-person report", "carer request for a child", "no person marked"
PHRASE_PERSON_EXCEPTIONS = {
    # 3sg possessive "we" (his/her body); no relation named
    "Uruhande rumwe rw'umubiri we ntirukora.": OTHER,
    # 1sg speaker; the person to be seen/treated is "umwana (wanjye)" (the/my child)
    "Ndashaka ko bapima ibiro by'umwana wanjye.": CARER,
    "Ndashaka imiti y'inzoka y'umwana wanjye.": CARER,
    "Ndashaka inama ku biryo byo kugaburira umwana wanjye.": CARER,
    "Mfite gahunda yo gukingiza umwana.": CARER,
    # no subject or object concord for a person: "the waters broke ..."
    "Amazi yamenetse ariko igihe cyo kubyara ntikiragera.": UNMARKED,
}
UNCERTAIN = {
    "Mfite gahunda yo gukingiza umwana.": "whose vaccination: the child's (carer) or unstated",
    "Ndashaka kugirwa inama uko nakonsa umwana.": "read as self (1sg 'nakonsa', breastfeeding advice for the mother); the child is also a subject of care",
    "Guhumeka birangora cyane ku buryo ntabasha no kuvuga neza.": "'ntabasha' read as 1sg subordinate negative (n-ta-); could be read as 3sg",
    "ndi kuva amaraso menshi kandi ntahagarara": "'ntahagarara' (it/he does not stop) has no 1sg reading; person carried by 'ndi'",
    "Amazuru yanjye arimo ariva imyuna myinshi kandi ntahagarara.": "as above; person carried by possessive 'yanjye'",
    "Mfite umuhaha.": "1sg, but in the paediatric domain; whose condition is not stated",
    "Amazi yamenetse ariko igihe cyo kubyara ntikiragera.": "no person marked; implicitly the speaker",
}


def reference(phrase: str) -> str:
    """Grammatical person of the clause's subject (who the verb agrees with)."""
    if V.REL_PLACEHOLDER in phrase:
        return OTHER
    return PHRASE_PERSON_EXCEPTIONS.get(phrase, SELF)


# {REL} phrases whose PATIENT is a child although the grammatical subject is the
# relative ("{REL} wants their child weighed"). Read from the phrase text.
REL_CHILD_PATIENT = {
    "{REL} ashaka ko bapima ibiro by'umwana we.",
    "{REL} afite gahunda yo gukingiza umwana.",
    "{REL} ashaka inama ku biryo byo kugaburira umwana we.",
    "{REL} ashaka imiti y'inzoka y'umwana we.",
}
P_SELF = "A. self-report (speaker's own condition)"
P_CHILD_REL = "B1. about a child: relation is a child"
P_CHILD_CARER = "B2. about a child: speaker's own request for their child"
P_CHILD_RELAYED = "B3. about a child: an adult relative's request, relayed"
P_ADULT = "C. about an adult or unspecified relative"
P_OTHER = "D. third person, nobody named"
P_UNMARKED = "E. no person marked"


def patient(phrase: str, rel: str | None) -> str:
    """Whose condition the row describes."""
    if V.REL_PLACEHOLDER in phrase:
        if phrase in REL_CHILD_PATIENT:
            return P_CHILD_RELAYED
        return P_CHILD_REL if rel in V.CHILD_RELATIONS else P_ADULT
    ref = reference(phrase)
    return {SELF: P_SELF, CARER: P_CHILD_CARER, OTHER: P_OTHER, UNMARKED: P_UNMARKED}[ref]


# ── Automatic concord classifier ────────────────────────────────────────────────
HUMAN_NOUNS = {  # class 1/1a human nouns and kin terms as subjects
    "umwana", "umuhungu", "umukobwa", "umwuzukuru", "umugore", "umugabo", "mama",
    "papa", "mushiki", "umuturanyi", "umukecuru", "umuntu",
}
NOT_VERBS = {  # frequent n-/m-/a-/y- initial words that are not person-marked verbs
    "mu", "mwinshi", "menshi", "myinshi", "nabi", "nka", "nk", "neza", "none", "nyuma", "nta",
    "ntabwo", "ni", "na", "no", "nijoro", "muganga", "mumbabarire", "maraso", "mubiri", "mutwe",
    "amaraso", "amazi", "amazuru", "amashyira", "abandi", "ariko", "aho", "yo", "ya", "ye",
    "yanjye", "mwaka", "mbere", "malariya", "mazi", "mama", "ntibuhagarara", "ntirukora",
    "ntikiragera", "mirire", "nzoka", "mazuru", "mfasha", "nyabuneka", "muraho",
}
FIRST_SUBJECT = re.compile(r"^(sin[a-z]|nd[a-z]|ng[a-z]|nk[a-z]|nj[a-z]|ns[a-z]|nz[a-z]|nt[a-z]|mb[a-z]|mf[a-z]|mp[a-z]|mv[a-z]|maze|na[a-z]{2}|nu[a-z]|ni[a-z]{2})")
FIRST_OBJECT = re.compile(r"^[a-z]{1,3}ra(n|m)[a-z]{2}")  # bi-ra-n-gora, u-ra-n-rya, ha-ra-n-rya
THIRD_SUBJECT = re.compile(r"^(a(?!ma|ba|ri(?:ko)?$)[a-z]{2}|ya[a-z]{2}|nta[a-z]{2}|ada[a-z]+|yu[a-z]+)")
FIRST_POSS = re.compile(r"^[a-z]{1,3}anjye$")
THIRD_POSS = {"we", "ye", "rwe", "cye", "kwe", "bwe", "rye", "zayo"}


def classify_v1(text: str) -> str:
    """First rule set, as run before inspecting its errors. Kept for disclosure."""
    tokens = re.findall(r"[a-z]+", text.lower())
    first = third = False
    for i, tok in enumerate(tokens):
        prev = tokens[i - 1] if i else ""
        if tok in HUMAN_NOUNS and prev not in {"by", "y", "gukingiza", "kugaburira", "w"}:
            third = True
            continue
        if FIRST_POSS.match(tok):
            if prev not in HUMAN_NOUNS:
                first = True
            continue
        if tok in THIRD_POSS:
            third = True
            continue
        if tok in NOT_VERBS:
            continue
        if FIRST_OBJECT.match(tok) or FIRST_SUBJECT.match(tok):
            first = True
        elif THIRD_SUBJECT.match(tok):
            third = True
    if first and third:
        return "mixed"
    return SELF if first else OTHER if third else UNMARKED


NOUN_LIKE = re.compile(r"^(umu|umw|aba|imi|ama|iki|igi|ibi|uru|ubu|uku|aka|utu|in[a-z]|im[a-z]|isu|umu)")
FIRST_SUBJECT_V2 = re.compile(r"^(sin[a-z]|nd[a-z]|ng[a-z]|nk[a-z]|nj[a-z]|ns[a-z]|nz[a-z]|mb[a-z]|mf[a-z]|mp[a-z]|mv[a-z]|maze|na[a-z]{2}|nu[a-z])")
THIRD_SUBJECT_V2 = re.compile(r"^(a(?!ma|ba|riko$)[a-z]{1,}|ya[a-z]{2}|nta[a-z]{2}|ada[a-z]+|yu[a-z]+)")
CLAUSE_BREAK = {"kandi", "ariko", "none", "iyo"}


def classify(text: str) -> str:
    """Second rule set, revised AFTER inspecting v1's errors on this same corpus.

    Changes: 'nt-a-' is 3sg negative, not 1sg (1sg negative is 'si-n-'); a human noun
    is a subject only clause-initially or after 'iyo' / 'kubyara'; a verb right after a
    non-human noun (and its possessive) agrees with that noun, not with a person.
    Because it was revised on the evaluation data, its error rate is optimistic.
    """
    tokens = re.findall(r"[a-z]+", text.lower())
    first = third = False
    noun_pending = False
    for i, tok in enumerate(tokens):
        prev = tokens[i - 1] if i else ""
        if tok in CLAUSE_BREAK:
            noun_pending = False
            continue
        if tok in HUMAN_NOUNS:
            if i == 0 or prev in {"iyo", "kubyara"}:
                third = True
            noun_pending = False
            continue
        if FIRST_POSS.match(tok):
            if prev not in HUMAN_NOUNS:
                first = True
            continue
        if tok in THIRD_POSS:
            if prev not in HUMAN_NOUNS:
                third = True
            continue
        if tok in NOT_VERBS:
            continue
        if NOUN_LIKE.match(tok) and not FIRST_OBJECT.match(tok):
            noun_pending = True
            continue
        if FIRST_OBJECT.match(tok) or FIRST_SUBJECT_V2.match(tok):
            first = True
            noun_pending = False
        elif THIRD_SUBJECT_V2.match(tok):
            if not noun_pending:
                third = True
            noun_pending = False
    if first and third:
        return "mixed"
    return SELF if first else OTHER if third else UNMARKED


def rendered_clause(row: dict[str, str]) -> tuple[str, str | None]:
    """The phrase as rendered in the row, and the relation used (for {REL} rows)."""
    phrase, text = row["phrase"], row["text"]
    low = text.lower()
    if V.REL_PLACEHOLDER not in phrase:
        return phrase, None
    for rel in sorted({*V.RELATIONS["kinyarwanda"], *V.CHILD_RELATIONS, *V.ADULT_RELATIONS}, key=len, reverse=True):
        candidate = phrase.replace(V.REL_PLACEHOLDER, rel).rstrip(V.SENTENCE_END).lower()
        if candidate in low:
            return candidate, rel
    return phrase.replace(V.REL_PLACEHOLDER, ""), "UNRECOVERED"


def pct(n: int, d: int) -> str:
    return f"{n:,} / {d:,} ({100 * n / d:.1f}%)" if d else "0 / 0"


def main() -> None:
    rows = []
    for split, path in FILES.items():
        for r in csv.DictReader(path.open(encoding="utf-8")):
            r["split"] = split
            rows.append(r)
    phrases = {r["phrase"]: r["domain"] for r in rows}
    assert len(rows) == 330_000 and len(phrases) == 165
    N = len(rows)

    pat = Counter()
    by_domain = defaultdict(Counter)
    rels_per_phrase = defaultdict(set)
    auto = {"v1 clause": Counter(), "v2 clause": Counter(), "v2 whole row": Counter()}
    distinct_err = {"v1 clause": set(), "v2 clause": set()}
    distinct_all = set()
    frame_conflict = Counter()
    reporting = []
    for r in rows:
        clause, rel = rendered_clause(r)
        if rel:
            rels_per_phrase[r["phrase"]].add(rel)
        pt = patient(r["phrase"], rel)
        pat[pt] += 1
        by_domain[r["domain"]][pt] += 1
        ref = reference(r["phrase"])
        for name, fn, src in (("v1 clause", classify_v1, clause), ("v2 clause", classify, clause), ("v2 whole row", classify, r["text"])):
            out = fn(src)
            auto[name][(ref, out)] += 1
            if name in distinct_err and ref != CARER and out != ref:
                distinct_err[name].add(clause.lower())
        distinct_all.add(clause.lower())
        about_child = pt.startswith("B")
        text = r["text"]
        if text.startswith("Nzanye umwana wanjye") and not about_child:
            frame_conflict["opener 'Nzanye umwana wanjye' (I have brought my child) on a row not about a child"] += 1
        if "Abandi bana na bo bafite iki kibazo" in text and not about_child:
            frame_conflict["context 'Abandi bana na bo bafite iki kibazo' (other children have this too) on a row not about a child"] += 1
        if r["split"] == "eval" and r["phrase_group"] in REPORTING_GROUPS:
            reporting.append((r, pt))

    def block(title: str, counter: Counter, total: int) -> None:
        print(title)
        for k in sorted(counter):
            print(f"  {k:62s} {pct(counter[k], total)}")

    block("== 1. Whole corpus (330,000 rows): whose condition ==", pat, N)
    third = sum(v for k, v in pat.items() if k[0] in "BCD")
    child = sum(v for k, v in pat.items() if k.startswith("B"))
    print(f"  -> self-report {pct(pat[P_SELF], N)}; about someone else {pct(third, N)}; about a child {pct(child, N)}")

    print("\n== 2. Seed phrases (165 distinct) ==")
    seed = Counter()
    for p in phrases:
        if V.REL_PLACEHOLDER in p:
            rels = rels_per_phrase[p]
            if p in REL_CHILD_PATIENT:
                seed["{REL}, patient is a child (relayed request)"] += 1
            elif rels and rels <= set(V.CHILD_RELATIONS):
                seed["{REL}, rendered with child relations only"] += 1
            elif rels & set(V.CHILD_RELATIONS):
                seed["{REL}, rendered with child and adult relations"] += 1
            else:
                seed["{REL}, rendered with adult relations only"] += 1
        else:
            seed[{SELF: "no {REL}: self-report", CARER: "no {REL}: speaker's request for their child",
                  OTHER: "no {REL}: third person, nobody named", UNMARKED: "no {REL}: no person marked"}[reference(p)]] += 1
    for k in sorted(seed):
        print(f"  {k:52s} {seed[k]:3d} / 165 ({100 * seed[k] / 165:.1f}%)")

    print("\n== 3. n=9 reporting set (v2d test set) ==")
    rp = Counter(pt for _, pt in reporting)
    block(f"  rows {len(reporting):,}; distinct phrases {len({r['phrase'] for r, _ in reporting})}", rp, len(reporting))
    for p in sorted({r["phrase"] for r, _ in reporting}):
        print(f"    {reference(p):22s} {p}")

    print("\n== 4. Domains ==")
    for dom in sorted(by_domain, key=lambda d: -sum(by_domain[d].values())):
        tot = sum(by_domain[dom].values())
        print(f"  {dom:20s} {pct(tot, N)}")
        for k in sorted(by_domain[dom]):
            print(f"      {k:58s} {pct(by_domain[dom][k], tot)}")

    print("\n== 5. Frame contradictions (opener/context implies a child, clause does not) ==")
    for k, v in frame_conflict.items():
        print(f"  {k}: {pct(v, N)}")

    labels, outs = [SELF, OTHER, CARER, UNMARKED], [SELF, OTHER, "mixed", UNMARKED]
    print(f"\n== 6. Automatic concord classifier vs reference subject person ({len(distinct_all)} distinct clauses) ==")
    for name, table in auto.items():
        print(f"  -- {name}")
        print("  " + "reference \\ automatic".ljust(32) + "".join(o[:14].rjust(16) for o in outs))
        for lab in labels:
            print(f"  {lab[:30]:32s}" + "".join(f"{table[(lab, o)]:16,}" for o in outs))
        agree = table[(SELF, SELF)] + table[(OTHER, OTHER)] + table[(UNMARKED, UNMARKED)]
        scored = sum(v for (lab, _), v in table.items() if lab != CARER)
        extra = f"; wrong on {len(distinct_err[name])} distinct clauses" if name in distinct_err else ""
        print(f"  row error {100 * (1 - agree / scored):.2f}% ({scored - agree:,} of {scored:,} rows, carer requests excluded){extra}")

    print("\n== 7. Uncertain hand readings (need a Kinyarwanda speaker) ==")
    for p, why in UNCERTAIN.items():
        print(f"  - {p}  [{why}]")


if __name__ == "__main__":
    main()
