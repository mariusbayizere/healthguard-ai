# Session state — handover

Everything a fresh session needs to continue without re-deriving it. Written 2026-09-01, updated after the
infectious_fever rulings. All figures below were read from the files, not recalled.

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

| domain | filled | held |
|---|---|---|
| cardiac_respiratory | 26/28 | 3 |
| obstetric | 27/28 | 1 |
| infectious_fever | 10/30 | 4 | *(+1 not-applicable: IF07)*
| gastrointestinal | 6/28 | 0 |
| haemorrhage_trauma | 6/28 | 0 |
| neurological | 6/28 | 0 |
| chronic_care | 4/28 | 0 |
| paediatric | 4/28 | 0 |
| preventive | 4/28 | 0 |
| **total** | **93/254** | **8** |  *(+1 not-applicable = 94 resolved)*

Swahili brief (`speaker_brief_swahili_v2.csv`) is generated and untouched: 0/254.

**Provenance so far: 77 speaker, 14 machine_approved, 3 unresolved, 1
not_applicable.** A ~85% speaker rate. Frame fragments are complete: 17/17, of which 12 machine_approved
and 5 speaker rewrites.

## 3. Unresolved and held — nothing generates from these

| concept | person | why |
|---|---|---|
| CR04 | both | chest indrawing. `igituza kiramanuka` and `munsi y'igituza harinjira` are different descriptions. **Do not choose between them.** Held for a Rwandan clinician. |
| CR05 | third | wheeze. Redrafted to restore chest tightness alongside the sound; not accepted. The `-mu-` object marker is the uncertain part. |
| OB12 | third | breastfeeding advice. Restricted to the four obstetric relations, but **`Mama` is flagged, not decided** — it implies the speaker's own mother recently delivered. |
| PR02 | — | family planning. Unresolved pending Rwandan service-design confirmation on whether men present. **Out of generation entirely.** |

### needs_clinician — 10 rows, in two kinds

**Wording settled by the speaker, clinician not consulted (4):**

- `OB03` first and third — cord presentation. **Do not generate until validated.**
- `OB05` first — puerperal sepsis discharge description
- `CR04` first and third also carry a settled speaker phrasing, but are held
  above for a different reason.

**My draft held, nothing authored (6)** — `your_phrasing` empty, the draft left
in `suggested_kinyarwanda` as the record of what was rejected:

- `CR04` first and third — chest indrawing, a specific IMCI sign
- `CR05` third — `ijwi ridasanzwe` is patient-understandable but not a definitive
  clinical term for wheeze
- `IF01` first — fever with stiff neck. A specific danger sign; the wording is a
  guess. **Do not substitute a guess.**
- `IF03` first — IMCI general danger sign (unable to drink). Draft held as-is;
  no alternative invented.
- `IF04` first — `nkabira ibyuya` for sweating is unvalidated.
- `IF06` first — dysuria wording unvalidated and possibly the wrong register.

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

34 ROUTINE concepts, ruled by group:

```
CHILD_RELATIONS      18   group A (child services) + group C (mild symptoms)
NO_RELATIONS         10   group B, first person only
HOUSEHOLD_RELATIONS   4   group D: PR04, PR10, PR03, PR05
held                  1   OB12
do not generate       1   PR02
```

Group C's reasoning: a parent reports a child's mild cough; an adult does not
usually report another adult's.

**These are recorded per concept and must be materialised into
`CONCEPT_RELATIONS` at v2 build time**, because the generator keys on phrase
strings and most third-person phrases do not exist yet.

## 5. Standing rules — `docs/phrasing-guide.md`

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

## 6. Row target: 2,016,000

126 concepts x 2 persons x 4 languages = **1,008 authored phrases**. At 2,016,000
rows the median authored phrase accounts for 2,000 rows, which is the diversity
figure the project argues from. The person split doubled the denominator, so the
earlier 1,008,000 target would now give 1,000 rows per phrase.

**IF07 was ruled a duplicate of EX29** (see section 7), which takes the
generation-eligible concept count from 126 toward 125 once its third-person row
follows. The denominator above is not yet updated: `IF07` third is still
`applies=yes` on disk, and collapsing the concept touches `concepts.py`,
`concept_anchors.csv` and this figure. **Confirm before making that change.**

**It is a ceiling reached by valid combinations, not a quota to fill.** At roughly
0.8% of the combination space, no validity decision taken so far moves it at all.
The generator default is still `TARGET_ROWS_V2 = 1_008_000` and should move to
2,016,000 when the relation sets are materialised.

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

`IF07` first is now `applies=no`. **Its third-person row is untouched** and the
concept is not yet collapsed in `concepts.py` — see section 6.

The 15 third-person infectious_fever rows are **not** drafted, per the rhythm:
first person is ruled before third is drafted, and these rulings had to be
recorded first.

### Open question: is paediatric first person largely not-applicable?

**Rule this before drafting paediatric.** All 14 of its first-person rows would
have *a child speaking about themselves*. The four paediatric phrases the speaker
authored were third person (`umwana afite...`) and were moved to the third-person
rows accordingly.

If first person is not-applicable for most paediatric concepts, that domain is
closer to 14 rows than 28, and the `applies=no` mechanism already supports it —
`progress.py` counts such rows as resolved and the linter skips them. An older
child speaking for themselves is plausible for some concepts (PA08 ear pain, PA06
fever and rash) and not for others (PA02 too weak to breastfeed, PA03 unconscious).
So this may be a per-concept ruling rather than a domain-wide one.

This is a ruling, not a drafting decision, and it determines the size of the
domain.

### Blocked on the speaker, in order

1. Paediatric first-person applicability — this is next, and it is a ruling
2. `PR02` service-design question
3. `OB12` — is `Mama` plausible for a recent delivery?
4. `CR01` first person and `CR05` third person — the `-mu-` object marker
5. Confirm collapsing IF07 into EX29 in `concepts.py` and the row target
6. A clinician session for the `needs_clinician` rows — now 10, of which 6 are
   held drafts with nothing authored

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
review/walk.py              row-by-row accept/edit/rewrite, atomic writes
review/bulk_declare.py      bulk form/person declaration
review/split_authoring.py   two-author split preserving a blind overlap
review/make_second_review.py  second-speaker RATE and BLIND arms
```

`make test-clean` runs the suite in a throwaway clone of HEAD and is the guard
against ambient-state failures. 59 tests.

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
- **`attribute_phrase` was case-sensitive** and lost every row with an opener,
  which would have hollowed out the phrase holdout silently. It is now
  case-insensitive and `{REL}`-aware.
