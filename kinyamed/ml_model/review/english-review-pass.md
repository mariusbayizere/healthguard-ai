# English review pass — session summary

Written 2026-09-05. The detail is in the sections below; this is what a fresh
session needs first.

## What this arm produced

`review/speaker_brief_english_v2.csv` — 254 rows on the same 127-concept x
first/third spine as the Kinyarwanda brief.

```
190  drafted this pass, as utterances, with terminal stops
 50  applies=no, inherited from the Kinyarwanda spine
 21  held, each for a stated reason
184  reviewed on form, fidelity and register
 47  carrying a Rwandan-English doubt
  0  ruled — `your_phrasing` is empty on every row, by design
```

**Provenance, and this is the sentence for the paper: `source = machine_reviewed`.
Drafted by a model, reviewed by the same model, NOT verified by a native or
Rwandan English speaker.** The English arm is a weaker artefact than the
Kinyarwanda arm, and the difference is in kind, not degree: the Kinyarwanda has a
speaker who authored and ruled; the English has one model doing both jobs.

## The order things happened in, because it explains the shape

1. **Inventory before drafting.** The brief was built off the Kinyarwanda spine
   rather than off the old review sheet, which is what surfaced that the sheet was
   four days stale and that 10 of its 80 drafts were for collapsed concepts.
2. **Survey before each domain.** Every batch was surveyed for duplicate
   candidates first. That is what caught the paediatric cluster — five of ten new
   concepts restating v1 concepts — before any of them were drafted into.
3. **Draft, then check mechanically, then record what could not be checked.**

## What the English arm found that was not about English

Most of the session's findings were Kinyarwanda-side or corpus-side, surfaced by
needing to attach English text to concepts:

| finding | where |
|---|---|
| 7 EX rewrites moved off their v1 concept; 6 stand | `ex-concept-drift.md` |
| 7 v1 positions where en/fr/sw agree and Kinyarwanda differs | `v1-cross-language-parity.md` |
| 5 Kinyarwanda phrase groups holding more than one concept | `kinyarwanda-phrase-group-collisions.md` |
| 4 paediatric duplicate clusters, EX26/EX27, EX42/PA06 | `paediatric-duplicate-rulings.md` |
| **48,398 shipped v1 rows with a lowercased pronoun `i`** | `rendering-defects-english.md` |
| a second onset problem: the phrase already carries the time | `docs/urgency-frame-coupling.md` section 9 |
| shared-anchor duplicate detector, 3 urgency conflicts | `shared_anchors.py` |

## The one thing to read if you read nothing else

`review/rwandan-english-questions.md`. 47 rows, 22 concepts, 19 questions.
**The verdicts in the brief are a model's; these are what the model could not
settle.** Three of the groups — CR05 wheeze, GI05 stool, PA08 ear discharge — are
questions the Kinyarwanda is blocked on too, and should go to the same person at
the same time.

## Standing constraints this arm worked under

- **`dataset/` was never touched.** Two changes were needed and both are described
  rather than made: the language-keyed relation sets, and the capital-`I` fix.
- **Shared files were edited only on an explicit ruling** — `concept_anchors.csv`
  twice, `concepts.py` once. Byte-wise, because that file is CRLF and a text-mode
  write rewrites all 71 lines.
- **The drafter never writes the reviewer's columns.** `apply_english_drafts.py`
  still refuses `verdict_register`; `model_register_review.py` is a separate tool
  so the model review is a labelled act rather than a loosened invariant.

## Tools, and what each is for

```
build_english_brief.py     builds/refreshes the brief; --check reports derived drift
apply_english_drafts.py    merges a batch; refuses to overwrite a ruled row
model_register_review.py   the model's register review; stamps provenance
check_english_grouping.py  the real splitter rule over the English inventory
shared_anchors.py          concepts citing one anchor — a duplicate detector
english_relations.py       staging for the dataset/ relation-set change
blind_register_arm.py      the blind arm — built, unrated, needs a rater
```

Run `build_english_brief.py --check` and `check_english_grouping.py` after any
Kinyarwanda change. Both import the real rules, so neither can drift from what
the generator and splitter actually do.

---

# English review pass — state, and the one change `dataset/` needs

English work is confined to `review/`. This note carries the single change that
is not, so the Kinyarwanda session can make it.

## The `dataset/` change, and why it cannot wait for v2 build time

`RELATIONS` in `dataset/vocabulary.py` is keyed by language and has one key,
`kinyarwanda`. Every *named* set beside it — `CHILD_RELATIONS`,
`HOUSEHOLD_RELATIONS`, `ADULT_RELATIONS`, `DOMAIN_RELATIONS` — is a bare tuple or
dict of Kinyarwanda strings with no language key at all.

**That combination hard-fails the v2 build the first time an English `{REL}`
phrase exists in a restricted domain.** `build_families` does:

```python
allowed = CONCEPT_RELATIONS.get(phrase, DOMAIN_RELATIONS.get(domain))
pool = RELATIONS.get(phrase_lang, ("",))
...
pool = tuple(r for r in pool if r in allowed)
if not pool:
    raise SystemExit(...)
```

`DOMAIN_RELATIONS["obstetric"]` returns the Kinyarwanda obstetric four. Filtering
`RELATIONS["english"]` against them leaves nothing, so the build raises. It has
not fired yet only because no English phrase carries `{REL}`. The obstetric
drafts in `speaker_brief_english_v2.csv` are the first fourteen that will.

### The change

1. Add an `"english"` key to `RELATIONS` — the eight, in the Kinyarwanda order,
   using the wording v1's own `SUBJECTS` slot already chose (Umukecuru is
   "My grandmother" there):

   ```
   "My child", "My wife", "My husband", "My mother",
   "My father", "My sister", "My neighbour", "My grandmother",
   ```

2. Make the named sets language-keyed, keeping the bare names bound to the
   Kinyarwanda ones so every existing import and every test that mutates them in
   place keeps working:

   ```python
   CHILD_RELATIONS_BY_LANGUAGE = {"kinyarwanda": (...), "english": (...)}
   CHILD_RELATIONS = CHILD_RELATIONS_BY_LANGUAGE["kinyarwanda"]
   ```

   Same shape for `HOUSEHOLD_RELATIONS`, `ADULT_RELATIONS` and
   `DOMAIN_RELATIONS`. `NO_RELATIONS` is `()` and needs no key.

3. One call site in `dataset/generate_large_dataset.py`:

   ```python
   by_language = DOMAIN_RELATIONS_BY_LANGUAGE.get(phrase_lang, {})
   allowed = CONCEPT_RELATIONS.get(phrase, by_language.get(domain))
   ```

The English member lists are written out in `review/english_relations.py`, which
is a **staging file** — nothing in `dataset/` imports it and nothing generates
from it. It exists so the wording is decided and reviewable now.
`python review/english_relations.py` checks each English set is the same size as
the Kinyarwanda ruling it mirrors, and that `ADULT_RELATIONS` is still
`ALL_RELATIONS` minus the child, in order.

### Evidence it is safe

Both changes were applied, verified, and reverted before this note was written:

- `python -m pytest -q` — **111 passed**
- `make verify-full` — **8/8, every committed digest re-derived from seed 42**

v1 does not move, because no v1 phrase contains `{REL}` and the addition is
purely new keys.

## What is in `review/` now

| file | what it is |
|---|---|
| `speaker_brief_english_v2.csv` | the brief, 254 rows on the 127-concept spine |
| `build_english_brief.py` | builds and refreshes it; `--check` reports derived-column drift |
| `apply_english_drafts.py` | merges a domain's drafts in; refuses to overwrite a ruled row |
| `drafts/obstetric_english.csv` | the obstetric batch, 27 rows |
| `english_relations.py` | staging for the change above |
| `blind_register_arm.py` | the blind arm; `--build` / `--score` |
| `blind/register_arm_items.csv` | 92 items to rate — no origin column |
| `blind/register_arm_key.csv` | the key. Not to be opened until the ratings are in |

## Two things a Kinyarwanda session should know

**The EX ids are positional, and position is not concept.** An EX id names the
slot a v1 phrase occupied. Several of the speaker's rewrites landed on a
different presentation than the phrase they replaced — `EX30`'s slot held "mild
runny nose" and its rewrite is "I cough a little but have no fever", which is why
it collapsed into `CR07` and why `EX31` exists at all. `EX29` did the same, cough
to fever, and `EX47` narrowed from general nutrition advice to infant feeding,
which puts it very close to `PR08`. This is recorded per row in the English
brief's `suggestion_note`; it is a Kinyarwanda-side fact that happens to have
been surfaced by needing to attach English text to concepts.

**One v1 English pair already shares a phrase group.** `severe abdominal pain`
(EX14) is a substring of `severe abdominal pain in pregnancy with bleeding`
(EX38), so the substring closure joins them and the phrase holdout cannot
separate them. Both are v1 strings, so this is pre-existing, not introduced —
but it is the failure shape freeze-checklist step 12 says will multiply as
phrases are added, and there is now a concrete instance to point at. EX14's
Kinyarwanda rewrite (`inda irandya cyane`) is a paraphrase, so an English rewrite
may dissolve it.

## Flagged for the Kinyarwanda session

**PR05 and OB11 survive on one character.** Their third persons share **29** of a
30-character `PREFIX_UNION_CHARS` threshold:

```
{REL} aratwite kandi ashaka kwisuzumisha kwa muganga bwa mbere.
{REL} aratwite kandi ashaka kujya kwa muganga kwisuzumisha.
                             ^ divergence at 29
```

One more shared character and a ROUTINE antenatal booking and a ROUTINE antenatal
check become one phrase group. The frame is the `kujya kwa muganga kwisuzumisha`
one section 7 already tracks as shared with CC09, CC10 and PR07. English solved
its own version by moving the axis word to the head; Kinyarwanda cannot use that
fix, because `bwa mbere` belongs at the end of the clause.

**EX04 disagrees with itself across persons.** The first says `iminwa yanjye
yahindutse ibara` (changed colour); the third says `iminwa ye yahindutse
ubururu` (turned blue). One concept, two claims. Blue is right — rule 11 names a
patient's own lips as directly perceptible and CR03 is the speaker's own
`Iminwa yanjye yahindutse ubururu` — so the first person is the row out of step.

**EX43's third still says `ntabwo arimo kubasha kurya`.** The reviewer ruled the
concept back to not-eating with the label kept at URGENT, and the English is
drafted that way. Until the Kinyarwanda third moves with it, English and
Kinyarwanda disagree on this row — a gap opened deliberately, not one found.

**EX27 duplicates EX26, and EX42 duplicates PA06.** Both in
`review/ex-concept-drift.md`.

## PREFIX_UNION_CHARS — the question was dissolved, not answered

**Superseded 2026-09-05.** The threshold was removed from `split_dataset.py`
entirely and replaced by an ordered-subsequence rule plus explicit
`GROUPED_CONCEPTS` declarations. The measurement behind that: over 163
Kinyarwanda phrases the prefix rule made ten prefix-only unions, **one right and
eight wrong** — it folded the domain grammar it had been set above, merging
`{REL} afite umuriro mwinshi kandi ...` across three unrelated presentations and
merging the recorded EX01/EX05 chest-pain axis. It also leaked in its own
motivating example: EX18/EX20 third unioned at exactly 30 while their first
persons shared 24 and did not.

The English half of that analysis recommended keeping 30, on the grounds that no
English pair came within four characters of it. That recommendation is moot; the
Kinyarwanda half is what carried.

**What survives from it, and is worth keeping:** the per-language framing was
sound and the measurement is why the rule went. A single number calibrated on one
language's grammar could not serve both, and the answer turned out to be that it
could not serve *either*.

**One consequence to be aware of.** `OB09` was reworded from
`I am pregnant and I have a fever` to `I have a fever and I am pregnant` to break
a 30-character union with `OB01` third. That union no longer exists as a
mechanism. The reword stands on its second argument — leading with the symptom is
the better patient register — not on the one it was made for.

### Checking English under the rule that replaced it

`python review/check_english_grouping.py`, after every batch. It imports the real
rule from `split_dataset.py`, so it cannot drift from what the splitter does.

Current state: **147 English strings, 1 containment, 0 subsequence unions.** The
containment is the pre-existing v1 pair (`severe abdominal pain` inside `severe
abdominal pain in pregnancy with bleeding`).

**Watch the short phrases rather than waiting for a union.** English packs
meaning into function words that recur everywhere — "I have a", "and my" — where
Kinyarwanda packs it into inflected verbs that do not, so a short English phrase
is a likelier subsequence of a long one than a short Kinyarwanda phrase is. The
tool prints the five shortest candidates for that reason. Today they are v1
noun-phrase fragments awaiting rewrite (`vomiting blood`, `severe abdominal
pain`); once rewritten as utterances they get longer and safer, so the risk falls
as the pass proceeds rather than rising.

## Concept collapses ruled during the English pass — execution checklist

All four are cross-language and none is executed here. English side is done for
each: the survivor is drafted, the collapsing concept is held with the ruling on
its row, and no English text exists for anything that is going away.

| ruled | survives | why it survives | still to do, Kinyarwanda side |
|---|---|---|---|
| PA06 -> **EX42** | EX42 | carries the speaker's authored wording | `applies=no` both PA06 rows; anchor `IMCI: MEASLES` re-keyed to EX42 |
| PA03 -> **EX32** | EX32 | authored wording; floppy is an unrecorded axis | `applies=no` both PA03 rows; anchor re-keyed to EX32 |
| PA01 -> **EX33** | EX33 | authored wording, PA01 has none | `applies=no` both PA01 rows; anchor re-keyed to EX33 |
| EX40 -> **IF02** | IF02 | both persons authored, plus an anchor | `applies=no` both EX40 rows; **EX40's wording becomes IF02's second phrasing**, not discarded |

**Row target falls by four concepts.** Recompute rather than subtracting by hand:
EX40 and PA01 both had an `applies=yes` third and an `applies=no` first, so they
are not four identical subtractions.

**EX40's second phrasing is the one that can be lost silently.** The other three
collapses discard nothing, because the collapsing concept had no authored text.
EX40 does — `above 40 degrees` is a real distinction the speaker wrote, kept on
the EX16/EX17 pattern. It is sitting in EX40 third's `suggested_english` on a
held row. If the collapse is executed by marking rows `applies=no` and nothing
else, that wording goes and nobody notices.

### Done here, and it touched a shared file

`review/concept_anchors.csv`, one line, at the reviewer's instruction:

```
-IF02,...,fever with convulsions,IMCI general danger sign: convulsions,...
+IF02,...,fever with convulsions,IMCI: convulsions -> VERY SEVERE FEBRILE DISEASE,...
```

The file has CRLF line endings; the edit was made byte-wise so the diff is one
line rather than 71. It brings IF02 into line with IF01 and IF05, which anchor to
what fever-plus-the-sign classifies as, and it records the fever axis separating
IF02 from EX33 so the next duplicate survey does not re-open the question.

**`review/shared_anchors.py` now reports two remaining conflicts**, both outside
paediatric and neither ruled: `HT02`/`HT05` (same domain, CRITICAL vs URGENT) and
`CR02`/`CC04` (chest pain vs heart failure, sharing a coarse BEC module anchor).

## Flagged from the cardiac_respiratory batch

**`EX02` and `CR02` are one phrase group in Kinyarwanda, by containment.** The
speaker's CR02 first person literally contains their EX02:

```
EX02  guhumeka birangora cyane
CR02  Guhumeka birangora cyane ku buryo ntabasha no kuvuga neza
```

They are different concepts — *serious difficulty breathing* against *too
breathless to complete a sentence* — and the substring closure joins them, so the
phrase holdout cannot separate them. Not introduced by the English pass and not
fixable from it; the English drafts deliberately do not inherit the shape.

**`CR03`'s gloss claims more than the speaker's phrase does.** The gloss is
*central cyanosis - blue lips or fingertips*; the phrase is
`Iminwa yanjye yahindutse ubururu.`, lips only. English follows the phrase under
the parity ruling. If the concept is meant to carry fingertips, the gloss and
both languages need it — not English alone.

**`EX29`'s English candidate now describes CR07's concept.** It is still the
stale v1 `a mild cough with no fever`, while EX29's Kinyarwanda was rewritten to a
mild one-day fever and CR07 now carries the mild-cough wording from the EX30
collapse. The correction belongs to the infectious_fever batch; recorded here so
it is not lost in between.

**`EX26` and `EX27` are still an unruled duplicate.** Both now say fever, chills
and suspected malaria after the EX27 rewrite; EX26 is the one phrase of the 47
the speaker left byte-identical. It is the largest open item in infectious_fever
and it should be ruled before that domain is drafted. Full evidence in
`review/ex-concept-drift.md`.

## CR03 narrowed to lips — done, and French is now out of step

Ruled by the reviewer: the concept is lips only; fingertips would be a new
concept, not a gloss stretch. Narrowed byte-wise in both places that carry it:

```
review/concept_anchors.csv   central cyanosis - blue lips or fingertips -> central cyanosis - blue lips
review/concepts.py           same
```

**Two consequences the narrowing does not itself fix**, both in `concepts.py`,
whose English and French phrase columns are due to be dropped under the
source-of-truth ruling but have not been yet:

```
english  "my lips and fingertips have turned blue"
french   "mes levres et le bout des doigts sont devenus bleus"
```

Both still assert fingertips under a lips-only gloss. The English one is dead —
the brief is the source of truth and carries `My lips have turned blue`. **The
French one is live**, because French has no brief and `concepts.py` is the only
place its phrasing exists. French should narrow with it.

## haemorrhage_trauma — surveyed, 23 of 28 drafted

| | |
|---|---|
| concepts | 14 |
| `applies=no` | 4 — HT01 and HT06, both persons, collapsed into EX18 and EX22 |
| held | HT03 first (clinical), HT05 both (concept question, below) |
| Kinyarwanda authored | 20/28 |

**`HT05`'s hold was narrowed, not lifted.** Its Kinyarwanda block is lexical —
no attested word for a deformed limb exists in any source, only the fracture
vocabulary — so English has the wording available. But the block has a concept
consequence: the recorded alternative is ruling that the concept *becomes* "broken
limb after a fall", and then the gloss and anchor move too. Drafted to the gloss
as it stands and held, so it cannot be accepted into a state where English says
*deformed* and Kinyarwanda says *broken* under one id. That is the EX43 shape and
it is worth not repeating.

**`HT03` third is drafted while its first stays held.** The hold turns on whether
a confused patient can report their own confusion — rule 11's question. An
observer reporting it has no such problem, and the Kinyarwanda holds only the
first person too.

**`EX18`/`EX20` was worded apart deliberately.** In Kinyarwanda EX18 is every word
of EX20 in order, so they are one phrase group. The English leads EX20 with the
nose rather than with the bleeding, so neither contains the other and the two
concepts stay separable in the English holdout.

**`EX22`'s second phrasing is blocked upstream.** HT06 collapsed into it with the
ruling that the swollen wording be kept as a second phrasing, and that slot is
still empty in Kinyarwanda pending the speaker. Writing an English second phrasing
first would invent the wording the ruling reserved for them.

**`HT02`/`HT05` share an anchor and disagree on urgency** — CRITICAL against
URGENT on `BEC Module 2: approach to trauma`. Flagged, not ruled; it looks like a
coarse module-level anchor covering two real presentations, the same shape as
CR02/CC04.

## gastrointestinal — surveyed, 20 of 28 drafted

| | |
|---|---|
| concepts | 14 |
| `applies=no` | 5 — EX17 both, GI08 both, GI04 first |
| held | GI03 both (lifted, below), GI04 third (collapse into GI04 pending) |
| Kinyarwanda authored | 22/28 |

**Two of the five phrase-group collisions land in this domain**, and both were
worded apart rather than inherited:

- `EX14` inside `GI07` — `inda irandya cyane` sits whole inside
  `Inda irandya cyane kandi ububabare ntibuhagarara.`
- `EX14` inside `EX38` — the third person is an ordered subsequence of the
  obstetric row.

So EX14 collides in two directions in Kinyarwanda and in neither in English.
`GI07` third says *the stomach* rather than *their stomach* for exactly this
reason: the possessive would have made EX14 third a subsequence of it.

**`GI03`'s hold is lifted.** Purely lexical: no word for stool exists in the
approved Kinyarwanda — `umwanda`, `amabyi`, `ubwiherero`, `kwituma` and `amase`
were all checked and rejected, and an outreach question is open. English has no
such gap. Third in the series after PA08's ear term and CR05's wheeze.

**`GI05` carries a lexical divergence worth not mistaking for a parity one.** The
speaker's phrase is `Mfite impiswi zirimo amaraso.` — *diarrhoea* with blood in
it, not *stool* — because the stool noun was unavailable to them. The gloss says
blood in the stool and English follows the gloss. This is the opposite of the
EX15/EX35/EX37 cases: there the Kinyarwanda was the better report and English was
overclaiming, here the Kinyarwanda is narrower only because a word was missing.
**A vocabulary constraint is not a finding about how patients speak** and should
not be propagated.

**`EX16` can have a second phrasing and `EX22` cannot.** EX17's wording survived
its collapse into EX16 and is sitting in the speaker's `second_phrasing_optional`,
so the English equivalent is derivable — proposed in the row note rather than
written into the reviewer's column. EX22's equivalent slot is still empty pending
the speaker, so nothing can be proposed there without inventing it.

### A frame collision that no wording can fix

`EX12`, `GI06` and `CR06` each carry their own duration — three days, more than
two weeks, more than two weeks — and the ONSET slot supplies another, so they
render as `...for three days for three days`. **The duration cannot be dropped**:
it is the axis between EX12 and GI06. The Kinyarwanda has the identical collision
with ` kuva hashize iminsi itatu`. `lint_phrases.py` does not catch it, because it
only checks whether the phrase's last word begins an onset.

This is `docs/urgency-frame-coupling.md` territory rather than a drafting
mistake, and it is now measured in a second language.

## neurological — surveyed, 10 of 28 drafted, and 12 rows do not exist

| | |
|---|---|
| concepts | 14 |
| `applies=no` | **12** — NE01-NE04 and NE08 both persons, plus EX32 and EX33 first |
| held | NE06 first, added here |
| Kinyarwanda authored | 6/28 |

The five collapsed concepts are the largest `applies=no` block in the corpus, and
that is the domain's whole story: neurological was surveyed once already, five of
its eight new concepts turned out to restate v1 concepts the speaker had authored,
and what is left is thin.

**Two new vocabulary-gap findings, and they are not the same kind.**

`NE05` is blocked in Kinyarwanda on a word for *light* — `urumuri` is attested
nowhere, `izuba` once and meaning sunbathing — so its Kinyarwanda draft carries
two of the concept's three signs. English carries all three.

This is **not** the PA08 / CR05 / GI03 pattern, and the difference matters. Those
three were blocked on a word for a thing the phrase names — ear, wheeze, stool —
and the concept survived intact the moment English supplied it. Here the missing
word costs a **sign the concept is defined by**. Two languages would be describing
different presentations under one id rather than the same presentation in
different words.

```
wording gap    PA08, CR05, GI03    English fills it, concept unchanged
content gap    NE05                English fills it, concept DIVERGES
```

Flagged rather than held, because the English is right to its gloss — but if the
Kinyarwanda stays at two signs, that is a parity divergence of the EX43 kind and
should be ruled, not left.

**`NE06` first is not drafted, and is now held.** The Kinyarwanda reason is
clinical and transfers unchanged: *whether a patient who can accurately report new
confusion is meaningfully confused is a clinical question; the first-person row is
not written until a clinician settles it.* English does not write it either. The
third is drafted — an observer reporting confusion has no such problem, the same
split as HT03.

**`EX34` diverges structurally, and English is the better-off language for once.**
It is the one authored Kinyarwanda third still outside the relation architecture:
its subject is `uruhande` (the side) and the patient is a possessor, so it needs
`rw'umubiri wa {REL}` — a rewrite only the speaker can make — and until then it
generates a single instance. English puts `{REL}` in subject position naturally
(`{REL} cannot move one side of their body`) and expands over all eight. Same
content, different row counts. An argument for the Kinyarwanda rewrite.

**A small drafting rule this domain forced.** `EX36` and `EX37` thirds are
CHILD_RELATIONS — a carer reporting a child's mild headache or tiredness — and
both say *says*: `{REL} says their head hurts but not badly`. That is not padding.
A mild headache is not observable, so a carer can only be relaying what the child
told them. Contrast `EX32` and `EX35`, where the sign is visible and no reporting
verb is needed. Worth applying wherever a third person reports a subjective
symptom.

## preventive — surveyed against chronic_care, drafted first, 20 of 28

Drafted ahead of chronic_care on every measure that matters:

| | preventive | chronic_care |
|---|---|---|
| `applies=no` | 4 | 5 |
| held | 2 (PR02 both, out of generation) | 3 (CC01, CC02, CC04 firsts) |
| `needs_clinician` | **0** | 3 |
| Kinyarwanda authored | **22/28** | 18/28 |

Every remaining preventive row is now drafted except PR02, which is out of
generation pending the service-design ruling, and the four `NO_RELATIONS` thirds
(EX44, EX45, PR06, PR07) that are `applies=no`.

**The EX47 drift is closed and the flag is discharged.** When the concept-drift
survey ran, EX47's Kinyarwanda had been rewritten to `kugirwa inama ku biryo byo
kugaburira umwana` — infant feeding, which is PR08's concept. It has since been
returned to `Ndashaka inama ku mirire myiza.`, general nutrition. Six of the
original seven movements still stand; `review/ex-concept-drift.md` is updated.

**PR01 is the pair that falsified a claim in the closure doc.** Its `{REL}` sits
mid-phrase, so its first and third share 42 leading characters — and
`docs/phrase-group-closure.md` says a prefix rule "can never catch a first/third
pair, because a third-person phrase begins with {REL} … prefix is 0 by
construction". That held when every `{REL}` was sentence-initial. It no longer is.

**PR07's short form was a deliberate Kinyarwanda choice and the English keeps it
anyway.** The speaker wrote `Ndashaka kwisuzumisha kanseri y'inkondo y'umura`
rather than the longer `Ndashaka kujya kwa muganga kwisuzumisha X` frame, because
that frame shares 40 characters with CC09 and CC10 and would have grouped all
three. English inherits no such constraint, but the short form is also the better
register, so nothing is lost by matching them.

### chronic_care, still to do — what the survey found waiting

Three first persons are held and all three holds are **clinical, not lexical**, so
none of them lifts for English the way PA08, CR05 and GI03 did:

- `CC01` diabetic ketoacidosis — whether a drowsy patient can report drowsiness
- `CC02` hypoglycaemia — the same question about confusion, explicitly NE06's
- `CC04` swollen legs and breathless lying flat — re-held on one word, `ngaramye`,
  which is what makes the phrase orthopnoea rather than ordinary breathlessness

`CC03` inherits the `EX09` containment collision — `umuvuduko w'amaraso wanjye
wazamutse cyane` sits whole inside CC03's phrase — so the English will need
wording apart, the same treatment EX14/GI07 got. And `CC06`'s stale English
carries its own time expression, which is now section 9's business.

## chronic_care — 20 rows, and a correction to my own count

I said last time that chronic_care had "9 workable rows". **That was wrong** — it
counted only the rows with no text at all. Eleven more carried stale 2026-08-31
sheet drafts or v1 noun phrases, which every other domain has had redrafted as
utterances. Drafting only the nine would have left this the one domain still
carrying unreviewed machine text in its first persons. 20 rows drafted; the three
clinical holds stand untouched.

**The three holds stay, and none of them is the kind that lifts.** CC01, CC02 and
CC04 firsts are held on clinical questions — whether a drowsy patient can report
drowsiness, whether a confused one can report confusion, and one Kinyarwanda word
(`ngaramye`) that is what makes CC04 orthopnoea rather than ordinary
breathlessness. The first two transfer to English unchanged. **All three thirds
are drafted**, because an observer reporting the sign has none of those problems —
the same split as HT03 and NE06.

**`EX09` inside `CC03` is mirrored, not worked around.** The faithful English does
what the Kinyarwanda does:

```
EX09  My blood pressure has gone very high
CC03  My blood pressure has gone very high and my head is aching badly
```

Wording them apart would have been a contortion around a source-side problem the
Kinyarwanda session is already fixing, and it would go unmotivated the moment they
fix it — which is exactly what happened to the OB09 reword when
`PREFIX_UNION_CHARS` was removed underneath it.

`check_english_grouping.py` now carries an `INHERITED` list so this stays a signal
rather than turning the tool permanently red. **Delete the entry when the
Kinyarwanda pair is reworded** and let the check confirm it.

**`CC06`'s stale draft is gone.** It was `I finished my HIV medicine several days
ago` — the phrase section 9 uses to refine section 8's own counter-example. The
speaker's Kinyarwanda is `Nta miti ya SIDA mfite.`, which carries no duration, and
the English now matches: `I have no HIV medicine left`.

**`CC09`/`CC10` need a declaration in English if they need one at all.** They are
the one union `PREFIX_UNION_CHARS` made correctly and are now declared in
`GROUPED_CONCEPTS` on the Kinyarwanda side. The English pair does not nest — the
disease word sits mid-phrase rather than clause-final — so sharing a phrase group
in English is a declaration, not something the rule will produce.

**`EX11` is still an open drift.** Its rewrite broadened *follow-up after previous
treatment* into *continuing check-ups generally*, close to CC09, CC10 and EX44.
The English follows the rewrite, so if the concept is narrowed back this row moves
with it.

## infectious_fever — the last domain, 22 rows drafted

15 concepts, 30 rows. Four `applies=no` before this batch (EX30, IF07), two more
after it (EX27). Nine rows were held; **six of those holds are lifted** and the
reasoning is the same one four times over.

**IF01, IF03, IF04 and IF06 were held on unvalidated Kinyarwanda WORDS, not on
their concepts.** `ijosi ryarakomeye` for a stiff neck, the precision of the
unable-to-drink draft, `nkabira ibyuya` for sweating, `iyo nihagarika` for
dysuria. Every one of those concepts is a settled IMCI sign with ordinary English
wording. Fourth through seventh in the series after PA08, CR05 and GI03. Each
third person was held only because its first was — *"drafting the third would
transform a guess"* — which stops applying once the English first is not a guess.

**`EX29`'s English is corrected.** Its candidate was still the stale v1 `a mild
cough with no fever`, which after the EX30 collapse describes CR07's concept and
not its own. The speaker's rewrite moved EX29 from cough to fever, and IF07 was
removed as a duplicate of the result. The corrected row carries a duration and
joins section 9's list.

### A fragment the collapse ruling preserves

`EX26` survives the collapse, and its Kinyarwanda is a **bare noun phrase declared
`form=utterance`**:

```
ibimenyetso bya malariya, umuriro n'imbeho     "malaria symptoms, fever and chills"
```

No verb. As an utterance it renders as a fragment with no main clause — the
EX44-EX47 bug, in a row that fix never reached, **because EX26 is the one phrase
of the 47 the speaker left byte-identical and so was never revisited**. The third
person already carries `afite`, which is what makes the gap visible.

The minimal fix is the one they used on EX44: prefix `Mfite`. English supplies the
verb because English must; the Kinyarwanda still needs it.

**Scanned for others.** A 1sg-marker check over all 83 authored first-person rows
flagged 8; hand-reading leaves **1**, this one. The other seven are grammatical
sentences whose subject is a body part with a possessive (`Iminwa yanjye
yahindutse ubururu`) or whose first person is an object marker (`guhumeka
bira-ng-ora cyane`). Another heuristic that is a lead generator and not a verdict.

### And a direction worth noticing in the ruling itself

The surviving wording is v1 text the speaker approved by leaving it. The demoted
wording — `mfite umuriro kandi numva mfite imbeho, nkeka ko ari malariya` — is
text they actively wrote, is a proper first-person sentence, and is the better
patient register of the two. Recorded, not argued: the concept ruling is right
either way, and which wording leads is a separate call that is still open.

## The review, and what its provenance actually is

Ruled 2026-09-05: the reviewer cannot judge Rwandan hospital English, so the
model reviewed all three verdicts on all 186 reviewable rows.

**`source = machine_reviewed` on every one of them. Drafted by a model, reviewed
by the same model, NOT verified by a native or Rwandan English speaker.** That
string is what belongs in the paper, unqualified. The English arm is a
weaker artefact than the Kinyarwanda arm and the difference is not a matter of
degree: the Kinyarwanda has a speaker who authored and ruled, and the English has
one model doing both jobs.

**The three-way verdict split was designed to prevent exactly this.** Register had
a separate owner because it is the judgement the drafter cannot make about their
own work. With one reviewer holding all three verdicts, the split's purpose is
gone and only its bookkeeping remains. `review/model_register_review.py` is a
separate tool from the drafter for that reason — `apply_english_drafts.py` still
refuses to write `verdict_register`, so the model review is a distinct, labelled
act rather than a loosened invariant.

**So the flag list is the load-bearing output, not the verdicts.**
`review/rwandan-english-questions.md` — 47 rows, 22 concepts, grouped into 19
questions. Three of the groups (CR05 wheeze, GI05 stool, PA08 ear discharge) are
places where the **Kinyarwanda was blocked on the same question**, which is not a
coincidence: they are the concepts nobody has settled in either language.

| verdict | result |
|---|---|
| form | 186/186 `utterance`, all render as complete clauses |
| fidelity | 118 `ok`, 65 `unverified: no gloss` (every EX row), 2 `unverified: clinician` |
| register | 170 rated 4, 16 rated 3, none below |
| Rwandan English | **47 flagged** |

The 65 `unverified: no gloss` are not a gap in the review; they are the EX rows,
which have no recorded concept in any language, so fidelity has nothing to check
against. That was true before this pass and is unchanged by it.

### Two rendering defects — written up in review/rendering-defects-english.md

**The capital-I one is not a v2 risk. It is in the shipped v1 corpus, 48,398 rows
of 1,000,000 — 4.8%.** 26,673 labelled mixed, 21,725 english; the frame is where
it lives, so an English frame carrying a Kinyarwanda phrase is affected too.
36,724 of those rows contain both the lowercased `i` and a correct capital `I`
later in the same sentence.

Fixing it changes v1 and moves every frozen digest, so it needs sequencing rather
than a patch — three options are laid out in that document. Full detail there;
the summary below is what the review found before the corpus was checked.

### A rendering defect the review found, and it is English-specific

**72 of 203 English phrases begin with the pronoun "I", and the renderer
lowercases it.**

```python
if continues:                                  # opener ends in a comma
    phrase = phrase[0].lower() + phrase[1:]
```

```
"Doctor, " + "I am having a lot of trouble breathing"
  ->  "Doctor, i am having a lot of trouble breathing"
```

Five of the six English openers end in a comma, so **83% of frames** for each of
those 72 phrases render a lowercase *i*. That is roughly 60 of every 72 rows built
on them.

The line is correct for Kinyarwanda and correct for the general case in English —
a phrase continuing after a greeting should not keep its capital. It is wrong only
for the one English word that is capitalised for its own sake. Kinyarwanda has no
such word, which is why the code has been right for as long as the corpus has been
Kinyarwanda-first.

**This is a `dataset/` change and is described, not made.** The fix is to
lowercase only when the first word is not `I`:

```python
if continues and phrase.split(" ", 1)[0] != "I":
    phrase = phrase[0].lower() + phrase[1:]
```

Guarding on the whole word rather than the character matters: `I` must stay
capitalised but `In labour...` must not.

**v1 does not exhibit it**, because v1 English phrases are noun phrases that
follow a subject — the subject takes the lowercasing and the phrase never starts a
clause. It appears the moment English moves to utterances, which is what the
person split did.

### A consistency question, not a defect

Kinyarwanda authored utterances end in a full stop (`Iminwa yanjye yahindutse
ubururu.`); the English drafts do not. With an empty closer the English renders
with no terminal punctuation. v1 behaved the same way, so nothing has regressed —
but the two languages now differ, and the renderer collapses duplicate stops, so
adding them to the English costs nothing. Worth one ruling either way.

## Rulings of 2026-09-05, applied

**Capital-I: site B only.** v1 keeps the defect. Recorded in
`review/rendering-defects-english.md` under its own heading, with the grep that
checks a candidate quotation: **no paper may quote one of the 48,398 v1 rows that
carry it**. An illustrative row is chosen rather than sampled, so this is entirely
avoidable — but only if someone remembers, which is why it has a section rather
than a sentence.

**Terminal punctuation: applied.** 190 drafted English phrases now end in a full
stop, matching the Kinyarwanda. Verified across all three frame shapes; grouping
and lint unchanged.

Note what the second fix makes visible: with the stop in place, the bare frame
reads `My lips have turned blue.` and the greeting frame still reads
`Doctor, i am bleeding heavily and it will not stop.` **Defect 2 is fixed in the
data and defect 1 is not fixed until site B lands** — the two are independent and
both are needed before an English v2 row renders correctly in every frame.
