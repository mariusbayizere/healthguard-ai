# Session state — handover

Everything a fresh session needs to continue without re-deriving it. Written 2026-09-01, reconciled
against disk 2026-09-03. All figures below were re-derived from the files by running the tooling, not recalled.

**Every count here is reproducible.** `held` is `hold=yes`; `filled` is a non-empty `your_phrasing`
on a row that is **not** `applies=no` (EX30 first keeps the speaker's text but was collapsed, so it
counts as not-applicable — see section 7's counting note); `resolved` is filled-or-not-applicable,
which is what `progress.py` prints. Where a number appears twice in this document it has been made
to agree; where it disagrees with the files, the files win.

---

## 1. What this phase is

Expanding the seed vocabulary from 184 phrases to a speaker-authored, clinician-
reviewed set, then regenerating the corpus as **v2**. v1 is frozen and must stay
byte-identical: `make verify-full` passes 8/8 and is checked after every change to
the generator. **If v1 stops reproducing, stop and fix that first** — both frozen
manifests depend on it.

The Kinyarwanda speaker is the project owner. They author and rule; drafts are
suggestions only.

## 2. Where each domain stands

Kinyarwanda brief: `review/speaker_brief_kinyarwanda_v2.csv`, 254 rows
(127 concepts x first/third person).

| domain | filled | held | resolved | |
|---|---|---|---|---|
| cardiac_respiratory | 26/28 | 3 | 26 | *(CR07 now carries EX30's wording)* |
| obstetric | 27/28 | 1 | 27 | |
| infectious_fever | 17/30 | 9 | 21 | *(+4 not-applicable: IF07 and EX30, both persons)* |
| gastrointestinal | 13/28 | 3 | 16 | *(+3 not-applicable: GI04 first, GI08 both)* |
| haemorrhage_trauma | 6/28 | 1 | 6 | |
| neurological | 6/28 | 1 | 8 | *(+2 not-applicable: NE01, NE02 first)* |
| chronic_care | 4/28 | 2 | 4 | |
| paediatric | 4/28 | 1 | 15 | *(+11 not-applicable: only PA08-PA10 first survive)* |
| preventive | 4/28 | 2 | 4 | *(both holds are PR02, newly marked)* |
| **total** | **107/254** | **23** | **127** | *(+20 not-applicable = 127 resolved)* |

The `held` column counts **every** `hold=yes` row, including the eight
infectious_fever and gastrointestinal third-person rows held only because their
first person is held. An earlier version of this table counted the first-person
holds alone, summed to 16 and printed 18. Read it from the brief, not from here:

```
python -c "import csv,collections; print(collections.Counter(r['domain'] for r in csv.DictReader(open('review/speaker_brief_kinyarwanda_v2.csv')) if r['hold']=='yes'))"
```

Swahili brief (`speaker_brief_swahili_v2.csv`) is generated and untouched: 0/254.

**Provenance so far: 78 speaker, 27 machine_approved, 5 unresolved, 20
not_applicable.** CR07 first moved from machine_approved to speaker when it took
EX30's wording; the infectious_fever third-person batch added seven
machine_approved and one speaker rewrite. The two PR02 rows became `unresolved`
when its exclusion was recorded in the brief (section 3).

**Speaker rate: 78 of 105 authored rows, 74%** — not the ~85% an earlier draft
claimed. 105 is `speaker + machine_approved`; the not-applicable and unresolved
rows are not authored and do not belong in the denominator.

Frame fragments are complete: 17/17 of the rows marked `TO WRITE`, of which 12
machine_approved and 5 speaker rewrites. The file has 33 rows — the other 16 are
`existing` and were already in v1.

## 3. Unresolved and held — nothing generates from these

| concept | person | why |
|---|---|---|
| CR04 | both | chest indrawing. `igituza kiramanuka` and `munsi y'igituza harinjira` are different descriptions. **Do not choose between them.** Held for a Rwandan clinician. |
| CR05 | third | wheeze. Redrafted to restore chest tightness alongside the sound; not accepted. The `-mu-` object marker is the uncertain part. |
| OB12 | third | breastfeeding advice. Restricted to the four obstetric relations, but **`Mama` is flagged, not decided** — it implies the speaker's own mother recently delivered. |
| PR02 | both | family planning. Unresolved pending Rwandan service-design confirmation on whether men present. **Out of generation entirely** — and now marked as such in the brief, not only here (see below). |

### needs_clinician — 16 rows, in three kinds

Split by whether the row is authored, which is what decides if it can generate.
An earlier version of this list put `CR04` in both groups and labelled the second
"(6)" while listing eight rows; the counts below are from the brief.

**Authored — wording settled by the speaker, clinician not consulted (5):**

- `OB03` first and third — cord presentation. **Do not generate until validated.**
- `OB05` first — puerperal sepsis discharge description
- `CR04` first and third — a settled speaker phrasing, but held above for a
  different reason: two rival descriptions, neither chosen.

**My draft held, nothing authored (6)** — `your_phrasing` empty, the draft left
in `suggested_kinyarwanda` as the record of what was rejected:

- `CR05` third — `ijwi ridasanzwe` is patient-understandable but not a definitive
  clinical term for wheeze
- `IF01` first — fever with stiff neck. A specific danger sign; the wording is a
  guess. **Do not substitute a guess.**
- `IF03` first — IMCI general danger sign (unable to drink). Draft held as-is;
  no alternative invented.
- `IF04` first — `nkabira ibyuya` for sweating is unvalidated.
- `IF06` first — dysuria wording unvalidated and possibly the wrong register.
- `EX27` third — attributing a suspicion of malaria to another person.
  `nkeka` -> `akeka` follows the regular pattern but the speaker has not written
  it.

**Nothing drafted; the question itself is clinical (5)** — `suggested_kinyarwanda`
empty too, so there is nothing to hold:

- `NE06` first — new confusion. `applies=yes` stands. Whether a patient who can
  accurately report their own new confusion is meaningfully confused is a
  clinical question, not a linguistic one, so no first-person phrase is written
  until it is settled.
- `HT03`, `CC01`, `CC02`, `NE04` first — held, `applies=yes`, **not deleted**.
  All four turn on severity and capacity: whether a patient that unwell can still
  report. Clinical questions, so rule 11 raised them and stopped.

5 authored + 6 drafted-and-held + 5 undrafted = 16, `NE06` counted in the last
group. Re-derive rather than trusting the split:

```
python -c "import csv; r=[x for x in csv.DictReader(open('review/speaker_brief_kinyarwanda_v2.csv')) if x['needs_clinician'].strip()]; print(len(r), sum(1 for x in r if x['your_phrasing'].strip()))"
```

### PR02 — recorded in the brief, not just in this document

`PR02` was described here as "out of generation entirely" while both its brief
rows sat `applies=yes` with no hold, no source and no note. Nothing outside this
paragraph knew, and `walk.py` would have presented both rows for authoring like
any other blank. They now carry `hold=yes`, `source=unresolved`, and the reason
in `notes`.

**It is deliberately not `applies=no`.** That value means *this person does not
apply to this concept* — rule 9 and rule 11's outcome — and pairs with
`source=not_applicable`, which `progress.py` counts as **resolved**. PR02 is the
opposite of resolved: the concept is waiting on a service-design ruling. Marking
it `applies=no` would have moved the resolved count to 129 and recorded a settled
answer where there is an open question. `hold=yes` + `unresolved` is OB12's
shape, and it is the honest one.

The third person is additionally pinned `NONE — do not generate` in
`review/routine_relation_sets.csv`. That covers only the third; the brief now
covers both.

### Drafted but explicitly NOT accepted

- `CR01` first — drafted to match the third after the speaker added jaw-or-arm.
  Blocked on the first-person object marker.
- `CR05` third, and `IF01`, `IF03`, `IF04`, `IF06` first — as above.

All sit in `suggested_kinyarwanda` with `your_phrasing` empty.

**needs_clinician is a legitimate outcome, not a failure.** A low-confidence
draft is not converted into a rewrite to keep progress moving: holding beats
manufacturing a plausible phrase that later reads as speaker-authored.

## 4. Relation-set architecture

A third-person phrase carries `{REL}`, expanded at family-build time over a
relation set. **The canonical `{REL}` phrase stays one phrase in the inventory**, so
attribution maps every expansion back to it and the holdout cannot split
`umwana wanjye` from `mama`.

Resolution order: `CONCEPT_RELATIONS[phrase]`, then `DOMAIN_RELATIONS[domain]`,
then all relations.

**Sets defined in `dataset/vocabulary.py`:**

```
RELATIONS            8   Umwana wanjye, Umugore wanjye, Umugabo wanjye, Mama,
                         Papa, Mushiki wanjye, Umuturanyi wanjye, Umukecuru
CHILD_RELATIONS      5   Umwana wanjye, Umuhungu wanjye, Umukobwa wanjye,
                         Umwuzukuru wanjye, Umwana w'umuturanyi
HOUSEHOLD_RELATIONS  6   Umugore wanjye, Umugabo wanjye, Mama, Papa,
                         Mushiki wanjye, Umwana wanjye
NO_RELATIONS         0   the concept has no third-person form
```

**`NO_RELATIONS` is a restriction, not a deletion.** The concept keeps its
first-person phrase. A *non-empty* set naming nothing available still raises, as
the misconfiguration it is. Two tests pin the difference, including that an empty
set does not silently fall back to the full list — which would generate exactly the
rows a ruling excluded, with no error.

### Domain rulings

| domain | relations |
|---|---|
| obstetric | 4 — Umugore wanjye, Mama, Mushiki wanjye, Umuturanyi wanjye. Umukecuru excluded as past childbearing age; the other three cannot be pregnant. |
| paediatric | `CHILD_RELATIONS` (5). **Do not expand without individual speaker review of each form.** |
| cardiac_respiratory, gastrointestinal, haemorrhage_trauma, infectious_fever, neurological | all 8, confirmed |

### Concept rulings

- **NE03, NE04, CC04**: keep children. Paediatric stroke and congenital heart
  disease are uncommon but real, and under-triage is the failure that matters.
- **CC03**: keep children — rarity is not invalidity.
- **CC05, PR06**: adult relations. Scope, not rarity.
- **CC08**: `NO_RELATIONS`.

### ROUTINE third person — `review/routine_relation_sets.csv`

31 ROUTINE concepts, ruled by group:

```
CHILD_RELATIONS      15   group A (child services) + group C (mild symptoms)
NO_RELATIONS         10   group B, first person only
HOUSEHOLD_RELATIONS   4   group D: PR04, PR10, PR03, PR05
held                  1   OB12
do not generate       1   PR02
```

31 rows, down from 34: IF07, EX30 and GI08 were removed with their concepts.

Group C's reasoning: a parent reports a child's mild cough; an adult does not
usually report another adult's.

**These are recorded per concept and must be materialised into
`CONCEPT_RELATIONS` at v2 build time**, because the generator keys on phrase
strings and most third-person phrases do not exist yet.

## 5. Standing rules — `docs/phrasing-guide.md`

**Twelve rules, not eleven.** Rule 12 (SERVICE_SPEAKER) landed in `122b4a7` and
was missing from this section for four commits while section 7 went on listing
the question it answers as an open blocker. If the guide and this list disagree,
the guide is the record.

1. **Clarity over sophistication.** If an older rural patient understands it
   immediately, that is the better training example.
2. **Prefer `{REL}` as grammatical subject**, not an object marker.
3. **Never mix first and third person inside one phrase.**
4. **Never increase dataset size by generating questionable combinations.**
   Validity and provenance beat row count.
5. **Never accept machine Kinyarwanda because the grammar looks plausible.**
6. **Where a combination is uncertain, restrict the relation set** — do not invent
   Kinyarwanda and do not generate a doubtful example.
7. **Never silently resolve low-confidence Kinyarwanda.** Mark `needs_clinician`
   or leave unresolved.
8. **A draft is a suggestion, never an approval.** Nothing is `machine_approved`
   without an explicit "accept" from the speaker.
9. **Where a paediatric first-person row would duplicate an adult concept**
   because the child-ness lives only in `{REL}`, mark it `applies=no` rather than
   authoring a near-duplicate. The relation carries the distinction; first person
   has no slot for it.
10. **Where a ruling conflicts with evidence, say so before recording it**, not
    after. A ruling made on wording does not settle a question about the concept.
11. **Three-way test before writing any first-person row.** A symptom the patient
    can report -> potentially first person. A routine service the patient
    *receives* -> third person. An observer or measurement finding -> third
    person. The measurement limb means *has not been told*, not *was measured*:
    the speaker's EX08 and EX09 report a blood sugar and a blood pressure in
    first person and are right to. **A patient can report an observer sign when
    they perceive it directly** — their own lips, the sensation of indrawing.
    **Rule 11 flags; it does not overrule an authored phrase.**
12. **SERVICE_SPEAKER — for a service concept, first person is the person
    presenting or requesting the service, not necessarily the patient.** Where
    the beneficiary and the requester are the same (CC08 refill, PR07 screening,
    OB11 antenatal, PR03 HIV test) first person is ordinary. Where they differ
    (`EX46 gukingiza umwana`, PA09, PA10, PR08, EX47) **first person is the
    requester** — the carer who walks in, not the child. Two consequences: a
    service concept's first-person row is not a child speaking, so rule 9's
    duplication test does not apply to it; and it does not license mixing person
    inside one phrase, which rule 3 still forbids. This **narrows rule 11's**
    "routine service the patient receives -> third person" limb: that limb
    excludes the *patient's* first-person row, not the carer's, and both persons
    can exist for a service concept as two different speakers.

## 6. Row target: 1,776,000

**Standing: the target is a consequence of the valid inventory, not a quota.**
2,000 rows per authored phrase is the invariant.

```
ceiling  123 concepts x 2 persons x 4 languages =   984 phrases
minus    14 applies=no rows x 4                 =    56
minus    10 NO_RELATIONS thirds x 4             =    40
net                                                 888 phrases
                                    at 2,000/phrase -> 1,776,000 rows
```

126 -> 125 -> 124 -> 123: IF07 into EX29, EX30 into CR07, GI08 into EX16/EX17.
PR02 is out of generation on top of that.

**How 123 and 14 reconcile with the brief**, because they look wrong next to it:

```
127  concept ids in the brief
 -3  IF07, EX30, GI08 collapsed into other concepts
 -1  PR02, out of generation pending the service-design ruling
123  concepts in the ceiling

 20  applies=no rows on disk
 -6  the six rows of the three collapsed concepts, already outside the ceiling
 14  applies=no rows the ceiling still counts
```

**PR02 is subtracted once, as a concept, not again as two rows.** Its rows stay
`applies=yes` (section 3), so they never enter the 14. A future session that
marks them `applies=no` must drop the concept subtraction at the same time or
the target silently loses eight phrases.

**The EX16/EX17 collapse is confirmed but deliberately not executed** — it waits
on the consumer, which now exists (section 7). Once it runs, 122 concepts, 880
phrases, **1,760,000**.

History: 2,016,000 at 126; 2,000,000 at 125; 1,888,000 after PA01-04; 1,832,000
after PA05-07 and EX40-43; 1,808,000 after GI04, NE01, NE02; 1,792,000 after the
EX30 collapse; **1,776,000** after GI08. `TARGET_ROWS_V2` is still `1_008_000`.

## 7. Current batch and what is blocked

### Settled: infectious_fever first person, all 7 ruled

| id | ruling | outcome |
|---|---|---|
| IF01 | `needs_clinician` | draft held; stiff neck is a specific danger sign, no guess substituted |
| IF02 | rewrite | `Mfite umuriro mwinshi kandi nagagaye.` — `source=speaker` |
| IF03 | `needs_clinician` | draft held as-is; IMCI general danger sign, no alternative invented |
| IF04 | `needs_clinician` | `nkabira ibyuya` unvalidated |
| IF05 | accept | `Mfite umuriro kandi mfite uduheri ku mubiri wose.` — `source=machine_approved` |
| IF06 | `needs_clinician` | dysuria wording unvalidated |
| IF07 | duplicate of EX29 | `applies=no`, `source=not_applicable`; draft withdrawn |

Two suggestion notes were corrected in the same pass, both flagged before the
ruling rather than changed silently:

- **IF02** — the note credited `naragagaye` to OB01, but OB01 first person is
  `Ndatwite kandi nagagaye.`; the `-ra-` form is OB01 *third* (`yaragagaye`).
  The speaker's rewrite restores `nagagaye`.
- **IF05** — the note quoted EX42 as `umwana ufite...`; it is `umwana afite...`.

**IF07 / EX29 ruling.** They are one concept, not two. IF07's anchor is
`IMCI: fever, no danger sign (green)`, glossed "a slight fever since yesterday
but otherwise well"; EX29 — `mfite umuriro woroheje umaze umunsi umwe, ariko nta
kindi kibazo mfite` — states exactly that. This is **not** the CR01/EX05 case:
there, two real presentations existed (crushing pain with jaw-or-arm radiation
vs the simpler chest-pain-to-arm), and both rows carry a `distinct from` note
recording the axis. Here no axis exists in `concepts.py` or
`concept_anchors.csv`, and inventing one would be manufacturing. The concrete
cost of keeping both: two phrases differing by one comma enter the corpus as
separate concepts, and the *phrase* holdout can place one in train and the other
in eval — the leakage `near_duplicates.py` and `test_leakage.py` exist to catch.

`IF07` first is now `applies=no`. **Its third-person row is also `applies=no` /
`not_applicable`** — the whole concept went, as section 2's "+4 not-applicable:
IF07 and EX30, both persons" says. An earlier version of this paragraph claimed
the third was untouched; the brief disagrees, and the brief is right. The concept
is not yet collapsed in `concepts.py` — see section 6.

### Settled: gastrointestinal first person

**21 rows left in the domain, not 22** — GI04 first went `applies=no` in the
person-applicability rulings. Seven first-person rows were outstanding: **5
accepted, 2 blocked.** That took the domain to 11/28 filled, 12/28 resolved *at
the time of this batch*; the GI01/GI02 third-person acceptances below have since
moved it to **13/28 filled, 16/28 resolved**, which is what section 2 and
`progress.py` show.

| id | phrase | provenance |
|---|---|---|
| GI01 | `Ndaruka ibyo ndya byose kandi sinshobora no kunywa.` | machine_approved |
| GI02 | `Ndaruka amaraso.` | machine_approved |
| GI05 | `Mfite impiswi zirimo amaraso.` | machine_approved |
| GI06 | `Maze ibyumweru birenga bibiri ndwaye impiswi.` | machine_approved |
| GI07 | `Inda irandya cyane kandi ububabare ntibuhagarara.` | machine_approved |

GI01 and GI06 reuse whole clauses of the speaker's: `ndaruka ibyo ndya byose`
from OB10, `Maze ibyumweru birenga bibiri` from CR06. GI05 is phrased as bloody
diarrhoea, which is the dysentery presentation and routes around the missing
word for stool.

**Two concord flags are now inside accepted phrases** and stay in the record on
their `suggestion_note`: `zirimo` on `impiswi` (GI05), and the class-14 negative
`ntibuhagarara` (GI07), where the speaker's attested `ntahagarara` agrees with
`amaraso` rather than with `ububabare`. The speaker accepted both; the
uncertainty is recorded, not resolved.

**GI03 blocked — no word for stool exists in the approved vocabulary.**
`umwanda`, `amabyi`, `ubwiherero`, `kwituma`, `amase` appear in none of the
speaker's phrases, none of `dataset/vocabulary.py`, none of
`phrase_review_sheet.csv`. Melaena needs the noun and cannot be routed around the
way GI05 was. Same blocker shape as PA08's ear term. **No replacement invented.**

**GI08 blocked — probable duplicate of EX16/EX17.** GI08 is "mild indigestion
after eating"; EX16 `iyo maze kurya numva inda itameze neza` and EX17 `iyo maze
kurya numva mu nda ntameze neza` both already say it. The IF07/EX29 shape, within
one domain this time. Separately: **EX16 and EX17 are near-duplicates of each
other**, both speaker-authored — same family so no family-holdout risk, but
different phrase strings, so they can split across the phrase holdout.

### Second phrasings — the consumer now exists

The EX16/EX17 collapse was blocked on this and is still not executed. What was
built, so EX17's wording survives the collapse instead of being lost by it:

- **`vocabulary.PHRASE_VARIANTS`** — maps a second phrasing to its concept's
  primary. Empty today, populated at v2 build time. v1 is untouched.
- **`phrase_components` consumes it** — a declared pair is unioned into one
  phrase group regardless of substring containment. A pairing naming a phrase
  that is not in the inventory **raises**: silence there would leave the pair in
  separate groups, which is the exact failure the declaration prevents.
- **`review/second_phrasings.py`** — reads a brief's `second_phrasing_optional`
  column into that map, rejecting a second phrasing with no primary, one
  identical to its primary, and one declared against two different primaries.
- **`tests/test_second_phrasings.py`** — six tests, including one that shows the
  two indigestion phrasings landing in *separate* groups without the declaration,
  so the bug is demonstrated rather than asserted away.

Run it any time: `python review/second_phrasings.py review/speaker_brief_kinyarwanda_v2.csv`.

### Cost of the attribution sweep, measured rather than feared

It grows with the corpus, so it was worth projecting before it becomes a problem.
It will not.

```
frame combinations per phrase                    1,500
now        107 phrases ->  538,500 renderings    ~170s   (measured 2026-09-03)
complete   234 phrases ->  729,000 renderings    ~4 min   (1.4x, projected)
```

Only 1.4x, because most rows still to be authored are **first person**, which
renders once rather than across eight relations, while the authored set is
already heavy on `{REL}`. **No reduction needed — keep it exhaustive.**

**But the CI headroom is gone, and this is worth watching.** The
"Reproducibility and dataset tests" job has `timeout-minutes: 10` and runs the
sweep **twice**: once as its own `make check-attribution` step, and again inside
`pytest -q`, which selects `test_attribution_corpus.py` like any other test.
Measured locally at the current 107 phrases:

```
make check-attribution   ~170s
full suite (68 tests)    ~250s   <- includes the same sweep again
                         ~420s   + make verify + pip install
```

That was ~7.5 of the old 10 minutes, on a machine that is not a shared runner,
and the projection above puts the sweep at ~4 min each at full corpus — roughly
11 minutes for the pair, over the limit.

**Ruled: keep both runs, raise the limit.** `timeout-minutes` on the
`reproducibility` job is now **20**. The duplication is deliberate — attribution
has failed silently three times and a green suite hid all three, so the
standalone step exists precisely so the guard survives someone deselecting the
file. Deselecting it from the suite to save time would give back the failure mode
the step was built to prevent. **Do not deselect, and do not shrink the sweep.**

### Ruled: GI08 collapsed, EX16/EX17 confirmed and waiting

**GI08 collapsed into EX16/EX17 — executed.** Removed from `concepts.py`
(66 entries), `concept_anchors.csv` (78 rows) and `routine_relation_sets.csv`
(31 rows); both brief rows are `applies=no`, kept as the record.

**`CR07` first normalised** to `Nkorora gake ariko nta muriro mfite.` — capital
and full stop added to match CR07 third, no word changed, provenance stays
`speaker`.

**EX16 and EX17 are one concept, and both phrasings are kept.** Two ways of
saying the same thing is what the corpus wants — phrasing guide Part 3, item 5.
Neither wording is discarded. But as two *concepts* they are two phrase groups,
and `phrase_components` unions only on **substring containment**:

```
"iyo maze kurya numva inda itameze neza"      EX16
"iyo maze kurya numva mu nda ntameze neza"    EX17
neither contains the other -> not unioned
shared prefix "iyo maze kurya numva " -> 21 characters
```

So one could train while the other evaluates, with 21 characters in common, and
the existing safeguard would not raise it. **The substring closure catches nested
phrases and misses divergent ones with a long shared prefix.** Worth knowing
generally, not only here.

Proposal: EX16 primary, EX17 into `second_phrasing_optional`. **Caveat that
matters:** nothing reads that column today — `make_second_review.py` writes it
empty and no consumer exists. Unless the v2 build reads it *and* maps both
phrasings to one phrase group, collapsing **loses** EX17's wording rather than
preserving it. That is the opposite of the intent, so the mechanism has to land
before the collapse does.

The EX16/EX17 collapse is confirmed and **still not executed**: the consumer
exists now, but the pairing has to be written into the brief's
`second_phrasing_optional` column and into `PHRASE_VARIANTS` at build time. Doing
it takes the target to **1,760,000** (880 phrases, 122 concepts).

### Blocked on the speaker — two words that do not exist in the corpus

`GI03` needs a word for stool and `PA08` needs a word for ear. Neither appears in
any authored phrase, in `dataset/vocabulary.py`, or in
`phrase_review_sheet.csv`. **These cannot be drafted, suggested or worked around**
— inventing Kinyarwanda is what standing rules 5 to 8 exist to prevent, and a
plausible-looking guess here would enter the record as a phrase rather than as a
question. GI05 routed around the stool noun by using `impiswi`; melaena and ear
pain have no such route.

### In flight: gastrointestinal third person

14 rows. **2 accepted, 9 awaiting a ruling, 2 held, 1 `applies=no` with GI08.**
All eleven drafts render across all eight relations in
`review/gastrointestinal_third_render.csv`, 88 rows for individual ruling.

Accepted -> `machine_approved`:

| id | phrase |
|---|---|
| GI01 | `{REL} araruka ibyo arya byose kandi ntashobora no kunywa.` |
| GI02 | `{REL} araruka amaraso.` |

Still awaiting a ruling: **GI04, GI05, GI06, GI07, EX12, EX13, EX14, EX15,
EX16.**

| id | conf | draft |
|---|---|---|
| GI01 | med | `{REL} araruka ibyo arya byose kandi ntashobora no kunywa.` |
| GI02 | med | `{REL} araruka amaraso.` |
| GI04 | low | `{REL} afite impiswi zikomeye kandi amaso ye yinjiye.` |
| GI05 | med | `{REL} afite impiswi zirimo amaraso.` |
| GI06 | med | `{REL} amaze ibyumweru birenga bibiri arwaye impiswi.` |
| GI07 | med | `{REL} arababara cyane mu nda kandi ububabare ntibuhagarara.` |
| EX12 | med | `{REL} amaze iminsi itatu arwaye impiswi zikomeye.` |
| EX13 | med | `{REL} arakomeza kuruka kandi ntashobora kurya.` |
| EX14 | med | `{REL} arababara cyane mu nda.` |
| EX15 | med | `{REL} araruka cyane kandi yumva afite intege nke.` |
| EX16 | med | `Iyo {REL} amaze kurya, yumva inda itameze neza.` |

Three worth reading before ruling:

- **GI04 is drafted from the concept, not transformed** — its first person is
  `applies=no`, and the caregiver realisation is what stays. Two flags: `amaso`
  appears in **no approved phrase**, only in an unapproved draft (D005 on the
  phrase review sheet); and GI04's third sign, the very slow skin pinch, is an
  examination manoeuvre a caregiver cannot report either. The draft carries two
  of three signs.
- **GI07 properly contains EX14** (`{REL} arababara cyane mu nda`), so
  `phrase_components` will union them into one phrase group. That is the
  substring closure working as intended, and worth knowing rather than
  discovering later.
- **EX16 puts `{REL}` mid-phrase**, the shape that silently broke attribution
  twice over. The sweep covers it now and passes.

GI07 and EX14 both take `arababara cyane mu nda` from EX38 third rather than
transforming the first person's `irandya` idiom, which would need an object
marker — the speaker already uses different idioms across the two persons here.

**Held (2):** `GI03` third, blocked on the same missing word for stool as its
first person; `EX17` third, pending the collapse — if EX17 becomes a second
phrasing of EX16, the concept has one third-person row, not two.

### Settled: infectious_fever third person

14 rows. **8 authored, 1 needs_clinician, 4 held on their first person, 1
collapsed.** The domain is 17/30 filled and 21/30 resolved.

Counting note: `EX30` first still holds the speaker's text but is `applies=no`
after the collapse, so it counts as not-applicable rather than filled. Read
totals from `progress.py`, not from a count of non-empty cells.

| id | phrase | provenance |
|---|---|---|
| IF02 | `{REL} afite umuriro mwinshi kandi yaragagaye.` | machine_approved |
| IF05 | `{REL} afite umuriro n'uduheri ku mubiri wose.` | speaker rewrite |
| EX24 | `{REL} afite umuriro wa dogere 39.` | machine_approved |
| EX25 | `{REL} afite umuriro mwinshi kandi arakorora cyane.` | machine_approved |
| EX26 | `{REL} afite ibimenyetso bya malariya, umuriro n'imbeho.` | machine_approved |
| EX28 | `{REL} afite umuriro kandi umutwe uramubabaza cyane.` | machine_approved |
| EX29 | `{REL} afite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo afite.` | machine_approved |
| EX31 | `{REL} amazuru ye aratemba gake.` | machine_approved |

IF05 took the EX42 `n'` join rather than repeating `afite`. EX27 is
`needs_clinician`, draft held, nothing authored. `IF01`, `IF03`, `IF04` and
`IF06` third stay undrafted while their first person is held. `EX30` collapsed
into CR07.

### Bug found while checking this batch — `attribute_phrase` and mid-phrase `{REL}`

Verifying that the newly accepted phrases attribute correctly turned up **24
misattributions among phrases that were already authored**. `attribute_phrase`
matched `{REL}` phrases by deleting the placeholder and looking for the
remainder, which welds the two halves together with a double space:
`Iyo {REL} ahumeka` became `Iyo  ahumeka` and never matched `Iyo Mama ahumeka`.

Three authored phrases have `{REL}` mid-sentence and all three attributed to
`None`: **`CR04` third, `EX07` third, `OB05` third**. Rows built from them would
have dropped out of the phrase holdout and the leakage analysis **with no error
raised** — the same silent failure as the case-sensitivity bug in section 9, in
the same function.

Fixed by matching each segment around the placeholder in order.

### And a third, found by the standing check the moment it was written

`tests/test_attribution_corpus.py` drives the real generator over the real brief
and failed immediately on a **larger** silent leak:

**A phrase authored as a complete sentence never matched its own rendering
whenever the sentence continued.** `_drop_terminal_stop` removes the final stop
before an onset or context, so `Ndakorora cyane.` renders as `Ndakorora cyane
kuva ejo` — and the authored form, stop attached, is not a substring of it.
**57 of the 100 authored phrases end in sentence punctuation**, so this reached
most of the corpus, and every v2 utterance-form phrase is exposed to it.

Worse than losing the row: it falls through to a **shorter** phrase that happens
to be a prefix. `Guhumeka birangora cyane ku buryo ntabasha no kuvuga neza.` lost
its rows to `guhumeka birangora cyane` — a real mis-attribution between two real
phrases, which would have put one concept's rows in another's phrase group.

Fixed by matching on a comparable form: lowercased and with a terminal stop
removed, mirroring what the generator does at render time. `SENTENCE_END` now
lives in `vocabulary.py` so the generator and attribution cannot drift apart.

### The standing check

`tests/test_attribution_corpus.py`, **~170s on an idle machine** and longer under
load (it took 473s while other work ran alongside it). The "~70s" this section and
the Makefile both used to quote was measured at a much smaller authored set; both
now say ~3 min. Re-measure rather than trusting either:

- **exhaustive** — every authored phrase, expanded across the relations its
  concept actually allows, rendered through the real `Family.render` across
  every frame combination, must attribute back to its canonical form. A `None`
  fails.
- **cross-attribution** — with the whole inventory in the index, a rendering must
  still resolve to its own phrase, so a near-duplicate cannot capture its
  neighbour's rows.

It drives `build_families` rather than reimplementing the expansion, so a change
to the real path is what it tests. Wired into `make test-clean` and CI through
the suite, **and** called out as its own `make check-attribution` target and CI
step, so the guard survives someone deselecting it or marking it slow.

**68 tests**, and v1 still reproduces 8/8 (re-run 2026-09-03) — v1 phrases are noun-phrase fragments
with no terminal stop and no `{REL}`, so none of these fixes can move a frozen
digest. That is also precisely why `verify-full` never caught any of the three.

### Person-applicability audit — `review/person_applicability_audit.csv`

Rule 11 applied to all 254 rows across the nine domains. **9 catches, 6
conflicts** (15 rows, matching the file) — recorded as findings, not as edits,
because unlike rule 9 this test needs clinical judgement per concept and six of
its findings disagree with phrases the speaker already authored.

**Two have since been ruled**: `NE06` (`applies=yes`, needs_clinician) and `PR09`
(`applies=yes` under rule 12). The rest still stand as raised.

**Catches — first-person row still empty, no work lost by ruling `applies=no`:**

| concept | limb | certainty |
|---|---|---|
| GI04 watery diarrhoea, sunken eyes, slow skin pinch | observer | high — the skin pinch is an examination manoeuvre |
| NE01 continuous convulsion | observer | high — cannot speak, as PA01 |
| NE02 unconscious, cannot be roused | observer | high — cannot speak, as PA03 |
| ~~PR09 deworming for a child~~ | service received | **superseded by rule 12: `applies=yes`.** The catch reasoned from the patient; SERVICE_SPEAKER reasons from the requester, and PR09 is EX46's shape exactly |
| ~~NE06 new confusion today~~ | observer | **ruled: applies=yes, needs_clinician** |
| HT03 head injury with vomiting and confusion | observer | medium |
| CC01 diabetic with vomiting, deep breathing, drowsiness | observer / capacity | low — reclassified, see below |
| CC02 hypoglycaemia with sweating and confusion | observer / capacity | low — reclassified, see below |
| NE04 sudden difficulty speaking | observer | low — flagged, not proposed |

**`NE06` is ruled:** `applies=yes` stands, flagged `needs_clinician`. Whether a
patient who can accurately report new confusion is meaningfully confused is a
clinical question, not a linguistic one, so the test raised it and stops there.

**`CC01` and `CC02` reclassified by the direct-perception refinement.** A patient
can feel drowsy and can notice they are breathing deeply, so imperceptibility is
the wrong ground for CC01 — what excludes first person there is *capacity*, which
is NE02's and PA03's ground and is a clinical judgement about severity. CC02 is
mostly self-perceived apart from the confusion, which makes it NE06's question
rather than GI04's; the same `needs_clinician` treatment probably fits.

**Conflicts — resolved. The authored phrases stand and the resolution is now in
rule 11.**

- `CR04`, `CR03`, `EX04` — **resolved into the rule**: a patient can report an
  observer sign when they perceive it directly. They can see their own lips and
  fingertips and feel their chest pull in. "Observer sign" is a clinical
  category, not a linguistic one, and the two do not line up.
- `EX08`, `EX09` — these **refine rule 11** rather than falling to it. A blood
  sugar and a blood pressure are measurements reported correctly in first person
  because the patient was told the reading. `CC03` is the same shape with an
  empty first-person row, so by this evidence it should be **authored, not
  excluded**.
- `EX46` `gukingiza umwana` — structural, and **since answered**. The child
  receives the vaccination, so limb 2 said third person, but the authored
  first-person phrase is the *carer* speaking. That became **rule 12
  (SERVICE_SPEAKER)**: for a service concept first person is the requester. EX46
  stands as authored, and PA09, PA10, PR08 and PR09 were ruled `applies=yes` with
  it. Rulings are recorded per concept in `review/service_speaker_audit.csv`.

Beyond paediatric the test now proposes removing at most **7** first-person rows
(NE06 and PR09 both ruled in), adds none, and identifies one row (`CC03`) it
would be wrong to remove. Two of its own limbs have been corrected by what the speaker had
already written — the measurement limb by EX08/EX09, the observer limb by
CR03/CR04/EX04.

### PA08 first person — held, and blocked on vocabulary

`applies=yes`, `hold=yes`, draft **not** approved. Substantiating the draft
`Ugutwi kwanjye kurandya kandi hasohoka amazi.` against approved vocabulary
only:

- `hasohoka` **holds** — your OB05 `hasohoka ibintu binuka`.
- `amazi` **does not** — it is attested only as the waters of OB07
  `Amazi yamenetse`, a different sense entirely. The attested discharge word is
  `amashyira`, from the v1 phrase `igikomere cyanduye kitukura kandi kirimo
  amashyira`, in the pattern `kirimo amashyira`.
- **Blocker: no ear term exists in the approved vocabulary at all.** `ugutwi`
  appears in none of your phrases, none of `dataset/vocabulary.py`, none of
  `phrase_review_sheet.csv`. The head noun cannot be substantiated, and neither
  can the class agreement on `kurandya` that depends on it.

So one substitution is substantiable and the row still cannot be completed. **No
replacement invented — the ear term has to come from the speaker.**

### Blocked on the speaker, in order

1. Paediatric first-person applicability — this is next, and it is a ruling
2. `PR02` service-design question
3. `OB12` — is `Mama` plausible for a recent delivery?
4. `CR01` first person and `CR05` third person — the `-mu-` object marker
5. `PA08` — the ear term, which no approved phrase supplies
6. ~~`PA09`/`PA10`, and `EX46`~~ — **resolved by rule 12 (SERVICE_SPEAKER)**: the
   first-person row is the requester. All three ruled, along with PR08 and PR09,
   in `review/service_speaker_audit.csv`. Their phrases are still unauthored, so
   they are ordinary outstanding rows now, not blockers
7. `CR07` first — the form of the adopted wording: EX30's verbatim lowercase
   string, or the same words in this row's capitalised sentence form. **Not
   normalised without a ruling.**
8. `GI03` — the word for stool, which no approved phrase supplies
9. `GI08` vs `EX16`/`EX17` — concept ruling
10. The 11 gastrointestinal third-person drafts, rendered in
    `review/gastrointestinal_third_render.csv`
11. A clinician session for the `needs_clinician` rows — **16**, of which 6 are
   held drafts with nothing authored and 5 are undrafted (section 3)

### Then

Resume the rhythm: **first person first, then third with `{REL}`, one domain at a
time, rendered across every relation for individual ruling. Never batch-accept.**

Remaining: 163 of 254 Kinyarwanda rows, all 254 Swahili. Roughly 7-10 hours per
language at 2-3 minutes a row.

infectious_fever first person is closed. The domains with no unresolved
architecture are gastrointestinal, haemorrhage_trauma and neurological — all at
6/28 with all eight relations confirmed. infectious_fever third person is the
other open front, and needs no new ruling to start.

## 8. Tooling

```
review/progress.py          completion by domain, respects applies=no
review/lint_phrases.py      structural checks; errors vs warnings; partial-file safe
review/walk.py              row-by-row accept/edit/rewrite, atomic writes; SKIPS hold=yes
review/bulk_declare.py      bulk form/person declaration
review/split_authoring.py   two-author split preserving a blind overlap
review/make_second_review.py  second-speaker RATE and BLIND arms
review/second_phrasings.py  reads second_phrasing_optional into PHRASE_VARIANTS
review/attest.py            is a Kinyarwanda word attested? all sources at once
```

**`attest.py` before writing any phrase with an uncertain word.** It searches the
speaker's own phrases, v1 vocabulary, the review sheet, and the 524 CC BY 4.0 CHW
questions in `review/attestation/`, and says which tier the hit is in — because a
hit in the CHW corpus is a *lead for the speaker*, not permission to write the
phrase. Matching is substring by default, since a stem hides behind noun-class
prefixes; read the contexts before believing a hit.

**`walk.py` now skips `hold=yes` rows.** It filtered on `applies` alone, so all 23
held rows were still offered for authoring — the hold lived in a column nothing
read, and authoring past it was one keystroke away. It prints how many it skipped;
`--include-held` overrides, but the intended move is to lift the hold in the brief
after a ruling.

Ruling records, none of them generated from — read before re-opening a settled
question:

```
review/service_speaker_audit.csv        22 rows; rule 12, per concept
review/person_applicability_audit.csv   15 rows; rule 11, 9 catches + 6 conflicts
review/concept_relation_audit.csv       per-concept relation-set rulings
review/routine_third_person_audit.csv   the 31 ROUTINE concepts by group
review/routine_relation_sets.csv        the resulting sets, incl. PR02 'do not generate'
review/gastrointestinal_third_render.csv  88 rows, 11 drafts x 8 relations
review/infectious_fever_third_render.csv  72 rows, the settled batch
```

`make test-clean` runs the suite in a throwaway clone of HEAD and is the guard
against ambient-state failures. **68 tests** — this section and section 7 said 59
and 62; both were stale. `python -m pytest --collect-only -q | tail -1` settles
it.

## 9. Cautions learned the hard way

- **Three linter rules were retired as the phrase form changed** — trailing full
  stop, leading capital, and a 12-word limit. Each was tightening the speaker's
  language to fit an assumption that no longer held. Expect more.
- **My Kinyarwanda heuristics have produced false positives twice**: a first-person
  detector matched `nda` (belly), and a state detector missed `igituza` because a
  word-boundary regex cannot see a stem behind a noun-class prefix. Prefer
  substring matching on stems, and treat any morphological check as a hint.
- **`walk.py` once truncated a brief to its header.** It now writes atomically and
  refuses a zero-row write. Briefs hold hours of speaker work; never write one
  non-atomically.
- **`attribute_phrase` has now failed silently three times.** Case-sensitive,
  losing every row with an opener. Then the `{REL}` match deleting the
  placeholder, losing every phrase where `{REL}` was not at the front. Then the
  terminal stop, losing 57 of 100 phrases to the generator's own
  `_drop_terminal_stop` and mis-attributing some of them to shorter neighbours.
  Every one hollowed out the phrase holdout with no error raised, and every one
  passed a green suite, because the tests used phrases written for the test.
  **`make check-attribution` now sweeps the real corpus and must stay wired in.**
- **A blank `form` cell silently defaults to `NOUN_PHRASE`.** Six authored
  infectious_fever third-person phrases (EX24, EX25, EX26, EX28, EX29, EX31) were
  recorded as done in section 7 with `form` empty. `build_families` defaults an
  undeclared phrase to `NOUN_PHRASE`, which takes a subject — so
  `{REL} afite umuriro wa dogere 39.` would have rendered as
  `afite {REL} afite umuriro wa dogere 39.`, a doubled subject on a complete
  sentence, across every relation and frame. **Nothing raised**: `verify-full`
  cannot see it (v1 declares no forms and defaults correctly), the attribution
  sweep passes because it compares a rendering to itself, and the linter did not
  look at the column. Only `progress.py`'s "N completed rows have no form
  declared" line mentioned it, and it was read as cosmetic. Caught before v2 was
  ever generated, so nothing downstream was affected. **`lint_phrases.py` now
  errors on an authored row with no declared form**, which is the guard that was
  missing. Same shape as the attribution bugs: a wrong default is worse than a
  crash, because it produces plausible output.
- **`verify-full` cannot see any of this.** v1 has no `{REL}` phrases and no
  terminal stops, so the frozen digests are untouched by attribution bugs that
  would wreck v2. A green 8/8 is not evidence that attribution works.
