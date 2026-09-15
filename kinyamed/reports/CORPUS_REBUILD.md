# Corpus rebuild — specification (not to execute until a clinical lead and native authors exist)

## 1. Why the v2 corpus is replaced

- **Effective size is 165 authored phrases.** 330,000 rows are those phrases × relations × frames: about 2,000
  rows per phrase (DATASET_AUDIT; TAXONOMY_SCOPE §8).
- **More than half the rows are mechanical person-transforms.**
  - 180,272 of 330,000 rows (54.6%) are person-transforms of a first-person phrase (e.g. *ndi* → *ari*).
  - Of those, 99,136 transform a **machine-drafted** phrase: 36.6% of all third-person rows, 55.0% of the
    transformed rows.
  - The other 81,136 transform a speaker-authored phrase (definitions: `ml_model/review/provenance.py`).
- **This does not meet CLAUDE.md §10.2.** Machine output may enter only as a draft that a native reviewer
  accepts, with `validated_by` recorded. No row records `validated_by`.
- **Not publishable as it stands.** No per-row provenance or validator; frames carry no provenance; 45,232 rows
  (13.7%) have a frame that contradicts the clause on age; the anchor licences are unresolved (DATASET_AUDIT).
  Nothing in it may be released or cited as a dataset contribution.

## 2. What replaces it

All numbers below are **engineering proposals for diversity, not clinical requirements**. They are to be
confirmed after the pilot measures real authoring rates (CLINICIAN_BRIEF).

**Unit: the seed utterance.** One sentence a native speaker writes as a patient or carer would say it, in
Kinyarwanda first (§10.2, E5). Paraphrases count as separate seeds only when written by a different author.

| Requirement | Proposal | Blank until |
|---|---|---|
| Domains | the national protocol's own organisation, not the current 9 | **[BLANK — H4: MoH/RBC triage protocol]** |
| Age groups and boundary | as the chosen framework defines them | **[BLANK — E6; ETAT manual / adult framework in `docs/clinical/`, cited]** |
| Which reporter applies to which presentation (e.g. who can report a convulsion) | per concept | **[BLANK — clinical lead, H6]** |
| Urgency definitions | from D7 protocol §3 | **[BLANK — H3/H4 + H6]** |
| Cell | domain × intended urgency × reporter (self / carer / other) × patient age group | — |
| **Minimum distinct seeds per non-empty cell** | **30** | — |
| **Minimum distinct seeds per language** | **3,000** (18× today's 165), or cells × 30 if larger | — |
| **Authors per language** | **≥ 10** native speakers; **no author > 20%** of any language × domain; clinician-authors for acute cells per H7 | — |
| Separation from evaluation | no scenario shared with EVAL_SET_SPEC items (§8) | — |
| Frames (openers / closers) | natively authored, with provenance; each tagged with the reporters and age groups it is compatible with | — |

**Per-item metadata (every seed and every frame):**
- identity and language: `item_id`, `text`, `language`, `matrix_language` (mixed), `variant` (Swahili);
- how it was written: `author_code`, `generation_method` ∈ {`native`, `native_paraphrase`,
  `t1_reviewed_translation`}, `validated_by`, `validated_at`;
- who is described: `reporter` ∈ {self, carer, other}, `patient_age_group`, `patient_relation` (if not self);
- clinical placement: `domain`, `scenario_id`, `clinical_source` (document + page for the concept);
- `licence`.
- **Intended urgency** is held separately by the coordinator, as in the D7 protocol, and joined at build time.

## 3. Diversity gates

**Where they run:**
- `validate_dataset.py` refuses to write splits if any gate fails.
- `evaluate.py` refuses to report metrics for a model whose training manifest lacks a passing validation record
  (manifest hash).
- Gates are tested with deliberately failing fixtures, including the current v2 corpus.

| # | Gate | Threshold | v2 corpus today |
|---|---|---|---|
| G1 | Max rows per distinct seed | ≤ **50**, and no seed > 0.1% of rows | ~2,000 per phrase — **fails** |
| G2 | Min distinct seeds | ≥ 3,000 per language **and** ≥ 30 per non-empty cell | 165 — **fails** |
| G3 | Lexical diversity floor | Moving-average type-token ratio (500-token window), computed over **one row per seed** so row expansion cannot inflate it. Floor: **≥ 80% of the MATTR of the natively authored pilot set**. Not set from the v2 corpus. | not computed — **floor BLANK until the pilot** |
| G4 | Near-duplicate seeds | MinHash Jaccard ≥ 0.85 between distinct seeds ≤ **2%**; exact duplicates 0 | measured on rows, not seeds: ≥ 2.77% of rows have a ≥ 0.85 neighbour (lower bound) — **fails** |
| G5 | **Machine person-transformation: hard ban** | any item with `generation_method` outside the allowed set, or without `author_code` and `validated_by`, fails the build. A first/third pair with identical content words and different concord is refused unless the two items have **different** `author_code`s | 180,272 transformed rows — **fails** |
| G6 | Frame consistency | a frame incompatible with the item's `reporter` / `patient_age_group` fails the build | 45,232 rows — **fails** |
| G7 | Provenance completeness | 100% of seeds and frames carry all §2 metadata | 0% per-row — **fails** |
| G8 | Author concentration | no `author_code` > 20% of any language × domain | not recorded — **fails** |

**Why G5 is enforced by metadata, not by a detector.** A Kinyarwanda concord classifier was 8.7–18.9% wrong on
this corpus's clauses (TAXONOMY_SCOPE §8.1), so it cannot be the gate. It may flag suspected transforms for a
native reviewer. The build decision rests on recorded authorship.

## 4. Not in scope of this document

- No clinical content: every clinical parameter above is a blank naming its source.
- No retraining plan, and no reuse of v2 rows. v2 stays frozen for reproducing past results only.

## 5. The arithmetic path to 1,000,000 rows (added 2026-09-15)

**The target stands:** FR-04-07 (≥ 1,000,000 examples) and all nine §9.1 standards. Nothing below lowers a gate.
Every figure is printed by `reports/measurements/corpus_1m_arithmetic.py` (output: `corpus_1m_arithmetic.txt`).
The authoring rates are **CLINICIAN_BRIEF's stated assumptions, not measurements**: 2–3 min to write a seed and
30–45 s for a T1 reviewer to validate it. The pilot replaces them.

### 5.1 What binds

- **G1** caps rows per seed at 50; at 1M, "no seed > 0.1%" allows 1,000, so 50 binds.
  → **≥ 20,000 distinct native seeds.**
- **G2** needs ≥ 3,000 seeds per language. If each of the 6 mixed pairs counts as a language (its authors,
  raters and κ are separate), that is 10 × 3,000.
  → **≥ 30,000 seeds, which binds over G1.**
- **G2 also needs ≥ 30 seeds per non-empty cell** (domain × urgency × reporter × age group). The cell count is
  **BLANK**: domains wait on H4 and age groups on E6. It is the largest single cost driver.
- **§9.1 balance** at the midpoints: each pure language 12.5% (125,000 rows); mixed 50% (83,333 rows per pair).
- **G5** bans machine person-transformation, so rows per seed can only come from natively authored frames. G6
  makes each frame compatible with the seed's reporter and age group.

### 5.2 Cost by cell scenario

| Non-empty cells per combination | Seeds per combination | Seeds total | Rows per seed for 1M (pure / pair) | Author-hours (write + validate) | Hours per author at 40 / 100 authors |
|---|---|---|---|---|---|
| ≤ 100 (G2's 3,000 binds) | 3,000 | **30,000** | 41.7 / 27.8 | **1,250–1,875** | 31–47 / 12–19 |
| 162 (the 9 placeholder domains × 3 × 3 × 2) | 4,860 | 48,600 | 25.7 / 17.1 | 2,025–3,038 | 51–76 / 20–30 |
| 720 (80 domains per §9.1 × 3 × 3 × 1 age group) | 21,600 | 216,000 | 5.8 / 3.9 | 9,000–13,500 | 225–338 / 90–135 |
| 1,440 (80 domains × 3 × 3 × 2 age groups) | 43,200 | 432,000 | 2.9 / 1.9 | 18,000–27,000 | 450–675 / 180–270 |

In the last two rows the **cell floors, not 1M**, set the cost. They produce well over 1M rows at the cap.

**Frames are a small cost.** About 42 variants per seed need, for example, 7 openers × 6 closers per reporter ×
age group: roughly 780 frames across 10 combinations, about 26–39 author-hours at the same rate.

**Authors:**
- ≥ 10 per combination (§2), and no author above 20% of any language × domain (G8), so ≥ 5 per language × domain.
- Across 10 combinations that is **40–100 distinct native or bilingual people**, depending on overlap.
- Acute cells need clinician-authors (H7). Evaluation-set authors are additional and separate (EVAL_SET_SPEC).

### 5.3 A constraint that cannot be computed yet

§9.1 caps near-duplicates below 2% (CLAUDE.md also requires MinHash Jaccard ≥ 0.85 to be reported). Rows built
from one seed with different frames are the likeliest near-duplicates. Whether 28–42 frame variants per seed
pass depends on frame length and variety, and no native frames exist to measure.

The v2 corpus is weak evidence only: ≥ 2.77% of rows had a ≥ 0.85 neighbour (a lower bound, DATASET_AUDIT) at
~2,000 rows per phrase, under a different frame design. If the standard forces fewer variants, seeds rise:

| Rows per seed | Seeds for 1M | Author-hours |
|---|---|---|
| 50 | 20,000 | 833–1,250 |
| 20 | 50,000 | 2,083–3,125 |
| 10 | 100,000 | 4,167–6,250 |
| 5 | 200,000 | 8,333–12,500 |
| 1 | 1,000,000 | 41,667–62,500 |

### 5.4 Verdict

- **Reachable under every gate** if non-empty cells per combination are ≤ about 160 and the near-duplicate
  standard allows about 17–42 frame variants per seed. That means 30,000–48,600 native seeds from 40–100 authors,
  about **1,250–3,040 author-hours** at the assumed rates.
- **Not reachable at realistic cost** if §9.1's 80+ domains are crossed with reporter and age group (720–1,440
  cells), or if the near-duplicate standard forces ≤ 5 variants per seed: **9,000–27,000 or more
  author-hours**. Whether that many hours can be recruited is your call. I cannot judge it from here.
- **Below full compliance, rows are not the measure.** Under about 1,875 author-hours (at the slower rate),
  G2's floor cannot be met in all 10 combinations, so §9.1 language balance fails whatever the row count.
  - Largest defensible size then = the combinations actually covered × 3,000 or more seeds × ≤ 50 rows per
    seed. For example, Kinyarwanda alone: 150,000 rows from 3,000 seeds.
  - Its quality profile: G1–G8 met in that combination; §9.1 language balance and FR-04-07 **not met**, stated
    as such.
  - That corpus must never be reported as meeting FR-04-07.
- **Report seeds beside rows, always.** At 30,000 seeds, 1M rows carries 30,000 seeds' worth of linguistic
  variety; G3 is computed on one row per seed for this reason.

**Still BLANK, and each changes the answer:** the domain list (H4); age groups (E6); the pilot's measured authoring
rate; the near-duplicate result on native frames; whether mixed pairs count as languages for G2 (assumed yes).
