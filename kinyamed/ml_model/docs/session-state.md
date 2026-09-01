# Session state — handover

Everything a fresh session needs to continue without re-deriving it. Written 2026-09-01, updated after the
infectious_fever rulings, the IF07 collapse and the paediatric person rulings. All figures below were read from the files, not recalled.

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
| infectious_fever | 10/30 | 4 | *(+2 not-applicable: IF07 both persons)*
| gastrointestinal | 6/28 | 0 | *(+1 not-applicable: GI04 first)*
| haemorrhage_trauma | 6/28 | 0 |
| neurological | 6/28 | 2 | *(+2 not-applicable: NE01, NE02 first)*
| chronic_care | 4/28 | 0 |
| paediatric | 4/28 | 1 | *(+11 not-applicable: only PA08-PA10 first survive)*
| preventive | 4/28 | 0 |
| **total** | **93/254** | **13** |  *(+16 not-applicable = 109 resolved)*

Swahili brief (`speaker_brief_swahili_v2.csv`) is generated and untouched: 0/254.

**Provenance so far: 77 speaker, 14 machine_approved, 3 unresolved, 16
not_applicable.** A ~85% speaker rate. Frame fragments are complete: 17/17, of which 12 machine_approved
and 5 speaker rewrites.

## 3. Unresolved and held — nothing generates from these

| concept | person | why |
|---|---|---|
| CR04 | both | chest indrawing. `igituza kiramanuka` and `munsi y'igituza harinjira` are different descriptions. **Do not choose between them.** Held for a Rwandan clinician. |
| CR05 | third | wheeze. Redrafted to restore chest tightness alongside the sound; not accepted. The `-mu-` object marker is the uncertain part. |
| OB12 | third | breastfeeding advice. Restricted to the four obstetric relations, but **`Mama` is flagged, not decided** — it implies the speaker's own mother recently delivered. |
| PR02 | — | family planning. Unresolved pending Rwandan service-design confirmation on whether men present. **Out of generation entirely.** |

### needs_clinician — 15 rows, in three kinds

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

**Nothing drafted; the question itself is clinical (1):**

- `NE06` first — new confusion. `applies=yes` stands. Whether a patient who can
  accurately report their own new confusion is meaningfully confused is a
  clinical question, not a linguistic one, so no first-person phrase is written
  until it is settled.
- `HT03`, `CC01`, `CC02`, `NE04` first — held, `applies=yes`, **not deleted**.
  All four turn on severity and capacity: whether a patient that unwell can still
  report. Clinical questions, so rule 11 raised them and stopped.

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

33 ROUTINE concepts, ruled by group:

```
CHILD_RELATIONS      17   group A (child services) + group C (mild symptoms)
NO_RELATIONS         10   group B, first person only
HOUSEHOLD_RELATIONS   4   group D: PR04, PR10, PR03, PR05
held                  1   OB12
do not generate       1   PR02
```

33 rows, down from 34: IF07 was removed with the concept.

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

## 6. Row target: 1,808,000

**Standing: the target is a consequence of the valid inventory, not a quota. If
removals shrink it, that is correct — the number never drives a clinical
decision.** 2,000 rows per authored phrase is the invariant; recompute whenever a
ruling changes the phrase count.

```
ceiling  125 concepts x 2 persons x 4 languages = 1,000 phrases
minus    14 applies=no rows x 4                 =    56
minus    10 NO_RELATIONS thirds x 4             =    40
net                                                 904 phrases
                                    at 2,000/phrase -> 1,808,000 rows
```

**`PR09` is not counted.** It is ruled `applies=no` but rule 12 makes its
first-person row valid, and it is not recorded either way. If it is removed the
figure is **1,800,000** (900 phrases); if rule 12 wins it stays at 1,808,000.

The 14 `applies=no` rows: PA01-PA07 and EX40-EX43 (paediatric first person),
plus GI04, NE01 and NE02. The 40 `NO_RELATIONS` phrases are ruled in
`routine_relation_sets.csv` but **not yet materialised in the brief**.

Held rows are *not* deducted: HT03, CC01, CC02, NE04 and NE06 keep `applies=yes`
and are held, not deleted, so they still count as authorable phrases.

History: 2,016,000 at 126 concepts; 2,000,000 at 125; 1,888,000 after PA01-04;
1,832,000 after PA05-07 and EX40-43; **1,808,000** after GI04, NE01 and NE02.
`TARGET_ROWS_V2` is still `1_008_000` and moves when the relation sets are
materialised.

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

### In flight: infectious_fever third person

14 rows (IF07 is gone). **9 drafted, 4 held, 1 flagged.** All nine render across
all eight relations in `review/infectious_fever_third_render.csv`, 72 rows for
individual ruling. Nothing accepted.

| id | draft |
|---|---|
| IF02 | `{REL} afite umuriro mwinshi kandi yaragagaye.` |
| IF05 | `{REL} afite umuriro kandi afite uduheri ku mubiri wose.` |
| EX24 | `{REL} afite umuriro wa dogere 39.` |
| EX25 | `{REL} afite umuriro mwinshi kandi arakorora cyane.` |
| EX26 | `{REL} afite ibimenyetso bya malariya, umuriro n'imbeho.` |
| EX27 | `{REL} afite umuriro kandi yumva afite imbeho, akeka ko ari malariya.` |
| EX28 | `{REL} afite umuriro kandi umutwe uramubabaza cyane.` |
| EX29 | `{REL} afite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo afite.` |
| EX31 | `{REL} amazuru ye aratemba gake.` |

Every transform reuses one of the speaker's own. EX28 is the strongest: OB02
turns the identical clause `umutwe urandya cyane` into `umutwe uramubabaza
cyane`, changing the verb to avoid the object marker. EX31 avoids the same
problem with the possessive, following CR03 and OB07 rather than reaching for
`aramutemba`.

**Held, not drafted (4):** `IF01`, `IF03`, `IF04`, `IF06`. Their first person is
held for a clinician and unaccepted, so a third-person draft would be
transforming a guess.

**Flagged, not drafted (1): `EX30`.** Its transform would be
`{REL} akorora gake ariko nta muriro afite.` — **byte-identical to the approved
CR07 third**. The first persons differ by one word (`sinta` / `nta`). This is the
IF07/EX29 shape, except **CR07 is cardiac_respiratory and EX30 is
infectious_fever**, so the same utterance would carry two domain labels. That is
worse than a within-domain duplicate and wants a ruling before either row moves.

Two flagged beyond their confidence marks: **EX27**, where `nkeka` -> `akeka`
follows the regular pattern but the speaker has not written it; and **EX26**,
whose first person carries no person marking at all, so the two rows differ by
nothing but `{REL} afite` — worth checking the third earns a separate phrase.

### Settled: paediatric first person — 11 of 14 rows are not applicable

Ruled per concept, not domain-wide. **Only PA08, PA09 and PA10 keep a
first-person row.** Third person is unaffected throughout.

| concept | first | ground |
|---|---|---|
| PA01 convulsing | `no` | a convulsing child cannot speak for themselves |
| PA02 too weak to breastfeed | `no` | an infant too weak to breastfeed cannot speak at all |
| PA03 unconscious or floppy | `no` | cannot speak for themselves |
| PA04 fast breathing with indrawing | `no` | severe respiratory distress; cannot speak |
| PA05 diarrhoea, sunken eyes | `no` | sunken eyes is an observer sign; removing it leaves a weaker concept overlapping GI04/GI06 |
| PA06 fever and rash | `no` | duplicates IF05; the distinction lives in `{REL}` |
| PA07 thin, not gaining weight | `no` | a growth-monitoring finding, not a self-report; thinness alone overlaps CR06 |
| EX40 convulsing with fever >40 | `no` | rule 9 — duplicates IF02 (and NE01); also cannot speak |
| EX41 cannot breathe, skin blue | `no` | rule 9 — duplicates CR03; also cannot speak |
| EX42 fever and rash | `no` | rule 9 — duplicates IF05, the PA06 collapse again |
| EX43 high fever, cannot eat | `no` | rule 9 — duplicates IF03 |
| **PA08 ear pain and discharge** | `yes` | no adult counterpart; a child can report both signs |
| PA09 growth monitoring | `yes` | untested — see below |
| PA10 due for vaccination | `yes` | untested — see below |

**Rule 9 caught EX40-EX43** and nothing outside paediatric. It does *not* catch
PA09 or PA10: neither duplicates an adult concept, since no adult growth-
monitoring or vaccination concept exists. They raise a different question —
whether an under-five self-presents for a routine child service at all — which is
the PA01-PA04 "would not speak" ground rather than the duplication ground.
**Not applied unasked; it needs a ruling.**

### Person-applicability audit — `review/person_applicability_audit.csv`

Rule 11 applied to all 254 rows across the nine domains. **9 catches, 6
conflicts, nothing recorded** — every row is left as it stands pending a ruling,
because unlike rule 9 this test needs clinical judgement per concept and six of
its findings disagree with phrases the speaker already authored.

**Catches — first-person row still empty, no work lost by ruling `applies=no`:**

| concept | limb | certainty |
|---|---|---|
| GI04 watery diarrhoea, sunken eyes, slow skin pinch | observer | high — the skin pinch is an examination manoeuvre |
| NE01 continuous convulsion | observer | high — cannot speak, as PA01 |
| NE02 unconscious, cannot be roused | observer | high — cannot speak, as PA03 |
| PR09 deworming for a child | service received | high — the child receives it, an adult brings them |
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
- `EX46` `gukingiza umwana` — structural. The child receives the vaccination, so
  limb 2 says third person, but the authored first-person phrase is the *carer*
  speaking. Either "first person" means the requester rather than the patient for
  service concepts, or EX46 belongs in the third-person row. **PA09 and PA10 wait
  on exactly this question.**

Beyond paediatric the test proposes removing at most **8** first-person rows
(NE06 now ruled in), adds none, and identifies one row (`CC03`) it would be wrong
to remove. Two of its own limbs have been corrected by what the speaker had
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
6. `PA09`/`PA10`, and `EX46` with them — for a service concept, is the
   first-person row the patient or the requester? One answer settles all three
7. `CR07`/`EX30` — the same utterance in two domains; concept ruling needed
8. The 9 infectious_fever third-person drafts, rendered in
   `review/infectious_fever_third_render.csv`
9. A clinician session for the `needs_clinician` rows — now 10, of which 6 are
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
