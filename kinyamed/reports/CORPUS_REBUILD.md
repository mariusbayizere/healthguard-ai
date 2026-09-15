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
