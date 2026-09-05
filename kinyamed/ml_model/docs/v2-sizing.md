# v2 corpus sizing

## Read this first: "rows per phrase" is a corpus MEDIAN, not a per-phrase property

Every figure in this document of the form "N rows per phrase" is a **corpus-wide
median**. It is not a guarantee that any given phrase yields N rows, and for a
large class of phrases it cannot be.

**Rows are drawn without replacement and quotas are capped at a family's
combination count.** `allocate()` gives each family
`min(bucket_target x share, family.combinations)` and `generate()` draws with
`rng.sample(range(family.combinations), quota)`. Nothing ever repeats, and a
family that runs out simply under-fills — the shortfall is redistributed to
families that still have headroom.

**A first-person phrase has 1,500 frame combinations and can never reach 2,000
rows on its own.**

```
openers x onsets x contexts x closers = 6 x 10 x 5 x 5 = 1,500
```

That is the whole space available to one first-person phrase instance. The corpus
reaches a median of 2,000 because a third-person `{REL}` phrase is **one phrase in
the inventory but expands to one instance per allowed relation** — four to eight
of them — so it carries 6,000 to 12,000 combinations and pulls the average up.

Two consequences worth holding onto:

- **The median is carried by third-person phrases.** A domain or class whose
  concepts are mostly first-person sits below it, structurally and permanently.
- **The relation rulings therefore move the sizing.** `NO_RELATIONS` and
  `CHILD_RELATIONS` reduce instances per phrase, and they concentrate on ROUTINE:
  2.6 instances per phrase against 4.3 for CRITICAL and URGENT. ROUTINE is the
  class furthest below the median and the least able to absorb any further
  narrowing — see `docs/urgency-frame-coupling.md`, where that is what decides a
  design question.

Where this document says "at 2,000 rows per phrase", read "at a corpus median of
2,000 rows per phrase".

## The arithmetic, computed from the generator

```
v1 as built
  families                160
  distinct phrase strings 184
  distinct combinations   6,900,000
  rows                    1,000,000   (14.5% of the space)
  mean rows per phrase     5,435

v2 projected (14 phrases per domain per language)
  (urgency,domain) cells  26   (+10; obstetric gains URGENT and ROUTINE, etc.)
  phrases per language    126
  distinct phrase strings 504
  distinct combinations   18,900,000   (2.74x v1)
```

The frame slots (opener x subject x onset x context x closer = 15,000 per language)
are unchanged by vocabulary work; the whole 2.74x comes from the phrase slot.

## What each row count buys

| rows | rows per phrase | share of combination space |
|---|---|---|
| 1,000,000 | **1,984** | 5.3% |
| **1,008,000** | **2,000** | 5.3% |
| 1,500,000 | 2,976 | 7.9% |
| 2,000,000 | 3,968 | 10.6% |
| 3,000,000 | 5,952 | 15.9% |

## The finding: above ~1M, more rows spend the quality the vocabulary bought

The brief asks for two things that pull in opposite directions — a bigger corpus,
and median rows-per-phrase around 2,000. At 504 phrase strings those meet at
**1,008,000 rows** and nowhere else.

Going to 2M does not make a better corpus. It makes each phrase repeat 3,968 times
instead of 1,984 — half the diversity per phrase, for a bigger number on the cover.
At 3M rows the corpus would be **less diverse per phrase than v1 is today** (5,952
against 5,435), which would mean the vocabulary expansion had bought nothing.

Repetition is not the binding constraint here — 2M rows uses only 10.6% of the
18.9M combination space, so nothing repeats. The constraint is that rows-per-phrase
is the honest measure of how much clinical variety a row count represents, and it
gets worse as rows go up and better only as phrases go up.

## If you want a genuinely larger corpus

The lever is phrases, not rows. Holding a **median** of 2,000 rows per phrase
(see the note at the top — first-person phrases cannot individually reach it):

| phrase strings | per language | per domain per language | supports |
|---|---|---|---|
| 504 | 126 | 14 | **1,008,000 rows** |
| 750 | 188 | ~21 | 1,500,000 rows |
| 1,000 | 250 | ~28 | 2,000,000 rows |

To say "2,000,000" and mean it at v2 quality needs roughly **1,000 phrase strings** —
double the current Phase 2 target, and double the speaker and clinician time.

## Recommendation

**Generate 1,008,000 rows.**

- Literally satisfies "1,000,000+" without inflating it.
- Hits 2,000 rows per phrase exactly.
- Uses 5.3% of the combination space, so uniqueness by construction still holds
  with wide margin.
- Every row is backed by 2.74x more distinct clinical material than v1.

The paper can then say **1,008,000 rows from 504 clinician-reviewed,
speaker-authored phrasings across 9 domains and 4 languages** — which is a stronger
sentence than "2,000,000 rows" from the same 504 phrases, and it is one nobody can
undercut by dividing.

If a bigger headline number is wanted later, fund more phrases. Do not raise the
row count.


---

# Revision after the utterance form and the relation audit

The earlier arithmetic on this page assumed 504 phrase strings — 126 per language,
one per concept. Two later decisions changed that.

**Person moved into the phrase.** Each concept now needs a first-person and a
third-person phrasing, because `ndakorora` and `umwana wanjye arakorora` are
different sentences rather than one sentence with two subjects. That doubles the
authored count.

```
concepts (language-independent)   125
authored phrases   125 x 2 persons x 4 languages = 1,000
v1 for comparison                  46 concepts, 184 phrases
```

**126 -> 125:** IF07 was ruled the same concept as EX29 and removed from
`concepts.py`, `concept_anchors.csv` and `routine_relation_sets.csv`. PR02 was
already out of generation, so the brief's 127 concepts give 125 eligible.

**{REL} multiplies rendered variety without adding authored phrases.** A
third-person phrase expands over its domain's relations, so one authored sentence
becomes four to eight rendered ones. The relation audit costs almost nothing in
space:

| scenario | rendered per language | combination space | 1,008,000 uses |
|---|---|---|---|
| all domains 8 (pre-audit) | 1,134 | 149,688,000 | 0.67% |
| audit: obstetric 4, paediatric 1 | 980 | 129,360,000 | 0.78% |
| audit + paediatric 5 | 1,036 | 136,752,000 | 0.74% |
| audit + paediatric 5, chronic_care 7 | 1,022 | 134,904,000 | 0.75% |

**Space is no longer the binding constraint anywhere.** Restricting obstetric to
four relations and paediatric to one moves usage from 0.67% to 0.78% of an enormous
space. Nothing about the audit threatens any row target, so relation sets should be
chosen purely for validity.

## What the row target should be

At **1,008,000 rows the median authored phrase accounts for 1,000 rows** — twice as
diverse as the 2,000 originally targeted, because the person split doubled the
denominator while the row count stayed fixed.

| rows | rows per authored phrase |
|---|---|
| 1,008,000 | 1,000 |
| 1,500,000 | 1,488 |
| **2,016,000** | **2,000** |

Two defensible answers:

**Keep 1,008,000.** Better diversity than the target, and the paper's "1,000,000+"
claim stands. The extra authoring already bought the improvement.

**Raise to 2,016,000.** Restores exactly 2,000 rows per phrase and doubles the
corpus, still using under 1.6% of the combination space.

**Recommendation: 2,016,000.** The original argument was that row count should match
the clinical content supporting it, and the content has doubled. 1,008,000 would now
be leaving half the earned corpus on the table, and 2,016,000 is defensible by the
same reasoning that produced the first figure rather than in spite of it. It also
keeps the round claim honest: 2,016,000 rows from 1,008 speaker-authored phrasings
across 126 clinician-reviewed concepts.

The generator default should move to 2,016,000 once the relation sets are settled.


## Row target: 2,016,000, subordinate to validity

Set by the speaker. It restores 2,000 rows per authored phrase after the person
split doubled the denominator.

**It is a ceiling reached by valid combinations, not a quota to fill.** Where a
relation set is restricted, a concept held for clinician validation, or a
combination judged clinically questionable, the corpus is smaller and that is the
correct outcome. At roughly 0.8% space usage there is no tension to resolve: no
validity decision taken so far moves the target at all.


---

# Recomputation at 125 concepts

IF07 collapsed into EX29, and paediatric first person ruled per concept.

```
ceiling   125 concepts x 2 persons x 4 languages = 1,000 authored phrases
          at 2,000 rows per phrase              -> 2,000,000 rows
```

That is the direct answer, and it is a **ceiling**. Two rulings already taken
reduce the phrases below it, though only the first is materialised:

| deduction | phrases | status |
|---|---|---|
| PA01-PA04 first person, `applies=no` — a convulsing, floppy, too-weak or severely breathless child cannot speak | 4 rows x 4 languages = 16 | materialised in the brief |
| the 10 `NO_RELATIONS` concepts have no third-person form | 10 x 4 = 40 | ruled in `routine_relation_sets.csv`, not yet in the brief |

```
net       1,000 - 16 - 40 = 944 authored phrases
          at 2,000 rows per phrase              -> 1,888,000 rows
```

**Which figure is the target is a ruling, not arithmetic.** 2,000,000 is round
and matches the materialised state today. 1,888,000 is what this page's own
principle implies — the row count follows the clinical content supporting it, so
content removed should remove rows rather than inflate the per-phrase figure to
2,119. `TARGET_ROWS_V2` is unchanged at 1,008,000 pending that ruling.


---

# Recomputation after the paediatric rulings

PA05-PA07 ruled `applies=no`, and standing rule 9 — a paediatric first-person row
that would duplicate an adult concept is not authored — caught EX40-EX43.

```
ceiling  125 concepts x 2 persons x 4 languages = 1,000 phrases
minus    11 applies=no rows x 4                 =    44
minus    10 NO_RELATIONS thirds x 4             =    40
net                                                 916 phrases
                                    at 2,000/phrase -> 1,832,000 rows
```

**Ruled: 1,832,000.** The target is sized from valid content; the per-phrase
multiplier stays at 2,000 and is never raised to reach a round number. Recompute
whenever a ruling changes the phrase count.

| after | concepts | ceiling | - applies=no | - NO_RELATIONS | net | rows |
|---|---|---|---|---|---|---|
| person split | 126 | 1,008 | 0 | 40 | 968 | 1,936,000 |
| IF07 collapse | 125 | 1,000 | 0 | 40 | 960 | 1,920,000 |
| PA01-PA04 | 125 | 1,000 | 16 | 40 | 944 | 1,888,000 |
| PA05-PA07, EX40-EX43 | 125 | 1,000 | 44 | 40 | 916 | **1,832,000** |

Every row deducts both kinds, so the columns are comparable. The headline
figures quoted earlier in this page's history — 2,016,000 and 2,000,000 — are
**ceilings** that had not yet deducted the `NO_RELATIONS` thirds; they are not
alternative targets.


---

# Recomputation after the person-applicability rulings

GI04, NE01 and NE02 ruled `applies=no` for first person. HT03, CC01, CC02, NE04
and NE06 held with `applies=yes` — held rows are not deducted, because the phrase
is still to be authored once the clinical question is answered.

```
ceiling  125 concepts x 2 persons x 4 languages = 1,000 phrases
minus    14 applies=no rows x 4                 =    56
minus    10 NO_RELATIONS thirds x 4             =    40
net                                                 904 phrases
                                    at 2,000/phrase -> 1,808,000 rows
```

**1,808,000**, with `PR09` unresolved and uncounted: 1,800,000 if it is removed.

| after | concepts | ceiling | - applies=no | - NO_RELATIONS | net | rows |
|---|---|---|---|---|---|---|
| person split | 126 | 1,008 | 0 | 40 | 968 | 1,936,000 |
| IF07 collapse | 125 | 1,000 | 0 | 40 | 960 | 1,920,000 |
| PA01-PA04 | 125 | 1,000 | 16 | 40 | 944 | 1,888,000 |
| PA05-PA07, EX40-EX43 | 125 | 1,000 | 44 | 40 | 916 | 1,832,000 |
| GI04, NE01, NE02 | 125 | 1,000 | 56 | 40 | 904 | **1,808,000** |

**The target is a consequence of the valid inventory, not a quota.** Every step
down this table is a clinical decision taken on its own merits; none of them was
weighed against the row count, and none should be.


---

# Recomputation after the EX30 collapse

EX30 (infectious_fever) collapsed into CR07 (cardiac_respiratory): one concept,
kept under CR07's IMCI anchor, carrying the speaker's EX30 wording.

```
ceiling  124 concepts x 2 persons x 4 languages =   992 phrases
minus    14 applies=no rows x 4                 =    56
minus    10 NO_RELATIONS thirds x 4             =    40
net                                                 896 phrases
                                    at 2,000/phrase -> 1,792,000 rows
```

| after | concepts | ceiling | - applies=no | - NO_RELATIONS | net | rows |
|---|---|---|---|---|---|---|
| person split | 126 | 1,008 | 0 | 40 | 968 | 1,936,000 |
| IF07 collapse | 125 | 1,000 | 0 | 40 | 960 | 1,920,000 |
| PA01-PA04 | 125 | 1,000 | 16 | 40 | 944 | 1,888,000 |
| PA05-PA07, EX40-EX43 | 125 | 1,000 | 44 | 40 | 916 | 1,832,000 |
| GI04, NE01, NE02 | 125 | 1,000 | 56 | 40 | 904 | 1,808,000 |
| EX30 collapse | 124 | 992 | 56 | 40 | 896 | **1,792,000** |

**The target is a consequence of the valid inventory, not a quota.** Every step
down this table is a clinical or structural decision taken on its own merits.


---

# Recomputation after the GI08 collapse

GI08 collapsed into EX16/EX17: the same concept, already carried by the
speaker's own first-pass phrasings, and its anchor was `not IMCI (minor
complaint)` — no anchor to hold it apart.

```
ceiling  123 concepts x 2 persons x 4 languages =   984 phrases
minus    14 applies=no rows x 4                 =    56
minus    10 NO_RELATIONS thirds x 4             =    40
net                                                 888 phrases
                                    at 2,000/phrase -> 1,776,000 rows
```

| after | concepts | ceiling | - applies=no | - NO_RELATIONS | net | rows |
|---|---|---|---|---|---|---|
| person split | 126 | 1,008 | 0 | 40 | 968 | 1,936,000 |
| IF07 collapse | 125 | 1,000 | 0 | 40 | 960 | 1,920,000 |
| PA01-PA04 | 125 | 1,000 | 16 | 40 | 944 | 1,888,000 |
| PA05-PA07, EX40-EX43 | 125 | 1,000 | 44 | 40 | 916 | 1,832,000 |
| GI04, NE01, NE02 | 125 | 1,000 | 56 | 40 | 904 | 1,808,000 |
| EX30 collapse | 124 | 992 | 56 | 40 | 896 | 1,792,000 |
| GI08 collapse | 123 | 984 | 56 | 40 | 888 | **1,776,000** |
| *EX16/EX17, when executed* | *122* | *976* | *56* | *40* | *880* | *1,760,000* |

The last row is confirmed but not executed: it waits on the second-phrasing
pairing being written into the brief and into `PHRASE_VARIANTS`, so EX17's
wording survives the collapse rather than being lost by it.

---

## The v2 target is 330,000, ruled 2026-09-05

**The invariant decided it: 2,000 rows per authored phrase, 165 phrases.**

```
165 phrases x 2,000 = 330,000 rows
```

### What was rejected, and why it was tempting

**1,008,000 was reachable and was refused.** The v2 corpus can produce 7,094,400
unique rows, so 1,008,000 fits with headroom in every class (CRITICAL 7.2x,
URGENT 9.2x, ROUTINE 4.1x). It is also the number in `TARGET_ROWS_V2` and the
number the freeze checklist was written around.

It was refused because **it would have meant 6,109 rows per phrase, not 2,000**,
and the reason for the increase is not more clinical material:

```
v1   184 phrases x 4 languages, 1,500 frame combinations
v2   165 phrases x 1 language,  13,200 frame combinations
```

**The frame space grew 8.8x; the clinical content did not.** The 17 authored
frame fragments took openers 6 -> 12, contexts 5 -> 10 and closers 5 -> 11, and
multiplying those out is what made a million rows reachable from a third of v1's
phrase inventory. Shipping 1,008,000 on that basis is precisely what standing
rule 4 forbids: *never increase dataset size by generating questionable
combinations; validity and provenance beat row count.* The combinations would not
be invalid, but the row count would be carrying weight the phrases cannot.

**The other argument for 1,008,000 was comparability with v1, and it is the
stronger one to answer.** Matching v1's scale would let v1 and v2 training numbers
sit in one table. That is exactly why it was rejected: **matching the scale of an
artefact with different provenance invites a comparison between two things that
are not alike.** v1 is four languages of unreviewed phrases with a mixed-language
half; v2 is one language, speaker-authored, clinician-flagged, with 23 rows
deliberately held out. A reader who sees 1,000,000 against 1,008,000 will read
them as versions of one dataset. They are not, and the freeze checklist already
says so in its own words: *"any v1 training result stays valid as a v1 result. It
is not comparable to a v2 number and must not be reported as one."* Choosing a
number that undercuts that sentence would be a strange way to keep it.

### What 330,000 concedes

**v2 ships smaller than v1 — a third of the rows.** That is the honest shape of
the artefact: fewer rows, from fewer phrases, every one of them authored by a
Kinyarwanda speaker rather than drafted by a template. The paper should say the
row count fell and why, rather than hold it level and explain nothing.

**Rows per phrase is a corpus median, not a guarantee.** At 330,000 over 165
phrases the mean is exactly 2,000, but a first-person phrase with no `{REL}`
draws on 13,200 combinations while a third-person one expanding over eight
relations draws on 105,600. The invariant describes the corpus, not any row in
it - stated here because `v2-sizing.md` is where someone will come looking for a
guarantee that was never made.

## Domain and family concentration in v2 — measured, and stated rather than found

**One family is 22% of the corpus.** `preventive` at ROUTINE holds
72,217 of 330,000 rows. The three largest families:

```
   72,217  21.9%  kinyarwanda->kinyarwanda:ROUTINE:preventive
   34,673  10.5%  kinyarwanda->kinyarwanda:CRITICAL:cardiac_respiratory
   27,187   8.2%  kinyarwanda->kinyarwanda:URGENT:gastrointestinal
```

Domain shares:

```
   76,100  23.1%  preventive
   49,049  14.9%  cardiac_respiratory
   43,811  13.3%  gastrointestinal
   40,747  12.3%  haemorrhage_trauma
   32,600   9.9%  obstetric
   32,487   9.8%  chronic_care
   28,832   8.7%  infectious_fever
   14,933   4.5%  neurological
   11,441   3.5%  paediatric
```

**This follows from the phrase distribution, not from the allocator.** `preventive`
contributed 22 of the 43 ROUTINE phrases, and `allocate()` divides a
(language, class) bucket among its domains in proportion to how much distinct
material each has. Half of ROUTINE's material is preventive, so half of ROUTINE's
rows are - and because v2 is monolingual there is no mixed bucket to dilute it.

**Why preventive has so many phrases is the real explanation**, and it is a fact
about the authoring order rather than about triage: preventive was drafted late,
in whole batches, when the method was working well, while `paediatric` lost
concepts to rule 9 and to three collapses and `neurological` lost five concepts
to collapse in one afternoon. The domains with the fewest phrases are the ones
whose concepts turned out to be duplicates.

**It passes every quality target**, including the per-domain floor, so nothing
here is a validation failure. It is stated because a reader who computes domain
shares will find it, and the honest answer - a corpus reflects where the
authoring got to, not what a clinic sees - is better given than extracted.

**What it means for training.** Class balance is enforced and holds at 33/34/33,
so the label distribution is not skewed. Domain is not balanced and was never
claimed to be. A model trained on this will see four times as many preventive
rows as paediatric ones, and any per-domain metric should be read against these
shares rather than as if the domains were equally represented.
