# Taxonomy scope — which patients the three urgency classes are defined for

**Status 2026-09-15: decision deferred at your instruction (E6/E7 below); corpus measurement added (§8); ETAT
manual read and cited (§2), and a MODALITY mismatch recorded separately from the age mismatch (§2a).** Nothing in this document is a clinical
definition. Where a clinical fact is needed, it names the document that must supply it.

## 1. The defect

CLAUDE.md §18 defines ETAT as the *"WHO framework used in Rwandan health centres; basis for the 3-class
taxonomy"*. The same specification applies that taxonomy to every patient: registration takes any age (§7.4 form: 1–120;
§8.2 `patients` CHECK: 1–129), and the population is "14M+ Rwandans" (§4.1). You reported that WHO ETAT and
Rwanda's ETAT+ are paediatric frameworks, for newborns and children.

**The WHO ETAT manual confirms this for ETAT (§2).** It covers sick children from newborns ("under two months" is
a priority sign), does not address adults, and does not state an upper age. The specification therefore defines
adult urgency from a framework that does not cover adults. ETAT+ is still unread: no document is present.

**A second, separate defect: modality (§2a).** ETAT is defined on examination signs, and KinyaMed classifies
unexamined text.

## 2. What ETAT actually covers — read from the manual, 2026-09-15

**Source, the only one used in this section:** World Health Organization, *Emergency Triage Assessment and
Treatment (ETAT). Manual for participants*. © WHO 2005, ISBN 92 4 154687 5, "All rights reserved" (p. II).
- **File:** `docs/clinical/participant_manual.pdf`, SHA-256
  `9f2c85bf95925dd29905372bb8d650aae696a4af05dc0f32c55c1f602154c104`.
- **Completeness, checked before use:**
  - `pdfinfo`: 83 pages, not encrypted, `%%EOF` present.
  - `pdftotext` extracted every page without error.
  - Printed pages 1–78 are all present in sequence, and PDF page = printed page + 5 throughout. Front matter is
    cover, I–IV.
  - The three near-empty pages (PDF 59, 63, 83 = printed 54, 58, 78) were rendered and are blank versos
    carrying only a page number.
  - The table of contents (pp. III–IV) ends at Chart 11, p. 77, and that chart is present.
- **Not in this file:** the companion *Facilitator guide* (ISBN 92 4 154688 3, p. II).
- **Citation form:** *printed page (PDF page)*. Quotations are verbatim from the extracted text. Nothing here is
  from memory. A blank cell names the document that would fill it.

| Question | Answer from the manual | Section, page |
|---|---|---|
| **Stated target population** | **Sick children presenting to a hospital or health facility.** "a process of rapid triage for all children presenting to hospital" · "Triage all sick children when they arrive at a health facility" · chart title "Triage of all sick children". Published by the WHO Department of Child and Adolescent Health and Development; catalogued under "Child health services". | Introduction, p. 1 (PDF 6); Learning objectives, p. 2 (PDF 7); Annex 3, Chart 2, p. 67 (PDF 72); cover (PDF 1); p. II (PDF 3) |
| **Age range** | **Lower end:** "Tiny baby: any sick child aged under two months" is a priority sign, so newborns are in scope. **Upper age limit: not stated.** The manual never defines what age "child" ends at. The ages that do appear are bands for specific tasks: infant "under 12 months" (airway positioning), "infant (less than one year of age)" (pulse), fluid volumes for "infants (aged <12 months)" and "children (aged 12 months to 5 years)". The oldest case in the manual is "a 10-year old boy". | Priority signs, p. 4 (PDF 9) and p. 6 (PDF 11); Module Two, p. 16 (PDF 21); Module Three, p. 27 (PDF 32); Chart 11, p. 77 (PDF 82); Assessment questions: Circulation Q9, p. 33 (PDF 38) |
| Upper age limit, **blank** | — | **Not in this document.** The manual says its guidelines are contained in WHO *"Management of the child with a serious infection or severe malnutrition"* and the *"Pocketbook of hospital care for children"* (p. 2, PDF 7). Neither is in `docs/clinical/`. Rwanda's ETAT+ materials, if they exist as a document, could also state it. Whether any of these does is unverified. |
| **Exact triage category names** | Table "Categories after triage": **EMERGENCY CASES** ("Need immediate emergency treatment"), **PRIORITY CASES** ("Need assessment and rapid attention"), **NON-URGENT CASES** ("Can wait their turn in the queue"). Short forms: "E Emergency · P Priority · Q Queue (non-urgent)". Chart 2's headings are "EMERGENCY SIGNS", "PRIORITY SIGNS", "NON-URGENT". The manual mentions colour as an option only: "a red sticker to emergency cases, a yellow for priority and green for the queue". | Module One, p. 4 (PDF 9); p. 3 (PDF 8); p. 8 (PDF 13); Chart 2, pp. 67–68 (PDF 72–73); colours p. 5 (PDF 10) |
| **Criteria for each category** | **Emergency ("ABCD")**, from Chart 2: (1) airway and breathing: obstructed breathing, or central cyanosis, or severe respiratory distress; (2) circulation: cold hands with capillary refill longer than 3 seconds and a weak, fast pulse; (3) coma, or convulsing (now); (4) severe dehydration, "only in child with diarrhoea": diarrhoea plus any two of lethargy, sunken eyes, very slow skin pinch. **Priority ("3 TPR-MOB")**: tiny baby (<2 months); temperature very high; trauma or other urgent surgical condition; pallor (severe); poisoning (history of); pain (severe); respiratory distress; restless, continuously irritable, or lethargic; referral (urgent); malnutrition: visible severe wasting; oedema of both feet; burns (major). **Non-urgent**: "no emergency or priority signs". The manual says priority signs "might need to be adapted" to local epidemiology. | Chart 2, pp. 67–68 (PDF 72–73); Module One, pp. 3–4 (PDF 8–9) |
| **Does it address adults?** | **No, not as a triage population.** Every category, sign and chart concerns children. "Adult" appears only for equipment: adult-size nasal prongs (p. 21, PDF 26), adult IV giving sets (p. 46, PDF 51), adult self-inflating bags (p. 65, PDF 70). The only wider reference concerns the improvement process, not triage criteria: "Lessons learned in this process can be applied to other areas of child health in hospital and to care of other patient groups." | pp. 21, 46, 65; Introduction, p. 2 (PDF 7) |
| **Examination signs, or a verbal description?** | **Physical examination signs, observed or elicited by a health worker with the child present.** Definition: "Triage is the process of rapidly **examining** all sick children when they first arrive in hospital". "Triage of patients involves **looking for signs** of serious illness or injury." "The health worker **looks at the child, observes the chest** for breathing and priority signs such as severe malnutrition **and listens** to abnormal sounds such as stridor or grunting." Each emergency sign is elicited by hand or eye: "take the child's hand in your own" (warm hands); pressing the nail bed and timing the refill (capillary refill); calling, shaking and "a firm squeeze to the nail bed" (AVPU); pinching the abdominal skin (skin pinch); "comparing the child's palms with your own" (pallor). **On convulsion the manual rules explicitly against history:** "This assessment depends on your observation of the child and not on the history from the parent. Children who have a history of convulsion, but are alert during triage, need a complete clinical history and investigation, but no emergency treatment for convulsions. The child must be seen to have a convulsion during the triage process or while waiting in the outpatient department." | Module One, p. 3 (PDF 8), p. 4 (PDF 9); Module Three, p. 26 (PDF 31); Module Four, pp. 35–36 (PDF 40–41); Module Five, p. 44 (PDF 49); p. 7 (PDF 12) |
| — where history is used | **Asked of the mother or caretaker, in person, as an adjunct to the examination.** Whether the child has diarrhoea ("This information comes from the parent or guardian"), which gates the dehydration signs. The child's age "If the child appears very young". Poisoning ("The mother will tell you"). Urgent referral ("Ask the mother if she was referred … and for any note"). Head or neck trauma ("Ask if the child has had trauma"). Choking ("Ask the child's caretaker explicitly for a history of choking"). Whether a sleeping child "is just sleeping". Whether the eyes are "more sunken than usual". **In each case, a sign on the examined child is still assessed**, except the tiny-baby age, poisoning and referral priority signs, which can rest on history alone. | p. 43 (PDF 48); p. 6 (PDF 11); p. 7 (PDF 12); p. 16 (PDF 21), p. 8 (PDF 13); p. 14 (PDF 19); p. 35 (PDF 40); p. 44 (PDF 49) |
| **Does it address triage from a remote or written report?** | **No.** Triage happens on arrival: "as soon as a sick child arrives in the hospital, well before any administrative procedure such as registration", in "the outpatient queue, in the emergency room, or in a ward". The extracted text of all 83 pages contains **no** occurrence of *telephone, phone, radio, remote, SMS* or *mobile*. The one written document the manual mentions is a referral note that the mother brings. The note is read at the triage point with the child present: "Read the note carefully and determine if the child has an urgent problem." | Module One, "When and where should triaging take place?", p. 5 (PDF 10); Urgent Referral, p. 7 (PDF 12) |
| Remote or written-report triage, **blank** | — | **Not in this document.** It would need a MoH/RBC protocol for remote, pre-arrival or telephone triage, if one exists (H4), or the lead clinician's ruling (H6). None is in `docs/clinical/`. |
| Who triages | "Triage may be done in 15-20 seconds by medical staff or by non-medical staff (after appropriate training) as soon as the child arrives" · "gatemen, record clerks, cleaners, janitors who have early patient contact should be trained in triage for emergency signs" | Introduction, p. 1 (PDF 6); p. 5 (PDF 10) |
| **Rwanda / ETAT+** | **Not addressed.** The manual does not mention Rwanda. It names its development and field-test countries as Malawi, Angola, Brazil, Cambodia, Indonesia, Kenya and Niger. Whether this 2005 edition is the one used in Rwandan facilities is not stated. | p. 2 (PDF 7) |
| ETAT+ content, **blank** | — | **Not in this document.** It needs Rwanda's ETAT+ training materials (H3). None is in `docs/clinical/`. |

## 2a. MODALITY mismatch — separate from the age mismatch

**ETAT is defined on physical examination signs, not on a reported description of symptoms.** Its categories
are assigned by a trained person who examines the child on arrival (§2, pp. 3–4). The emergency signs are
things that person sees, hears, feels, presses or times on the child. KinyaMed receives text written or relayed
by a patient or carer, and nobody examines the patient before the classification.

These are two different mismatches:

| | Age mismatch (§1) | **Modality mismatch (this section)** |
|---|---|---|
| What differs | who the patients are | **what the categories are defined on** |
| ETAT | sick children; upper age not stated (§2) | examination signs, elicited in person, at arrival (§2) |
| KinyaMed | all ages (form 1–120) | an unexamined text report, possibly from someone other than the patient |
| Could data fix it? | Partly: a paediatric-scoped, natively authored corpus could match ETAT's population | **No.** A larger or better corpus improves how text is classified. It cannot make a category defined on capillary refill, AVPU response to pain, skin pinch or an observed convulsion apply to text that nobody examined. |
| Could an age rule fix it? | Yes, if E6 chooses (a) or (c) | **No.** It applies to children and adults alike |

**What the manual itself says about the gap, and no more than that:**
- For **convulsion**, it rules that a parent's history does **not** establish the emergency sign. The child "must
  be seen to have a convulsion during the triage process" (p. 36, PDF 41).
- For the **other emergency signs**, it does not discuss whether a carer's description can stand in for the
  health worker's observation (for example "his lips are blue" for central cyanosis). It is silent, not
  permissive. Deciding that equivalence is a clinical question (L16), and I have not answered it.
- **Three priority signs rest on history** (tiny baby by age, poisoning, urgent referral), per pp. 6–7. These
  are the only ETAT criteria the manual shows being assigned from what someone says.

**What this does to the question for the lead clinician (H6).** The earlier question was "map ETAT's
categories to CRITICAL / URGENT / ROUTINE, and does it apply to text?" The manual answers the second half: it
does not describe text at all. The questions become:
1. Is there **any validated basis** for assigning urgency from an unexamined text or verbal report, for children
   or adults, in use in Rwanda? If so, which document? (Not ETAT, per §2.)
2. If there is none, **what may a text-based classification claim to be?** For example, a pre-examination hint
   that never replaces ETAT at the door. This is a product and clinical-safety question. I have not decided it.
3. If ETAT is kept as a reference at all, **which carer descriptions, if any, count as equivalent to an ETAT
   sign**, sign by sign? And who validates that mapping?

**Consequences recorded, nothing changed:**
- **E6 is not decided.** Options (a) and (c) in §4 both assumed ETAT could be the clinical basis, subject to H6
  confirming it applies to text. The manual now makes that confirmation unlikely in the form it was asked.
  So (a) does not escape the modality question.
- The same question applies to IMCI, BEC, MCPC and ESI (§3). Each is cited in the repo, none is in the repo,
  and whether each is examination-based is **unverified**.
- The evaluation-set label definitions (EVAL_SET_SPEC, D7 protocol §3) cannot be drawn from ETAT's criteria as
  written, because an annotator reading a vignette cannot examine anyone.
- CLAUDE.md §18 ("ETAT … basis for the 3-class taxonomy") is contradicted by the document on **two** counts, age
  and modality. SRS correction A21 needs both.

## 2b. Construct-validity gap — nothing in the repo authorises urgency from an unexamined written report

**Stated plainly: no document currently in this repository authorises assigning urgency to a patient from a
written symptom report by someone who has not examined that patient.** Everything the system does after
receiving text rests on that missing authority.

**Checked on 2026-09-15:**
- `docs/clinical/` holds one file, the WHO ETAT participant manual (§2).
- `docs/compliance/` does not exist.
- The only PDFs anywhere under `kinyamed/` are that manual and the project's own paper (`ml_model/paper/main.pdf`).
- No tracked file mentions telephone triage, nurse advice lines, tele-triage or remote triage, other than this
  file and STATE.md.

| Instrument | In the repo? | Bedside or report-based | Authority for text triage |
|---|---|---|---|
| **WHO ETAT** (2005 participant manual) | **yes**, `docs/clinical/participant_manual.pdf` | **Bedside examination.** "Triage is the process of rapidly examining all sick children when they first arrive in hospital" (Module One, p. 3, PDF 8). On convulsion: "This assessment depends on your observation of the child and not on the history from the parent … The child must be seen to have a convulsion during the triage process" (Module Four, p. 36, PDF 41). | **None.** It requires examination and does not address remote or written reports (§2). |
| **WHO IMCI Chart Booklet 2014** | **no** | Bedside, as you report it. **Not verifiable here: the document is absent.** | none that can be cited |
| **WHO-ICRC Basic Emergency Care 2018** | **no** | Bedside, as you report it. The repo's own summary is consistent with that but is not the document: "first-contact providers", "ABCDE and SAMPLE history" (`ml_model/docs/clinical-anchors.md:15–16`, `:20`). **Not verifiable here: the document is absent.** | none that can be cited |
| WHO MCPC 2017, ESI, Manchester Triage System | **no** | not verified | none that can be cited |

**This is a construct-validity gap, not a data gap.** The labels CRITICAL / URGENT / ROUTINE are meant to
measure a clinical construct. The only construct the repo can cite, ETAT's categories, is defined by an
examination that never happens in this system. Consequences:
- **No dataset fixes it.** More rows, native authoring, clinician labels and higher κ all make the labels more
  reliable. None of them makes the labels measure an examination-defined category, because the input lacks
  the examination.
- **No model fixes it.** A perfect classifier of these labels would still be classifying something no
  instrument defines.
- **It is fixed only by choosing a construct that is defined on the input the system actually receives**, and
  finding a document or clinical authority that supports it. `reports/CONSTRUCT.md` proposes one candidate; it is
  not adopted. STATE.md adds the question of whether a validated report-based instrument exists (a lead, not
  verified).

**Not decided here:** E6, the construct, and any renaming. Nothing in the code was changed.

## 3. What the system currently claims to cover

| Where | Claim | Age scope implied |
|---|---|---|
| CLAUDE.md §18 glossary | ETAT is the basis of the 3-class taxonomy | ETAT's scope: sick children, upper age not stated (§2, from the manual). ETAT is defined on examination signs (§2a). |
| CLAUDE.md §18 glossary | CRITICAL = "ESI 1–2", URGENT = "ESI 3", ROUTINE = "ESI 4–5" | ESI is the Emergency Severity Index, a different instrument from ETAT. The specification cites two incompatible bases. |
| CLAUDE.md FR-01-01, §7.4, §8.2 `patients` | age collected; 1–120 on the form, CHECK 1–129 | all ages |
| `ml_model/docs/triage-taxonomy.md`, `clinical-anchors.md` | concepts anchored in WHO IMCI 2014 (children under five, per that file), WHO-ICRC Basic Emergency Care 2018 (recorded as "adult-inclusive"), plus clinician-defined concepts | mixed; no age field on any concept |
| Paper `related_work.tex:26–37`, `method.tex:109–122` | IMCI 24 · BEC 15 · MCPC 11 · "clinician-defined, no WHO anchor" 20, totalled as "70 of 128 concepts carry an anchor" | mixed. **The 70 counts 20 concepts that have no anchor**, so 50 have a document anchor. Other repo files give IMCI 28–29, BEC 18, MCPC 10, and totals of 68, 80, 127 or 128 concepts (see STATE.md, SRS CORRECTIONS) |
| Corpus (DATASET_AUDIT) | 9 domains, including `paediatric`, `obstetric`, `chronic_care` and `preventive` | mixed; age is a domain, not a variable |
| v2d test sentences (MODEL_AUDIT §7) | include high blood pressure, chest pain with breathlessness, and a relative with fever | adult and unspecified |
| Backend | `patients.age` optional (0–130); **triage never reads it** | none: the model sees text only |
| D7 protocol, EVAL_SET_SPEC §11 | B1 = ETAT; B3 = "the adult triage tool, if not ETAT"; the adult question is flagged for the lead clinician | the defect was flagged, but not resolved |
| Patient-facing text, `CURRENT_CAPABILITY.md` | no age scope stated anywhere | — |

**None of the other source documents above (IMCI, BEC, MCPC, ESI) is in the repository.** Their scopes are
recorded here as the repo describes them. I have not verified them, including whether each is examination-based.
Only ETAT has been read (§2).

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
  be rethought with the clinician. **Update 2026-09-15:** the manual defines ETAT on examination signs and never
  mentions remote or written-report triage (§2, §2a). This is the likelier outcome, and the question to H6 is
  now the one set out in §2a. E6 stays undecided.
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

