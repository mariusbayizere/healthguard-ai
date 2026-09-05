# French review pass — session summary

Written 2026-09-05, the same day as the English pass. The detail is in the
sections below; this is what a fresh session needs first.

## What this arm produced

`review/speaker_brief_french_v2.csv` — **256 rows on the 128-concept x
first/third spine**, which is the spine as it stands today. The English brief is
still 254/127 and is the one out of step: `OB13` was added on 2026-09-05.

```
194  drafted this pass, as utterances, with terminal stops
 50  applies=no, inherited from the Kinyarwanda spine
 12  held, each for a stated reason
194  reviewed on form, fidelity and register
 51  carrying a French doubt, over 39 concepts
  0  ruled — `your_phrasing` is empty on every row, by design
```

**Provenance, and this is the sentence for the paper: `source = machine_reviewed`.
Drafted by a model, reviewed by the same model, NOT verified by a native or
Rwandan French speaker.** The French arm is the same kind of artefact as the
English one and weaker than the Kinyarwanda arm in the same way: the Kinyarwanda
has a speaker who authors and rules, and this has one model doing both jobs.

**The load-bearing output is `review/rwandan-french-questions.md`** — 51 rows, 39
concepts, 21 questions. Three of them are the same question the Kinyarwanda and
English arms are blocked on (wheeze, stool, ear discharge) and should go to one
person at one time.

## The order things happened in

Same method as English, deliberately.

1. **Inventory before drafting** — the brief was built off the Kinyarwanda spine,
   which is what surfaced that `build_english_brief.py` no longer runs and that
   the collapse list it hardcodes is three concepts stale.
2. **Survey before each domain** — every batch was surveyed against the spine,
   the English brief and the v1 French before anything was drafted into.
3. **Draft, then check mechanically, then record what could not be checked.**

## What French has that English did not

The English arm could mirror the person split almost for free: *"every English
relation is third-person singular, so one authored sentence fits all eight with no
verb agreement to vary."* **That sentence is false in French**, and it is the
spine of this pass.

```
FR-1  agreement     an adjective or participle agreeing with {REL} is wrong for
                    half the expansions. 35 rows carry an FR-1 note. A real cost.
FR-2  possessive    son/sa/ses agrees with the POSSESSED noun. No ruling needed —
                    the mirror image of the English singular-"their" problem.
FR-3  orthography   v1 French is unaccented ASCII, everywhere, undeclared.
```

**FR-1 is the same shape as the Kinyarwanda object-marker problem that holds
`CR01` and `CR05`**: a third person is not obtainable from a first by
substitution. On this axis French is closer to Kinyarwanda than to English, and
that is the finding a fourth-language arm should expect to meet again.

```
python -c "import csv; print(sum(1 for r in csv.DictReader(open('review/speaker_brief_french_v2.csv')) if 'FR-1' in r['suggestion_note']))"
```

### FR-1's five sub-cases, each found by a row rather than by theory

| # | construction | rows | fix |
|---|---|---|---|
| 1 | opening participle | `CR02`, `HT07`, `NE07`, `EX37`, `PR01`, `EX23`, `HT05` | verb or noun instead |
| 2 | `etre` + inflecting adjective | `CC01`, `CC02`, `HT03`, `NE06`, `PA03` | idiom or noun |
| 3 | relative clause on `{REL}` | `GI01` | drop the clause |
| 4 | subordinate clause needing a subject pronoun | `IF06` | noun complement |
| 5 | temporal clause with a reflexive | `CC04` | adjectival phrase on a fixed-gender noun |

**The escape hatch is the one the speaker already uses.** Make a body part the
grammatical subject and `{REL}` a possessor — `Les levres de {REL} sont devenues
bleues` — and the agreement attaches to the body part, which has fixed gender.
That is `CR03`, `EX03`, `EX08`, `GI03`, `EX20`, `EX31`, and it is *exactly* the
construction the speaker chose in Kinyarwanda for a different reason (avoiding the
`-mu-` object marker, rule 2). **Two languages, two unrelated grammatical
pressures, one construction.** English needs neither and writes `{REL}'s lips`.

**And it collides with rule 2.** Rule 2 prefers `{REL}` as grammatical subject;
FR-1's fix makes it a possessor, and in French a possessor must FOLLOW its head.
So `lint_french.py` warns *"{REL} is not at the head"* on 9 rows, 5 of them the
body-part construction. **FR-1 wins, and the warning is noise here**: rule 2 exists
because a Kinyarwanda `{REL}` can end up inside an object marker, and a French
`de {REL}` is not that. Recorded so the next reader does not "fix" it.

### FR-2 is recorded as a non-problem so nobody re-opens it

French possessive determiners agree with the possessed noun, not the possessor.
`ses levres`, `sa tension`, `son ventre`, `son enfant` are right for all eight
relations with no choice to make. The English arm had to rule singular *their*
over a real ambiguity and had to write a paragraph defending it; French has
nothing to rule. `EX07` and `EX28` add the invariable indirect object `lui`
(`sa poitrine lui fait mal`), which does the same work again.

### FR-3 — v1 French is unaccented, nobody wrote it down, and v2 follows it

Measured, not assumed:

```
609,975  shipped v1 rows labelled french or mixed
      0  containing a single accented character
```

**These two counts are no longer reproducible from the working tree, and that is
not a caveat on them.** They were measured against `dataset/raw/symptoms_large.csv`
while it still held the v1 corpus — 1,000,000 rows, four languages. Later the same
day the Kinyarwanda session regenerated that path as **v2: 330,000 rows,
monolingual**, and the corpus is generated rather than tracked, so git does not
hold the old one. Re-running the greps below against the working tree today
returns zero French rows.

To re-derive, rebuild v1 first — `dataset/vocabulary_v1.py` carries the frozen v1
vocabulary and `make verify-full` is what pins that it still reproduces
byte-identically — then grep the rebuilt corpus. The numbers are facts about the
frozen v1 corpus, which is exactly the artefact the paper quotes; they are not
facts about anything on disk right now.

Every French string in the project is ASCII: v1's 46 phrases, all six frame slots
(`S'il vous plait`, `Ma mere`, `depuis la nuit derniere`, `depuis tot ce matin`),
`concepts.py`, the review sheet, and now all 205 candidates in this brief.
**No document declares this and no ruling records it.** It is a convention that
arrived by accident and has held perfectly.

v2 follows it, because v1 is frozen and must stay byte-identical, and a corpus
accented in half its rows would be worse than one accented in none. **But it means
the French arm ships orthographically incorrect French, and the paper should say
so** in the same breath as `machine_reviewed`. Re-accenting is a whole-corpus
decision with the same shape as the capital-`I` fix: it moves every frozen digest,
so it needs sequencing rather than a patch.

### A v1 defect in the French frame, the same shape as the English capital-`I`

**`et je suis inquiet` — 41,872 shipped rows of 1,000,000, 4.2%.** 25,791 labelled
french, 16,081 mixed. It is a `CONTEXTS` slot, so it attaches to any French frame
regardless of who the patient is, and there is no feminine form anywhere in the
corpus:

```python
CONTEXTS["french"] = ("", " et cela empire", " et je ne peux pas dormir",
                      " et je suis inquiet", " et je n'ai pas de medicament")
```

Found the same way the English defect was — by asking what FR-1 implies for the
frame, not just for the phrase. **Not fixed here**: it is a `dataset/` change and
`dataset/` was never touched. Two options, and they are the capital-`I` options:
fix at site B only and leave v1 carrying it, or re-render and move every frozen
digest. If site B only, then **no paper may quote one of these 41,872 rows**, and
that is avoidable only if someone remembers.

The neutral rewrite is `et cela m'inquiete`, which needs no gender.

## The `dataset/` change French needs, described and not made

The same change `english-review-pass.md` describes, plus French:
`RELATIONS` is keyed by language and has one key; every named set beside it is a
bare tuple of Kinyarwanda strings. The first French `{REL}` phrase in a restricted
domain hard-fails `build_families`, and there are now **100 of them**.

`review/french_relations.py` is the staging file, mirroring
`review/english_relations.py`. Nothing in `dataset/` imports it.

## CR03 — the row `concepts.py` was out of step on

Checked before use, as instructed, and it was the live one.

```
spine  english_gloss   central cyanosis - blue lips or fingertips
anchors concept_anchors central cyanosis - blue lips          <- narrowed 2026-09-05
concepts.py gloss       central cyanosis - blue lips          <- narrowed 2026-09-05
concepts.py french      mes levres et le bout des doigts sont devenus bleus
sheet D054              mes levres et le bout des doigts sont devenus bleus
```

The English arm narrowed the concept to lips only and narrowed the two glosses,
and recorded that the English phrase left in `concepts.py` was **dead** — the
brief superseded it — while *"the French one is live, because French has no brief
and `concepts.py` is the only place its phrasing exists"*.

**That is now fixed where it matters: the brief carries `Mes levres sont devenues
bleues.` and `Les levres de {REL} sont devenues bleues.`** The French column in
`concepts.py` becomes dead the same way the English one is, the moment the brief
is accepted as the source of truth for French.

**`concepts.py` has NOT been edited.** Two reasons: it is a shared file and this
project edits those only on an explicit ruling, and the phrase columns are already
due to be dropped under the source-of-truth ruling. If that ruling is not
accepted, `concepts.py` still asserts fingertips.

**Three records still disagree three ways, and the spine is the one nobody
narrowed.** The brief's `english_gloss` column is regenerated from the spine, so
every French CR03 row still displays *"blue lips or fingertips"* next to a
lips-only phrase. Narrowing the spine is the Kinyarwanda session's to do.

## Parity: what French owed, and what it turned out not to owe

`v1-cross-language-parity.md` found seven v1 positions where English, French and
Swahili agree and say something the Kinyarwanda does not, and ends *"French and
Swahili need the same"*. This arm paid that bill and re-derived every item rather
than trusting the table.

| id | v1 French claimed | corrected to | status |
|---|---|---|---|
| `EX04` | lips **bleues** | `ont change de couleur` | paid |
| `EX15` | signes de **deshydratation** | `je me sens tres faible` | paid |
| `EX35` | le **visage** deforme | `ma bouche est de travers` | paid |
| `EX37` | fatigue **pendant la journee** | time of day dropped | paid |
| `EX43` | **refuse** de manger | `ne mange pas` | paid |
| `EX42` | — | — | moot, collapsed into IF05 |
| `EX13` | ne peux pas manger | **no correction needed** | closed from the Kinyarwanda side |

**`EX13`'s gap closed and nobody had recorded it.** v1's Kinyarwanda was
`kuruka kenshi kandi SINDYA` — *I do not eat* — against a French *je ne peux pas
manger*. The speaker's rewrite is `sinshobora kurya`, **cannot** eat. The
Kinyarwanda moved to what the other three languages already said. Verified against
the first brief's `original_corpus_phrase`, not inferred from the table.

One of the five "mixed" positions was also cheap enough to close: **`EX25`**, where
the Kinyarwanda puts the severity on both the fever and the cough and the other
three put it on the cough only. `EX21` is left alone deliberately — there English
is the outlier and the French is already on the correct side.

## Where the English brief is now stale, and the French is not

The French brief was built today against today's spine. The English one was built
before the 2026-09-05 rulings and nothing told it. **This list is for the English
session, not a claim about French.**

| concept | the spine now says | the English brief still says |
|---|---|---|
| `OB06` | fetal demise, the baby has died | *"the baby is no longer moving"* — which is OB13's concept |
| `OB13` | exists; reduced fetal movement | absent entirely; the brief is 254/127 |
| `HT05` | authored, unheld, the **leg**, fracture disclaimed | held, and *"their arm"* |
| `CC04` | authored, unheld, `ngaramye` restored | held |
| `EX40` third | unheld after the PA01 ruling | held |
| `GI03` first | authored, `umwanda usa umukara` | drafted, hold lifted — agrees |
| `EX27` first | authored: fever, chills, suspected malaria | stale v1 *"fever and aching all over"* |
| `PA08` | `Mfite umuhaha` — names a condition | *"My child's ear is hurting..."* — see below |

**And one of them is a defect, not just staleness.** `PA08` first has the person
note *"usually third (the parent speaks); write first only if an older child would
say it"*, so its first person is the **child** speaking about their own ear. The
English brief has *"My child's ear is hurting and there is fluid coming out"* —
a carer's report, which is the third person's speaker, in a first-person slot.
Session-state records the Kinyarwanda arm nearly making this exact error on this
exact row and says to read the person note before writing a paediatric row. The
French first person is the child.

## Two record conflicts, flagged and not resolved

**`EX26`/`EX27`.** `english-review-pass.md` reports EX27 going `applies=no` as
part of the EX26 collapse — *"two more after it (EX27)"*. The spine has both
concepts `applies=yes`, with EX27's first person authored by the speaker. **The
spine is the record**, so both are drafted here and worded apart; whoever rules
the collapse owns the conflict.

**`OB12`.** Held on the spine because `Mama` is *"flagged, not decided"*. The
English arm decided it — `OBSTETRIC_RELATIONS_NO_MOTHER` — and that is a ruling
about the CONCEPT, so it transfers. Mirrored here, derived from the obstetric four
rather than retyped, and it sits in `PENDING_RULINGS` in **both** language files
because neither arm may edit `routine_relation_sets.csv`. That map is a temporary
second source of truth and is exactly the drift trap this project keeps hitting.

## `OB13` — not drafted, and French is evidence on the question

`OB13` holds *reduced fetal movement*, opened so that the actionable half of the
old `OB06` did not vanish when `OB06` was re-ruled to fetal demise. It is **the
presentation where triage still helps**: a mother who notices less movement can be
seen in time, a demise cannot. It has no phrase and is not awaiting one — the
speaker reports Kinyarwanda has no natural expression for it — and the recorded
instruction is *do not draft*. **Respected: both rows are held and empty.**

But the question that ruling left open is *"does this presentation need to exist in
the corpus if no natural Kinyarwanda phrase expresses it?"*, and **French answers
the lexical half of it immediately**: `le bebe bouge moins que d'habitude` is
ordinary French. So the premise is Kinyarwanda-specific.

That makes `OB13` the sharpest case of the distinction the English arm drew at
`NE05` — a **wording gap** (English fills it, the concept survives: `PA08`, `CR05`,
`GI03`) against a **content gap** (English fills it, the concept diverges) — and
it runs one step further: here the gap decides whether the concept exists at all.
Drafting French and not Kinyarwanda would be a concept present in one language and
absent in another, which is the `EX43` divergence at its maximum. Recorded rather
than acted on.

## Tooling, and one thing that is broken today

```
build_french_brief.py       builds/refreshes the brief; --check reports derived drift
apply_french_drafts.py      merges a batch; refuses to overwrite a ruled row
model_register_review_fr.py the model's register review; stamps provenance
check_french_grouping.py    the real splitter rule over the French inventory
lint_french.py              lint_phrases.check against the FROZEN v1 French frames
french_relations.py         staging for the dataset/ change, plus the FR-1 check
```

**`build_english_brief.py` does not run.** Not on the missing `english` key — it
fails earlier, mapping v1 Kinyarwanda phrases to positions:

```
KeyError: 'ububabare bukabije mu gituza kandi sinshobora guhumeka'
```

`dataset/vocabulary.py` is mid-rewrite for v2: `LANGUAGES` is down to
`("kinyarwanda",)` and the Kinyarwanda phrase list has been rewritten, so the v1
positional mapping no longer resolves against the working tree. **The French
builder reads the frozen commit instead** — `git show HEAD:...vocabulary.py`, into
a temporary module, read-only — and so does `lint_french.py` for the frame slots.

That is not a workaround, it is the correct source. **v1 is frozen and must stay
byte-identical**, so a positional mapping into v1 is a fact about the frozen file,
not about a tree being edited for v2. The English builder should be moved to the
same source; until it is, it cannot be re-run and its brief cannot be refreshed.

**A better source is appearing, and this arm deliberately did not switch to it.**
`dataset/vocabulary_v1.py` turned up untracked in the working tree during this
pass — the Kinyarwanda session extracting the frozen v1 into a named file. Its
bytes differ from `HEAD:dataset/vocabulary.py` (comments and docstring), but
**every slot this arm reads is identical**: `SYMPTOMS`, `OPENERS`, `SUBJECTS`,
`ONSETS`, `CONTEXTS`, `CLOSERS`, `LANGUAGES`. Checked by loading both and
comparing the objects, not the text.

A named file beats a commit ref, so `V1_REF`/`V1_PATH` in `build_french_brief.py`
should become an import of it **once it is committed**. It was not switched to
here because it is untracked, in flight, and in `dataset/`, which this arm may not
touch. One line, when it lands.

### Three places the French builder is better than the English one, and why

1. **The collapse list is derived, not hardcoded.** A concept whose both persons
   are `applies=no` is out of generation. The English builder lists twelve ids;
   the spine has fifteen, because `EX42`, `PA06` and `PA01` collapsed after that
   list was written. A derived list cannot go stale — the same argument that moved
   `applies` and `person_note` into `REGENERATED` on 2026-09-05.
2. **Collapse targets are parsed from the spine's own notes** (`collapsed into
   EX16`), with one declared exception for `IF07`, whose note phrases it
   differently. A collapsed concept matching neither **raises**, because a silent
   gap there is a dropped French candidate nobody is told about.
3. **`agreement_check` is a REGENERATED column**, so an FR-1 verdict cannot
   outlive the wording it was computed for. It caught the sheet drafts at `CC01`,
   `PA03`, `CR02`, `HT05`, `HT07`, `EX32` and `NE06` without being told to look.

### And one thing the tooling had to learn mid-pass

`apply_french_drafts.py` skips empty cells, so a batch whose prose said *"hold
lifted"* left the hold standing in the data — and the register review then skipped
those rows as unreviewable and said so. **`hold=no` is now the explicit lift**, and
it has to be written in the drafts file where the reason is written too. Twelve
holds were lifted that way, in `drafts/holds_lifted_french.csv`.

## Checks, and what each of them is worth

```
build_french_brief.py --check   256 rows, derived columns agree with their sources
check_french_grouping.py        200 phrases, 0 containments, 0 subsequence unions
lint_french.py                  200 candidates, 0 errors, 116 warnings
french_relations.py             every set mirrors its Kinyarwanda ruling by size
agreement_check                 3 FR-1 risks left, all on rows that generate nothing
```

The 116 lint warnings are three kinds and none is an error: **111** are the
connective `et`, which a `CONTEXT` clause also opens with — Kinyarwanda has the
identical warning on `kandi` and the ruling there is that forbidding it would push
the speaker back toward stilted phrasing; **9** are the `{REL}`-not-at-head warning
discussed under FR-1; **4** are phrases over sixteen words.

The 3 remaining FR-1 risks are `CC01` first and `NE06` first — held, with their
sheet drafts retained as the record of what is not accepted — and `EX32` first,
which is `applies=no` under rule 11. **Nothing that generates carries an unresolved
agreement risk.**

**Relation expansion was rendered, not assumed.** All 100 `{REL}` phrases were
expanded across their sets through the generator's own head/non-head lowercasing
rule. `Les levres de {REL}` renders `Les levres de mon enfant sont devenues
bleues.` — the mechanism that lowercases a non-initial relation was written for
the Kinyarwanda `Iyo umwana wanjye ahumeka` case and is exactly what the French
body-part construction needs. `L'enfant de mon voisin` and `Ma voisine` both
render correctly.

## Per-domain, what the survey found

| domain | rows | applies=no | held | drafted | the thing worth knowing |
|---|---|---|---|---|---|
| cardiac_respiratory | 28 | 0 | 2 | 26 | CR03 narrowed; EX04 parity paid; CR01/EX05 kept apart |
| haemorrhage_trauma | 28 | 4 | 1 | 23 | HT05 unheld and it is the **leg**; `se faire mordre` |
| gastrointestinal | 28 | 5 | 0 | 23 | GI01 third is where FR-1 costs a clause |
| infectious_fever | 30 | 4 | 0 | 26 | six holds lifted, all on Kinyarwanda words; EX31 recovered |
| neurological | 28 | 12 | 1 | 15 | EX35 parity paid; NE06 held on the English arm's clinical ruling |
| chronic_care | 28 | 5 | 2 | 21 | CC04 unheld; the EX09/CC03 containment never existed in French |
| preventive | 28 | 4 | 2 | 22 | PR05 is why the FR-1 exemption is keyed on the relation set |
| paediatric | 28 | 16 | 0 | 12 | PA03's `mou`; PA08's person error in the English brief |
| obstetric | 30 | 0 | 4 | 26 | `Ma voisine` makes the set feminine, which buys `elle` back |

**`EX31` is recovered rather than invented**, and it is the one place a v1 French
string was found for a row the builder says has none. EX31 is the row the speaker
*added*, so it has no v1 counterpart — but `ex-concept-drift.md` records that the
rewrites rotated three concepts across three ids and that v1 `EX30`'s concept, the
runny nose, is where EX31 now sits. v1's French for EX30 is `un nez qui coule
legerement`. The string is v1's; the row it is attached to is not the row v1
attached it to, so the provenance stays `new_draft`.

## What is not done

- **`dataset/` untouched.** Two changes are described and not made: the
  language-keyed relation sets, and the `et je suis inquiet` frame defect.
- **`concepts.py` untouched**, including its CR03 French. See above.
- **The Kinyarwanda brief untouched.**
- **Nothing committed.**
- **`your_phrasing` is empty on all 256 rows.** Nothing here is ruled, by design.
- **The spine's CR03 gloss is still `blue lips or fingertips`** and is not this
  arm's to narrow.
- **The accent question is recorded, not decided.**
