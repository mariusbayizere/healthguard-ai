# External review of the paper — the full list

Committed because it was twice lost between sessions: it lived only in a chat
transcript, and two sessions began by reconstructing it from memory. It is the
input to the work, so it belongs in the repository beside the output.

Blocks are worked in order. Every item is verified against the repository
before anything is changed, and an item the reviewer got wrong is recorded as
wrong rather than "fixed" — a correction applied to text that was already
right is a regression that looks like progress.

Status values: `open`, `fixed`, `already correct` (reviewer mistaken),
`already addressed` (text already says this).

---

## Block 1 — five errors of fact (`42cb7aa`, done)

All five held; one was worse than the reviewer knew. Recorded in `STATE.md`
under *external review, BLOCK 1*. Summary: G2 must be strict (`>=` on an
exactly-2/3 constant let a degenerate model pass); the "tightest guarantee"
claim removed and the real bound stated; "no accuracy/recall/calibration
figure" replaced with "no figure is offered as evidence of model quality";
the 2,835 and 19,835 shortfalls separated; "degenerate ceiling" renamed
merge-strategy precision; G3 reports NOT COMPUTABLE above a 0.90 CRITICAL
share.

**Regeneration pending** — three of these live in generated `.tex` written by
`training/holdout_eval.py`, which has not been re-run.

## Block 2 — internal inconsistencies

| | Item | Status |
|---|---|---|
| B1 | Appendix A implies 128 concepts (50 of 256 rows = 128 x 2 persons) while Section 3.3 refuses to state a concept count because five values exist in the repo. The appendix silently asserts one. | **confirmed** — `method.tex` refuses a concept count (five values: 68, 80, 126, 127, 128); `appendix.tex` asserts 128 via 256 rows / 2 persons |
| B2 | 256 - 50 inapplicable - 23 held = 183, but the inventory is 165 phrases. Explain the gap. | **fixed, and my first diagnosis was wrong** — I blamed the flagged/held overlap. `applies=no` and `hold=yes` are disjoint (0 rows carry both, measured), so that overlap has no bearing on this subtraction. The missing term is 19 rows applicable and unheld but not yet written, plus 1 second phrasing: 256 - 50 - 23 - 19 + 1 = 165, verified set-equal to `dataset/vocabulary.py`. See SR9 |
| B3 | Appendix A says held rows generate nothing; Sections 3.2 and 7.7 say eight held or flagged phrases are in the corpus. Separate "held" from "flagged". | **confirmed** — `appendix.tex` L63 vs `limitations.tex` L145; the 'eight' is a stale held-only count, now 4 |
| B4 | The evaluation set (17,942 rows, 9 sentences) and the test split (34,425 rows, 15 seeds) are never related to each other. State which is which and why they differ. | **confirmed** — both named at `results.tex` L120-124, never reconciled. NOTE: '34,425' appears nowhere in the paper |
| B5 | The 26.07% worst-seed figure is computed against the 34,425-row split, not the reporting set. Label it so it cannot be misread. | **confirmed, worse than stated** — 26.07% is 'of the evaluation split' (L39) and 'of the test split' (L124) in the SAME file |
| B6 | Section 6.3 says the model labelled "7,793 URGENT rows" critical "almost without exception". 7,793 appears to be the total URGENT support; at urgent recall 0.0083 about 65 were correct, so the same number cannot also be the count mislabelled. Recompute from the confusion matrix and correct the wording. | **FIXED at the emitter** — `v2c['confusion'][1][0]`; 7,633 not 7,793. Lands with the regeneration |
| B7 | Section 7.3 promises "six instances" but lists five bullets. It works only if p50 and p95 latency count separately, so say so. | **confirmed** — five bullets under 'six instances' |
| B8 | The abstract footnote and conclusion say every number re-derives with one command, but the paper contains figures marked NOT REPRODUCIBLE (for example 60 of 61 concepts). Change to "every number except those marked". | **confirmed** — `introduction.tex` L96 + `abstract.tex` L59 vs `limitations.tex` L119 + `discussion.tex` L146 |
| B9 | Critical recall is 0.95 in the gate and 0.91 in the requirements. If the text already flags this as inherited and unverified, report the item as already addressed and change nothing. | **ALREADY ADDRESSED — do not edit.** `discussion.tex` L86-88 already calls 0.95 'inherited and unverified' against the 0.91 |
| B10 | "G1, G2, G3" names both the corpus gates (G1-G9) and the acceptance conditions. Rename one set, e.g. C1-C9 and A1-A3. | **confirmed** — decision taken, see *Decisions* |
| B11 | The introduction's "two failures worth more than the model" (split manifest, single-metric gate) are a different pair from the abstract's two failure modes (tokenizer, surface fragility). Readers will conflate them. | **confirmed** — `introduction.tex` L19 vs L59, different pairs 40 lines apart |
| B12 | The surface probe uses "200 sampled inputs" with no distinct-source-sentence count and no interval, which breaks the paper's own reporting rule. | **confirmed** — `results.tex` L155, no distinct-source count, no interval. Same passage as Block 3 item 1 |
| B13 | Section 5.2 reports a latency comparison ("roughly 26 times beyond") after saying no latency result is reported. | **confirmed** |
| B14 | The title says KinyaMed, the repository is healthguard-ai. Use one name or explain both. | **confirmed** |
| B15 | "38 refused cells" is never defined. Say what a cell is. | **confirmed** |

## Block 3 — overclaims

- Drop the causal attribution on surface fragility. Report flip rates without
  claiming the corpus caused them, and state the confounds: a cased tokenizer
  changes tokens under capitalisation, and a model whose confidence never
  exceeds 0.55 sits near its decision boundary, so flips are expected for
  reasons unrelated to the data.
- Narrow "no validated instrument in any language". Telephone triage protocols
  exist (nurse triage systems, symptom-checker audits). State why they are not
  a reference standard for patient-written free text rather than claiming
  nothing exists.

## Block 4 — method description

- Name the encoder, library versions, hyperparameters, sequence length and seeds.
- Write out the power-calculation assumptions behind 710, 365 and 720:
  confidence level, interval width, expected rates, any intra-cluster
  correlation.

## Block 5 — presentation

- Remove draft notes ("Moved from Section", the Appendix D heading explanation).
- Fix underscores in file paths (PAPER_NUMBERS.md, holdout_eval.py,
  generate_large_dataset.py, majority_baseline.py).
- Remove process notes from references ("verified via the Europe PMC REST API on ...").
- Cut repetition: each key number stated once in results, referred to elsewhere.
- Fold or remove the one-paragraph stub sections (3.4, 3.5, 5.3, 6.4, 6.5, 8.3, 8.4).

## Block 6 — missing sections

- Acknowledgements naming the Kinyarwanda speaker, with their consent.
- Ethics statement and data statement.
- Check whether redistributing the WHO ETAT PDF in a public repo is permitted;
  if not, remove it from the repo and cite the URL instead.

---

# Findings beyond the reviewer's list

## F1 — the paper's corpus counts are stale relative to the record (2026-09-18)

**The paper quotes 25 flagged rows. The record holds 29.**

Commit `934433a` (2026-09-11) reclassified four third-person rows — `IF01`,
`IF03`, `IF04`, `IF06` third — from `hold` alone into `needs_clinician`, because
each was held for no reason of its own beyond its first person being flagged.
The record moved. The paper did not.

Current, counted from `review/speaker_brief_kinyarwanda_v2.csv`:

| quantity | value |
|---|---|
| rows | 256 |
| flagged (`needs_clinician`) | 29 |
| held (`hold`) | 23 |
| both | 19 |
| held only | 4 |
| flagged only | 10 |

**This is what made B2 and B3 look like arithmetic errors.** They are drift.

- **B2.** `256 - 50 inapplicable - 23 held = 183` against an inventory of 165
  treats flagged and held as disjoint sets. They overlap by 19. The subtraction
  was never going to reconcile.
- **B3.** "Eight phrases carry an unresolved hold or a flag and are nonetheless
  in the corpus" matches the **held-only** count as it stood *before* `934433a`.
  It is now 4. So the sentence conflates two categories AND quotes a number from
  a state that no longer exists.

**It is the same shape as B6.** B6 reused an URGENT *support* figure where a
confusion-matrix cell belonged; these reuse a hand-typed count where the record
belonged. Both are stale copies of a number whose source moved. A paper whose
argument is that numbers need traceable sources should not carry hand-typed
counts at all.

## F2 — the motivation figure was unsourced, and wrong (2026-09-18)

`CLAUDE.md` §4.1 opened the problem statement with **"1 doctor per ~14,000
patients (WHO minimum 1:1,000)"** and **"~47-minute delay before urgency
assessed"**. None of the three carried a source.

The density figure is also wrong. The citable value is roughly **1 physician per
8,919 people** (Rwanda, 2018; 1,350 physicians; National Academies / PEPFAR
evaluation of Rwanda's Human Resources for Health Program). 14,000 overstates
the shortage by more than half again.

**Found while fixing a review about unsourced numbers**, which is the part worth
recording. The paper's entire argument is that a number in a specification needs
a stated source and a derivation; the specification that argument is written
against opened with three numbers that had neither. The review looked outward at
the paper and the defect was behind it.

**Decision (maintainer, 2026-09-18): cut, do not replace.** 8,919 is not
substituted in, because a paper arguing that unsourced numbers are the problem
cannot open its motivation with a figure whose source is not in the paper. If
the density point is needed, it is stated qualitatively with a citation, or the
sentence goes. The delay figure is now marked `NOT YET MEASURED` per L6.

**Not in the paper.** The figure appeared only in `CLAUDE.md`; `grep` across
`paper/` found no instance, so nothing typeset carried it.

---

# Decisions taken (execute these)

## D1 — B10 rename, one pass, every reference

**Corpus gates become C1-C9. Acceptance conditions become A1-A3.**

Confirmed by the maintainer 2026-09-18. `G1, G2, G3` currently names both sets,
which collide in `results.tex` (L39-41 are corpus gates; the acceptance gate
reuses the same names). Rename every reference in one pass — prose, tables,
labels, and the emitter if it writes any of these strings. Do not leave a mixed
state: a half-renamed paper is worse than the collision.

Check the emitter too: `training/holdout_eval.py` writes gate text into
`gate_derivation.tex` and `finding_gate_degeneracy.tex`.

## D2 — B2/B3 counts must be emitted, not typed

**Emit the corpus counts from `review/speaker_brief_kinyarwanda_v2.csv`, the way
`review/build_clinician_pack.py` emits the clinician pack.** The maintainer
chose the larger job deliberately: it removes the class of bug rather than the
instance.

The emitted text must state all six figures — 256 rows, 29 flagged, 23 held, 19
both, 4 held-only, 10 flagged-only — and must say **explicitly that flagged and
held overlap**, because the 183 arithmetic in the paper assumed they were
disjoint and a reader will otherwise repeat that subtraction.

Model it on `build_clinician_pack.py`: derive once, render from the derivation,
and add a test in the style of `tests/test_clinician_pack.py` that fails when
the emitted file drifts from the CSV.

---

# State at handover (2026-09-18)

**Regeneration:** RUNNING at handover — `training/holdout_eval.py --writeup`
over three sweep models, log at the session scratchpad (`regen2.log`). It
carries Block 1's emitter changes **and** the B6 fix. A backup of the
pre-run `paper/generated/` was taken first.

**When it lands, verify — and the baseline is git, not a scratch copy.** All
eight files under `paper/generated/` are tracked and were clean when the run
started, so the committed state IS the pre-run state:

```
git diff --stat kinyamed/ml_model/paper/generated/
git diff kinyamed/ml_model/paper/generated/
```

**Expected:** every scientific number unchanged EXCEPT the B6 count in
`finding_gate_degeneracy.tex` (7,793 -> 7,633, and the wording "almost without
exception" -> "N of 7,793"), plus Block 1's wording changes and a new
`generated_at` / `git_commit` in each provenance header.

**Any other numeric movement means the run did not reproduce.** Investigate it;
do not accept it. Block 1 changed wording only. A moved metric would mean the
manifest, the models or the seed differ from the 2026-09-08 run, and that is a
reproducibility failure worth more attention than the review.

If the diff is clean apart from provenance headers and B6, commit the emitter
change and the regenerated output together — they are one change.

**Done:** Block 1 (committed `42cb7aa`). B6 fixed at the emitter. All 15 Block 2
items verified. B9 confirmed already addressed and deliberately untouched.
CORPUS_REBUILD.md R1/R2/R3 recorded; `annotation/authoring.py` carries the R2
check (numerals only, plus a human-review flag — it cannot detect
monkey-versus-snake and says so).

**Not done:** Block 2 edits other than B6; D1; D2; Blocks 3-6.

**Note for Block 3.** Its first item (drop the causal attribution on surface
fragility) is the SAME passage as B12 — `results.tex` L152-160, which currently
says the flip rates are "a property of the training data rather than of the
tokenizer". Fix them together.

---

# Second review, of the compiled v2 PDF (2026-09-18)

Thirteen items, worked in one sitting. The instruction was to grep for each
phrase across every `.tex` file, fix every occurrence, then grep again and
confirm zero remain, because the first revision fixed sentences individually
and left stale copies behind. That method is why items SR1 and SR2 existed at
all, and it is the method used here.

Items 14 (figure) and 15 (anchor citations) were explicitly out of scope.
The reviewer verified and asked me not to re-derive: the parameter accounting,
8,975/34,425 and 8,975/17,942, merge precision 0.5349, 7,633 of 7,793,
3(0.7724)-2, the power sensitivity figures, and Appendix A's overlap
arithmetic. None was touched.

| | Item | Status |
|---|---|---|
| SR1 | Section 6.4's heading, its "localises the cause in the data", and the Conclusion's "locates the cause in the training data rather than the tokenizer" assert the causal claim that Section 4.3 refuses. | **fixed** — both rewritten to match 4.3: the flip rates are a measurement, not an attribution, and the two confounds (cased tokenizer, confidence pinned near the boundary) are named where the claim used to be. Zero occurrences remain |
| SR2 | "Ceiling" survives the rename in three places in Section 6.3. | **fixed** — heading now "The merge strategy's precision has a closed form", and both body uses renamed. The two remaining occurrences are the sentence that *denies* it is a ceiling, which is the generated text's own wording |
| SR3 | Introduction and Conclusion give only 19,835, while the abstract and 4.1 give both shortfalls. | **fixed** — both now state 2,835 to pass the seed-count gate and 19,835 to reach the row target, and say neither distance is measured in rows |
| SR4 | Section 3.2 says eight phrases carry a hold or flag; 7.5 says 10; Appendix A gives 10. Update 3.2. | **fixed, but not as directed — the premise was inverted.** 8 and 10 count different predicates and both are correct. 8 = rows that generate a phrase AND carry a flag. 10 = rows flagged and not held, two of which generate nothing (NE04 first is inapplicable, NE06 first is unwritten). Changing 3.2 to 10 would have made it wrong. Both sites now name their predicate and read the count from a new emitted macro, `\CorpusFlaggedInInventory` |
| SR5 | Section 7.1 cross-references itself. | **fixed** — `\ref{sec:limits:base}` resolved to 7.1 because the label sits on a `\paragraph` inside it. Now named in words instead |
| SR6 | Section 2.1 says "in any language" unqualified while 7.1 acknowledges telephone triage and symptom checkers. | **fixed** — the 7.1 qualification moved up into 2.1 |
| SR7 | 250,002 x 384 = 96,000,768, not 96,199,296. | **fixed, and the figure was right** — verified against `model.safetensors`' header without loading the model: the embeddings module is 96,000,768 + 197,376 + 384 + 384 + 384 = 96,199,296 exactly, and the checkpoint totals 117,641,859 exactly. Only the expression was wrong, and "the embedding table" understated what is frozen. Now states the module and its decomposition |
| SR8 | Reference [5] says the ETAT manual is "Verified against the copy in docs/clinical/participant_manual.pdf" while the data statement says clinical documents are not in the repository. | **fixed** — the reference cites the WHO IRIS handle only; the verification record moved to a BibTeX comment, which never typesets. The data statement now states the history exactly: committed in error 2026-09-17, removed 2026-09-18, still reachable from earlier commits, not purged |
| SR9 | 256 - 50 - 23 = 183 vs inventory 165, eighteen rows unaccounted. | **fixed; the suggested cause was not the cause** — held and inapplicable do not overlap at all (measured 0). The missing term is 19 unauthored rows minus 1 second phrasing. Appendix A now shows the full subtraction, every term emitted from the record, and `emit_corpus_counts.py` cross-checks its total against `dataset/vocabulary.py` and refuses to write if they disagree |
| SR10 | Underscores dropping from every file path. | **fixed at the cause** — the sources escaped them correctly as `\_`; the document had no T1 font encoding, so the glyph was not reliably available. `fontenc` and `url` are now loaded and all 17 paths use `\path{...}`, which takes its argument verbatim. Three tests added |
| SR11 | Abstract 2,768 characters against arXiv's 1,920. | **fixed** — 1,917. `paper/emit_arxiv_abstract.py` renders `reports/ARXIV_ABSTRACT.txt` from `sections/abstract.tex` so the two cannot drift, and refuses to write anything over the limit. Asserted in a test |
| SR12 | Draft residue in Appendix D and reference [5]. | **fixed** — both removed |
| SR13 | afro-xlmr named with no citation. | **fixed** — Alabi et al., COLING 2022, pages 4336-4349, BibTeX taken from the ACL Anthology |

## Still open after this sitting

1. **Three generated tables reach nothing.** `confusion_table.tex`,
   `results_table.tex` and `sweep_table.tex` are written by
   `holdout_eval.py` on every run and are `\input` by no file; they appear
   only in a comment in `main.tex`. Pre-existing, not a regression, and
   possibly deliberate for a paper that offers no model-quality figure, but
   nothing records the decision. Either input them or stop emitting them.
2. **`check_tex.py` reports 85 literal numbers typed in `results.tex`**, up
   from 73 at HEAD; the 12 new ones came with Block 4's "Two sets, and which
   is which" paragraph. The checker is not a CI gate and was already failing
   at HEAD, so this is a standing debt rather than a break.
3. **`gate_derivation.tex` still prints G1-G3** while the emitter writes
   A1-A3. The rename landed after the regeneration ran. No prose names either
   set, so the PDF carries no collision, but emitter and output disagree until
   the next `--writeup` pass.

---

# The recorded-but-unread pattern, instances four and five (2026-09-18)

The paper's Appendix C now calls this "the same shape, three times". Two more
turned up in the same sitting, both in code rather than in the document, and
both found only because something else forced a look.

## Four: a docstring, a constant and a validator, each knowing a different number

`review/build_swahili_brief.py` said three things about one quantity:

| where | said |
|---|---|
| module docstring, line 72 | "Eleven holds are lifted" |
| `LIFTED_HOLDS`, lines 268-294 | twelve entries |
| the run's own summary print, line 1222 | `len(LIFTED_HOLDS)`, so twelve |

**Twelve is correct** and the docstring was wrong. `LIFTED_HOLDS` is the French
set; the English arm lifted eleven of those twelve and deliberately kept `EX27`
third held. Eleven is the size of the intersection, twelve the size of this
arm's inheritance, and the docstring collapsed the two.

`check_lifts_match_french()` validated `LIFTED_HOLDS` against the French brief
**only**. That is why the discrepancy never fired: a check against one side
cannot detect a disagreement between two sides. It is now
`check_lifts_match_both_arms()` and reads both briefs. Run against the current
record it reports exactly one finding, which is the row that had been invisible:

```
('EX27', 'third') is lifted in French and HELD in English: this arm
inherits it from one arm only, not from two agreeing
```

The fix is to the docstring and the validator, not to the data.

## Five: a gate that could not fail

`dataset/corpus_gates.py::_g6` returned a hardcoded NOT COMPUTABLE string and
read no column. It gave the same answer whatever it was given, including the
sentence "the corpus carries no reporter or patient_age_group per row" about a
corpus that carries both. The generated corpus genuinely lacked those fields, so
the stub's answer was true by accident for as long as it was the only corpus,
and the gate looked like it was working.

The labelled corpus records `reporter` (Self 1,502 / Carer 780) and `age_group`
across five values, on every row. G6 is now written: it reads both columns,
fails on an incomplete record, and reports the nine observed reporter x
age-group pairs against `PERMITTED_REPORTER_AGE`.

**`PERMITTED_REPORTER_AGE` is deliberately empty.** Which combinations are
coherent is a judgement about who presents on whose behalf and nobody has made
it for this project, so G6 reports NOT COMPUTABLE with the pairs listed for
ratification rather than passing a corpus because the pairs look reasonable.
`tests/test_gate_g6.py` asserts the property the stub lacked: that the verdict
depends on the input, with PASS, FAIL and NOT COMPUTABLE each reachable.

Worth noting for the same reason as the others: nothing failed while the stub
was in place. The gate ran, printed a verdict, and was counted among nine.

# A figure withdrawn rather than reconciled (2026-09-18)

The labelled corpus arrived with a comparison figure attached: that the
generated corpus had "1,020 distinct sentences and 261 word types". Measured
with the same tokeniser against every committed artefact, nothing produces it:
`symptoms_large.csv` gives 330,000 rows and **363** types, the 1,000-row sample
1,000 and 357, the phrase holdout 135, v1's Kinyarwanda 46 phrases and 140
types.

The figure came from a pasted subset in a scratch file rather than from any
committed artefact, and **it was withdrawn rather than reconciled**. It never
entered a report: the discrepancy was raised before anything was written, and
`grep` confirms 261 appears nowhere as a word-type count. The canonical
comparison is 363 types over 330,000 generated rows against 3,930 over 2,282
authored ones.

This is recorded because the alternative was available and worse. A number that
cannot be reproduced can always be made to look reproducible by finding some
subset that yields it, and that reconstruction would have been indistinguishable
in the paper from a measurement.

## Three figures corrected in the same pass

| quantity | as given | measured |
|---|---|---|
| ids absent from the range | ~220 | **317** (99+19+100+99, the four ranges as stated) |
| rows in clinical-record voice | 335 | **336** |
| type/token ratio | 0.210 | **0.2095** |
