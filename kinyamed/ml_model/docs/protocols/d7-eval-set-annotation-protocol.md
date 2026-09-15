# D7 — Evaluation-set annotation protocol

**STATUS: NOT EXECUTED. Sections 3 and 4 are BLOCKED** until the clinical source documents are in
`kinyamed/docs/clinical/` and a lead clinician has approved the mapping. Nothing in this protocol is clinical
content: where a clinical definition belongs, it says what document must supply it.

**Version:** draft 0.1 (2026-09-14). Freeze a version number before the pilot. A label is only comparable with
labels given under the same protocol version.

Companion files:
- `reports/EVAL_SET_SPEC.md` — sizes and why.
- `ml_model/training/eval_spec.py` — the numbers.
- `ml_model/annotation/` — the tool.
- D1 — the earlier protocol for the corpus concepts.

---

## 1. What this produces, and who does what

A frozen evaluation set of clinician-authored, double-labelled, adjudicated items in Kinyarwanda, English,
French, Swahili and six mixed pairs. Every deployment-gate metric is computed on it.

| Role | Who | Does | Must not |
|---|---|---|---|
| **Lead clinician** | a registered clinician practising in Rwanda (D3) | approves §3 and §4; resolves protocol questions | label or adjudicate items they authored |
| **Author** | native-speaker clinician per language (D4) | writes items (§2) and records each one's intended urgency **separately**, for the coordinator only | annotate their own items |
| **Annotator A, Annotator B** | two native-speaker clinicians per language, **not** authors of the items they label | label every item independently (§5) | discuss items, see each other's labels, or see the intended urgency |
| **Adjudicator C** | a third native-speaker clinician per language | resolves disagreements (§6) | adjudicate an item they labelled |
| **Coordinator** | project engineer | runs the tool, imports items, computes κ, builds the gold set | change any label |

People are identified in the tool by **codes only** (A1, B1, C1). The mapping from code to person is kept by the
coordinator on paper or in a separate file that never enters the repository.

## 2. Writing items

1. **Invented, not remembered.** Items describe a plausible patient's own words. **No real patient's words, no
   record extracts, no names, phone numbers, places or dates that identify anyone** (L9, L10). The import step
   rejects phone- and email-shaped text automatically; the rest is the author's responsibility.
2. **Written natively in the item's language.** Never translated from an English draft (docs/ENGINEERING_SPEC.md §10.2). For a
   mixed pair, written by a speaker of both languages as people actually mix them; record the matrix language.
3. **One scenario, one test item.** Paraphrases of the same scenario may appear only in the calibration split
   (spec §8). Every item carries a `scenario_id`.
4. **Coverage.** Follow the allocation in spec §6 and the coverage cells in spec §7. The coordinator issues each
   author a quota sheet by language × intended urgency × domain × presentation type.
   - The domain list is **BLOCKED** on B2.
   - The clinical presentation types are **BLOCKED** on B1 and B4.
5. **Intended urgency is recorded apart from the item.** It goes in a separate file the coordinator holds. The
   annotation tool refuses any items file that contains a label column, so annotators never see it.
6. **What an item file looks like:** `item_id, text, language, split, scenario_id, domain, presentation_type`.
   The import refuses, writing nothing, if any item lacks a `scenario_id`, if two test items share a scenario, if a
   scenario appears in both the test and calibration splits (spec §8), or if an `item_id` was already imported.
   An item takes exactly two labels; a third is refused.

## 3. The labels — BLOCKED

Annotators choose one of four labels per item: **CRITICAL, URGENT, ROUTINE, UNCLASSIFIABLE.**

**The definitions of CRITICAL, URGENT and ROUTINE must come from the clinical source, cited to the page, and be
approved by the lead clinician before the pilot.** They are not written here, because writing them from memory
would be inventing clinical content (L5, L16).

| Label | Source category (e.g. ETAT) | Document in `docs/clinical/`, section, page | Definition text (verbatim or approved paraphrase) | Approved by (code), date |
|---|---|---|---|---|
| CRITICAL | **BLOCKED** | **BLOCKED** (needs B1/B2/B3) | **BLOCKED** | — |
| URGENT | **BLOCKED** | **BLOCKED** | **BLOCKED** | — |
| ROUTINE | **BLOCKED** | **BLOCKED** | **BLOCKED** | — |

**Documents required to unblock this section** (spec §11):
- **B1** — the WHO ETAT document in the edition used in Rwanda.
- **B2** — the Rwanda MoH / RBC triage protocol with its mapping of categories to these three labels.
- **B3** — the adult triage tool, if not ETAT.
- **B4** — the obstetric danger-sign guidance.

**Question for the lead clinician before anything else:** does ETAT cover adult presentations as used in Rwandan
facilities? If not, which document defines adult triage categories?

**What the annotator judges — to be confirmed by the lead clinician:** the urgency that the presentation
described in the text would warrant at first contact, judged from the text alone, without assuming facts the
text does not state. This is a task framing, not a clinical rule. The lead clinician may change it before the
pilot, and the change is versioned.

**UNCLASSIFIABLE** is not an urgency. Use it, with a reason code, only when:

| Reason code | When |
|---|---|
| `not_a_symptom_description` | the text describes no complaint (e.g. only a greeting or an administrative question) |
| `not_enough_information` | a complaint is described, but you could not choose between labels even with low confidence |
| `cannot_read_language` | you cannot read the text reliably |
| `other` | anything else; the adjudicator will see it |

If you can choose a label with low confidence, **choose the label and set confidence 1**. Do not use
UNCLASSIFIABLE to avoid a hard decision.

**Confidence**, recorded with every label:

| 1 — unsure | 2 — fairly sure | 3 — certain |
|---|---|---|

## 4. Worked examples — BLOCKED (clinical); procedural examples provided

**Clinical worked examples are BLOCKED.** Each needs an item, its label, and the §3 source passage that
justifies the label. They must be supplied or approved by the lead clinician from `docs/clinical/`, and must not
be items in the evaluation set. Needed, per pure language, before the pilot:
- ≥ 2 clear examples per label.
- ≥ 3 pairs close to the CRITICAL/URGENT line, and ≥ 3 close to the URGENT/ROUTINE line, with the passage that
  decides each.
- ≥ 2 examples each of the linguistic presentation types most likely to mislead: reported by a relative, a short
  fragment, a negated symptom.

**Procedural examples** (no clinical judgement involved):

| Situation | What to do in the tool |
|---|---|
| The text is "Muraho" and nothing else | UNCLASSIFIABLE, `not_a_symptom_description`, confidence 3 |
| The text is in a language you do not read well | UNCLASSIFIABLE, `cannot_read_language`, confidence 3. It goes to adjudication like any UNCLASSIFIABLE label; if this happens often, the coordinator has assigned the wrong language to you. |
| You can decide between two labels only with difficulty | pick the label you believe more likely, confidence 1 |
| You pressed Save on the wrong label | do not try to change it: the tool has no correction path, by design. Tell the coordinator the item id. The first label stands for κ. The coordinator runs `python -m annotation --db ann.sqlite3 request-adjudication ITEM_ID A1 saved_wrong_label`, which sends the item to adjudication even if both annotators agreed; the gold set cannot be built until it is adjudicated. |
| You recognise an item (e.g. you wrote it) | stop and tell the coordinator, who runs `python -m annotation --db ann.sqlite3 withdraw ITEM_ID A1 annotator_recognised_item`. Your label is kept as a record, the item takes no further labels, and it is excluded from κ and the gold set. The gold manifest records how many items were withdrawn and which. |

## 5. Labelling

1. **Pilot first.** 60 items per language, not in the evaluation set, labelled by A and B under the draft
   protocol. Then, and only then:
   - discuss disagreements;
   - revise §3 and §4 with the lead clinician;
   - freeze the protocol version.
   Pilot labels are never part of the gold set. Record seconds per item; this replaces the time estimates in the
   brief.
2. **Independent.** A and B label every item alone, in separate sessions, without discussion, until both have
   finished. The tool gives each annotator a different order. It shows no agreement, disagreement or κ until
   every item has two labels.
3. **Blind.** The annotator sees the item text and its language only: not the domain, not the presentation
   type, not any intended urgency, not the other annotator's label.
4. **Final.** An annotator's first label for an item cannot be changed (see the mistake procedure in §4).
5. **Pace.** Suggested: sessions of at most 60 minutes with a break. Measured seconds per item from the pilot
   set the schedule.
6. **Running the tool** (coordinator):
   ```bash
   cd kinyamed/ml_model
   python -m annotation import-items --db ann_kinyarwanda.sqlite3 items_kinyarwanda.csv
   python -m annotation serve --db ann_kinyarwanda.sqlite3     # http://127.0.0.1:8750 on the same laptop
   python -m annotation progress --db ann_kinyarwanda.sqlite3 A1 B1
   ```

## 6. Resolving disagreements

1. **Compute κ first** (§7), before looking at any disagreement. That number is the agreement result.
2. Export disagreements:
   `python -m annotation disagreements --db ann.sqlite3 --out disagreements.csv`.
   An item is a disagreement if A and B chose different labels, or if either chose UNCLASSIFIABLE.
3. **Adjudicator C** reviews each disagreement with the item text, both labels and the §3 definitions, and
   records a label and a reason code. The tool refuses an adjudicator who labelled the item.
   `python -m annotation adjudicate --db ann.sqlite3 ITEM_ID LABEL C1 REASON`

   | Reason code | Meaning |
   |---|---|
   | `annotator_a_correct` / `annotator_b_correct` | one label is right under §3 |
   | `neither_correct` | C records a third label |
   | `genuinely_ambiguous_exclude` | the text cannot support a label; record label UNCLASSIFIABLE and the item leaves the gold set |
   | `unclassifiable_confirmed` | C agrees the item is UNCLASSIFIABLE |

4. **No majority voting, no re-labelling.** A and B never re-label items after seeing disagreements. That would
   raise κ without raising agreement.
5. **Systematic disagreement is a protocol problem.** If one kind of disagreement dominates, stop, fix §3 with the
   lead clinician, re-pilot on **new** items, and report the original κ as well.
6. Excluded items are counted and reported with the results. If exclusions push any powered cell below its
   minimum (spec §4), more items must be authored. The gate refuses otherwise.

## 7. Cohen's κ per language

```bash
python -m annotation kappa --db ann.sqlite3
# or, from two label files:  python scripts/compute_kappa.py first.csv second.csv
```

- **Definition:** unweighted Cohen's κ over {CRITICAL, URGENT, ROUTINE, UNCLASSIFIABLE}, computed on first labels
  only. κ = (p_o − p_e) / (1 − p_e), where p_o is observed agreement and p_e is agreement expected from each
  annotator's own label frequencies.
- **Interval:** 95% bootstrap over items (1,000 resamples, fixed seed).
- **Reported per language and overall.** A linearly weighted κ over the three urgencies is printed beside it for
  information and never replaces it.
- **Minimum:** 200 double-labelled items per language, otherwise `INSUFFICIENT DATA (n=X, need 200)`.
- **Target:** κ ≥ 0.80 per language, judged on the **lower** interval bound (spec §2).
- **Below target:** do not build the gold set for that language. Revise §3, re-pilot on new items, re-label on
  new items. Report every κ computed, not only the last.

## 8. Building and freezing the gold set

```bash
python -m annotation build-gold --db ann.sqlite3 --out eval/kinyarwanda_v1/
```

- **Refusals:** the build fails if any item lacks two labels or any disagreement is unadjudicated.
- **Output:** `gold_test.csv`, `gold_calibration.csv` and `gold_manifest.json` with SHA-256 digests and
  per-language × label counts.
- **Freezing:** commit the manifest. Never rebuild, re-split or re-label a frozen set (L8); corrections produce a
  new version.
- **Leakage check:** before any evaluation, check the test set against all training data for exact and
  near-duplicate text and shared scenarios.
- **Scoring:** `python training/evaluate.py --gold eval/kinyarwanda_v1/gold_test.csv --model <model_dir> --out <report_dir>`.

## 9. Data handling

- Items are invented vignettes; no patient data is collected (L9). Confirm with D7 whether the clinicians'
  institutions require ethics review for this work before it starts.
- The SQLite file, item files and label exports stay on the annotation laptop and the project repository. The
  tool binds to 127.0.0.1, uses no external resources, and logs no requests.
- Annotator codes only. The code-to-person list is never committed.

## 10. What executing this does not establish

Agreement between clinicians shows the labels are reproducible under §3. It does not show that §3's categories
are clinically right (D2), that the items resemble real patients' speech (a speaker rating study, D3), or that a
model which passes will be safe with real patients (prospective validation, D7).
