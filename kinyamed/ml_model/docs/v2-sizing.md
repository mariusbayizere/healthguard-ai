# v2 corpus sizing

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

The lever is phrases, not rows. Holding 2,000 rows per phrase:

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
