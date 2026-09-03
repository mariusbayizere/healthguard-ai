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
| obstetric | 27/28 | 2 | 27 | *(OB12 and OB11, both held)* |
| infectious_fever | 17/30 | 9 | 21 | *(+4 not-applicable: IF07 and EX30, both persons)* |
| gastrointestinal | 20/28 | 3 | 25 | *(+5 not-applicable: GI04 first, GI08 both, EX17 both)* |
| haemorrhage_trauma | 20/28 | 2 | 24 | *(+4 not-applicable: HT01 and HT06, both persons)* |
| neurological | 6/28 | 1 | 8 | *(+2 not-applicable: NE01, NE02 first)* |
| chronic_care | 4/28 | 2 | 4 | |
| paediatric | 4/28 | 1 | 15 | *(+11 not-applicable: only PA08-PA10 first survive)* |
| preventive | 4/28 | 2 | 4 | *(both holds are PR02)* |
| **total** | **128/254** | **25** | **154** | *(+26 not-applicable = 154 resolved)* |

The `held` column counts **every** `hold=yes` row, including the eight
infectious_fever and gastrointestinal third-person rows held only because their
first person is held. An earlier version of this table counted the first-person
holds alone, summed to 16 and printed 18. Read it from the brief, not from here:

```
python -c "import csv,collections; print(collections.Counter(r['domain'] for r in csv.DictReader(open('review/speaker_brief_kinyarwanda_v2.csv')) if r['hold']=='yes'))"
```

Swahili brief (`speaker_brief_swahili_v2.csv`) is generated and untouched: 0/254.

**Provenance so far: 77 speaker, 49 machine_approved, 5 unresolved, 26
not_applicable.** CR07 first moved from machine_approved to speaker when it took
EX30's wording; the infectious_fever third-person batch added seven
machine_approved and one speaker rewrite. The two PR02 rows became `unresolved`
when its exclusion was recorded in the brief (section 3).

**Speaker rate: 77 of 126 authored rows, 61%.** 126 is `speaker +
machine_approved`; the not-applicable and unresolved rows are not authored and do
not belong in the denominator. The rate fell from 74% because the gastrointestinal
third-person batch added eight machine_approved rows, and because EX17 first — a
speaker row — became not_applicable in the collapse. **A falling rate here is the
third-person transform working as designed**, not a loss of speaker authorship: a
regular transform of a phrase the speaker wrote is `machine_approved` by
definition.

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

### needs_clinician — 18 rows, in three kinds

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

**The bridge now exists: `review/relation_sets.py`** (2026-09-03). Before it,
the rulings sat in a CSV no code path read, and every consumer fell back to
`DOMAIN_RELATIONS` without an error — which is how EX16 was rendered across eight
relations for ruling when its ruling allows five.

```
python review/relation_sets.py               # every ruling and whether it is in force
python review/relation_sets.py --materialise # emit CONCEPT_RELATIONS for the v2 build
python review/render_third_person.py <domain>  # render via the SAME resolver
```

`resolve(concept_id, domain)` is the single source of truth; `render_third_person.py`
uses it, so **a render can no longer disagree with a ruling**. Renders were ad hoc
before, which is why the EX16 one was wrong. `tests/test_relation_sets.py` (13
tests) pins the resolver, the materialiser and the renderer's substitution against
`build_families`.

**Five authored phrases carry a ruling that is not yet in force** — this is a live
exposure, not a future one: `CR07`, `EX16`, `EX29`, `EX31` are all ruled
`CHILD_RELATIONS` and would otherwise expand over their domain's eight, and
`OB11` is ruled `NO_RELATIONS` (see the conflict below). Nothing has generated
yet, so nothing is wrong in the corpus; it would have been wrong at v2 build.

**`OB11` — ruled HELD, 2026-09-03, and materialisation is unblocked.** The
conflict was: ruled `NO_RELATIONS`, so it generates no third person, but a
third-person phrase is authored (`machine_approved`):
`{REL} aratwite kandi ashaka kujya kwa muganga kwisuzumisha.` Applying the ruling
would have zeroed an accepted phrase silently; overriding it would have
contradicted a speaker ruling.

**Held, so both survive** — the same treatment PR02 got, and the same underlying
question: whether anyone presents on another's behalf for a first antenatal
booking is service design, not language.

Two details worth keeping:

- **`source` stays `machine_approved`, not `unresolved`.** PR02 became
  `unresolved` because it had nothing authored to record. Provenance says how a
  phrase came to be; `hold` says it must not generate. They are orthogonal and
  overwriting the first with the second destroys the acceptance record.
- **`materialise()` now understands `hold`**: a held row is excluded from the
  mapping *and* is not reported as a conflict, so one open question no longer
  blocks every other ruling. It is listed as `HELD — not in force, not blocking`.
  Pinned by `test_a_held_row_neither_generates_nor_blocks`.

`python review/relation_sets.py --materialise` now emits the four
`CHILD_RELATIONS` mappings (CR07, EX16, EX29, EX31) and exits 0.

Two further record conflicts, both on rows with nothing authored so nothing is at
risk yet:

- **`PR06`** is `NO_RELATIONS` in `routine_relation_sets.csv` but "adult
  relations" in the concept rulings above. There is no `ADULT_RELATIONS` set in
  `vocabulary.py`.
- **`CC05`** appears in the concept rulings above and is absent from the CSV.

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
ceiling  120 concepts x 2 persons x 4 languages =   960 phrases
minus    14 applies=no rows x 4                 =    56
minus    10 NO_RELATIONS thirds x 4             =    40
net                                                 864 phrases
                                    at 2,000/phrase -> 1,728,000 rows
```

126 -> 125 -> 124 -> 123 -> 122 -> 121 -> 120: IF07 into EX29, EX30 into CR07,
GI08 into EX16/EX17, EX17 into EX16, **HT06 into EX22 and HT01 into EX18 (all
executed 2026-09-03)**. PR02 is out of generation on top of that.

**How 123 and 14 reconcile with the brief**, because they look wrong next to it:

```
127  concept ids in the brief
 -6  IF07, EX30, GI08, EX17, HT01, HT06 collapsed into other concepts
 -1  PR02, out of generation pending the service-design ruling
120  concepts in the ceiling

 26  applies=no rows on disk
-12  the twelve rows of the six collapsed concepts, already outside the ceiling
 14  applies=no rows the ceiling still counts
```

**PR02 is subtracted once, as a concept, not again as two rows.** Its rows stay
`applies=yes` (section 3), so they never enter the 14. A future session that
marks them `applies=no` must drop the concept subtraction at the same time or
the target silently loses eight phrases.

**The EX16/EX17 collapse is executed** (2026-09-03). The consumer was built
first so EX17's wording would survive the collapse rather than be lost by it; the
pairing is now declared in the brief and `second_phrasings.py` emits it.

History: 2,016,000 at 126; 2,000,000 at 125; 1,888,000 after PA01-04; 1,832,000
after PA05-07 and EX40-43; 1,808,000 after GI04, NE01, NE02; 1,792,000 after the
EX30 collapse; 1,776,000 after GI08; 1,760,000 after EX17; **1,728,000** after HT01 and HT06.
`TARGET_ROWS_V2` is still `1_008_000`.

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

The EX16/EX17 collapse was blocked on this. **The consumer was built first, then
the collapse executed on 2026-09-03** — which is the order that mattered, because
collapsing before the consumer existed would have lost EX17's wording rather than
preserved it. What was built:

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

**Executed 2026-09-03.** EX16 primary, EX17's wording written into EX16 first's
`second_phrasing_optional`; EX17 both persons `applies=no` / `not_applicable` with
the wording kept as the record; EX17 removed from `routine_relation_sets.csv`
(31 -> 30 rows). `second_phrasings.py` now reports one second phrasing and emits:

```
PHRASE_VARIANTS = {
    'iyo maze kurya numva mu nda ntameze neza':
        'iyo maze kurya numva inda itameze neza',
}
```

The caveat that made the ordering matter: nothing read that column before the
consumer existed, so collapsing first would have **lost** EX17's wording instead
of preserving it. The mechanism landed first, deliberately. `PHRASE_VARIANTS`
itself is still populated at v2 build time from this column — the declaration
lives in the brief, not in `vocabulary.py`.

Target moved to **1,760,000** (880 phrases, 122 concepts).

### Blocked on the speaker — two words that do not exist in the corpus

`GI03` needs a word for stool and `PA08` needs a word for ear. Neither appears in
any authored phrase, in `dataset/vocabulary.py`, or in
`phrase_review_sheet.csv`. **These cannot be drafted, suggested or worked around**
— inventing Kinyarwanda is what standing rules 5 to 8 exist to prevent, and a
plausible-looking guess here would enter the record as a phrase rather than as a
question. GI05 routed around the stool noun by using `impiswi`; melaena and ear
pain have no such route.

### Settled: gastrointestinal third person — all nine ruled 2026-09-03

14 rows. **10 accepted, 2 held, 2 `applies=no`.** The domain is 20/28 filled and
25/28 resolved. Ruled one at a time against the rendered relations; nothing
batch-accepted.

| id | ruling | phrase |
|---|---|---|
| GI01 | accept | `{REL} araruka ibyo arya byose kandi ntashobora no kunywa.` |
| GI02 | accept | `{REL} araruka amaraso.` |
| EX14 | accept | `{REL} arababara cyane mu nda.` |
| GI07 | accept | `{REL} arababara cyane mu nda kandi ububabare ntibuhagarara.` |
| GI05 | accept | `{REL} afite impiswi zirimo amaraso.` |
| GI06 | accept | `{REL} amaze ibyumweru birenga bibiri arwaye impiswi.` |
| EX12 | accept | `{REL} amaze iminsi itatu arwaye impiswi zikomeye.` |
| EX13 | accept | `{REL} arakomeza kuruka kandi ntashobora kurya.` |
| EX15 | accept | `{REL} araruka cyane kandi yumva afite intege nke.` |
| EX16 | accept, after the collapse | `Iyo {REL} amaze kurya, yumva inda itameze neza.` |
| GI03 | held | blocked on the missing word for stool |
| GI04 | **held, `needs_clinician`** | see below |
| GI08 | `applies=no` | collapsed into EX16/EX17 earlier |
| EX17 | `applies=no` | collapsed into EX16 in this batch |

**EX14 was ruled before GI07 on purpose.** GI07 properly contains it, so
`phrase_components` unions them into one phrase group; settling the contained
phrase first makes that union concrete rather than theoretical. Verified after
both were recorded.

**GI04 held.** Two of three elements substantiate — `impiswi zikomeye` is the
speaker's own EX12, and `amaso`/`amaso ye` are now attested (20 distinct CHW
records), which **clears** the flag that said `amaso` appeared only in unapproved
draft D005. The verb carrying the clinical sign does not: **`yinjiye` has one hit
in 445k characters of real clinical Kinyarwanda and it means oxygen entering the
lungs.** No replacement invented — there is no attested candidate, and the 524 CHW
questions, which cover ICCM and childhood diarrhoea densely, describe dehydration
as `kubura amazi mu mubiri` and never by sunken eyes. Whether that is how the sign
is actually reported in Rwanda or an artefact of a 524-row sample cannot be told
from the sample. Separately unchanged: the very slow skin pinch is an examination
manoeuvre a caregiver cannot report, so the draft carries two of three signs
whatever the wording. **Same shape as PA08's ear term, in a different domain.**

### The render CSV can be wrong for a concept with a relation ruling — FIXED at the cause

`gastrointestinal_third_render.csv` rendered **EX16 across all eight relations**.
Its ROUTINE group-C ruling is `CHILD_RELATIONS`, five. The render fell back to the
gastrointestinal domain default because **`CONCEPT_RELATIONS` is still `{}`** — the
ROUTINE rulings in `routine_relation_sets.csv` have not been materialised into it,
which section 4 says must happen at v2 build time and has not happened yet.

Caught before EX16 was ruled; it was re-rendered against `CHILD_RELATIONS` and
ruled on the correct five. Of the nine in that batch only EX16 had such a ruling.

**The cause is fixed rather than the instance** (2026-09-03). Renders were ad hoc
scripts consulting the empty `CONCEPT_RELATIONS`;
`review/render_third_person.py` now resolves through `relation_sets.resolve()`,
the same function the v2 build materialises from, so a render cannot disagree
with a ruling again. It reproduces the hand-corrected gastrointestinal file
exactly — 85 rows, EX16 on five relations — and `tests/test_relation_sets.py`
carries the EX16 case as a regression test. **No need to check the CSV by hand
before a batch any more; use the renderer.** See section 4.

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

**86 tests**, and v1 still reproduces 8/8 (re-run 2026-09-03) — v1 phrases are noun-phrase fragments
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
9. ~~`GI08` vs `EX16`/`EX17`~~ — **ruled and executed**; both collapses done
10. ~~The gastrointestinal third-person drafts~~ — **all nine ruled 2026-09-03**;
    eight accepted, GI04 held. The domain's only open rows are GI03 (both
    persons) and GI04 third
11. A clinician session for the `needs_clinician` rows — **17**, of which 6 are
   held drafts with nothing authored, 5 are undrafted, and GI04 third is the
   newest (section 3)

### Settled: haemorrhage_trauma third person — all ten ruled, all accepted

10 rows ruled one at a time against `haemorrhage_trauma_third_render.csv` (77
rows: 9 concepts on eight relations, HT08 on five). **All ten accepted**; nothing
batch-accepted. **The domain is closed apart from HT03 and HT05**, both held on
their first person.

| id | phrase |
|---|---|
| EX18 | `{REL} ari kuva amaraso menshi kandi ntahagarara.` |
| EX19 | `{REL} afite igikomere gikomeye kirimo kuva amaraso menshi.` |
| EX20 | `{REL} ari kuva amaraso menshi mu mazuru kandi ntahagarara.` |
| EX21 | `{REL} afite igikomere ku mutwe nyuma yo kugwa.` |
| EX22 | `{REL} afite igikomere cyanduye, kiratukura kandi kirimo amashyira.` |
| EX23 | `{REL} yaraguye none arababara cyane.` |
| HT02 | `{REL} afite igikomere gikomeye ku buryo igufa rigaragara.` |
| HT04 | `{REL} afite ubushye bunini ku mubiri.` |
| HT07 | `{REL} yarumwe n'inzoka.` |
| HT08 | `{REL} afite igikomere gito kandi amaraso yarahagaze.` — **five relations** |

**Most of this batch was inert.** Eight of the ten are `mfite` -> `afite` and
nothing else, because the descriptors agree with the *wound* rather than with the
patient — `kirimo`, `gito`, `cyanduye`, `rigaragara`, `bunini` all transfer
untouched, and `nyuma yo kugwa` is a nominalisation with no person marking at all.
Worth knowing as a general property: **a phrase whose predicates agree with the
complaint rather than the speaker transforms for free.**

Three that did not:

- **`EX18`/`EX20` are the worst shared-prefix pair in the corpus.** They share a
  24-char head *and* a 19-char tail, differing only by `mu mazuru` inserted
  mid-phrase, so neither contains the other and `phrase_components` will not union
  them — 16 rendered rows across two CRITICAL concepts. Fourth instance of the
  shape (EX16/EX17 21 chars, HT02/EX19 25 chars). **A second phrasing is not the
  fix**: EX16/EX17 were one concept said two ways, these are two concepts. A
  rewrite following the speaker's own EX31 third pattern (`{REL} amazuru ye ...`)
  was offered and declined in favour of parallelism with the first person.
- **`EX23`'s `yaraguye` is unattested anywhere**, but the alternation is the
  speaker's own: IF02 third and OB01 third both carry `yaragagaye` from a first
  person `nagagaye`. Materially different from GI04's `yinjiye` (attested once, in
  the wrong sense) and HT05's deformity term (no candidate at all) — here the stem
  `kugwa` is attested three ways over and only the inflection is unseen.
- **`HT07` is the one row that rests on attestation rather than transform.**
  `yarumwe n'inzoka` IS the corpus construction across three real snake-bite
  consultations; the first-person `Narumwe` was derived from it. The direction is
  reversed from every other row because the attestation corpus is CHW case-report
  register. Standing caution: `inzoka` means intestinal worms in most hits, and
  the verb `-rumwe` is what disambiguates — a future phrase using the noun without
  a biting verb loses that protection.

**`HT08` is the fix's first clean win.** It rendered on five relations because
`render_third_person.py` resolved `CHILD_RELATIONS` from
`routine_relation_sets.csv` unprompted. The equivalent row before the bridge
existed would have been rendered on eight and ruled on three wrong ones — which is
precisely what happened to EX16.

### Ruled: CRITICAL frame restriction — mechanism built, applies at v2 build

`CONTEXTS_BY_URGENCY` and `CLOSERS_BY_URGENCY` in `vocabulary.py`, consulted by
`build_families`. **Both are empty, and that is deliberate: empty means no
narrowing, which is v1's behaviour exactly.** Applying the restriction now would
change CRITICAL family sizes, change what `rng.sample` draws, and break the frozen
digests — v1's CRITICAL families draw on all five closers. Populated at v2 build
time, like `PHRASE_FORMS` and `CONCEPT_RELATIONS`.

The ruled value is recorded as `V2_CRITICAL_CLOSER_EXCLUSIONS = ('. Murakoze.',)`
so it is not lost between now and the build.

```
CRITICAL closers   5 -> 4      frame 1,500 -> 1,200
capacity   5,250,000 -> 4,200,000
headroom        9.21x -> 7.37x     (needs 570,240)
```

Only `. Murakoze.` qualifies: `. Nkora iki?` ("What do I do?") is a real question
in an emergency and stays. When the fragment brief's `. Urakoze.` reaches
`CLOSERS` it is the same sign-off and joins the exclusion. URGENT is deliberately
not restricted. `tests/test_urgency_frames.py` pins empty-means-untouched,
restriction-shrinks-only-CRITICAL, and that CRITICAL still clears its bucket.

**Six de-escalating fragments added to `frame_fragments_brief.csv`** (33 -> 39
rows) — 3 contexts, 3 closers, English glosses and shapes only,
`kinyarwanda` and `suggested_kinyarwanda` deliberately **empty** for the speaker
to author. They are what lets ROUTINE be fixed by *adding* frame material instead
of removing it, which the capacity analysis says is the only safe direction.

### STOPPED before drafting neurological — five concepts may duplicate v1

`neurological` was next, and surveying it before drafting found that **five of its
eight new concepts restate concepts already in v1**, whose phrases the speaker has
already authored as EX32-EX36:

| new concept | v1 phrase, authored as | |
|---|---|---|
| `NE01` continuous convulsion | `EX33` `Yagagaye kandi arimo guhinda umushyitsi.` | v1: `kugagara no guhinda umushyitsi` |
| `NE02` unconscious, cannot be roused | `EX32` `Yataye ubwenge kandi ntasubiza.` | v1: `yataye ubwenge ntiyasubiza` |
| `NE03` sudden one-sided weakness | `EX34` `Uruhande rumwe rw'umubiri we ntirukora.` | v1: `uruhande rumwe rw'umubiri rutagikora` |
| `NE04` sudden difficulty speaking | `EX35` `Ntashobora kuvuga neza kandi umunwa we waragoramye.` | v1: `kutabasha kuvuga neza n'umunwa wagoramye` |
| `NE08` intermittent mild headache | `EX36` `umutwe urandya ariko ntabwo cyane` | v1: `uburibwe buke mu mutwe budakabije` |

**No `distinct from` note exists on any of them.** That is the IF07/EX29 test
exactly: the only concepts in the corpus carrying a recorded axis are CR01/EX05,
and inventing one here would be manufacturing. Possible axes are visible —
*sudden* for NE03/NE04, *intermittent* for NE08, *continuous* for NE01 — but none
is recorded in `concepts.py` or `concept_anchors.csv`, and the speaker's authored
EX34 already says the side "no longer works", which is the sudden reading.

**Corroborating evidence from rule 11.** `NE01` and `NE02` first person are already
`applies=no` — a convulsing or unconscious patient cannot report. `EX33` and `EX32`
first person are still open, and would fall to the same test. Two concepts that
take the same rule-11 outcome on the same ground are hard to tell apart.

**If all five collapse: 120 -> 115 concepts, and the target falls to roughly
1,648,000.** Not executed; five concept rulings are the speaker's.

**Drafted anyway, because they are not entangled: `NE05` and `NE07`.** `NE06` is
`needs_clinician` and deliberately not drafted. `NE05` carries only **two of its
three signs** — no word for light exists in any source (`urumuri` attested nowhere,
`izuba` once meaning sunbathing), so photophobia is vocabulary-blocked, the fourth
instance after GI03, PA08 and HT05.

### Eight authored third-person phrases carry no `{REL}` and sit outside the relation architecture

Found in the same survey. `EX32`-`EX35` are bare third-person sentences whose
subject prefix carries the person (`Yataye ubwenge...`), and `EX40`-`EX43` hard-code
`umwana` as a lexical subject. **None of the eight expands over relations** — each
contributes one phrase instance where a `{REL}` phrase contributes four to eight.

Two consequences: they are invisible to every relation ruling, including
`CHILD_RELATIONS` on the paediatric EX40-EX43 where varying the child term is
exactly what the set is for; and they depress the capacity of their classes in the
way `docs/urgency-frame-coupling.md` describes. Whether that is intended — the
speaker authored all eight — is a question for them.

### LIVE BUG found while designing the closure rule — `phrase_components` misses containments

`phrase_components` unions on **raw substring containment**, and every v2 phrase
is an utterance ending in a full stop. The stop defeats the `in` check:

```
EX14 third  {REL} arababara cyane mu nda.
GI07 third  {REL} arababara cyane mu nda kandi ububabare ntibuhagarara.
            -> NOT a containment today, because of the period
```

At render time `_drop_terminal_stop` removes exactly that period, so the *rendered
rows* do contain one another. **Five authored pairs are silently not unioned**
(CR02/EX02 both persons, EX02/EX04 third, EX14/GI07 both persons) — two by the
terminal stop, two by capitalisation.

**This is the fourth time a terminal stop has defeated a string match here.**
`attribute_phrase` failed the same way three times (section 9). The fix,
`_match_form`, already exists **in the same file** and is not used by
`phrase_components`. **v1 cannot be affected**: 0 of its 184 phrases end in a stop
or begin capitalised, and the full partition is provably identical, so the frozen
split survives. **Fix this before the next batch.**

### Open design question: phrase-group closure — `docs/phrase-group-closure.md`

Four near-duplicate pairs were noticed by hand across four rulings. Measuring found
**85 pairs sharing 15+ characters of prefix** — which is not a defect list, it is
the domain's grammar (`{REL} aratwite kandi`, `{REL} afite umuriro`,
`{REL} afite igikomere`).

Recommendation: fix the containment bug above, then add a **prefix threshold of
30**, which is **v1-safe** (partition identical; below 22 it breaks the frozen
digests) and catches **eight pairs of which six were missed by deliberate
inspection**. Emit the merges as a report rather than silently. Keep
`PHRASE_VARIANTS` for same-concept variants and do not overload it.

### Open design question: provenance categories — `docs/provenance-categories.md`

**The 61% speaker rate understates the corpus and should not be quoted.** It counts
a `ndi` -> `ari` transform of a sentence the speaker wrote as machine-authored, so
the rate falls every time third-person work lands even though nothing about the
speaker's involvement changed (74% -> 66% -> 61% across three batches).

Proposed five categories with mechanical tests:

```
speaker-authored                     77   60.2%
speaker-derived (person transform)   27   21.1%
machine-drafted, speaker-approved    11    8.6%
machine-derived                      11    8.6%
unresolved (CR04)                     2    1.6%

the speaker's own words   104/128 = 81%
newly composed by me       22/128 = 17%, every row with an explicit accept
```

The split is deliberately conservative — clauses reused from a *different* concept
(GI06 from CR06, GI01 from OB10) still count as machine-drafted, which
under-counts speaker-derived rather than flattering it.

### Open design question: urgency/frame coupling — `docs/urgency-frame-coupling.md`

Raised while ruling HT08 and analysed, **not implemented**. A ROUTINE phrase
renders with escalating contexts and closers (`sinshobora gusinzira`,
`Ndakeneye ubufasha vuba`), contradicting the label the row is trained on. It
runs the other way too — CRITICAL with `. Murakoze.` trivialises.

**The answer is capacity, not language.** Rows are sampled *without replacement*
and quotas are capped at a family's combinations, so nothing repeats — the only
question is whether each class can still fill its bucket. Restricting ROUTINE's
frames takes its headroom from **3.24x to 1.16x** (drop 2 contexts + 2 closers) or
to **0.78x** (also drop 2 openers), and 0.78x fails the 28% `CLASS_TARGETS` floor.
Restricting CRITICAL costs almost nothing — it has 9.21x.

**ROUTINE is structurally thin because the relation rulings concentrate there**:
2.6 instances per phrase against 4.3 for the other classes, because ten ROUTINE
concepts are `NO_RELATIONS` and eight more `CHILD_RELATIONS`. Recommendation:
restrict CRITICAL, and fix ROUTINE by having the speaker author *de-escalating*
contexts and closers rather than by removing frames.

**Also surfaced: "2,000 rows per phrase" is a corpus median, not a per-phrase
property.** A first-person phrase has only 1,500 combinations and can never reach
2,000 alone; `{REL}` phrases expanding over 4-8 relations carry the average up.
Worth stating in `v2-sizing.md` before someone reads the invariant as a guarantee.

### Drafted: haemorrhage_trauma first person — 7 rows, awaiting rulings

Suggestions only; nothing authored. **Two of the nine concepts collapsed before
any wording was ruled**, which is why drafting a domain starts with the concept
questions:

- **`HT06` into `EX22`** — one word apart (`kirabyimbye` swollen vs `cyanduye`
  infected). HT06 was clinician-defined with no WHO anchor; EX22 is a v1 concept
  and speaker-authored. **The "swollen" second phrasing was NOT written**: that
  wording is an unaccepted machine draft, and `second_phrasing_optional` feeds
  `PHRASE_VARIANTS` into the corpus, so putting a draft there would generate
  machine Kinyarwanda as corpus content without an accept. EX22's slot is left
  empty and open for the speaker to author if they want it kept.
- **`HT01` into `EX18`** — EX18's `ntahagarara` already carries uncontrolled
  bleeding; HT01's only axis was that pressure had been applied and failed. The
  attestation corpus could not settle whether a patient frames it that way: all
  seven pressure-plus-bleeding sentences are clinicians *instructing* a CHW
  (`shyiraho umwenda`, `bandeji ikanda`), never a lay self-report — and that
  corpus is CHW register, so patient speech is absent by construction. **The
  corpus was the wrong instrument for the question**, which is worth knowing
  before reaching for it again on a first-person concept.

**Ruled 2026-09-03: 4 accepted, 1 held.** `HT02`, `HT04`, `HT07`, `HT08` accepted
`machine_approved`; `HT05` held. `HT03` stays held. **First person is closed for
this domain.**

**`HT05` held, vocabulary-blocked — a third instance of the GI03/PA08 shape.** The
draft says BROKEN (`kwavunitse`); the gloss and the English seed say DEFORMED
("my arm is bent out of shape after a fall"). Those are different claims —
deformity is what a patient perceives, a fracture is the diagnosis, which is
exactly rule 11's axis. No attested Kinyarwanda for "bent out of shape" exists in
any source; only the fracture vocabulary is attested, which is what pulled the
draft off its own concept. Needs the speaker's word, or a ruling that the concept
becomes "broken limb after a fall" — in which case `concepts.py` and the anchor
gloss must move with it rather than be left disagreeing.

Flags carried on the rows rather than resolved:

- **`nkanda` and `narumwe` are not attested.** Their 3sg counterparts are
  (`bandeji ikanda`; `yarumwe n'inzoka` in real snake-bite cases) and the 1sg
  forms are regular transforms. **This is systematic: the CHW corpus is
  third-person register, so it under-attests first-person inflection.** For
  first-person drafting it supplies nouns and stems, not inflections.
- **`inzoka` is a false friend** — most hits mean intestinal worms (deworming,
  albendazole); the snake sense is real but only visible by reading contexts. A
  first read of three hits had it wrong in the other direction.
- **`ubushye` is the mirror case** — attested as a real burn in a clinician's
  scald description, but most hits are the simile `bimeze nk'ubushye` for a rash.
- `bunini` on `ubushye` and `kwavunitse` on `ukuguru` are concord inferences.
- **`HT05` says BROKEN where its gloss says DEFORMED.** Deformity is what a
  patient sees, a fracture is the diagnosis — substantive, and the speaker's.

### Then

Resume the rhythm: **first person first, then third with `{REL}`, one domain at a
time, rendered across every relation for individual ruling. Never batch-accept.**

Remaining: **100 of 254** Kinyarwanda rows, all 254 Swahili. Roughly 5-8 hours
per language at 2-3 minutes a row.

**Gastrointestinal is closed** apart from GI03 and GI04, both blocked on
vocabulary or a clinician rather than on drafting. infectious_fever first and
third are both closed.

**haemorrhage_trauma is closed** apart from HT03 and HT05. Four domains are now
effectively done — cardiac_respiratory, obstetric, gastrointestinal,
haemorrhage_trauma — leaving only blocked rows in each.

**Next, in this order:**

1. **`neurological`** — 6/28 filled, 20 left, all eight relations confirmed, one
   concept ruling to check (`NE08` is `CHILD_RELATIONS`). No unresolved
   architecture. The obvious next domain.
2. **`paediatric`** — 4/28 filled but only 13 left, because 11 rows are already
   `applies=no`. Rule 12 settled PA09/PA10, so the blocker that stalled it is
   gone; PA08 stays vocabulary-blocked on the ear term.
3. **`infectious_fever`** — 9 left, but **all nine are held**: IF01/IF03/IF04/IF06
   both persons and EX27 third. Nothing to draft until a clinician session.
4. **`chronic_care`** and **`preventive`** — 24 left each, the two biggest blocks
   and the least done. Both carry open questions to read first: CC01/CC02 held,
   PR02 out of generation, CC08/CC09/CC10 and six preventive concepts ruled
   `NO_RELATIONS` (first person only), four ruled `HOUSEHOLD_RELATIONS`, and the
   service concepts settled by rule 12. **Check `relation_sets.py` output before
   drafting either** — they carry more relation rulings than every other domain
   combined.

**Render any third-person batch with `review/render_third_person.py <domain>`**,
never by hand — that is what the EX16 bug cost, and HT08 is the proof it now works
unprompted.

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
review/relation_sets.py     concept ruling -> relations; --materialise for the build
review/render_third_person.py  render a domain's thirds via the SAME resolver
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
against ambient-state failures. **86 tests** — this section and section 7 once
said 59 and 62; both were stale. `python -m pytest --collect-only -q | tail -1` settles
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
