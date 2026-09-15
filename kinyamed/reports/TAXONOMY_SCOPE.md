# Taxonomy scope — which patients the three urgency classes are defined for

**Status 2026-09-15: decision deferred at your instruction (E6/E7 below); corpus measurement added (§8).** Nothing in this document is a clinical
definition. Where a clinical fact is needed, it names the document that must supply it.

## 1. The defect

CLAUDE.md §18 defines ETAT as the *"WHO framework used in Rwandan health centres; basis for the 3-class
taxonomy"*. The same specification applies that taxonomy to every patient: registration takes any age (§7.4 form: 1–120;
§8.2 `patients` CHECK: 1–129), and the population is "14M+ Rwandans" (§4.1). You report that WHO ETAT and
Rwanda's ETAT+ are paediatric frameworks, for newborns and children. If so, the specification defines adult
urgency from a framework that does not cover adults.

## 2. What ETAT / ETAT+ actually covers — PENDING the document

**Not yet citable.** `docs/clinical/` does not exist in the repository as of 2026-09-15. Per L5 this section
states nothing from memory. When the WHO ETAT Participant Manual is placed, fill in:

| Question | Answer (verbatim or close paraphrase) | Document, section, page |
|---|---|---|
| Stated target population / age range | PENDING | PENDING |
| Triage categories and their names | PENDING | PENDING |
| Criteria for each category | PENDING | PENDING |
| Does it address adults? | PENDING | PENDING |
| Does it assume physical examination by a trained health worker? | PENDING | PENDING |
| ETAT+ (Rwanda): which document, and what it adds | PENDING (no ETAT+ document listed for placement) | PENDING |

The last two questions matter to this project in particular. KinyaMed classifies a **patient's or carer's text**.
A framework whose categories depend on signs a health worker observes may not be applicable to text at all.
That is a question for the lead clinician (H6), not something I can decide.

## 3. What the system currently claims to cover

| Where | Claim | Age scope implied |
|---|---|---|
| CLAUDE.md §18 glossary | ETAT is the basis of the 3-class taxonomy | ETAT's scope (paediatric, per your finding) |
| CLAUDE.md §18 glossary | CRITICAL = "ESI 1–2", URGENT = "ESI 3", ROUTINE = "ESI 4–5" | ESI is the Emergency Severity Index, a different instrument from ETAT. The specification cites two incompatible bases. |
| CLAUDE.md FR-01-01, §7.4, §8.2 `patients` | age collected; 1–120 on the form, CHECK 1–129 | all ages |
| `ml_model/docs/triage-taxonomy.md`, `clinical-anchors.md` | concepts anchored in WHO IMCI 2014 (children under five, per that file), WHO-ICRC Basic Emergency Care 2018 (recorded as "adult-inclusive"), plus clinician-defined concepts | mixed; no age field on any concept |
| Paper `related_work.tex:26–37`, `method.tex:109–122` | IMCI 24 · BEC 15 · MCPC 11 · "clinician-defined, no WHO anchor" 20, totalled as "70 of 128 concepts carry an anchor" | mixed. **The 70 counts 20 concepts that have no anchor**, so 50 have a document anchor. Other repo files give IMCI 28–29, BEC 18, MCPC 10, and totals of 68, 80, 127 or 128 concepts (see STATE.md, SRS CORRECTIONS) |
| Corpus (DATASET_AUDIT) | 9 domains, including `paediatric`, `obstetric`, `chronic_care` and `preventive` | mixed; age is a domain, not a variable |
| v2d test sentences (MODEL_AUDIT §7) | include high blood pressure, chest pain with breathlessness, and a relative with fever | adult and unspecified |
| Backend | `patients.age` optional (0–130); **triage never reads it** | none: the model sees text only |
| D7 protocol, EVAL_SET_SPEC §11 | B1 = ETAT; B3 = "the adult triage tool, if not ETAT"; the adult question is flagged for the lead clinician | the defect was flagged, but not resolved |
| Patient-facing text, `CURRENT_CAPABILITY.md` | no age scope stated anywhere | — |

**None of the source documents above (IMCI, BEC, MCPC, ESI) is in the repository.** Their scopes are recorded
here as the repo describes them. I have not verified them.

## 4. Options

### (a) Restrict v1 to paediatric, and say so everywhere

- **Clinical basis:** one framework (ETAT/ETAT+), if H6 confirms it applies to text-described presentations.
- **Product:**
  - `age` becomes mandatory before triage. An adult, or an unknown age, gets the existing fail-closed path: no
    classification, "automated triage covers children only — triage manually" to staff.
  - Scope is stated on the patient receipt, the nurse screen, the doctor board, `CURRENT_CAPABILITY.md`, the
    paper, the README and CLAUDE.md §4.
  - Every adult who presents falls outside the tool, and staff must be told so; no adult is silently served.
- **Data and model:**
  - The concepts, corpus and v2d are mixed-age. Rows about adults leave scope in every domain, and v2d's
    evaluation no longer applies. The model must be retrained or re-scoped.
  - Paediatric input is almost always **reported by a carer**. That is v2d's measured weakness: 42% correct in
    first person against 14% in third person on the same fever sentence (MODEL_AUDIT §7).
- **Corpus survival (measured, §8):**
  - **70,131 rows (21.3%) are about a child, from 91 distinct symptom clauses.**
  - 67.2% of those are ROUTINE, mostly preventive requests (weighing, vaccination, deworming).
  - **Acute child content is 50 distinct clauses** (23 CRITICAL, 27 URGENT). Every one is the relation
    "Umwana wanjye" substituted into a concept, and 49.2% of child rows are machine-derived transforms.
  - Of the n=9 test set, 1,931 rows survive: 4 child renderings, 2 of them CRITICAL.
  - **In practice, (a) means authoring new caregiver-voice training data, not filtering the corpus.**
- **Risk:** narrowest claim; the easiest to validate and the easiest to state honestly.

### (b) Find and cite a separate adult framework instead

- **Clinical basis:** a document that defines adult triage categories and is in use in Rwandan facilities.
  - None is in hand.
  - The Rwanda MoH Internal Medicine Clinical Treatment Guidelines are adult, but whether they contain triage
    categories is unknown until read.
  - BEC 2018 is recorded as adult-inclusive, but whether it defines triage *categories* is unverified.
- **Product:** the mirror of (a). Children are excluded, and scope is stated everywhere.
- **Data:** the `paediatric` domain and the IMCI-anchored concepts leave scope.
- **Corpus survival (measured, §8):**
  - **141,934 rows (43.0%) name an adult relation** (wife, husband, mother, father, elderly woman), from 278
    distinct clauses; 16.9% of them are ROUTINE.
  - **Up to 259,869 rows (78.7%) survive** if rows whose age is not stated count as adult: 63,427 about a
    sister or neighbour, 53,571 self-reports, 937 other. Whether that assumption is acceptable is not an
    engineering call; the speaker could be an adolescent.
  - Of the n=9 test set, 9,303 rows are definitely adult; up to 16,011 if unstated ages count as adult.
- **Risk:** it depends on a document that may not exist in the form needed. It also excludes the population
  ETAT/ETAT+ was written for.

### (c) Both frameworks, with an age-based routing rule

- **Clinical basis:** two documents, two category mappings, two sets of worked examples, both ratified by H6.
  - The **age boundary itself is a clinical definition**: it must be cited (ETAT's stated range), not chosen by
    engineering.
- **Product:**
  - `age` becomes mandatory. Missing age fails safe (manual triage, or NEEDS REVIEW — a clinical choice).
  - Every triage record stores which framework applied.
  - The routing rule needs its own tests at the boundary and for missing or implausible ages.
- **Data and model:**
  - Age group becomes a variable in the corpus, the concepts and the model input: either separate models or
    one model conditioned on age group.
  - v2d does not use age.
- **Corpus survival (measured, §8):**
  - Every row can stay, but the router needs an age group per row.
  - **212,065 rows (64.3%) have an age group the text itself states**: 70,131 child, 141,934 adult relation.
  - **116,998 rows (35.5%) do not** (sister, neighbour, or self-report). Those need an age added at generation
    or a stated default.
  - Separately, 21,651 rows (6.6%) open with "Nzanye umwana wanjye" (*I have brought my child*), and 25,670
    (7.8%) carry "Abandi bana na bo bafite iki kibazo" (*other children have this too*), on a clause **not**
    about a child: 45,232 distinct rows (13.7%), since some carry both. Their frame and clause contradict each other on age. The router would have to rule on these,
    or they would need regenerating.
- **Risk:** matches a real health centre's population; roughly doubles clinical sign-off, annotation and evaluation.

## 5. Recommendation (the decision is yours) — revised 2026-09-15 after the §8 measurement

### Summary: how much of the existing corpus survives each option

| | (a) paediatric only | (b) adult only | (c) both, routed |
|---|---|---|---|
| Rows kept | **70,131 (21.3%)** | **141,934 (43.0%)** certain; up to 259,869 (78.7%) if unstated ages count as adult | 330,000, but only **212,065 (64.3%)** carry an age group in the text |
| Distinct symptom clauses kept | 91 | 278 certain; up to 487 | 578 |
| Acute (CRITICAL + URGENT) distinct clauses | **50** | not separately counted | — |
| ROUTINE share of rows kept | 67.2% | 16.9% (adult-relation rows) | — |
| Machine-derived share of rows kept | 49.2% | 33.0% (adult-relation rows) | 36.6% of all third-person rows |
| n=9 test set rows kept (of 17,942) | 1,931: **4 sentences, 2 CRITICAL** | 9,303 certain; up to 16,011 | 17,942, of which 11,234 carry an age in the text |

**What the measurement changed.** My earlier recommendation of (a) treated it as the cheap, narrow option. On
the data side it is not cheap:
- it keeps a fifth of the rows;
- it keeps only 50 distinct acute sentences, all mechanical "Umwana wanjye" substitutions;
- it leaves a test set of 2 CRITICAL sentences.

A paediatric v1 would need natively authored caregiver speech for training as well as for evaluation. The
clinical logic of (a) is unchanged: it is still the only option whose framework is being placed in
`docs/clinical/`.

**Revised recommendation:**
- **Do not choose E6 on corpus grounds.** The corpus fails every option, for different reasons:
  - (a) has too little child content;
  - (b) depends on assuming the age of 116,998 rows;
  - (c) has no age variable, and 45,232 rows' frames contradict their clause on age.
  The evaluation set has to be authored fresh under any option (EVAL_SET_SPEC), so the evaluation set does not
  favour one option either.
- **Decide E6 on H6's answers to two questions:**
  1. Can ETAT categories be applied to a text description?
  2. Which adult framework, if any, is used at first contact in Rwandan health centres?
- **Whatever E6 becomes, record two separate fields on every new evaluation item from the pilot:**
  - **patient age group** (as the chosen framework defines it);
  - **reporter**: self, carer, or other.
  The corpus shows why they must be separate. 32,179 rows have an adult relative as the grammatical subject and
  a child as the patient.

What would change this recommendation:
- H6 says ETAT's categories cannot be applied to text descriptions. Then (a) has no basis either, and scope must
  be rethought with the clinician.
- The Internal Medicine guidelines turn out to contain a usable adult triage scheme. Then (c) becomes feasible
  sooner.

The cost of (a) is real: every adult is excluded, and the tool must say so clearly enough that no adult is
silently triaged by a paediatric model.

## 6. What this changes in EVAL_SET_SPEC.md

The grid (§7) and power calculation (§3–4) assume one taxonomy with one set of definitions.

| Spec element | (a) paediatric only | (b) adult only | (c) both, routed |
|---|---|---|---|
| Protocol §3 definitions | one set, from ETAT | one set, from the adult document | **two sets**; annotators trained on both; the item records which applies |
| Urgency × language power (400 CRITICAL per pure language) | unchanged | unchanged | **per age group, if the gate must hold per group**: 3,200 CRITICAL items instead of 1,600 |
| Test set size | 4,900 (unchanged) | 4,900 | about **9,800** if powered per group; 4,900 if age is coverage-only |
| Kinyarwanda first phase (E5) | 1,300 items | 1,300 | about **2,600**. The labelling estimate grows from ~11–16 h to ~22–33 h per annotator (CLINICIAN_BRIEF rates; still unmeasured) |
| Domain axis (§7) | from ETAT's organisation; `chronic_care` / `preventive` adult concepts out | from the adult document; `paediatric` out | union of both, per group |
| Presentation type "paediatric" | becomes the whole set; replaced by the document's own age bands (cite) | removed | becomes the age-group axis |
| Voice axis (first person / reported) | mostly carer-reported; the ≥ 10% first-person floor needs revisiting | unchanged | per group |
| Reporter vs patient (§8 finding, all options) | split "voice" into two fields: **reporter** (self / carer / other) and **patient age group**. The subject of the verb is not always the patient. | same | same |
| Obstetric | adolescent pregnancy only, if in scope at all (clinical question) | in scope (B4) | per group |
| κ (§9) | per language | per language | per language **and per framework**, since the definitions differ |
| Calibration split (§5) | unchanged | unchanged | per group, or shown to transfer |
| New items | age group recorded per item; adults are refused at item import | children refused | boundary items (just under / over the cited age) as a coverage cell |

**Decisions this adds to EVAL_SET_SPEC §12:**
- **E6** — scope option (a), (b) or (c).
- **E7** — under (c), is age group a *powered* axis (the gate must pass for children and for adults separately)
  or *coverage-only* (pooled gate, per-group reported but not gated)? A coverage-only axis lets a model that
  fails children pass overall, so powered is the safer choice and the more expensive one.

## 7. Other documents this touches, whichever option

- **CLAUDE.md §18:** the ETAT basis and the ESI mapping contradict each other. This is a specification
  correction for you (add to SRS CORRECTIONS REQUIRED).
- **Paper `related_work.tex` / `method.tex`:** "70 carry an anchor" includes 20 concepts defined as having no
  anchor (50 are anchored), and the counts disagree with `clinical-anchors.md` and `licensing.md`. Recorded as
  submission-blocking in STATE.md.
- **`CURRENT_CAPABILITY.md`:** it says nothing about age scope. It should, once E6 is decided.
- **D7 protocol §3, CLINICIAN_BRIEF, the D2 clinician pack:** they carry the single-taxonomy assumption.

## 8. Measurement: grammatical person and patient of the v2 corpus (2026-09-15)

Script: `reports/measurements/grammatical_person.py`. Output: `reports/measurements/grammatical_person.txt`.
Run from `ml_model/`, about 1 minute. It reads the frozen split files (`train_phrase_holdout.csv` +
`eval_phrase_holdout.csv` = 330,000 rows, Kinyarwanda only, 165 distinct phrases) and writes nothing.

### 8.1 Method

- **Unit: the symptom clause, not the row.** Openers and closers carry first-person *speaker* morphology into
  rows about someone else, as in "**Nzanye** umwana wanjye", "**Nda**keneye ubufasha", "kandi **sin**shobora
  gusinzira". The clause is the phrase as rendered in the row, recovered exactly from the row's `phrase` column
  and the relation substituted into it. There are 578 distinct clauses.
- **Reference: grammatical person of the clause's subject.** All 165 phrases are "utterance" form (no subject
  slot), so person is carried by the phrase:
  - a `{REL}` phrase is third person by construction, and the relation is recovered from the row text;
  - the other 88 were read from Kinyarwanda subject concord (1sg *n-/m-*, negative *si-n-*; 3sg class 1 *a-*,
    *ya-*, negative *nt-a-*), 1sg object concord (*-ra-n-*: *birangora*, *urandya*) and possessives (*-anjye*
    vs *-e*);
  - **this reading agrees with the Kinyarwanda speaker's `person` column** in
    `review/speaker_brief_kinyarwanda_v2.csv` **on all 165 phrases**. So the grammatical-person reference is
    speaker-ruled, not mine.
- **Patient, meaning whose condition it is, is a second label and partly my reading:**
  - a child relation (`CHILD_RELATIONS`; only "Umwana wanjye" occurs in the rows) means about a child;
  - 4 `{REL}` phrases and 4 first-person phrases name "umwana (we/wanjye)" as the person to be weighed,
    vaccinated, dewormed or fed. They are counted as about a child although the subject is an adult.
  - **"Umwana wanjye" means *my child*: the text does not state an age.** Whether these rows describe children
    is a speaker question, as are the 7 readings the script lists as uncertain.
- **Automatic concord classifier**, to answer "can person be told from morphology". It sees only the clause
  text: no phrase column, no `{REL}` marker.

| Classifier | Row error vs speaker-ruled person | Distinct clauses wrong (of 578) |
|---|---|---|
| Rule set v1, as first written | **18.9%** | 130 |
| Rule set v2, revised after inspecting v1's errors **on this same corpus** | **8.7%** (optimistic: no held-out data) | 60 |
| Rule set v2 on the **whole row** instead of the clause | **71.8%** | — |

Residual errors are real ambiguities, not only bugs:
- *nt-a-* is 3sg negative in a main clause, but can be 1sg in a subordinate clause (*ku buryo ntabasha*);
- class-6 nouns (*amaraso*, *amazuru*) take the same *a-*/*ya-* concord as a class-1 person;
- carer requests ("Ndashaka ko bapima ibiro by'umwana wanjye") are grammatically first person, so no
  concord rule can see that the patient is the child.

**Conclusion on method.** On this templated corpus, person can be counted reliably from the generator's
structure plus the speaker's rulings, and that is what every share below uses. A concord rule set alone is
8.7–18.9% wrong on clauses and useless on whole texts. On open patient speech it would be worse, and it must
not be used without a Kinyarwanda speaker.

### 8.2 Results

| | Rows | Share |
|---|---|---|
| **Self-report** (speaker's own condition) | 53,571 | **16.2%** |
| **About someone else** | 275,985 | **83.6%** |
| – about a child: the relation is "Umwana wanjye" | 33,352 | 10.1% |
| – about a child: the speaker's own request for their child | 4,600 | 1.4% |
| – about a child: an adult relative's request, relayed | 32,179 | 9.8% |
| – about an adult relation (wife, husband, mother, father, elderly woman) | 141,934 | 43.0% |
| – about a sister or neighbour (age not stated) | 63,427 | 19.2% |
| – third person, nobody named ("umubiri we") | 493 | 0.1% |
| No person marked ("Amazi yamenetse") | 444 | 0.1% |

**The corpus is not self-report.** 83.6% of rows describe someone other than the speaker, and 21.3% describe a
child. The premise that the corpus is written like "sinshobora guhumeka" holds for 16.2% of rows.

**Seed phrases (165):**
- 82 self-report (49.7%), 78 third person, 4 carer requests, 1 unmarked.
- The 77 `{REL}` phrases render as: 50 with child and adult relations, 14 with adult relations only, 9 with
  child relations only, and 4 relayed child requests.

**Provenance of the third-person rows** (270,892), from `review/provenance.py`:
- 86,708 (32.0%) speaker-authored;
- **81,136 (30.0%) speaker-derived and 99,136 (36.6%) machine-derived**, i.e. person-transforms of a
  first-person phrase;
- 3,912 (1.4%) machine-approved.

**Two-thirds of the carer-voice rows reuse self-report vocabulary with the concord changed; they were not
written as carer speech.** Your point that caregiver speech differs in vocabulary, not only morphology, is
therefore not testable on this corpus: it barely contains natively written caregiver speech.

**n=9 test set (17,942 rows):**
- 5 self-report phrases: 3,016 rows (16.8%);
- 4 `{REL}` phrases rendered over 8 relations: 14,926 rows (83.2%);
- about a child: 1,931 rows (10.8%), four sentences, **2 CRITICAL**.

**Domains:**

| Domain | Share of corpus | Self-report | About a child | About an adult or unstated-age relation |
|---|---|---|---|---|
| paediatric | 11,441 (3.5%) | 439 (3.8%)¹ | **11,002 (96.2%)**, of which 9,170 are weighing requests | 0 |
| obstetric | 32,600 (9.9%) | 6,985 (21.4%) | 0 | 25,171 (77.2%); 444 unmarked |
| all other 7 domains | 285,959 (86.7%) | 46,147 | 59,129 | 180,190 (+493 third person, nobody named) |

¹ "Mfite umuhaha", first person in the paediatric domain.

- **Paediatric acute content is 4 phrases, 1,832 rows.** The remaining paediatric rows are one ROUTINE
  weighing request.
- **Obstetric** is phrased as report by a relative in 77.2% of rows (wife, mother, sister or neighbour, per
  the speaker's `DOMAIN_RELATIONS` ruling) and as self-report in 21.4%.

### 8.3 Data findings outside the question, recorded not acted on

- **Brief/corpus mismatch.** "iyo maze kurya numva mu nda ntameze neza" is in the corpus (1,141 rows), but the
  speaker brief marks that first-person concept (EX17) `applies=no`. "Nkorora gake ariko nta muriro mfite"
  maps to CR07 (`applies=yes`) and also to EX30 (`applies=no`).
- **Frame contradictions on age:** 21,651 rows open "Nzanye umwana wanjye" and 25,670 rows carry "Abandi bana
  na bo bafite iki kibazo" on a clause not about a child; 45,232 rows (13.7%) have one or both.

### 8.4 What this measurement does not establish

- The age of any self-reporter.
- Whether "umwana wanjye" rows describe children.
- Whether any concept is clinically valid for a child (H6).
- How real caregivers phrase a child's symptoms: no natively written caregiver speech exists to compare.

