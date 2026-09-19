# STATE

## READ THIS FIRST — status at end of day, 2026-09-15

Branch `audit-p0-p1-and-frontend`. HEAD `a32a5b0` plus the commit carrying this file. `main` untouched.

**In one line:** every engineering item that was blocked only on code is built and verified. No clinical content
was invented. **No model has been trained or measured,** because no evaluation set exists. What is left needs
people, documents, or your decisions.

### Items 1–5

| Item | Status | Evidence |
|---|---|---|
| 1 CI on every branch and PR | **DONE-VERIFIED locally**; see CI below | `95bd49e`; `ci-triggers.test.ts` 7 tests, red first. Blocks nothing until branch protection is set (yours). |
| 2 Red-flag layer, empty term table | **DONE-VERIFIED** | `809ced8`: PostgreSQL CHECKs make it escalate-only. `447c41e`: loader, header-only table. `f9b1c61`: runs before the model; start-up refuses an invalid lexicon. 50 tests. H6 ruled: no rules-only CRITICAL. **Terms blocked on H10.** |
| 3 Gate refuses below the spec | **DONE-VERIFIED** | `87a746e`, `fed9c3d`: counts distinct scenarios; per-language cells. The n=9 refusal is reproduced from a clean clone (`make reproduce` step 7). It scores the served thresholded decision (`9d34977`). |
| 4 Annotation tool | **DONE-VERIFIED (tool); unused** | `7de4061` plus the gaps; `test_annotation.py`. No clinicians yet (H1, H6–H8). |
| 5a Tokenizer study | **DONE-VERIFIED** | `TOKENIZER_STUDY.md`, `7cc63f9`; 10 tests. Synthetic text only. Needs network, so not in `make reproduce`. |
| 5b Latency and memory | **Fix DONE-VERIFIED; NFR NOT MET here** | `82bf6db`: micro-batching, 15 tests. p50 < 150 ms at 50 concurrent is unreachable on this machine (A29). Gates 14/15 need a target CPU (H15). |
| 5c Training pipeline | **DONE-VERIFIED except a real training run, deliberately not run** | `3d84c8b`…`4b5fe24`: loss, calibration, safety thresholds, manifest, pipeline. It refuses on the n=9 set. `a8c18aa`, `16968ed`: **the backend serves the recorded temperature and thresholds or refuses to start** (27 tests: red 25, green 27). |

### Test counts at HEAD, each suite run alone

| Suite | Result |
|---|---|
| Backend, clean clone with no `.env`, CI's variables only | **362 passed, 0 failed, 0 skipped**; 422 s; `mypy --strict` 0 issues in 64 files |
| Frontend, Vitest | **150 passed** (15 files), 0 failed; 65 s. Measured at HEAD `44dbefb` on 2026-09-16. |
| ML with torch | **324 passed, 0 failed, 3 skipped**; 1,208 s, peak 591 MB. Measured at HEAD `44dbefb` on 2026-09-16. The 3 skips are the slow power recomputation and two paper-number placeholders. |
| ML without dependencies (CI's dataset job, clean clone, pytest only) | Collection now succeeds. At `aca3e11`: **199 passed, 1 failed, 13 skipped**. The failure is fixed in `a32a5b0` (17/17 for that file in the same venv). `make verify` 6/6; attribution sweep 2 passed. |
| Ruff | check and format clean (273 files) |

### `make reproduce` from a clean clone: **PASS, all 8 steps**

- Clone `e4d253a` in `/tmp`, run under `env -i PATH=/usr/bin:/bin`: no pyenv, no pip cache, system `python3` 3.12.
- `make reproduce-env` (Python 3.11 plus the complete 43-package lock) took 725 s. Step 0 passed (interpreter, lock
  and imports), then steps 1–8 all PASS, in 895 s. The clone's `git status` was empty afterwards.
- The earlier attempt passed steps 1–6 and failed 7–8. The cause was the **environment, not the code**: pyenv's 3.11
  applies only under `~`, and system Python lacked numpy and pandas. The fix is `8b242c9`: in-repo
  `.python-version`, `requirements-reproduce.lock` (complete, proven with `--no-deps` and `pip check`), and step 0.

### CI

- **Last GitHub result I know of: run #77 at `e4d253a`, RED on 2 jobs**, 6 green (as you reported; `gh` is not
  installed here).
- **"Reproducibility and dataset tests", exit 2.** The job installs only pytest. Four new 5c test modules imported
  numpy/torch at module level, so collection errored.
  - Fix `66f5c5c`: they `importorskip`.
  - A second defect surfaced only when replicating the job: a run-manifest test asserted numpy was installed.
    Fixed in `a32a5b0`.
- **"Backend suite", exit 4.** `tests/conftest.py` refuses to load without `DATABASE_URL`. Your machine has a local
  PostgreSQL and a git-ignored `backend/.env`; the runner has neither.
  - Fix `26010aa`: a `postgres:16` service plus `DATABASE_URL`, `SECRET_KEY`, `SMS_API_KEY` and `SMS_ENABLED`
    (throwaway CI values, not secrets).
  - Guarded by `frontend/src/__tests__/ci-backend-db.test.ts` (red 3, green).
  - Replicated locally without `.env` (above). **Not replicated: the service container itself** (no Docker daemon
    here).
- **Green on GitHub is NOT VERIFIED until the push runs.** Check the run for this push.

### Specification citations

- Tracked files cited a git-ignored local file 135 times. They now cite **`docs/ENGINEERING_SPEC.md`** (tracked,
  ignored by no rule): laws L1–L16, gate table §16, practitioner standards §1, sourcing tiers §10, dataset standards
  §9.1, the 15 metrics §9.2, and every other section cited. Unsourced numbers are marked in the file.
- **Zero** occurrences remain in tracked files. 80 mentions and 209 section references were checked, and every one
  resolves (`aca3e11`, `57f51b4`, and this file).
- The local ignore rule moved to `.git/info/exclude`. Commit messages are unchanged; no history was rewritten.

### Commit hygiene note

**`26010aa` mixes two concerns** (L13). Its message is the CI backend fix, but it also adds
`docs/ENGINEERING_SPEC.md` and deletes `kinyamed/.gitignore`: they were already staged when I committed. The content
is correct; the commit is not one concern. It was left as is, because you said not to rewrite history.

### Blocked on human input, in priority order

1. **H1** Ethics answer from clinicians' institutions. It gates engaging any clinician.
2. **H6** Lead clinician: ratify the taxonomy and the unsourced 0.91, < 1% and 0.75. **H6b:** the cost of a missed
   CRITICAL against a false alarm; the 10:1 is unsourced and reaches every served decision (A30). **H6a:** is there a
   validated report-based urgency instrument?
3. **H3–H5** Clinical documents in `docs/clinical/`: the Rwandan ETAT edition, the national triage protocol and its
   mapping, obstetric danger signs and referral data.
4. **H12** Your spec rulings E1–E7, including **E6** (scope: paediatric, adult, or both).
5. **H7** Kinyarwanda clinician pilot, which starts the evaluation set and unblocks every model number.
6. **H15** Target CPU and an arrival-rate latency NFR (A29).
7. **Branch protection** on `main`, requiring the CI checks.
8. **H21** Alembic merge revision before merging `wip/account-analytics-frontend`.
9. **H10** red-flag validators; **H8/H9** other languages and code-switch raters; **H11** receipt translations;
   **H16** v2d weights location; **H13/H19** governing spec and applying A27–A30 to the .docx; **H20** SAMU/912
   unconfirmed, never shown.
10. **H2** NHRC/IRB approval, before any real patient.
- Your local `backend/.env`: `MODEL_MAX_LENGTH` must be unset or 96 before serving v2d (you are doing this).

### Uncommitted and unpushed

- **Unpushed before this push:** `26010aa`, `66f5c5c`, `aca3e11`, `57f51b4`, `a32a5b0`, and the commit carrying this
  file. `origin` had `16968ed`.
- **Uncommitted, deliberately:** `docs/clinical/` (the WHO PDF, never committed).

### Tomorrow's single next action

Done 2026-09-16: CI run #79 green on all 8 jobs at `44dbefb`; ML suite and Vitest re-run at HEAD, counts above.
Next: the clinician and ethics questions (H1, H6/H6a/H6b), and the pilot authoring instrument below. Then send **H1** (ethics) and the **H6 / H6a / H6b** clinician questions.

---

## 2026-09-16 — item 1: the pilot authoring instrument (no vignettes, no labels)

**Built, not authored.** `annotation/authoring.py` + `tests/test_authoring.py` (18 tests; red observed with the
module removed, and one fixture was wrong: 40 rows sharing one placeholder text, which G4 correctly refused as an
exact duplicate).

- The issued sheet has **no urgency column** (a label would anchor the annotator; `annotation/store.py` already
  refuses one at import) and an **empty `text` column**: Kinyarwanda vignettes are written by native-speaker
  clinicians (ENGINEERING_SPEC §10.2 T1; machine-authored or translated text is inadmissible). **I authored no
  vignette.**
- Columns: item_id, text, language, split, scenario_id, seed_id, reporter, patient_age_group, domain, voice,
  length, negation, multiple_complaints, register, author_code, generation_method, validated_by (`PENDING`), date.
- Gates enforced when a filled sheet comes back (`--check`): **G1** rows per seed, **G4** near-duplicate and exact
  duplicate seeds, **G5** machine person-transformation (metadata, plus a first/third pair from one author),
  **G7** provenance completeness, **G8** author concentration, and EVAL_SET_SPEC §8's one-item-per-scenario rule in
  the test split. **G2** is corpus-scope only; **G3** cannot exist yet, since its floor is defined from this pilot.

**Where the gates bind, for a 2,354-item Kinyarwanda pilot with 5 authors** (`python -m annotation.authoring`):

| Gate | Binds at | Why |
|---|---|---|
| G8 author concentration | **25 items per language × domain** | 5 authors × 20% each. This binds first, and hardest: a 2,354-item pilot needs **≥ 5 authors per cell**, and more if one author writes most of a cell. |
| G4 near-duplicate seeds | **50 items** | Above 50 items a single near-duplicate pair exceeds 2%. The likeliest real collapse: authors writing to a grid converge on phrasings. |
| G1 rows per seed | does not bind | One item per scenario in the test split means each item is its own seed. It binds only for calibration variants (50 per seed; above 1,000 items the 0.1% share is tighter). |
| G2 distinct seeds | 3,000 per language (corpus) | A 2,354-item pilot is below it by construction: G2 is a corpus gate, not a pilot gate. **Its per-cell floor (30 per non-empty cell) cannot be computed at all** — see below. |
| G3, G5, G7 | per item, or not yet computable | G5 and G7 bind per item; G3's floor is this pilot's own MATTR. |

**The blocking finding: the set size cannot be computed.** The number of non-empty cells is
domain × urgency × reporter × age group, and **the domain axis is BLOCKED** (H4: the national triage protocol is
not in the repository; the repo's 9 corpus domains are an unratified placeholder). Without it, G2's per-cell floor
has no denominator, so the minimum viable pilot size is unknown. The other BLOCKED axes: the clinical presentation
types (D2/D3) and the urgency definitions themselves (H6, protocol §3). **E6 (paediatric / adult / both) is also
undecided, so `patient_age_group` is issued as BLOCKED.**

**Collapse risk, in order:** (1) too few authors — with 5, no cell may exceed 25 items; (2) phrasing convergence
under a grid (G4 at 2%); (3) one author dominating a cell (G8); (4) paraphrase reuse, which is admissible only in
the calibration split.

## 2026-09-16 — items 2 and 3

### Item 2 — AfriBERTa-large measured, shortlist closed with a decision rule (`a066608`)

AfriBERTa-large was already measured on 2026-09-15 once `sentencepiece==0.2.2` was pinned (`7cc63f9`): Kinyarwanda
**1.66 [1.64, 1.68]** tokens per word against XLM-R's 2.52, and French **2.40 [2.37, 2.43]**, the worst of any
language and vocabulary measured. What remained was closing the table, now done in TOKENIZER_STUDY §4.

- **The shortlist does not close to one on tokenization, and saying otherwise would be inventing evidence.**
- **For the pilot's first training run: AfroXLMR-mini.** It is the only checkpoint whose CPU latency and memory
  are measured anywhere (MODEL_AUDIT §3.3), it is the incumbent so results stay comparable, and the pilot run
  exists to exercise the pipeline on real labels, not to select an encoder. Its weakness is stated: the highest
  Kinyarwanda fertility measured.
- **Production encoder: chosen by the gate, in a pre-registered order** — gate 5 per pure language, then gate 7,
  then gates 14/15 on the named target CPU (H15), then gate 9, then cost. Each candidate has one named
  measurement that eliminates it.

### Item 3 — malfunction probe, NOT A GATE METRIC (`training/probe.py`, 19 tests)

Built as a **malfunction probe, not an urgency probe**: asserting that a text is unambiguously CRITICAL is a
clinical claim, so none was authored. `data/probe/urgency_probe.csv` ships empty and needs a source and a named
validator per row; even filled, the report prints the model's answer per item and never a score. `evaluate.py`
does not import it, and a test enforces that.

**A finding I got wrong, and retracted the same day.** The first run reported ROUTINE for 200 of 200 inputs with
p(CRITICAL) never above 0.17, and I was one step from writing "single-class collapse" into MODEL_AUDIT.
- **It was my probe's defect.** It loaded the tokenizer from the model directory root, which holds no tokenizer
  files. Transformers did not raise: it returned a **vocabulary of 5**, every word became `<unk>`, and the model
  answered its prior on unreadable input.
- **What caught it:** the result contradicted MODEL_AUDIT's own recorded confusion matrix for v2d, which
  over-predicts CRITICAL and cannot be a ROUTINE collapse. The contradiction was checked before the claim was
  recorded.
- The probe now checks **input encoding** (vocabulary size, unknown-token rate) and fails loudly. A model shipped
  without its tokenizer would show exactly this signature in production, so the check earns its place.
- `evaluate.py`, `holdout_eval.py` and the backend all resolved the tokenizer correctly; only the probe did not.

**What the corrected probe measured** (200 texts from the v2 eval split; MODEL_AUDIT §11):
CRITICAL 102, URGENT 33, ROUTINE 65 — **no collapse**; encoding clean (0.0% unknown); determinism 200/200; label
order correct; **capitalisation alone changes the class for 63 of 200 inputs (31.5%)**, whitespace for none; mean
probabilities 0.36 / 0.33 / 0.31 and **highest p(CRITICAL) 0.55**.

**Is v2d behaving sanely? Partly, and not well enough to matter.** It is not collapsed and it is deterministic,
but it is fragile to capitalisation and uniformly unconfident: every prediction sits below the 0.75 review
threshold, so the service flags it for clinician review (FR-04-03, L4) rather than assigning urgency silently.

## 2026-09-16 — ONE finding: the corpus, the model and the evaluation set are the same failure

Recorded as a single causal chain, not three defects. Sources: DATASET_AUDIT §10 (corpus and eval-set collapse),
MODEL_AUDIT §4, §11 (model behaviour and the probe), `reports/measurements/majority_baseline.txt`.

1. **The corpus could not teach the task.** 330,000 rows expanded from **165 seed phrases**, with mechanical
   person-transformation applied to 180,272 rows (54.6%) — CORPUS_REBUILD §1, marked NOT REPRODUCIBLE. Gates G1,
   G2, G4, G5, G6, G7 and G8 all fail on it.
2. **The model trained on it cannot be characterised.** v2d over-predicts CRITICAL on the reporting subset
   (confusion matrix, §4), is uniformly unconfident (no CRITICAL probability above 0.55 anywhere in the probe
   sample), and **changes its answer on capitalisation alone for 31.5% of inputs**. Its loss sat at the uniform
   prior (ln 3 = 1.0986) for the first 200 of 1,150 steps before descending to 0.53.
3. **The evaluation set could not reveal either.** The held-out set is **17,942 rows from 9 distinct source
   sentences**; the gate refuses every one of its 45 cells on it. The reported 0.7065 accuracy has a
   phrase-cluster interval of [0.400, 0.914].
4. **The floor makes the number readable.** Always-majority on that split scores **0.4995** (always CRITICAL);
   always-ROUTINE would score 0.0662. So 0.7065 is about 21 points above the floor — **weak evidence, not
   evidence of nothing, and not evidence of deployability.** An earlier claim that 0.7065 was near the
   always-ROUTINE value is corrected here.

5. **A fourth symptom of the same root cause: no surface variation.** The corpus contains **0 of 34,425 rows in
   capitals**, **0 with double spacing**, and no typos at all (the generator has no noise step); 134 of its 165
   seeds end in terminal punctuation. The model trained on it flips its predicted urgency under
   **capitalisation 31.5%**, **typos 21.0%**, **punctuation 5.0%**, **whitespace 0.0%** (MODEL_AUDIT §11). Real
   patients type in all of these. Recorded as **gate G9** in CORPUS_REBUILD §3 and §3.1, to be produced by authors
   deliberately. **The fix is not to lowercase input at serving time:** that hides the fragility and discards
   information the tokenizer is case-sensitive to.

**The chain, in one line:** a corpus built from 165 phrases by machine transformation, with no surface variation,
produced a model whose behaviour no one can characterise, and an evaluation set of 9 sentences could not have
revealed it either way. **One root cause, four symptoms** — few seeds, mechanical transforms, absent surface
diversity, and an evaluation set too small to show any of it. Fixing any one alone changes nothing.

## 2026-09-16 — production risk: a model shipped without its tokenizer fails silently

Recorded in its own right, separately from the probe finding it caused (MODEL_AUDIT §11.1).

**The failure mode.** `AutoTokenizer.from_pretrained(<directory with no tokenizer files>)` **does not raise** in
transformers 5.8.1. It returns a tokenizer with **vocabulary size 5**; every word becomes `<unk>`; the model then
answers its class prior on unreadable input. Nothing in the output looks wrong: probabilities are well formed,
the model is deterministic, and the predictions are plausible. It presents exactly as a model that has collapsed
to one class.

**Why it matters in deployment.** A model directory is copied, renamed or repacked far more often than it is
retrained. Tokenizer files sit in a subdirectory here, so any packaging step that flattens or drops it produces a
service that looks healthy and reads nothing.

**Where this repository stands today:**
- `backend/app/services/model_classifier.py`, `training/evaluate.py` and `training/holdout_eval.py` all resolve
  `<model>/tokenizer` before falling back, so none of them is affected.
- `training/probe.py` now measures its own **input encoding** (vocabulary size and unknown-token rate) and fails
  loudly; it caught this defect in my own harness on 2026-09-16.
- **Not yet done:** the service does not check the encoding of a loaded model. A start-up check — tokenize a fixed
  string and refuse a vocabulary below a floor or an unknown-token rate above one — is the obvious next guard, and
  is the same contract as `max_length` and the decision rule.

**For the paper.** Worth one sentence in the limitations or deployment section: a silent tokenizer mis-load makes a
model answer its prior on unreadable input while every surface signal stays healthy, and it is invisible to any
metric computed from the model's own outputs.

**v2d is NOT A BASELINE.** It is an audit artefact. No future model is compared against it, no retraining of it is
planned, and it is not served to patients. What it is useful for: exercising the serving path, the gate's refusal,
and this probe.

## 2026-09-16 — the four-step synthetic-corpus plan: executed, and it stopped at step 3

Full record: `reports/PRELIMINARY_RESULTS.md`. Nothing was waived, and the pipeline was not modified.

- **Step 1, generation to 1,000,000 rows: done** (130 s, 96 MB peak; the generator's own targets passed). Run
  through the CORPUS_REBUILD gates (`dataset/corpus_gates.py`, 19 tests): **4 FAIL** (G5, G7, G8, G9), 5 NOT
  COMPUTABLE. On the phrase-attributed v2 split, **6 FAIL** (G1, G2, G5, G7, G8, G9), with one seed producing
  8,975 rows — 26.07% of the split.
- **The largest gate-passing corpus is 0 rows, at any size.** G2's floor is on **seeds** (≥ 3,000 per language)
  and the generator has **165**. The shortfall to 1M is **19,835 seed phrases**, not rows. Rows are free; seeds
  must be authored. G5, G7, G8 and G9 would fail at 165 seeds anyway: no authors, no per-row provenance, no
  surface variation.
- **Step 2, seed provenance** (`dataset/seed_provenance.py`, 5 tests): train **150** distinct seeds / 295,575
  rows; test **15** / 34,425 rows; **0 shared seeds**; largest single seed **26.07%** of the test split. Disjoint
  is not independent: one generator, one inventory. The banner now heads every report carrying a synthetic metric.
- **Step 3, the pipeline: REFUSED**, exit 2 in 9.6 s, "Nothing was trained." 38 test-split cells INSUFFICIENT DATA
  on the n=9 set, plus no calibration split. `reports/measurements/pipeline_refusal_1m_corpus.txt`.
- **Steps 4 and 5: NOT PRODUCED**, because no checkpoint exists. Had the refusal been overridden, every cell would
  have rested on **15 distinct source sentences**, whose intervals are already on record: accuracy [0.400, 0.914],
  CRITICAL recall [0.08, 1.00].
- **Unchanged:** §16 gates UNMET; v2d NOT A BASELINE and not-for-deployment; the clinician gold-set path is still
  the only route to a publishable claim.

## 2026-09-16 — render-path audit: the reading copy was short of the paper twice over

**What I checked and what I found.** After `sections/appendix.tex` turned out never to have
been in `render_plain.py`'s file list, I audited the whole path. A second, larger omission:
the renderer did not expand `\input`, so two subsections the typeset paper carries were
absent from every plain render and every artifact version v1-v7:

| Missing from the render | Is in the LaTeX build via |
|---|---|
| The acceptance gate, and where each threshold comes from (6.4) | `sections/discussion.tex` -> `generated/gate_derivation.tex` |
| A single-metric safety gate certified a model that had abandoned an urgency class | `sections/discussion.tex` -> `generated/finding_gate_degeneracy.tex` |

A third, opposite defect: the renderer ignored the `\renewcommand{\subsection}[1]{}`
inside a `\begingroup` in `sections/limitations.tex`, so it printed a second "Limitations"
heading that the PDF does not have. All three fixed in `87e7113`.

**Now enforced, not promised.** `tests/test_render_completeness.py`, 6 tests: every
`\input` target reachable from `main.tex` is reachable from the renderer; the two heading
sequences are identical; no unresolved reference; the committed render is current; no file
in the build would typeset an em dash. One allowed omission,
`generated/results_macros.tex`, named with its reason and verified to hold nothing but
`\newcommand` lines.

**Three generated files are not in the build at all**: `confusion_table.tex`,
`results_table.tex`, `sweep_table.tex`. Nothing `\input`s them. They are emitter output
that no longer has a home in the paper. Not deleted, and flagged here rather than acted on.

## 2026-09-16 — em dashes: fixed at the emitter, zero reach the PDF

`training/holdout_eval.py` is the single emitter for all seven generated `.tex` files. It
wrote an em dash in two file headers and `---` (which LaTeX sets as an em dash) in the
macro-average row of `results_table.tex`. Both now write ASCII; the cell reads `n/a`, which
states what it means. **Measured across all 16 files the LaTeX build compiles, with
comments excluded: zero em dashes, either spelling.** The `---` that existed was in
`results_table.tex`, which nothing `\input`s, so it never reached the PDF.

**REGENERATION NOT RUN, and this is the one open item.** The generated files still carry
their 2026-09-08 bytes. Re-running `holdout_eval.py --writeup` needs the three sweep models
at `~/kinyamed-runs` (466 MB each) and three inference passes over 17,942 rows. Available
memory at the time of writing was 2.1 GiB with Chrome and Firefox running, and the standing
lesson is to close browsers before an ML job and not retry after a kill. The emitter change
takes effect on the next regeneration; nothing in the PDF depends on it.

## 2026-09-16 — paper length: six blocks moved to appendices, nothing deleted

Main text **11,552 -> 10,083 words**; appendix **1,708 -> 3,639**. Moved, each leaving a
one-sentence pointer naming its appendix: the leakage-declaration and search-cost
subsections (Discussion), the v1 leakage post-mortem and the three-language-arm status
(Method), the language-arm status and the one-inference-pass diagnostic (Future work).
Apparatus 5.3 code-switching was already three sentences plus a pointer (`22d36ee`).
The three open questions stay in the main text. Appendices are now A-H; every
cross-reference resolves (`75f31a1`).

**No page count is claimed.** There is no LaTeX toolchain on this machine, so a page
figure would be an estimate presented as a measurement. The word counts above are
measured; the page count is whatever Overleaf reports on the next build.

**A second defect found while doing it.** `sections/appendix.tex` was never in
`render_plain.py`'s file list, so every plain-text render since the appendices were
created was main text only, and so was the reading copy built from it. Fixed in `f621d96`,
with four further renderer defects in `4644bd5` (references rendered as their own labels,
headings split across source lines, labels leaking into prose, tables keeping their column
specification and orphaning wrapped cells).

## 2026-09-17 — item 1b parts 4-5: bcrypt cost measured, logout blocklist with a real fallback

### Part 4: bcrypt cost 12 is exercised, not just configured (`4d9c487`)

The suite runs at cost 4 so fixture users do not add minutes to every run, so **nothing
ever computed the digest production would produce** — only the config rejection path was
asserted. A setting whose effect is never measured is a claim.

Two checks, because either alone passes while the property is false: the cost embedded in
the digest (exact), and elapsed time, because a cost recorded in a digest is worth nothing
unless the work was done. Bounds are deliberately loose (50 ms absolute, 20x over cost 4
against a theoretical 256x) so the test signals a stubbed library or a clamped cost rather
than flaking on a loaded laptop.

Also pinned: **a digest made at the suite cost still verifies after the setting is raised.**
That is why a cost increase needs no migration, and it is the property that would silently
lock every user out if it stopped holding.

### Part 5: logout withdraws the access token (`186564f`, `ab9d104`, `6f423c2`)

Logout revoked the refresh token in Postgres and did nothing to the **access** token, which
stayed valid for up to fifteen minutes because verifying it needs no state. For that window
a stolen token still opened the ward queue.

**The fallback is the part that matters, as instructed.** Redis is a cache in front of a
safety property, never a dependency of the request path. Four tests run with Redis pointed
at a closed port — down, not merely misconfigured — covering serving, logging out, refresh
revocation (unaffected: it lives in Postgres) and readiness. What degrades is stated
plainly: an access token then remains usable until it expires, which is exactly the
behaviour the system had before the blocklist existed.

Readiness **reports** redis and does not gate on it: taking a pod out of rotation for a
degraded blocklist would turn a cache outage into a triage outage, and hiding it would leave
nobody knowing the window had reopened.

Two details that decide whether this is an asset or a liability: entries carry a TTL bounded
by the access-token lifetime, so the blocklist cannot grow without bound on a box that also
serves the queue; and the connect timeout is 250 ms, because it sits on the request path.

**CI gained a `redis:7` service** — and then a second, more important fix. CI went green on
the blocklist commit and **that proved less than it looked**: the fixture skips when Redis is
unreachable, so had the service failed to come up, the four feature cases would have skipped
and the job would still have passed, with "CI is green" saying nothing about whether logout
withdraws a token. **That is the vacuous pass this project keeps finding in other people's
work, written into its own.** Skipping stays the courtesy on a developer machine; on the
runner (`CI=true`) the absence is now a failure naming the service to check. Verified by
running with `CI=true` against a closed port: four errors, four fallback cases still passing.

**454 backend tests pass**; CI green on `main` runs #121 and #123.

### Remaining in item 1b

The password-reset OTP (FR-05-12): six digits, ten-minute expiry, single use. Not started.

## 2026-09-17 — item 1b part 6: password reset by code (`662a5e3`). **FR-05 item 1b complete.**

Four properties, each of which fails quietly if only assumed.

**Enumeration.** Same status, same body, same elapsed time for a known and an unknown
address. Hitting the per-account cap is silent for the same reason: a visible refusal would
confirm the address exists. Every failure on confirm returns one error, because
distinguishing unknown address from wrong code from expired tells a caller which part they
got right.

**The timing test was vacuous when first written, and mutation caught it.** With the
equalising hash deleted from the unknown path it still passed: the suite hashes at cost 4,
about two milliseconds, which HTTP overhead swamps. Rewritten to run at cost 12, where the
hash dominates, it fails against the mutation with a **55x** difference and passes with the
equaliser restored. Recorded because the lesson generalises: **a test written at a
convenience setting can measure nothing while looking thorough**, and the only way to know
is to break the code and watch it fail.

**Single use.** `consumed_at` is set when a code is spent, so a replay inside the window is
refused. Attempts capped at five, so a six-digit code cannot be walked.

**Stored as a hash.** A bcrypt digest, never the code. The threat is a read of the table (a
backup, a query log, a support export) becoming takeover for every reset in flight. A test
scans every column of every row for the plaintext.

**Per-account cap**, three per hour. The IP limiter does not cover this: an attacker rotates
addresses and the victim is chosen by email. Without it, anyone who knows an address can
make this service send unlimited SMS to that phone at the project's expense.

**The audit completeness test caught both new endpoints before I did**, which is what it is
for. The request is recorded with **no actor**: the endpoint needs no credentials, so the
requester is not known to be the account holder, and attributing it would log an attacker as
the victim. The confirmation is attributed, because possession of the code was proved.

**KNOWN GAP, not papered over.** Delivery is by SMS to the patient record's phone, so a
**staff account has no phone here and gets a code that cannot reach anyone**. Logged as
`password_reset_undeliverable`. Closing it needs either an email sender or a phone on
`users`, and inventing one would have been worse than naming it. FR-05-12 says "email OTP";
this project has an SMS provider and no mail transport, which is the discrepancy behind the
gap.

**469 backend tests pass**; CI green on `main` run #127.

### FR-05 status after item 1b

| FR | Status |
|---|---|
| FR-05-01 roles, RBAC | DONE-VERIFIED (was already) |
| FR-05-05 RS256, 15 min | DONE-VERIFIED (`9d9765e`) |
| FR-05-09 10 per 15 min on auth routes | DONE-VERIFIED (`dc6c1fc`) |
| FR-05-10 logout blocklist, with fallback | DONE-VERIFIED (`186564f`, `6f423c2`) |
| FR-05-11 composition rules, bcrypt 12 measured | DONE-VERIFIED (`8a3e19e`, `4d9c487`) |
| FR-05-12 reset code | DONE-VERIFIED for patients; **undeliverable for staff** |
| FR-05-13 family-scoped reuse detection | DONE-VERIFIED (`17df027`) |
| FR-05-02 registration fields | **still INCORRECT**: `full_name` not first/last, no `confirm_password`, and a malformed phone still returns 500 rather than 422 (the `ValueError` from `normalise_phone` has no handler) |
| FR-05-06 refresh cookie | **PARTIAL**: SameSite is `lax`, not `strict`; the token is not hashed at rest |

**Next:** item 2, Google OAuth. FR-05-02 and FR-05-06 are left open deliberately and should
be picked up with it, since all three touch the same registration and cookie surface.

## 2026-09-17 — item 2: Google sign-in, plus FR-05-02 and FR-05-06 (`0444c7c`, `4e4c995`)

### The verification, and the seven mutations

A Google ID token is a JWT: anyone can read one and anyone can write one. What makes it
evidence is the signature against Google's published keys, plus the claims saying who it was
issued **for** and **by**. An implementation that decodes it and trusts the `email` inside
authenticates whoever can type JSON, and **from the outside that is indistinguishable from a
correct one**, because both sign the user in. Hence more forgery tests than happy paths.

Checks: signature against the key the `kid` names; `aud` equal to our client id; `iss`;
`exp`; and `email_verified`. **The algorithm is pinned and the header's `alg` is never
consulted** — trusting it reopens the confusion attack the RS256 work closed, one layer up.

**Mutation results, as instructed.** Each check was broken in turn and its guard test had to
fail:

| Mutation | Guard | Round 1 | Round 2 |
|---|---|---|---|
| `aud` not verified | token for another application | invalid mutation* | CAUGHT |
| `iss` check removed | wrong issuer | CAUGHT | CAUGHT |
| algorithm unpinned | HMAC with the public key | CAUGHT | CAUGHT |
| `email_verified` removed | unverified address | CAUGHT | CAUGHT |
| signature verification off | stranger-signed token | **SURVIVED** | CAUGHT |
| expiry not enforced | expired token | CAUGHT | CAUGHT |
| unknown `kid` tolerated | wrong `kid` | **SURVIVED** | CAUGHT |

\* Removing `audience=` makes PyJWT *stricter*, not weaker: with an `aud` claim present and
no expected audience it raises. The mutation was wrong, not the test. Redone as
`verify_aud: False`.

**The two survivors were real and worth the exercise.** My stranger-signed token carried the
stranger's **own** `kid`, so it was rejected as an unknown key and proved nothing about
signatures — with signature verification disabled it still passed. It is now three tests: an
unknown `kid`; a token signed by a stranger **under Google's `kid`**, which only a signature
check can refuse; and a token signed by Google's real key **under a wrong `kid`**, which only
the `kid` lookup can refuse. Source verified byte-identical to the pre-mutation backup.

**This is the second time in two features that mutation testing found a test passing for the
wrong reason** (the first was the reset-timing test). Treat "it passed first try" as a
prompt to break the code, not as good news.

### FR-05-02 and FR-05-06, done with it

`full_name` split; `last_name` NULLABLE on purpose, because a one-word legacy row has no
last name to recover and writing `''` would be inventing data. `confirm_password` compared
and discarded. **Phone validation moved into the schema: a malformed number was returning
500, which pages somebody and tells the user nothing; it is now a 422 naming the field.**
`users.phone` also closes the staff reset-delivery gap. Cookie is `SameSite=strict` (a test
pins the configured default, not this environment's value). Refresh token hashed at rest
with **SHA-256, not bcrypt** — bcrypt truncates past 72 bytes and a JWT is longer, so it
would hash a prefix; the token is high-entropy, so the slow-hash argument does not apply.

### Schema

One migration (`f4c81d5a9e27`): names, phone, avatar, `oauth_provider`/`oauth_id` with a
UNIQUE over the pair, `hashed_password` relaxed to NULL behind a CHECK that every row has a
password **or** an OAuth identity. Without that CHECK, relaxing the column permits an
account nobody can authenticate as. The downgrade refuses loudly if OAuth-only rows exist
rather than writing a placeholder digest that would look like a credential. `DROP COLUMN
full_name` is the only destructive statement written in this project; it is backfilled in
the same transaction and the SQL was shown before it ran.

**507 backend tests pass**; CI green on `main` runs #131 and #133.

### Still open

- Google **revocation** on logout is not called (§12.2). Sessions end locally; Google's own
  grant is untouched.
- No frontend sign-in button: the backend accepts a token nothing yet sends.
- `patients.name` is still a single field. The spec splits it too; only `users` was done.

## 2026-09-17 — item 3 steps 1-2: the CRITICAL backfill (`9331080`)

Design in `reports/ALERT_DELIVERY_DESIGN.md`, approved as proposed. Built transport-free on
purpose: the safety property lives in these queries, so it is settled before any wiring
exists to obscure it. An early stop here leaves the system **safer** than before, which is
why the order was chosen.

**Bounded by state, not time.** `outstanding_for` has no `since` clause, and a test asserts
its absence against a month-old row. A CRITICAL still waiting after a week is still an
emergency; a time window would suppress exactly the row that matters most.

**Acknowledgement is not a clinical act**, and the schema says so by keeping it in its own
table rather than as a column on `queue`. Per doctor, so one clinician's dismissal cannot
hide a live CRITICAL from the one coming on shift.

**Six mutations, all caught first time**: a 24h window creeping into the backfill,
acknowledgement going global, completed entries staying owed, acknowledging advancing
`queue.status`, routine entries treated as alerts, zero recipients reported as delivery.

**522 backend tests pass**; CI green on `main` run #141.

### CLINICAL DECISION OUTSTANDING — re-alerting on an acknowledged CRITICAL

`alerts.acknowledged_and_still_waiting(db, longer_than=...)` lists CRITICALs that somebody
acknowledged and that are **still waiting**. It is a measurement and nothing more: nothing
calls it on a timer, nothing escalates from it, and **`longer_than` has no default** — a
test asserts the default stays absent, because an interval baked into the signature becomes
policy by accident.

**Two questions belong to a clinical lead, not to this project:**

1. **What interval means "too long"?** It plausibly differs by presentation, by time of day
   and by how many clinicians are on. There is no defensible single number available here.
2. **Should exceeding it escalate at all**, and to whom — re-alert the same doctor, alert
   everyone, page someone not on the floor? Each is a different operational commitment and
   none is an engineering choice.

Until both are answered the function stays a query. Building an escalation on a guessed
interval would put a number nobody ratified in front of a clinical decision, which is the
same defect as the unsourced thresholds recorded in A30.

### Also recorded: a CRITICAL can reach nobody

With no clinician on duty, a real-time CRITICAL alert has **zero recipients**.
`recipients_for_broadcast` reports it and `warn_if_unattended` logs
`critical_alert_unattended` with the consequence. **The alert is not lost** — it stays
outstanding and the next doctor to connect receives it from the backfill — but the real-time
part did not happen, and a push that silently succeeds against an empty set is
indistinguishable from one that worked. A stats/readiness surface for it comes with step 3.

## 2026-09-18 — external review: Block 2 verified, B6 fixed, and a staleness finding

**The review list now lives on disk: `reports/EXTERNAL_REVIEW.md`.** It was lost between
sessions twice because it existed only in a chat transcript. It carries all six blocks, a
status per item, the findings beyond the reviewer's list, and the decisions taken. Work the
review from that file, not from memory.

**All 15 Block 2 items verified against the repository. The reviewer was wrong about none.
One (B9) was already addressed and was deliberately left alone** — `discussion.tex` L86-88
already calls the 0.95 critical-recall threshold "inherited and unverified" against the 0.91
in the requirements. Rewriting honest text because a list says to is a regression.

**B6 fixed at the emitter.** The paper said the degenerate run "assigned the CRITICAL label
to 7,793 URGENT rows almost without exception". 7,793 is the URGENT *support*; at URGENT
recall 0.0083 about 65 of those rows were correct, so the same figure cannot also be the
count mislabelled. It now reads `v2c["confusion"][1][0]` — truth URGENT, prediction CRITICAL
— which is **7,634**. `holdout_eval.py`'s own header comment had carried the right figure
since 2026-09-07; only the emitted sentence was wrong.

**FINDING BEYOND THE LIST: the paper's corpus counts are stale, and commit `934433a` is why.**
That commit moved four third-person rows into `needs_clinician`. The record now holds 256
rows, **29** flagged, 23 held, 19 both, 4 held-only, 10 flagged-only. The paper still says 25
flagged, and its "eight phrases" is the held-only count from *before* that commit.

This is what made B2 and B3 look like arithmetic errors. They are drift. B2's
`256 - 50 - 23 = 183` assumed flagged and held are disjoint; they overlap by 19.

**It is the same shape as B6**: a number hand-copied from a source that later moved. Decision
taken — the corpus counts will be **emitted from the CSV** the way the clinician pack is,
rather than corrected in place. See `EXTERNAL_REVIEW.md` D2.

**Regeneration was running at handover.** It carries Block 1's emitter changes and the B6
fix. A backup of `paper/generated/` was taken before it started. When it lands: every
scientific number must be byte-identical to that backup EXCEPT the B6 count. Block 1 changed
wording only, so numeric movement means the run did not reproduce.

**Process note.** The first regeneration was stopped deliberately, a third of the way in, to
fold in the B6 fix rather than run twice. That is a chosen stop, not a memory kill, and the
"do not retry after a kill" rule does not apply to it. Separately: `pkill` returned 144 and
short-circuited an `&&` chain, so an edit silently did not apply — the STATE rule about
reading the whole failure rather than the tail caught it.

## 2026-09-17 — external review, BLOCK 1: five errors of fact (`42cb7aa`)

Every claim was checked against the repository first and the arithmetic recomputed. **All
five hold.** One is worse than the reviewer knew.

| Item | Verified how | Outcome |
|---|---|---|
| G2 must be strict | `MINIMUM_MACRO_F1 = 2.0/3.0` compared with `>=` | **Confirmed, and worse**: the constant is exactly 2/3, so the bug was *not* masked by rounding at 0.6667. Two perfect classes and one dead scored exactly 2/3 and **passed**. Now strict |
| "tightest guarantee" is wrong | Derived: macro = Σf/3 and f≤1 ⟹ min F1 ≥ 3·macro − 2 | Confirmed. **0.0000** at the threshold, **0.3172** at our 0.7724. Claim removed, bound stated |
| "no accuracy/recall/calibration figure" is false | Paper reports 0.9749, 0.0083, 0.5337, 0.7724, 31.5%, 21.0% | Confirmed false. Replaced everywhere with **"no figure is offered as evidence of model quality"** |
| Two shortfalls conflated | Recomputed from `corpus_gates.py`: floor 3,000 − 165 = **2,835**; 1,000,000 ÷ 50/seed = 20,000 − 165 = **19,835** | Confirmed. The gates demand 3,000 seeds, not 20,000. Now separated in abstract and results |
| "degenerate ceiling" misnamed | It is one strategy's precision, valid only if no ROUTINE row is labelled CRITICAL | Confirmed. Renamed **merge-strategy precision**, assumption stated |
| G3 undefined above 0.90 CRITICAL share | share + 0.10 > 1.0 ⟹ no model can pass | Confirmed a real gap. Now reports **NOT COMPUTABLE** naming the set's class balance as the cause, rather than failing the model |

**Why the "no figure" wording mattered.** The narrower claim is the true one *and* the one
actually meant: a paper cannot describe a gate certifying a degenerate model without saying
what the gate saw. A recall of 0.9749 beside an urgent recall of 0.0083 is evidence about a
**gate**, not a performance claim.

**REGENERATION PENDING.** Three of these live in generated `.tex`, so the emitter changed and
the output has not been rebuilt: 1.4 GiB free with a browser open is below what three model
loads need. **The generated files still carry the old wording until it runs** — the paper is
not yet internally consistent, and that is visible rather than hidden.

87 ML tests pass; render-completeness 11/11; lint clean.

## STANDING RULE (2026-09-17) — when a command chain fails, read the failure

**Do not re-run a sub-part of a failed chain without the gate that stopped it.**

On 2026-09-17 a commit chain was `ruff check . && git add && git commit -F msg`. Ruff
failed, the chain short-circuited, and nothing was staged. I read only the last line of the
output — a git error about a missing message file — and retried with a bare
`git add -A && git commit`, which **dropped the lint gate** rather than answering why it had
fired. CI caught it on `main` (run #145, Lint). The gate worked; I walked around it.

The failure mode is specific and worth naming: a `&&` chain reports the LAST thing that went
wrong, which is often a consequence rather than the cause, and the natural next move —
"just run the bit that failed" — is exactly the move that skips the check.

**How to apply.** When a chain fails: read the whole output, not the tail. Identify which
link failed. Fix that. Re-run the WHOLE chain. If a gate has to be bypassed deliberately,
say so out loud and give the reason, so it is a decision rather than an accident.

## DEFERRED REGISTER — open by decision, not by oversight

Things that were noticed, understood, and consciously not built. Listed together so that
"we knew about that" stays checkable rather than being a claim made afterwards. Each says
what it costs to leave and what closing it needs.

| # | Deferred | Cost of leaving it | What closing it needs | Raised |
|---|---|---|---|---|
| D1 | **Google revocation on logout** (§12.2). Logging out ends the local session and does **not** call `https://oauth2.googleapis.com/revoke`, so Google's own grant to this application survives. | Low today and not zero: a user who "signs out everywhere" after losing a laptop still leaves this app authorised in their Google account, and would reasonably expect otherwise. No KinyaMed session survives, so it is not an access path into the service. | One outbound call on logout for accounts with `oauth_provider='google'`, called best-effort: a failure must not fail the logout, exactly as the blocklist does not. | 2026-09-17, item 2 |
| D2 | **No frontend Google sign-in button.** The backend accepts and verifies an ID token; nothing in the UI obtains one. | The feature is unreachable by a user. It is not dead code — the endpoint is tested and correct — but it delivers nothing until a client sends a token. | Google Identity Services in the React app, the client id as build config, and posting the credential to `/auth/google`. Frontend work, so it belongs with item 4's UI rather than here. | 2026-09-17, item 2 |
| D3 | **`patients.name` is still one field** while `users` now has `first_name`/`last_name`. §8.1 splits both. | An inconsistency across two tables that both hold a person's name, and a migration that gets harder as more rows arrive. No functional failure: nothing depends on the split for patients. | The same treatment `users` got in `f4c81d5a9e27`: add both, backfill on the first space, leave `last_name` nullable for rows with one word, drop the old column. Roughly 20 call sites. | 2026-09-17, item 2 |

**Rule for this table:** an entry leaves it only by being built or by being ruled out in
writing. Nothing drops off because it stopped being mentioned.

## STANDING RULE (2026-09-17) — never point a schema command at the developer's database

**Never run `alembic`, `psql`, or any migration or DDL command in a way that inherits
`DATABASE_URL` from `kinyamed/backend/.env`.** That file points at the working database
`kinyamed`. Always name the throwaway database explicitly:

```
cd kinyamed/backend
DATABASE_URL="postgresql://<user>:<pass>@localhost:5432/kinyamed_test" \
  ./venv/bin/python -m alembic <command>
```

The test database is created, migrated and dropped by `tests/conftest.py` for every session,
so it is the only correct target for an ad-hoc schema command. To check a migration, prefer
`alembic upgrade <from>:<to> --sql`, which prints the statements and executes nothing.

**Why this is a rule and not a preference.** On 2026-09-17 I ran `alembic upgrade head` with
no explicit URL while verifying the `family_id` migration. It went to the developer's
`kinyamed` database and failed on the first migration with `relation "analytics" already
exists`, changing nothing. **That was luck, not design**: the same command against a database
whose `alembic_version` had been one revision behind would have altered a real schema without
being asked. L14 exists for this and the command slipped under it because it looked like a
read.

The dev database's own inconsistency (tables present, `alembic_version` at base) is the
developer's to resolve. Do not stamp, migrate or rebuild it.

## 2026-09-17 — item 1b part 3: reuse detection scoped to a token family (`17df027`)

Replaying a rotated refresh token revoked **every** session the user had. Safe, and far too
broad: a clinician with a phone, a ward workstation and a laptop lost all three because one
of them replayed a token, mid-shift, with no way to tell which device was at fault.

A **family** is one login and everything rotated from it. Logging in starts a lineage, each
rotation stays inside it, and reuse ends that lineage only. The blast radius is the
compromised device rather than the person.

**Deliberate actions keep their old breadth**, and tests hold that line: logging out
everywhere still ends every family, and deactivating an account still revokes all of them.
Narrowing reuse must not narrow those.

Migration `d2a7c81b4e60` is additive: `family_id` NOT NULL with a `gen_random_uuid()`
default so each pre-existing row becomes its own family (the safe reading: an old token
replayed then ends only itself), and the default is dropped immediately so a future insert
cannot silently start its own family instead of joining one.

An existing test named `..._ends_every_session` was renamed `..._ends_that_lineage`. It
passed either way, because that account has a single family. **A test name that claims more
than its body checks is how a weakened guarantee goes unnoticed**, which is the same failure
mode as the split manifest nobody read.

7 new tests; **441 backend tests pass**; CI green on `main` run #117.

## 2026-09-17 — RECOMMENDATION: the NAT risk in per-IP auth rate limiting

**The risk.** FR-05-09 specifies ten authentication attempts per fifteen minutes **per IP**,
and that is what `dc6c1fc` implements. A health centre whose staff share one public address
therefore shares ten attempts between all of them. At shift change, with several clinicians
signing in at once and some mistyping, the eleventh legitimate attempt is refused. The
control aimed at an attacker lands on the ward.

**What I recommend, and what I recommend against.**

- **Do not raise the IP limit.** A number large enough to clear a shift change is large
  enough for useful online guessing, and it degrades the control everywhere to fix it in one
  place.
- **Add a per-account counter alongside the per-IP one**, and refuse when *either* is
  exhausted. The two answer different threats: per-account stops guessing at one person's
  password from many addresses, per-IP stops guessing at many accounts from one address.
  Neither subsumes the other, which is why this is an addition rather than a replacement.
- With both in place, the per-IP limit can be relaxed for *authenticated-adjacent* traffic
  without weakening the guess-resistance that per-account now carries.

**Not built.** It is a design change with its own state, and it should be decided rather
than slipped in beside a limiter that currently meets the written requirement. Recorded here
so the trade-off is visible before a clinic hits it rather than after.

## 2026-09-17 — SECRET_KEY removed, and item 1b parts 1-2 of 6

### SECRET_KEY is gone (`095dfd1`)

It signed tokens under HS256. Once tokens became RS256 nothing read it, and a required
variable that nothing reads is a trap: it gets rotated during an incident in the belief
that doing so invalidates sessions. Removed from `Settings`, `.env.example` and the CI
workflow, along with the placeholder blocklist that guarded only this value.

**A future CSRF token or signed URL must introduce its own purpose-named secret rather
than reviving this one.** Three tests hold the line: the field is absent from the model, a
stray `SECRET_KEY` in an environment stays ignored (`extra="ignore"`) rather than quietly
becoming live, and no non-comment line under `app/` mentions it. The frontend's CI-contract
test now asserts the workflow does **not** set it, so the trap cannot return as an env var.

**Action taken by the user:** line 17 of `backend/.env` deleted.

### FR-05-11 password composition (`8a3e19e`)

`aaaaaaaaaaaa` was valid: twelve characters, one distinct letter, nothing to stop it. All
four character classes are now required, checked together so one attempt reports every
failing rule, and the message names the classes that are missing.

**The length floor stays at 12 although FR-05-11 says 8.** A specification minimum is a
floor, not a target; lowering a limit that already holds to match a document would weaken a
live gate for nothing. A test pins 12 so a later reading of the spec cannot lower it.
`current_password` is deliberately not composition-checked: it is a credential being
verified, and applying new rules there would lock out everyone whose password predates them.

### FR-05-09 authentication rate limiting (`dc6c1fc`)

One global bucket of 120/60s covered every route, so a guessing client had 120 attempts a
minute **and** shared that allowance with ordinary traffic. Credential endpoints now have
their own counter at ten per fifteen minutes per IP, separate in both directions: queue
polling cannot consume the login budget, and an exhausted login budget does not lock a
clinician out of the queue. `Retry-After` reports the window actually exhausted.

Refresh and logout are excluded by design: refresh runs on a timer, once per access-token
lifetime per session, so counting it would throttle a clinician with several tabs open.

**The X-Forwarded-For fix still holds on this path**, verified rather than assumed: an
integration test rotates the header and is still refused, and a unit test drives
`client_ip` directly, because the TestClient's peer is the literal string `testclient` and
can never be a configured proxy — asserting through HTTP would have proved something weaker
while looking like coverage. The right-most-non-proxy rule is pinned, including a
client-supplied hop to the left and a proxy appending its own address.

**Operational risk recorded in the middleware, not hidden:** the key is an IP, as
specified, so a clinic behind one NAT shares ten attempts between all staff. When that
bites at shift change the answer is a per-account counter alongside this one, not a larger
number here.

**Side finding, now guarded:** a 422 must not echo the submitted value. Pydantic carries
the offending input in its error objects, and a handler serialising them would reflect the
phone, name and password back to the caller. It strips them today; `test_pii_scan.py` now
keeps it stripped.

**431+ backend tests pass**; CI green on `main` runs #111 and #113.

### Remaining in item 1b, and one blocker to decide

Not started: `family_id` reuse detection scoped to a token family rather than user-wide;
bcrypt cost 12 exercised by a test rather than only configured; the Redis logout blocklist;
the password-reset OTP.

**Blocker for the blocklist: CI has no Redis service.** Redis runs locally and `redis-py`
7.4.0 is installed, but the backend CI job declares only Postgres. Two things are needed:
a Redis service in the job to test the real path, and the ENGINEERING_SPEC §6.3 fallback
("Redis unavailable → database-only state, no crash") which must be tested with Redis
deliberately absent. Flagged before building rather than after.

## 2026-09-17 — item 1a: RS256, a clean break from HS256

**DECISION, recorded because it has a cost.** The cutover is a **forced re-login for
everyone**, with **no dual-verification path**. Your rationale, kept in your words: there
are no production sessions, and a transition path that accepts HS256 is the thing we are
removing; a clean break beats a temporary code path nobody remembers to delete. Any token
issued before `9d9765e` is now rejected, by design.

**What was wrong.** `JWT_ALGORITHM` was `HS256` and tokens were signed with `SECRET_KEY`
(`core/config.py:68`, `core/security.py:100`). Under a symmetric algorithm the signing
secret and the verifying secret are one string, so anything able to *check* a token was
also able to *mint* one. No RSA settings existed, so this was a design change rather than
a config flip.

**The attack now closed.** The verifier pins the algorithm to the configured one and never
reads `alg` from the token header. Without that pin, an attacker takes the public key,
which is not a secret, computes an HS256 MAC over it, and a header-trusting verifier checks
that MAC using the same public key and admits a token the attacker minted. The test
hand-assembles exactly that token, because **PyJWT refuses to encode it and an attacker is
not using PyJWT**, and asserts rejection both with and without a matching `kid`. `alg=none`
is covered by its own test.

**Key identity is derived, not configured.** A `kid` is a truncated SHA-256 of the public
DER, and the public half is derived from the private key rather than configured beside it,
so the two cannot drift apart.

**Rotation, in two deploys, without signing anyone out:** put the old public PEM in
`JWT_RETIRED_PUBLIC_KEYS` and the new private PEM in `JWT_PRIVATE_KEY`, deploy; wait one
refresh-token lifetime (7 days); clear the retired key, deploy. Retired keys verify and
never sign. Asserted by a test and by a three-process drill (signed under A, verified after
rotating to B with A retired, rejected once A was dropped).

**Development** with no key configured generates an ephemeral pair and logs it loudly;
**production refuses to boot** without one. `hardening_problems()` was extracted from the
validator so that refusal is directly testable rather than only reachable by booting a
process that raises on import.

**`SECRET_KEY` is now vestigial.** After this cutover **no application code reads it** — it
is defined and validated in `config.py` and used by nothing. It is still required at
start-up, which is a trap: rotating it now changes nothing. Flagged, not removed, because
dropping a required env var is a breaking config change and CI supplies it. Decide whether
it goes or gets a use (CSRF tokens, signed URLs).

17 new tests, **408 backend tests pass**, CI green on `main` run #107, all 8 jobs.

**Also corrected** three stale rows in `REQUIREMENTS_MATRIX.md`: FR-03-03 cited
`routes/Dashboard.tsx` and `components/charts.tsx` as evidence (neither exists; the
frontend has four routes and no admin page), FR-03-07 claimed the confidence threshold was
referenced by 0 lines of app code (it is live at `services/review.py:39` and
`services/queue_service.py:65`, with 6 passing tests, and the cited config line 101 was
actually 109), and FR-03-09 still read MISSING after `audit_logs` landed.

**Failed logins stay unaudited**, confirmed: they change no state, and an unauthenticated
caller must not be able to append rows to the audit table at will. They remain in the
structured log.

**Next:** the rest of FR-05 — refresh rotation with `family_id` reuse detection, bcrypt
cost 12 exercised by a test rather than only configured, login rate limiting at 10 per 15
minutes per IP, the Redis blocklist, password complexity rules, and the reset OTP.

## 2026-09-17 — item 0: audit_logs, the precondition the other four items needed

**Sequencing call I made, and why.** The order given was FR-05 auth, OAuth, Kafka, admin.
I inserted an item 0 first: the cross-cutting rule "every state-changing operation writes
an audit_logs row, proven by a row-counting test" was unsatisfiable, and all four items add
state-changing endpoints. Building them first would mean retrofitting audit writes into
every one, with the completeness test written last against code shaped without it.

**What the audit found before anything was written** (four parallel surveys, all verified):

| Area | Reality at `340abcc` |
|---|---|
| FR-05 auth | 1 of 10 DONE-VERIFIED (FR-05-01 RBAC). HS256 not RS256; no OTP; no `family_id`; no Redis blocklist; global 120/60s rate limit, not 10/15min on login; SameSite `lax`; no password complexity rules |
| FR-05-03/04 OAuth | Nothing. No route, JWKS, columns or tests, on any branch. `hashed_password NOT NULL` actively blocks it |
| Kafka + WebSocket | Nothing. One unread config constant. The frontend polls every 5 s instead |
| FR-03 admin | FR-03-02 DONE-VERIFIED; FR-03-04/05/06/09 MISSING; FR-03-07 INCORRECT (restart-only env var); no admin frontend at all |
| audit_logs | MISSING entirely |
| PII invariant | **DONE-VERIFIED** and genuinely strong |

**Two stale rows in our own reports, corrected.** `REQUIREMENTS_MATRIX.md:71` cites
`routes/Dashboard.tsx` and `components/charts.tsx` as FR-03-03 evidence; neither file
exists. `:75` says the confidence threshold is referenced by 0 lines of app code; it is
live and evaluated on read (`services/review.py:31,39`) with 6 passing tests.

**Built (`df93491`).** `audit_logs` table, `app/services/audit.py`, `AuditContext`
dependency, and writes in all 23 state-changing endpoints.

- The completeness test enumerates the app's own route table. A new POST/PATCH/PUT/DELETE
  must be exercised or exempted with a written reason; none are exempt. It asserts
  **exactly one** row, so a duplicated write fails too.
- The row is written by the service, inside the change's transaction (`commit=False` on
  the repository call, one commit after). A rejected write leaves no row: asserted.
- Where one operation performs another as a step (assigning a doctor also starts the
  consultation; deactivating an account also ends its sessions) only the outer operation
  writes. One act, one row.
- Payloads are scrubbed through the same `_scrub` the log processors use, so a key masked
  in a log line is masked in an audit row. `hashed_password`, `password`, `jti`, `token`
  are never copied. The triage payload carries identifiers and the decision, **never the
  symptom text**.

**391 backend tests pass.** Migration is additive; its downgrade was exercised. CI green on
`main`, run #103, all 8 jobs.

**Not done, and not claimed:** no endpoint reads the audit log yet (FR-03-09's "searchable
by date, user, action" view is unbuilt), and failed logins are logged but not audited — they
change no state, and an unauthenticated caller must not be able to append rows at will.

**Flagged, not fixed:** `backend/.env` holds `SECRET_KEY=kinyamed_secret_key_2026`, which is
on the app's own placeholder blocklist. Gitignored and untracked, so nothing leaked, but
every HS256 token on that machine is signed with a known string. Moot once RS256 lands.

**Next action:** item 1, FR-05 auth. RS256 first, because it is a design change (no key
settings exist, so `jwt.encode` would fail with a raw secret) and every other FR-05 item
sits downstream of the token format.

## 2026-09-16 — CI was red for ten consecutive pushes, and I reported it green

**The finding, stated against myself.** Ten runs on `audit-p0-p1-and-frontend` failed
(`a7a8a9d`, `7ad6025`, `bdd3c5d`, `03a0bfe`, `ee89121`, `8c29a83`, `1cbc536`, `d4e3a50`,
`cfb3a4b`, `1ab2214`) on **one job**: Lint, step `ruff format --check .`. The other seven
jobs passed in every one of them. The cause was
`reports/measurements/majority_baseline.py`, added unformatted in `a7a8a9d` — the first
red run — so every commit after it inherited the failure. `1ab2214` touched only
`paper/main.tex` and was red for a violation four commits older.

**Not environmental, and that is the point.** Local ruff is 0.16.6, the version CI pins,
and `required-version` in `pyproject.toml` enforces it. Re-running the check reproduces
the failure identically. I had reported "all files formatted" several times; those reports
were of a check that did not cover the file. The runner was correct for ten runs while I
said it was not. Fixed in `acdde0a` by applying the formatter's output verbatim — no logic
change, no check weakened. Run #93 green, all 8 jobs.

**Standing rule now in force (the user's words):** after every push, check the CI result
and report it before moving on. A green local suite is not a CI result.

**Runs since:** #94 (`75f31a1`) green, #95 (`4644bd5`) green.

**What this is an instance of.** It is the same shape as the two failures the paper is
about: a fact was recorded correctly, in a machine-readable place, by a system built to
record it, and the person who needed it did not read it. The split manifest recorded 100%
leakage in a field nobody read. The CI run recorded a failing job in an API nobody queried.
Adding a third: I reported a local result as if it were the remote one. The instrument was
never the problem in any of the three.

## 2026-09-16 (later) — FR-04-07 is a row count with no seed floor, and that is the same defect as the other five

Recorded as **SRS correction A30**, which now consolidates all six numbers (A28 and A29 are folded into it).

**The finding.** The 1,000,000-example requirement was met in **130 seconds** of generation and failed the quality
gates in the same specification. The requirement constrains **rows**, a unit the machine produces for free, while
every gate that matters constrains **distinct authored seeds**, a unit only a native-speaking clinician produces.
The shortfall to FR-04-07 is therefore **19,835 seed phrases (≈ 660–990 clinician-hours)**, not 999,000 rows.

**Why it belongs with the other five.** 0.91, < 1%, the two latency targets and the 10:1 cost were each written
before anyone checked what would have to be true for them to mean something — the test-set size, the hardware, a
clinical judgement. FR-04-07 is the same act in a different place: a number with no accompanying check, satisfiable
without delivering anything the number was meant to stand for.

**The fix, stated once for all six:** a number enters the specification only with (1) a source or a named owner's
ratification, and (2) the derivation of what makes it measurable or achievable. For FR-04-07 that derivation
already exists elsewhere in the repository — **G2's floor of 3,000 distinct seeds per language** — and the row
count should follow from it, not lead it.

## Order agreed

1 fail closed → 1b make the interlock visible → 2 threshold + remove patient reassurance → 3 logger-level phone
masking + PII scan → 4 X-Forwarded-For bypass → docs commit (delete now-false fallback text) → **5 evaluation-set
specification (design only)** → stop. The red-flag layer stays deferred until `docs/clinical/` exists (L5, L16).
No new feature work after item 4.

**Item 2d was inserted "before item 4" after items 4, docs and 5 were already committed.** It was not redone or
reordered: 2d lands after `ed7063e` in history (no rewrite, L14).

## Commits of items 1–5 of the first remediation order (historical table; the branch is pushed, see top)

| Commit | Item | What |
|---|---|---|
| `fb64dc2` | 1 | fix(triage)!: fail closed when the trained model cannot classify |
| `0ab9d60` | 1b | fix(frontend): show the API's own error message instead of "Request failed" |
| `21e90fc` | 1b | fix(api): readiness reports model: false when no triage model is loaded |
| `86b61dd` | 1b | feat(frontend): blocking triage-offline alert and persistent offline banner |
| `2db26c8` | 2a | feat(triage): below the confidence threshold, require clinician review — **BROKEN AT THIS SHA: deleted `PendingResponse.tsx` (and its test) while still imported; the frontend does not build. `git bisect` will fail here — `git bisect skip` it** |
| `fed85d7` | — | revert(frontend): restore PendingResponse removed by accident in 2db26c8 |
| `e22efd8` | 2b | fix(triage)!: stop telling patients their condition can wait |
| `69576b4` | 2c | feat(frontend): intake shows the receipt, a labelled clinician hint and the review flag |
| `70fd98f` | 3a | fix(logging): mask phones, emails and names where logs are produced |
| `57edb9b` | 3b | fix(api): mask phones in responses and stop echoing PII in error bodies |
| `5d26081` | 4 | fix(security): believe X-Forwarded-For only from configured trusted proxies |
| `0e04818` | docs | docs: delete now-false descriptions of the keyword fallback and response slot |
| `6c44f67` | 5 | feat(eval): evaluation-set specification with exact power calculations |
| `87a746e` | 5 | feat(eval)!: evaluate.py is the 15-metric gate and refuses to report on too little data |
| `7de4061` | 5 | feat(annotation): local double-blind annotation tool, Cohen's kappa and gold-set builder |
| `ed7063e` | 5 | docs(protocols): D7 evaluation-set annotation protocol |
| `453e052` | 2d | fix(queue)!: cases the model could not classify sort above URGENT and ROUTINE |
| `511699b` | 2d | feat(frontend): the doctor board shows NEEDS REVIEW as its own band |
| `9ad59b5` | 2d-a11y | fix(frontend): the screen-reader announcer speaks the queue band, not the model's guess |

Only these items' files were staged. Your other uncommitted work (41 status lines, including `reports/`) is
untouched and unstaged.

## Item 1 — fail closed (`fb64dc2`)

No model, or a model that raises → `POST /api/v1/triage` returns **503**, `Retry-After: 60`, code
`TRIAGE_MODEL_UNAVAILABLE`, and a manual-triage message; **nothing is written**. The keyword classifier and its
term lists are deleted. Backend 213 passed at commit. Real uvicorn: no model → 503, rows (0, 0, 0); v2d → 201.

## Item 1b — interlock visible (`0ab9d60`, `21e90fc`, `86b61dd`)

**What the nurse sees** — captured from a real stack (uvicorn without a model, Vite, Chrome), not mocks.
Screenshots: `scratchpad/nurse_intake_503_desktop.png`, `nurse_intake_503_phone.png`,
`doctor_board_offline_desktop.png`, `doctor_board_offline_phone.png`.

- **Every screen:** a sticky bar across the top, "Automated triage offline — triage manually".
- **Intake, after submitting "sinshobora guhumeka":** a bordered alert above the form, heading
  "Automated triage is offline", body verbatim from the API: "Automated triage is unavailable. This report was not
  assessed and was not added to the queue. Triage this patient manually now; do not wait for the system."
  - It has no close button and no timeout; it was still visible after 6 s.
  - It survives a retry that is in flight; only a successful assessment clears it.
  - Focus moves to it.
  - The typed symptoms stay in the form.
  - No "Request failed" text anywhere.
- **Doctor board:** the same top banner.
- Measured in that run: `/health/ready` → `{"status":"ready","database":"ok","model":false}`;
  `POST /triage` → 503, `Retry-After: 60`; rows written (0, 0, 0).

**Evidence (executed):**
- **Red first.**
  - Backend: 6 failed.
  - Vitest: 5 failed, and the banner suite could not import.
  - Playwright: 2 failed, on the missing alert and banner.
- **Green after.**
  - Backend: **217 passed**.
  - Vitest: **98 passed** (9 files).
  - Playwright: **2 passed**.
  - `tsc -b`: 0 errors.
  - `vite build`: 78.5 KB gzip.
  - ruff: clean.
  - mypy --strict: **18** (was 19; the non-existent `app.ml.model_loader` import is gone).

**Judgement calls to check:**
- **Alert, not modal.** A modal nobody can close would also lock staff out of the queue board where manual
  triage continues. The alert blocks the intake flow visually and cannot be dismissed. Say if you want a true modal.
- **Banner on every screen, not only the doctor board.** It is mounted in `main.tsx` (above the router) because
  `Layout.tsx` and `Doctor.tsx` contain your uncommitted work. It also shows on the sign-in page.
- **The banner fails closed.** An unreachable or hanging `/health/ready` (5 s timeout) shows it. Poll interval
  is 15 s.
- **A missing model does not make `/health/ready` return 503.** Readiness gates on the database only, and
  `model` reports the triage state. If a probe removed the pod for no model, nobody could see the banner.
- **Amber, not red.** The alert uses the existing "offline" tone, keeping red for patient urgency only.
- **Playwright is not in CI.** `.github/workflows/ci.yml` holds your uncommitted edits. It needs a job with
  Chrome (`npx playwright install chrome`).
- **The Playwright spec serves a recorded 503.** A backend contract test pins that recording to
  `TriageModelUnavailableError`, so the recording cannot drift silently.

**Found, not fixed (your uncommitted files):**
- At 390 px the navigation in `Layout.tsx` runs off the right edge ("Accoun…").
- `Doctor.tsx` offers "Done" on WAITING rows, which the API rejects (noted in the audit).

**Still true after 1b:** with v2d loaded, "sinshobora guhumeka" is classified ROUTINE and the "safe to wait"
template is returned. Item 2 addresses this.

## Item 2 — threshold, and no more reassurance (`2db26c8`, `fed85d7`, `e22efd8`, `69576b4`)

**Commit error, stated:** a staged deletion from unfinished frontend work was swept into the backend-only commit
`2db26c8`, so that one commit does not build the frontend. I did not amend it (L14: no history rewriting without
you). `fed85d7` restores the files immediately after. If you want a clean bisect history, say so and I will squash
`2db26c8`+`fed85d7` before anything is pushed.

**Bisect warning (recorded 2026-09-14).** `2db26c8` is broken at that SHA: it deletes
`frontend/src/components/PendingResponse.tsx` (and its test) while `routes/Triage.tsx` still imports it, so the
frontend does not build there. `fed85d7`, the next commit, restores both files. A `git bisect` that lands on
`2db26c8` will report a false failure — mark it with `git bisect skip`.

**2a — threshold wired.** `MODEL_CONFIDENCE_THRESHOLD` (0.75) is now read. Confidence below it, or missing, sets
`requires_human_review: true` plus a `review_reason` naming score, threshold and that the score is uncalibrated,
on POST and GET `/triage` and on every `/queue` item (with `confidence_score`). It is evaluated on read against the
current threshold and **not persisted as decided** (needs the deferred migration).

**2b — patient reassurance removed, every class.** `patient_response` is now one receipt for every urgency:
"Your report has been received. Your queue number is N and you are number P in the queue. If you feel worse or this
is an emergency, go to the health centre immediately." `patient_receipt()` takes no urgency argument. The SMS sends
the same text. The urgency templates (incl. "Fata gahunda yo kureba muganga…", glossed "make an appointment")
are no longer read on any patient path; `ai_response_rw` ("Ikibazo cyawe ni ROUTINE. Uzabona muganga vuba.") and
`possible_conditions` are neither returned nor stored (NULL). Urgency and confidence remain for clinicians with
`clinician_hint_notice`.

**2c — intake screen.** "Prioritisation hint — clinicians only" section; "Needs clinician review" status with the
reason; "Message for the patient" shows the receipt captioned "The same for every patient — not a triage result.
English only". `PendingResponse` (which told staff to "tell the patient their urgency") removed.

**Evidence (executed).** Red first: 16 backend tests failed; 4 frontend failed plus an unimportable suite.
- **Weak test, disclosed.** The English banned-word test passed against the old code, because the Kinyarwanda
  "appointment" template contains no English word. The structural tests are the ones that actually fail old code:
  the message must be identical for every urgency, and no authored urgency template may reach it. I did not add a
  Kinyarwanda word list, because choosing those words needs a speaker (L16).
- **Green after.**
  - Backend: **239 passed** (full suite at `e22efd8`). The threshold-only state was checked with 112 targeted
    tests before `2db26c8`.
  - Vitest: **103 passed**.
  - Playwright: 2 passed.
  - `tsc`: 0 errors.
  - ruff: clean.
  - mypy: 18 (unchanged).
- **Real stack, v2d loaded, "sinshobora guhumeka".**
  - API: 201, `urgency_level` ROUTINE, `confidence_score` 0.598, `requires_human_review` true, reason
    "Model confidence 0.60 is below the review threshold 0.75…", `patient_response` = receipt.
  - Queue item: flag and reason present.
  - Stored `ai_response_rw` / `possible_conditions`: `(None, None)`.
  - Screenshot: `scratchpad/item2_intake_result_v2d.png`.

**Decisions / limits you should see:**
- **The review flag does not reorder the queue.** A patient the model wrongly calls ROUTINE is still sorted as
  ROUTINE. It is flagged, not escalated. Escalating flagged cases is a clinical decision (D3).
- **93% of v2d predictions fall below 0.75** (MODEL_AUDIT §5), so almost every triage will be flagged. That is
  the correct reading of this model, not a bug.
- **The receipt is English**, so the L1 requirement of an escalation instruction "in the patient's language" is
  only partly met. Translations need D4.
- **Dead code left in your uncommitted files:** `sms_service.build_triage_sms` and `services/response_templates.py`
  are no longer reached by triage. Remove them once D0 is resolved.
- **Stale frontend types:** `frontend/src/api/types.ts` still declares the retired fields. The new ones are read
  through a runtime check (`api/triageResponse.ts`) until that file is committed.

## Item 3 — PII masked where it leaves (`70fd98f`, `57edb9b`)

**Logs, structurally.**
- **structlog:** one processor, last before rendering, masks phone- and email-shaped text in every field
  (including exception text) and redacts `name`/`full_name`/`patient_name`/`phone`/`to` keys.
- **stdlib:** a filter on the root handlers and on uvicorn's loggers. Handlers matter here, because logger-level
  filters miss records propagated from libraries such as httpx.
- **Database errors:** the IntegrityError handler logs the constraint name, not the driver message that quotes
  the row.
- **Format:** phones keep their last two digits (`+**********23`).

**API, structurally.**
- A `MaskedPhone` response type on `PatientResponse.phone` and `QueueItemResponse.patient_phone`. Storage stays
  E.164.
- 422 bodies no longer echo `input`.
- `EMAIL_ALREADY_REGISTERED` no longer repeats the address.

**PII scan test (§13)** drives patient creation, registration, triage, the queue, a phone search, a 422, a 409,
an SMS password reset and a quoted-row database error. It checks every log line and error body for the fixture's
phone, name and email, and logs for any phone-shaped number. There is no Kafka producer or CSV export, so neither
is scanned; the test file says so.

**Evidence (executed).**
- Red first: the scan reported `['788555123', 'josiane.mukandayisenga@example.rw', '250788555123', '250788555124']`
  in logs before the change.
- Green after: backend **263 passed**. The PII tests passed 3 consecutive runs. ruff clean. mypy 18 (same
  error set).
- **Real uvicorn**: 36 log lines, **0 phone-shaped numbers, 0 fixture PII, 0 logging errors**.
  - Access line reads `GET /api/v1/patients?search=********23`.
  - `sms_stubbed … to=+**********24`.

**Errors I made and caught, stated:**
1. **Access logging broke.** The first stdlib filter set `record.args = None`, which broke **every uvicorn access
   line** (9 "Logging error" tracebacks). The unit tests passed; the real-server run caught it. It now keeps the
   arguments' shape, and a regression test formats a record through uvicorn's real `AccessFormatter`.
2. **The regex missed a phone at the end of a sentence** ("…on 0788123456."). Fixed and tested.
3. **The first scan flagged false positives:** example numbers in validation messages, and digits inside a random
   token. The body check was narrowed to the fixture's own PII, and the log check to phone-shaped runs.

**Limits:**
- **Names inside free text cannot be masked by pattern.** A test pins this. Names are masked by key, and
  row-quoting driver messages are no longer logged.
- **Staff screens now show masked phones everywhere**, including the intake patient picker. Staff who must call a
  patient have no reveal action yet. Adding one is a product decision; if built, it should be audited.

## Item 4 — X-Forwarded-For bypass closed (`5d26081`)

**The fix.** The limiter now keys on the TCP peer. `X-Forwarded-For` is believed only when the peer is in
`TRUSTED_PROXIES` (IPs/CIDRs, **empty by default**, documented in `.env.example`). Behind a trusted proxy, the
client is the right-most forwarded address that is not itself a trusted proxy. An invalid entry fails at start-up.

**Evidence (executed).** Red first: all 5 new tests failed.
- **Green after.**
  - Rotated header after exhaustion: **30/30 → 429**. The audit measured 30/30 accepted.
  - Two untrusted peers claiming the same forwarded address get separate buckets.
  - Behind a trusted proxy, two clients get separate buckets.
  - A client-written left-hand value cannot evade the limit.
  - A bad config is rejected.
- Backend **268 passed**. ruff clean. mypy 18 (same set).

**Not in scope, still open:**
- **No login-specific bucket.** FR-05-09's 10 per 15 min per IP does not exist; one global 120/60 s bucket
  remains.
- **Counter is per process.** It lives in memory, so N workers allow N× the limit.

## Docs commit (`0e04818`)

**Deletion only; no new claims.**
- `paper/sections/system.tex`: removes the two-implementation classifier and the keyword fallback, and the
  paragraphs describing a speaker-authored-or-pending patient response and SMS.
- `docs/protocols/d6-deployment-runbook.md`: removes the baseline from the start-up and rollback steps, and the
  `response_pending` check, whose field no longer exists.

Paper tests pass (8 passed, 2 skipped). **The paper was not compiled; `tectonic` is not installed.**

**Still false, left because it is outside the two files you named:**
- `ml_model/paper/sections/limitations.tex:127-131` ("Patient-facing text exists in two of four languages… English
  and French return an explicit pending state") no longer describes the system.
- `runbook` preconditions 3–4 (response templates) describe a path the patient message no longer uses. Their
  status cell ("0 of 24 authored") was already stale before this work.

## Item 5 — evaluation-set specification (`6c44f67`, `87a746e`, `7de4061`, `ed7063e`; design only, no data generated, no labels invented)

**Delivered:**

| # | Deliverable | Where |
|---|---|---|
| 1 | Spec with the power calculation, grid, cell minimums and justification | `reports/EVAL_SET_SPEC.md`, numbers from `ml_model/training/eval_spec.py` |
| 2 | Annotation protocol | `ml_model/docs/protocols/d7-eval-set-annotation-protocol.md` (§3 definitions and §4 clinical examples **BLOCKED**) |
| 3 | Local two-annotator tool | `ml_model/annotation/` (SQLite store, 127.0.0.1-only form, κ, adjudication, gold builder), `ml_model/scripts/compute_kappa.py` |
| 4 | `evaluate.py` rewritten as the 15-metric gate with refusals | `ml_model/training/evaluate.py`; old file moved unchanged to `training/holdout_eval.py` |
| 5 | One-page clinician brief | `reports/CLINICIAN_BRIEF.md` |

**Key numbers (computed, exact binomial, standard library):**
- **CRITICAL recall per pure language needs n ≥ 365 gold CRITICAL items** for 80% power to show the lower 95%
  bound ≥ 0.91 when true recall is 0.95. At true 0.93 it needs 1,535.
- **An observed 0.91 never clears:** at n=400 its interval is [0.878, 0.936].
- **CRITICAL→ROUTINE < 1%:** 720 CRITICAL pooled at a true 0.2% rate (368 if zero events are observed).
- **ECE needs ≥ 2,000 items.** A perfectly calibrated model scores mean ECE 0.061 at n=300 from sampling noise
  alone.
- **Set size:** test 4,900 (1,000 per pure language: 400/300/300; 150 per mixed pair) plus calibration 1,500,
  **6,400 items in all**, each labelled twice. Kinyarwanda first: 1,300.
- **κ:** ≥ 200 double-labelled items per language to report any κ; target 0.80 judged on the lower bound.

**`evaluate.py` behaviour.**
- It computes gates 1–15 plus ECE and language ID, per language where §9.2 requires it.
- Proportions use exact Clopper–Pearson and scenario-cluster bootstrap intervals; F1 and ECE use bootstrap.
- It writes an SVG reliability diagram, only at ≥ 2,000 items.
- Below the spec minimum it prints `INSUFFICIENT DATA (n=X, need Y)` and no number.
- It exits 0 only if every row is MET.
- `--writeup` and `--manifest` still dispatch to the paper pipeline, and the old names are re-exported, so
  `train_holdout.py` and the paper tests are unchanged.

**Evidence (executed).**
- **Clopper–Pearson** matches published values: 5/10 → [0.1871, 0.8129]; 0/10 → [0, 0.3085].
- **`--verify` recomputed every power-derived minimum** and caught an error of mine: I had typed 880 for gate 4;
  the derived value is 485. Fixed, and pinned by a slow test.
- **Tests:** spec 11 passed plus 1 slow; gate 18 passed; annotation 25 passed.
- **Mutation checks, done because the tests came second:**
  - removing the evaluator's refusal fails 4 tests;
  - removing "no agreement before completion" or "adjudicator must be a third person" fails the matching test.
- **Paper and label-parity tests** still pass. `train_holdout` still imports.
- **CLI smoke run on synthetic items:**
  - kappa refused before completion;
  - the gold build refused with 1 unadjudicated disagreement;
  - after adjudication, `gold_test.csv` was written with a SHA-256 manifest.
- **Full ML suite:** **182 passed, 2 skipped** (34 min, with `KINYAMED_SLOW=1`, so stored = derived minimums was checked). Backend and frontend are unchanged since item 4 (268 backend, 103 Vitest, 2 Playwright at their last runs).

**Process breach, stated:** `eval_spec.py`, `evaluate.py` and the annotation tool were written **before** their
tests, contrary to L15. I compensated with the reference values, `--verify`, and the mutation checks above. That
is not the same as red-first, and I am recording it as a breach.

**BLOCKED — documents and people needed (exact list in EVAL_SET_SPEC §11):**
- **B1** — the WHO ETAT document in the edition Rwandan facilities use. Unverified by me. To be confirmed with a
  clinician: my understanding is that ETAT is paediatric, so it may not cover adults.
- **B2** — the Rwanda MoH/RBC triage protocol and its category mapping.
- **B3** — the adult triage tool, if not ETAT.
- **B4** — RBC obstetric danger-sign guidance.
- **B5** — a lead clinician.
- **B6** — native-speaker clinicians per language (authors, 2 annotators, 1 adjudicator).
- **B7** — confirmation of whether the clinicians' institutions require ethics review.

**Decisions requested (EVAL_SET_SPEC §12):**
- **E1** — interval decision rule (stricter than a point-estimate gate).
- **E2** — pooled mixed accuracy with a 100-per-pair floor.
- **E3** — distinct-item minimums instead of "n=100,000".
- **E4** — ECE on the test set, with temperature fitted on a separate calibration split.
- **E5** — Kinyarwanda first.

**Tool gaps, stated in the protocol:** there is no command to withdraw a label (an annotator who wrote the
item), and no route to adjudicate an item both annotators agreed on (a mis-click). The coordinator logs these by
hand.

## Item 2d — flagged cases no longer sort as ROUTINE (`453e052`, `511699b`)

**The gap.** Item 2 flagged low-confidence cases but still sorted them by the class the model could not
confidently assign. Measured with v2d, "sinshobora guhumeka" = ROUTINE at 0.5977, `requires_human_review=True`,
at the bottom of the queue. Worse than stated in the brief: the doctor board's `QueueEntry` type had **no review
field at all**, so the flag was not shown on the board anywhere — only on the nurse's intake result.

**Ordering now** — four bands, arrival (`created_at`, then id) within each:
1. CRITICAL — predicted CRITICAL, **at any confidence**.
2. NEEDS REVIEW — confidence below `MODEL_CONFIDENCE_THRESHOLD` (or NULL), any other predicted class.
3. URGENT. 4. ROUTINE.

- **Judgement call:** a low-confidence CRITICAL stays in CRITICAL (flag still reported). Moving it to NEEDS REVIEW
  would demote a CRITICAL prediction, which your "CRITICAL must still outrank everything" rules out.
- One rule, two forms: `app/models/queue_band.py` — `band_for` (Python) and `band_sql` (the ORDER BY / count
  expression). The band is derived on read from stored confidence and the *current* threshold, like the flag.
- Wait estimate: NEEDS REVIEW is capped like URGENT (`_wait_for_band`).
- API: `GET /queue`, `GET /queue/{id}` add `band` and `band_label`. Positions from the triage response, the list
  and the single entry agree (tested).

**Doctor board.** Grouped by band in `QueueTable` for both layouts: cards get an `<h3>` per band; the table gets
one `<tbody>` per band opened by a `<th scope="rowgroup">`. NEEDS REVIEW's header is a solid ink-900 bar with white
text reading **"Model could not classify — review these first (n)"**; its rows have an ink edge. **Not red.** No
new colour token: the palette is closed on purpose and `tailwind.config.js` holds your uncommitted work. Inside
that band the model's class is shown as outlined neutral text "Model hint (low confidence): ROUTINE", not the
filled green badge. The Queue page's count tiles count by band (4 tiles).
- Band order and labels are generated from `QueueBand` into `frontend/src/api/queueBand.gen.ts` by
  `gen_frontend_constants.py`; `test_frontend_constants.py` fails on drift.
- **Fail safe on the client:** a row with no or an unknown `band` goes to NEEDS REVIEW (CRITICAL stays CRITICAL).
  This matters: `useSubmitTriage` inserts a row without a band until the next poll.
- `useQueue` (in your uncommitted `hooks.ts`) still sorts by urgency alone; grouping ignores the incoming order and
  uses the server's `queue_position`, so nothing in `hooks.ts`, `types.ts` or `Doctor.tsx` was touched. Fold the
  runtime-read fields into `QueueEntry` when `types.ts` is committed.

**Tests (red first: 16 backend failures, 9 frontend + 1 unloadable module).**
- `tests/integration/test_queue_bands.py` — flagged ROUTINE above confident URGENT and ROUTINE; CRITICAL outranks
  NEEDS REVIEW when it arrives later; low-confidence CRITICAL stays CRITICAL; arrival order within NEEDS REVIEW
  ignores predicted class; label text; single entry agrees with the list; the configured threshold decides
  membership; **property test** (seed 20260914, 30 random sequences of 1–10 arrivals, mixed classes and
  confidences either side of 0.75): no flagged case below an unflagged non-CRITICAL case, CRITICAL outranks all,
  bands monotone, arrival order within a band.
- The existing invariant test `test_full_triage_path.py::test_the_queue_orders_critical_before_routine` is
  **extended, not replaced**: a third, flagged patient ("sinshobora guhumeka" scripted at ROUTINE 0.598) must sit
  between CRITICAL and ROUTINE; the original priority assertion stays.
- Frontend: `queueBand.test.ts` (fail-safe, grouping, a seeded 200-sequence property test), `QueueTable.test.tsx`
  (band header precedes the flagged row which precedes URGENT/ROUTINE in both layouts; header is h3 / rowgroup;
  review band markup contains no `critical` class; hint text; no header for an empty band; band-less row goes to
  review), `Queue.test.tsx` (tiles by band), a11y test gains a review row.
- **Mutation checks:** dropping the NEEDS REVIEW clause from `band_sql` → 6 backend tests fail, including the
  property test. Client fail-safe returning the predicted class → 3 fail. Review edge coloured `critical` → 2 fail.

**Green after.** Each commit's exact tree was tested in a clean worktree (staged blobs compared byte-for-byte with
the tested files; your uncommitted `queue_repo.py` hunks were not staged and are still in your working copy):
- `453e052`: backend **238 passed**, ruff clean, mypy 15 at `ed7063e` → 15 at `453e052`.
- `511699b`: Vitest **118 passed**, `tsc -b` clean, Playwright 2 passed, generator `--check` clean,
  `test_frontend_constants.py` 9 passed.
- Working tree (with your uncommitted work): backend suite no failures; Vitest 125 passed (the extra 7 are
  spacing-scale checks over your untracked route files); mypy 18, same set as before (my first draft added a
  19th, an untyped `tuple`, fixed before commit).

**Live, v2d loaded** (`/home/marius/kinyamed-runs/model_v2d_freeze8_lr1e-5`, scratch DB `kinyamed_audit_migr`,
readiness `model: true`). Four confident ROUTINE submitted first, "sinshobora guhumeka" last:

| Position | Band | Predicted | Confidence | Queue no. |
|---|---|---|---|---|
| 1 | NEEDS_REVIEW | ROUTINE | 0.5977 | #386 (arrived last) |
| 2–5 | ROUTINE | ROUTINE | 0.8268, 0.8348, 0.8345, 0.8388 | #382–#385 |

Screenshots: `item2d_doctor_board_desktop.png`, `item2d_doctor_board_phone.png` (scratchpad). While probing for
"genuine ROUTINE" phrases, **5 of 9 candidates I tried came back flagged** (English/French/Swahili routine
requests at 0.65–0.75, one Kinyarwanda request as URGENT at 0.42) — with v2d the NEEDS REVIEW band will not be
small. They were cancelled from the demo queue so the screenshot shows what you asked for.

**Screen-reader follow-up — done in `9ad59b5`.** `QueueAnnouncer` counted by predicted urgency, so a flagged case
was spoken as "routine". It now counts with the board's own `bandOf` (same fail-safe), announces "New case the
model could not classify. Review it first." after any new critical arrival, and speaks a band change with no
change in total.
- Tests: 6 new announcer tests, 1 in the axe harness (board rerendered with a review case: announcement text and
  zero violations). Red first: 8 failed.
- Mutation: counting by `urgency_level` makes 7 tests fail.
- Verified in a clean worktree at `511699b` + the change: Vitest 125 passed, `tsc -b` clean, Playwright 2 passed.

**`reports/CURRENT_CAPABILITY.md`** (366 words, every figure from MODEL_AUDIT §3–§6 or this file). One correction to
the brief: the measured share below the 0.75 threshold is **93.4%** of test-set predictions, not "roughly half".
The NEEDS REVIEW band's share is lower, because flagged CRITICAL predictions stay in CRITICAL, and it was not
measured. The page states 93.4% flagged and does not give a band share.

## 2026-09-15 — taxonomy scope and document intake

**Finding 1, the scope defect: written up in `reports/TAXONOMY_SCOPE.md`.** Nothing was decided or built.
- docs/ENGINEERING_SPEC.md §18 cites ETAT as the basis of a 3-class taxonomy applied to all ages (age 1–120 on the form).
  You report ETAT/ETAT+ as paediatric. **The same glossary also maps the classes to ESI 1–2 / 3 / 4–5**, a
  different instrument. The specification cites two incompatible bases.
- The repo's own concept taxonomy never used ETAT. It anchors to IMCI 2014 (children under five, per the repo),
  WHO-ICRC BEC 2018 (recorded as adult-inclusive) and clinician-defined concepts. **None of those documents is in
  the repo.** The paper's anchor counts disagree with `clinical-anchors.md`, and with the paper's own table.
- The backend stores `patients.age` but triage never reads it. No scope is stated to patients or staff.
- Options set out: (a) paediatric-only, (b) adult framework only, (c) both, with age routing. Consequences are
  given for product, data, model and EVAL_SET_SPEC. Under (c), if age group is powered, the test set roughly
  doubles (about 9,800) and Kinyarwanda-first grows from 1,300 to about 2,600 items.
- **My recommendation is (a) for v1, with age group recorded on every item from the pilot so (c) stays open.
  The decision is yours:** E6 (option) and E7 (is age group powered or coverage-only).
- ETAT's actual coverage is **PENDING**: §2 of that file is a fill-in table to complete, with page citations,
  once the manual is in `docs/clinical/`.

**Finding 2, the documents: none present yet.** `kinyamed/docs/clinical/` does not exist as of this update, so no
H3–H5 item is cleared or partly cleared. When the files land, I will check each against this list and cite
section and page. I will not assume any of it in advance:

| Document you are placing | Could clear, if it contains it | Stays open regardless |
|---|---|---|
| WHO ETAT Participant Manual | H3: ETAT categories, criteria, stated age range (fills TAXONOMY_SCOPE §2) | The mapping of ETAT categories to CRITICAL/URGENT/ROUTINE (H4, needs H6). Whether ETAT applies to a text description (H6). Rwanda's ETAT+ specifically (no document listed). |
| Rwanda MoH Clinical Treatment Guidelines — Internal Medicine | Part of H4: an adult triage scheme, **only if it defines triage categories**. A treatment guideline may not. | The national triage protocol for health centres (H4) unless this is it. Paediatric content. |
| RBC guidelines index | H5: obstetric danger signs; emergency numbers; referral pathways — **only where a listed document states them** | Anything the index names but does not include in full text |

Still not started from these documents, as instructed: the red-flag layer and the lexicon. A lexicon drawn from
documents without clinician ratification is still unvalidated (H10).

**SAMU / 912.** Not hardcoded anywhere: searched `.py/.ts/.tsx/.md/.tex/.json/.csv`; the only "912" is an
unrelated phrase count in `ml_model/docs/session-state.md`. Added to the register as **H20**.

**Your uncommitted `hooks.ts` / `types.ts` (reported before touching, as asked).** Nothing was modified.
- `hooks.ts` (+237): 17 new hooks: `useMe`, `useSessions`, `useChangePassword`, `useRegister`, the analytics
  hooks (`useSummary`, `useUrgencyBreakdown`, `useQueuePerformance`, `useLanguageBreakdown`,
  `useUrgencyOverTime`, `useThroughput`, `useWaitByUrgency`), `useLogout`, `useLogoutEverywhere`,
  `useUpdateProfile`, and the password-reset trio.
- `types.ts` (+117): their response types, and `QueueStatus` gains `CANCELLED`.
- **Neither touches the queue sort.** The client-side urgency re-sort, in `useQueue` and in
  `useSubmitTriage`'s cache insert, is committed code. Item 1 can land cleanly after you commit or stash (H14).

## 2026-09-15 (later) — grammatical person of the corpus, measured

Full write-up: `TAXONOMY_SCOPE.md` §8. Script and output: `reports/measurements/grammatical_person.{py,txt}`.
E6 is **not** decided, at your instruction. Nothing clinical was decided and nothing was built.

- **The corpus is not self-report.**
  - 330,000 rows: **16.2% self-report, 83.6% about someone else, 21.3% about a child.**
  - Seed phrases: 82 self-report of 165, 78 third person, 4 carer requests, 1 unmarked.
  - n=9 test set: 16.8% self-report, 10.8% about a child (4 sentences, 2 CRITICAL).
  - Paediatric domain: 3.5% of rows, 96.2% about a child, but 9,170 of its 11,441 rows are one ROUTINE weighing
    request.
  - Obstetric: 9.9% of rows, 77.2% reported by a relative.
- **Method and error.**
  - Person is taken from the generator's structure and **agrees with the Kinyarwanda speaker's `person` ruling
    on all 165 phrases**.
  - A concord-morphology rule classifier alone is **18.9%** wrong on symptom clauses as first written, and
    **8.7%** after revision on the same data (optimistic). On whole rows it is **71.8%** wrong, because frames
    add speaker first-person.
  - Whether "umwana wanjye" (*my child*) rows describe children, and 7 other readings, need a speaker.
- **Two-thirds of carer-voice rows are person-transforms of first-person phrases**: 30.0% speaker-derived,
  36.6% machine-derived. The corpus barely contains natively written caregiver speech.
- **Survival per option:**
  - (a) 70,131 rows (21.3%), only **50 distinct acute clauses**;
  - (b) 141,934 (43.0%) certain, up to 259,869 (78.7%) if unstated ages count as adult;
  - (c) all rows, but only 212,065 (64.3%) carry an age group in the text.
- **Recommendation revised.** Do not choose E6 on corpus grounds, since the corpus fails every option
  differently. Decide on H6's two answers: can ETAT apply to text, and which adult framework is in use. Whatever
  is chosen, record **reporter** and **patient age group** as separate fields on every new evaluation item.
- **Data findings recorded, not acted on:**
  - brief/corpus mismatch: EX17's first-person phrase is in the corpus (1,141 rows) though marked
    `applies=no`;
  - 45,232 rows (13.7%) have a frame that names a child on a clause that is not about a child.
- **SRS CORRECTIONS:**
  - A24, four triage instruments cited, none in the repo.
  - A25, the paper anchor count, flagged as blocking submission.
  - **Correction to your brief:** the paper's table *does* add up to its stated 70. The error is that the 70
    includes 20 concepts defined as having no anchor, so the true anchored count is 50. My previous session's
    "the table sums to 50" was wrong wording, and `TAXONOMY_SCOPE.md` is corrected.

## 2026-09-15 — corpus rebuild specified (`reports/CORPUS_REBUILD.md`)

Measurement phase closed at your instruction; no further corpus analysis. The spec (914 words) states:
- the effective corpus is 165 authored phrases;
- 180,272 rows (54.6%) are mechanical person-transforms, and 99,136 of them start from a machine-drafted
  phrase;
- none records `validated_by`, so §10.2 is not met; the corpus is not publishable.

It proposes the replacement (not yet executable):
- ≥ 3,000 natively authored seeds per language, ≥ 30 per cell, ≥ 10 authors, none above 20%;
- per-item reporter / age / provenance metadata;
- eight build-blocking gates, G1–G8, including a hard metadata ban on machine person-transformation.

All clinical parameters are blanks naming H3/H4/H6/E6. The G3 lexical-diversity floor is blank until a native
pilot exists.

**Two corrections to your brief, both reflected in the spec:**
- **"37% of person-transformed rows were machine-transformed" needs restating.** Every person-transformed row
  was a mechanical transform (`provenance.py`). The 36.6% is the share of *third-person* rows transformed from a
  *machine-drafted* phrase; as a share of transformed rows it is 55.0%.
- **§10.2 does not ban machine output outright.** It forbids its use unless a native reviewer accepts it and
  `validated_by` is recorded, and no row records that. The spec's ban (G5) is a new, stricter rule for you to
  adopt.

**A26 added to SRS CORRECTIONS:** the concept total takes **five** values across the repo (68, 80, **126**, 127,
128), not four, with every `file:line`. The brief itself has 128 concept ids.

## 2026-09-15 — ETAT reading task: BLOCKED, the manual is not in the repository

You reported the WHO ETAT Participant Manual placed in `docs/clinical/`.
- **As of this session, `kinyamed/docs/clinical/` exists (created 06:55) and is empty.**
- No branch tracks a file under `docs/clinical/`.
- A search for ETAT-named or recently modified PDF/EPUB/DOCX files on this machine found only unrelated
  personal documents in `~/Downloads`. I did not open them.

The TAXONOMY_SCOPE §2 table therefore stays blank, nothing is stated from memory, and the modality question
(examination signs vs a verbal or written description) stays open. **Please place the file itself, e.g.
`kinyamed/docs/clinical/<name>.pdf`, and tell me.** The engineering items below do not depend on it, so they
proceeded.

## Item 1 — the client sorts nothing; the server's order is authoritative (`af643d0`, `6e81dd8`)

**Two client-side orderings, not one.**
- `useQueue` re-sorted the API response by urgency.
- `groupByBand` (my own item 2d code) then re-sorted inside each band by `queue_position` / `queue_number`.
- Both are removed.

**What changed.**
- `useQueue` returns rows exactly as the API sends them.
- The board draws a band header wherever the band changes along that order. If the server ever returned bands
  out of order, the board would show a repeated header rather than silently rearranging patients.
- The optimistic insert after a submission is spliced in at the server's `queue_position`, with the server's
  `band`.
- That needed one backend addition: `band` and `band_label` on `POST /triage` and `GET /triage/{id}`, from the
  same `band_of` that orders the queue. The client never re-derives the band rule.

**Tests, written first** (red: 1 backend, 8 frontend).
- Backend: the triage response band equals the queue list band for NEEDS_REVIEW, URGENT and a low-confidence
  CRITICAL.
- Frontend:
  - property tests that `useQueue` returns (25 sequences) and the board renders, in cards and table (40
    sequences each), **exactly the API order**;
  - `groupByBand` flattened equals its input (300 sequences, including missing and unknown bands);
  - no sort within a band;
  - a reappearing band starts a new segment;
  - the optimistic row lands at the server's position, and past-the-end appends.
- The old tests that encoded client re-ordering (fixture given in urgency order, expected re-grouped) were
  rewritten to give the API's order.
- Mutations: restoring the urgency sort in `useQueue` fails 2 tests; restoring the within-band sort fails 4.

**Green:** backend **242 passed**; ruff clean; mypy **15** (this clean branch; the old 18 counted your
uncommitted files); Vitest **132 passed**; `tsc -b` clean; Playwright 2 passed.

**Seen on your WIP branch, not touched:** its `ci.yml` change adds a PostgreSQL service to the backend job and
notes the job "never ran" without one. On this branch the backend CI job still has no database. Your fix
resolves that when merged; item 2 will not duplicate it, to avoid a conflict.

## Item 2 — Playwright in CI (`f739985`)

- **New `e2e` job** in `.github/workflows/ci.yml`:
  - `npm ci`;
  - `npx playwright install --with-deps --force chrome`. The config uses `channel: "chrome"`; `--force`
    because the runner image already ships a Chrome;
  - `npm run e2e`;
  - traces uploaded with `actions/upload-artifact@v4` on failure;
  - 15-minute timeout.
- **`forbidOnly: !!process.env.CI`** in `playwright.config.ts`: a stray `test.only` fails the run instead of
  reporting one spec green.
- **Guard test `src/__tests__/ci-e2e.test.ts`**, run by the existing frontend job. It fails if the job is removed,
  given `continue-on-error` or `|| true`, stops installing Chrome or uploading traces, or if `forbidOnly` is
  dropped. It checks the workflow text structurally, with no YAML library, since none is a direct dependency.
- **Red first:** 6 of 7 failing. **Mutations:** a planted `test.only` under `CI=true` fails with the forbidOnly
  error; renaming the job fails 5 guard tests.
- **Green:** Vitest 139 passed; `tsc -b` clean; `CI=true` Playwright 2 passed locally; the workflow parses as
  YAML with jobs `[… frontend, e2e, lint]`.
- **Not verified:** the job has not run on GitHub from here (branch not pushed). The first push will show whether
  the runner install step works as written.
- **Scope note.** The a11y tests are Vitest and already ran in the `frontend` job; what was missing from CI was
  the two Playwright specs.

## Item 3 — mypy `--strict` backlog cleared, 15 → 0 (`caada64`, `994bbdf`)

**Starting count was 15, not 18.** The 18 in the gate-exception table was measured on a working tree that held
your uncommitted files. On this branch the count was 15 from `ed7063e` onward (see item 2d and item 1 above).

**Tests first, as characterisation tests** (`caada64`). Nothing tested the code being retyped, so these pin its
behaviour. They were written alongside the fixes, not red-first. To show they test the behaviour and not the new
code, both files were run with and without the fixes, and passed each time.
- `tests/unit/test_update_validators.py`: `PatientUpdate`/`DoctorUpdate` strip text and reject blanks through the
  base models' shared validator; unnamed fields are untouched.
- `tests/integration/test_repository_rowcounts.py`: analytics `delete_by_date`/`delete_all`, refresh-token
  `revoke_all_for_user` (live sessions only) and `delete_expired` (expired only) return the rows changed.

**The fixes** (`994bbdf`), no behaviour change intended:
- `core/logging.py`: `list[structlog.typing.Processor]`.
- `core/middleware.py`: `RateLimitMiddleware` takes `ASGIApp`, as Starlette's factory protocol expects.
- `repositories/base.py`: `Select[Any]`.
- `repositories/analytics_repo.py`, `repositories/user_repo.py`: `cast(Table, Model.__table__)` and
  `cast(CursorResult[Any], ...)`. The statements are unchanged. They were not switched to ORM-enabled delete,
  which would change session synchronisation.
- `services/queue_service.py`, `services/analytics_service.py`: `dict[str, Any]`.
- `schemas/patient.py`, `schemas/doctor.py`: **type suppression, not a fix.** See the follow-up below.

**Verified 2026-09-15, after the restart, at HEAD `994bbdf`:**
- `mypy --strict app main.py` (run with `pipx run mypy --python-executable venv/bin/python`, since mypy is not
  installed in the backend venv): **"Success: no issues found in 62 source files"**.
- ruff: all checks passed.
- Backend suite: the previous session reported 250 passed. The first re-run after the restart was stopped at
  about 11 minutes because the machine was swapping, so that count is **not yet re-verified**.

**Follow-up, open: replace the `cast(Any, ...).__func__` suppression.**
- Where: `backend/app/schemas/patient.py:84–86`
  (`_strip_text = field_validator("name", "location")(cast(Any, PatientBase._strip_text).__func__)`) and
  `backend/app/schemas/doctor.py:54–56` (the same, for `"name", "specialty"`).
- Why it is a suppression: reusing the base classmethod's function through `__func__` is invisible to mypy. The
  cast only tells the checker what runtime already does.
- The real fix: one module-level strip-and-reject-blank function, applied by `field_validator` in both the base
  and update models. This changes validation code, so it needs its own test-first increment.
  `test_update_validators.py` already pins the behaviour it must keep.

**Still not enforced by CI:** `.github/workflows/ci.yml` has no mypy step (0 occurrences). Until it does, mypy is
run by hand before each backend commit, and any new error blocks that commit.

## 2026-09-15 (after the restart) — counts re-verified; ETAT manual read

**Recovery check.** The session died after `994bbdf`. On disk:
- no partial files;
- `I18N_PLAN.md` complete but uncommitted, now `23842f0`;
- STATE lacked item 3, now `7fa2099`.

**Suites, run one at a time, nothing else running:**

| Suite | Result | Time |
|---|---|---|
| Backend pytest | **250 passed**, 0 failed / skipped / errors; exit 0 | 363 s; lowest free memory 2,373 MB |
| Vitest | **139 passed** (13 files); exit 0 | 153 s |

The first backend attempt was stopped at about 11 minutes because the host was swapping with both browsers open.

**ETAT reading task: done** (`TAXONOMY_SCOPE.md` §2, every cell cited by printed and PDF page).
- **Source:** `docs/clinical/participant_manual.pdf`, WHO *ETAT Manual for participants*, © 2005, SHA-256
  `9f2c85bf…c104`.
- **Checked complete before use:** 83 PDF pages, printed pp. 1–78 all present, text extractable, three blank
  versos confirmed by rendering.
- **Age:** "all sick children". Newborns are in scope ("under two months" is a priority sign). **No upper age is
  stated.** Adults are not addressed; "adult" appears only for equipment.
- **Categories:** EMERGENCY CASES / PRIORITY CASES / NON-URGENT CASES (E / P / Q), p. 4.
- **Modality: examination-based.** "Triage is the process of rapidly examining all sick children" (p. 3). The
  emergency signs are elicited by hand and eye (capillary refill, AVPU, skin pinch). On convulsion the manual
  rules against parental history (p. 36). History from the mother is an adjunct. Only the tiny-baby age,
  poisoning and referral priority signs rest on history alone.
- **Remote or written report: not addressed.** Triage happens on arrival. There are 0 occurrences of
  telephone/phone/radio/remote/SMS/mobile. The only written item is a referral note read with the child
  present.
- **Recorded as a MODALITY mismatch (§2a), separate from age.**
  - No dataset fixes it, and no age rule fixes it.
  - The question for H6 changes: is there any validated basis for urgency from an unexamined report, and if
    not, what may a text classification claim to be?
- **Not decided:** E6, or which carer descriptions equal an ETAT sign.
- **Not built:** the lexicon and the red-flag layer.
- **Not in the file:** Rwanda (0 mentions) and ETAT+. The upper age limit and ETAT+ cells name their missing
  documents.

**Licensing flag.** The PDF is marked "© WHO 2005, All rights reserved", and `docs/clinical/` is **untracked**.
I did not commit it: committing the PDF would redistribute it if the repo is public. Whether to commit it,
gitignore it or link to it is your call.

## 2026-09-15 (later) — consequences of the ETAT finding recorded; stopped

Documentation only. No code, test, model or server ran. Nothing renamed, no wording changed; the lexicon and
red-flag layer were not built; E6 was not decided.

1. **`TAXONOMY_SCOPE.md` §2b, the construct-validity gap.**
   - No document in the repo authorises assigning urgency from a written report by someone who has not examined
     the patient.
   - ETAT requires examination (p. 3 definition; the p. 36 convulsion rule).
   - IMCI and BEC are recorded as bedside instruments **as you report them**. Neither document is in the repo, so
     this is not verified from the documents. The repo's own BEC summary is consistent with it
     (`clinical-anchors.md:15–16`, `:20`).
   - This is a gap in what the labels measure, so no dataset or model fixes it.
   - Checked: `docs/clinical/` holds only the ETAT manual, `docs/compliance/` does not exist, and no tracked file
     mentions telephone, advice-line or remote triage.
2. **SRS correction A27.**
   - The inventory script `reports/measurements/triage_wording_inventory.py` (output `.txt`) finds 895 matching
     lines in 153 files.
   - The curated list covers the spec, README, paper, staff UI strings, API strings, and clinician-, speaker- and
     externally facing documents, each with file:line. Code identifiers are counted, not listed.
   - **Patient-facing text contains no occurrence** of "triage" or ETAT. The paper has no ETAT citation; it frames
     the work as triage against ESI and MTS.
   - "Triage manually" refers to staff triaging in person, and is flagged as possibly correct as it stands.
3. **`reports/CONSTRUCT.md` (497 words), proposal only.**
   - It describes the system as queue prioritisation from a patient-authored report.
   - Proposed ground truth: a clinician's urgency judgement from the text alone.
   - It lists what that construct can and cannot support: agreement with clinicians is not accuracy against
     outcomes, and clinicians and model share blind spots.
   - It lists the D7 §3/§4/§10 and EVAL_SET_SPEC §4/§7/§9/§10/§11 changes adoption would require.
   - One correction made while drafting: the 0.75 review threshold is not an EVAL_SET_SPEC gate threshold, so it
     is not listed among the §4 changes.
4. **H6a added** to the clinical-lead questions.
   - The question: is there a validated instrument for urgency from a report without examination (for example a
     telephone or nurse-advice-line protocol), and is one in use in Rwanda?
   - If yes, it replaces ETAT as the anchor.
   - **Marked as an unverified lead.** No such system is asserted.

**Uncommitted, for your review:**
- modified: `reports/STATE.md`, `reports/TAXONOMY_SCOPE.md`;
- new: `reports/CONSTRUCT.md`, `reports/measurements/triage_wording_inventory.{py,txt}`;
- untracked: `docs/clinical/participant_manual.pdf` (© WHO, all rights reserved; not committed).

## 2026-09-15 (later) — public README corrected; CI trigger and runs #71/#72 checked; stopped

No clinical decision. Nothing renamed. `main` not touched. An earlier message's placeholder "[their answer]" was
disregarded; **no clinician has answered H6a.**

### README.md (repository root) — rewritten on this branch, uncommitted

- Every figure cites its report: CURRENT_CAPABILITY, MODEL_AUDIT §3–§6, DATASET_AUDIT §5.1/§6/§8,
  CORPUS_REBUILD §1, TAXONOMY_SCOPE §2–§2b, and this file. Claims with no report behind them were cut: the 1M-row
  corpus description, "41 tests", crash-safety anecdotes, the repository layout and the second "planned" module.
  All 7 report links were checked to resolve.
- It states: not deployed and must not be used with patients; "AI-powered medical triage" withdrawn, with no
  clinical basis in `docs/clinical/` (§2b); the corpus is 165 phrases, 54.6% person-transforms, no `validated_by`,
  not publishable; the model fails its gates on a 9-sentence test set.
- **Judgement call: the CI badge was removed, not re-captioned.** It was *accurate* for `main` (the latest run on
  `main`, #75, passed). But it covered only the four dataset/training jobs, and a green icon beside a medical
  system's title reads as more than that. CI status is described in prose instead.
- **Correction to the brief:** the badge did not say "passing" while main was red. Runs #71 and #72 failed, then
  #73, #74 and #75 on `main` all passed.
- **The public page is unchanged until this reaches `main`.** GitHub shows the default branch's README. Merging
  is yours; I did not touch `main`.
- **The README relies on a stale line elsewhere:** `CURRENT_CAPABILITY.md:46` still says `mypy --strict` is
  "currently failing". It passed with 0 errors at `994bbdf`. Listed, not edited.

### CI — `.github/workflows/ci.yml`

- **The push trigger is restricted to `main`:** `on: push: branches: [main]`, plus `pull_request` (any branch)
  and `workflow_dispatch`. Pushing `audit-p0-p1-and-frontend` without a pull request therefore triggers nothing.
  The newest run is #75, 2026-09-09, `main`.
- **`main`'s workflow has 4 jobs:** reproducibility, full 1M-row digest, training tests, hygiene. The `backend`,
  `frontend`, `e2e` and `lint` jobs exist only on this branch and **have never run on GitHub**.
- **Runs #71 (`ed02093`, 2026-09-07) and #72 (`6a7ef86`, 2026-09-08), push to `main`, both failed** in the same two
  steps. The 1M-row digest job and the hygiene job passed. The two steps both run
  `cd kinyamed/ml_model && python -m pytest -q -rs`:
  - "Reproducibility and dataset tests" → step "Dataset test suite (training tests skip without torch)";
  - "Training checkpoint tests" → step "Full test suite".
  - The public API shows only "Process completed with exit code 1". Job logs need authentication (HTTP 403), so
    **the failing test names were not seen.**
  - The project's own record, from the commit message of `3ccb014`: "Commit 6a7ef86 was pushed after running the
    backend suite and the LaTeX checker but NOT `make test-clean` … It left HEAD red: 4 failed, 112 passed. This
    commit fixes those failures." Not independently verified.
- **On `main` the failures were fixed.** #73 (`3ccb014`), #74 and #75 passed all four jobs. `ci.yml` is identical
  between `6a7ef86` and `3ccb014`, so no step was disabled to get green.
- **At this branch's HEAD** (33 commits ahead of `main`, 90 files changed under `ml_model/` and `.github/`), the same
  command was run locally with torch 2.12.0+cpu: **181 passed, 3 skipped, 0 failed**, exit 0, 1,028 s. The skips
  are `test_eval_spec.py:67` (needs `KINYAMED_SLOW=1`) and `test_paper_numbers.py:62`, `:74`.
  - **Not run locally:** that command *without* torch, as the reproducibility job does; `make verify`;
    `make check-attribution`; `make verify-full`; and the backend/frontend/e2e/lint jobs on a GitHub runner.
    Local green is not CI green.

### Proposed CI change — APPLIED 2026-09-15 (development week, item 1; see below)

```yaml
on:
  push:              # every branch (was: branches: [main])
  pull_request:      # every pull request, any base branch
  workflow_dispatch:
```

- **Test first:** add a guard to `frontend/src/__tests__/ci-e2e.test.ts` that fails while `push:` carries a
  `branches:` filter or `pull_request:` is missing. It fails now; it passes after the one-line change.
  The existing guard does not check triggers.
- **Cost, stated so you can decide:**
  - every push to any branch runs all 8 jobs, including the 1M-row regeneration (20-min limit) and training
    tests (25-min limit);
  - a branch with an open PR runs twice, once for the push ref and once for the PR merge ref, because the
    concurrency group is per ref.
  - Path filters or `branches-ignore` could trim this later. Not proposed now, because a filter is how this
    branch went unchecked.

## Development week — item 1: CI runs on every branch and pull request (uncommitted)

**What changed**
- `.github/workflows/ci.yml`: `on: push:` no longer carries `branches: [main]`. `pull_request` and
  `workflow_dispatch` are unchanged. A comment names the guard test.
- **Test first:** `frontend/src/__tests__/ci-triggers.test.ts`, 7 tests.
  - No branch, tag or path filter on `push` or `pull_request`.
  - `workflow_dispatch` present.
  - No job pinned to `main` through `github.ref`.
  - No `continue-on-error: true`.
  - All 8 gate jobs present.
- **Red first:** 1 failed (the `branches: [main]` filter), 6 passed.
- **Green:** 7/7, and 14/14 together with `ci-e2e.test.ts`.
- **Mutation:** adding `branches: [main]` under `pull_request` fails 1 test. The workflow was restored
  byte-identical (checksum compared).
- The workflow parses as YAML: `on = {push: None, pull_request: None, workflow_dispatch: None}`, 8 jobs.

**Pre-push checks, run one at a time, of what the first run on GitHub will execute**

| Check | Result |
|---|---|
| Vitest, full | **146 passed** (14 files); was 139, +7 new |
| `tsc -b` | clean |
| `npm run build` | built; JS 72.35 kB gzip |
| `make verify` | 6/6 PASS, 5.5 s |
| ML suite, with torch (earlier this session) | 181 passed, 3 skipped |
| Backend suite (earlier this session; no backend change since) | 250 passed |
| `ruff check .` / `ruff format --check .` at the repo root | **Would have failed the `lint` job.** Fixed; see below |

**Lint defect found and fixed, separate concern.** Both offenders were my own measurement scripts:
- `reports/measurements/grammatical_person.py:33` had an unused `# noqa: E402` (RUF100), and the file needed
  formatting.
- `reports/measurements/triage_wording_inventory.py` needed formatting.
- Fixed with `ruff check --fix --select RUF100` and `ruff format`. **The Python AST of both files is identical
  before and after** (hash of `ast.dump` compared), so behaviour is unchanged.
- Now: "All checks passed!" and "237 files already formatted".

**Runs #71 and #72** (unchanged from the entry above):
- Both failed in the two ML `pytest` steps. Test names are not visible without authenticated logs.
- The repo's own record says 4 tests failed; fixed on `main` by `3ccb014`.
- At this HEAD, locally with torch: 181 passed, 0 failed.
- Not run locally: the no-torch variant, `make check-attribution` as a standalone step, `make verify-full`, and
  anything on a GitHub runner.

**"Our gates have never gated" — what this fixes and what it does not**
- **Fixed:** the workflow now *runs* on every push and pull request.
- **Not fixed; needs you, not code:** a red run does not *block* anything until `main` has a branch-protection
  rule that requires these status checks before merge. That is a GitHub repository setting. It cannot be made in
  `ci.yml`, and I have no authenticated GitHub access here.
- **Still missing from CI:** `mypy --strict`. docs/ENGINEERING_SPEC.md §16 makes it a commit gate, and the backend passes it (0
  errors), but no job runs it. Proposed as a follow-up: one step in the `backend` job, with a guard test. Not done.
- **Warning seen in runs #71/#72:** Node.js 20 is deprecated for `actions/checkout@v4` and `actions/setup-python@v5`
  (forced onto Node 24). Not a failure today. Recorded only.
- **Not verified:** that the 4 never-run jobs pass on a GitHub runner. The first push will show it.

**Uncommitted on `audit-p0-p1-and-frontend`.** Proposed as separate commits:
1. `ci: run on every branch and pull request`: `ci.yml` and `ci-triggers.test.ts`
2. `style: ruff format two report measurement scripts`
3. `docs: README states only what the reports measure`: `README.md`
4. `docs(state): …`: this file

**Items 3 and 4 already exist, for planning.**
- `87a746e` built `training/evaluate.py` as the 15-metric gate that refuses on too little data, with
  `tests/test_gate_evaluate.py`.
- `7de4061` built the local double-blind annotation tool (`ml_model/annotation/`), Cohen's κ, and the gold-set
  builder, with `tests/test_annotation.py`.
- When those items come up, I will audit them against the new asks (reliability diagram, per-language cells,
  per-row confidence and timestamp) and build only the gaps.

## Development week — A: items 3 and 4 audited; gaps built; eval-set collapse recorded (uncommitted)

Test-first throughout. Each change ran only its own test file; the full ML suite runs once at the end, result
below. **No model trained. The one inference run was stopped at your instruction before it produced any
predictions.**

### Item 3 — `training/evaluate.py`: what already existed, and the defects found

**Already built** (`87a746e`):
- 15 gates with exact and scenario-cluster bootstrap intervals;
- CRITICAL recall per pure language;
- ECE, language identification and a reliability SVG;
- INSUFFICIENT DATA below the EVAL_SET_SPEC minimum;
- a non-zero exit unless every gate is MET.

**The bootstrap resamples clusters, not rows.** It draws scenario multiplicities from a multinomial
(`evaluate.py:537–541`), and a test proves clustered errors widen the interval. There was no row-bootstrap
defect in the gate.

**Defects found and fixed**

| # | Defect | Red first | Fix |
|---|---|---|---|
| 1 | **The minimum-n check counted rows.** 2,000 rows from 4 CRITICAL sentences printed CRITICAL recall **MET, [0.998, 1.000]**: the gate would have permitted a model on four sentences. A gold file without `scenario_id` was accepted, making every row its own scenario. | 2 failed | *n* counts distinct source sentences (`scenario_id`) per population. The refusal prints both counts: `INSUFFICIENT DATA (17,942 rows from 9 distinct source sentences; need 780 distinct)`. A missing `scenario_id` is REFUSED. A report header warns when a test split has more than one item per scenario (EVAL_SET_SPEC §8). |
| 2 | **`evaluate.py --model` (no `--gold`), `--writeup` and `--manifest` were forwarded to `holdout_eval.py`**, which prints metrics on the 9-sentence holdout with no refusal and applies the superseded 0.95 three-condition gate. | 4 failed | Refused with exit 2 and a pointer. `holdout_eval.py` must be run by name, and it prints "NOT A DEPLOYMENT GATE". The paper's instruction comments and the legacy docstrings now name `holdout_eval.py`. Generated `.tex` provenance headers were left as written. |
| 3 | **Pooled gates had no per-language rows** (docs/ENGINEERING_SPEC.md §16: all 15 metrics per language). | 3 failed | Gates 2, 3, 4, 6, 7 and 8 are gated per pure language, with the pooled gate's own threshold and minimum. Gates 5 and 9–12 were already per language. |
| 4 | **The red-flag suite (§16 hard gate) had no row**, so it was silently absent. | 4 failed | A `X-REDFLAG` row. NOT MEASURED without `--red-flag-report` or with 0 cases; MET only if every case passes; NOT MET otherwise; a malformed report is REFUSED. |
| 5 | **Gate 14 printed MET from `latency_v2d.json`** (warm p95 103 ms): percentiles with no interval, on an unnamed laptop. Gate 15 likewise. | 7 failed | Latency needs ≥ 1,000 per-request `samples_ms`. p50 and p95 are printed with bootstrap intervals, and MET needs both upper bounds under threshold. **Neither 14 nor 15 can be MET without `--target-hardware` matching the machine (H15).** Memory is labelled a single measurement, as the spec defines gate 15. |
| 6 | **Inference ran before any check that the gold set could support a result.** | 3 failed | `--check-gold` counts every population from the gold file alone, with no model. `--model` refuses before loading the model when no cell is measurable. |

**Specification conflict created by fix 3, for your decision (proposed E8).**
- EVAL_SET_SPEC §6 allocates 400 CRITICAL per pure language. Per-language gate 7 (CRITICAL→ROUTINE) needs 720.
- A perfect model on the designed 4,900-item test set is therefore **blocked**. Test:
  `test_the_designed_allocation_cannot_clear_per_language_critical_to_routine`.
- The options are yours: (a) enlarge the per-language CRITICAL allocation to ≥ 800 (the test set grows from
  4,900 to about 6,500); (b) gate 7 pooled only, with per-language rows reported but not gated. That would
  loosen §16, so it needs your explicit ruling.
- Not decided. The code is conservative: blocked.

**The permitted-model test now uses an allocation big enough per language** (800 / 600 / 600 per pure language).
It proves the gate can still permit.

### Item 4 — annotation tool: what already existed, and the gaps built

**Already built** (`7de4061`):
- binds to 127.0.0.1 only;
- PII rejected at import;
- opaque annotator codes; first label final;
- per-row annotator ID, label, confidence and UTC timestamp;
- a different order per annotator; nothing about agreement shown before both finish;
- adjudication by a third person;
- per-language κ with a bootstrap lower bound, refused below 200 items;
- the gold builder with digests.

**Gaps built** (8 tests red first)
- **Import rules:**
  - every item needs a `scenario_id`;
  - one test item per scenario;
  - no scenario in both splits (EVAL_SET_SPEC §8);
  - a duplicate `item_id` is refused cleanly (it was a raw `sqlite3.IntegrityError`).
- **A third label on an item is refused.** It used to be stored, then permanently block agreement with a
  misleading message.
- **The two tool gaps the D7 protocol itself named:**
  - `withdraw` keeps the label as a record, blocks further labels, excludes the item from κ and gold, and records
    count and ids in the gold manifest and the label export;
  - `request-adjudication` sends an agreed item to adjudication; the first labels still stand for κ.
  - D7 protocol §2 and §4 are updated. No "tool gap" remains.
- **Synthetic annotators end to end through the CLI:** two seeded annotators label 250 Kinyarwanda and 120
  Swahili items. The CLI's κ equals a direct computation, and Swahili is refused (n=120, need 200). **This test
  passed on first run, so it is characterisation coverage of existing behaviour, not red-first.**

### The evaluation set has the same template collapse as the training corpus

Recorded in DATASET_AUDIT §10.
- **17,942 rows from 9 distinct source sentences** (about 1,994 rows each): 4 CRITICAL (8,962 rows), 4 URGENT
  (7,793), **1 ROUTINE (1,187)**.
- `evaluate.py --gold dataset/processed/gate_n9_gold.csv --check-gold`: **0 of 45 cells measurable**, 38
  INSUFFICIENT DATA, 5 NOT KNOWN. Exit 2. Output: `reports/measurements/gate_n9_check_gold.txt`.
- `--model` on the same file refuses before loading the model.
- **The corrected interval for the recorded v2d run is: none.**
  - The gate prints no interval, because 9 distinct sentences are below every minimum. That refusal is the
    honest replacement for a number.
  - The v2d run record and the paper tables never carried an interval: `train_holdout.py` and `holdout_eval.py`
    compute none.
- **L6 finding:** MODEL_AUDIT §4.2's phrase-cluster intervals (CRITICAL recall 0.08–1.00, accuracy 0.40–0.91,
  URGENT recall 0.16–0.85) were produced by `ml_audit.py`. §9 records it as uncommitted; it is not on disk. They
  cannot be re-run.
  - They are quoted in `CURRENT_CAPABILITY.md` and in the held `README.md`.
  - Not edited. Proposed: mark them "not reproducible from the repository (MODEL_AUDIT §9)", or replace them with
  the gate's refusal.
- **Side finding:** `holdout_eval.py --manifest` reported the local v1 train split has drifted from
  `eval_manifest_phrase_v1.json`, and refused. v1 is superseded; not investigated.

### FR-04-07: the path to 1,000,000 rows — CORPUS_REBUILD §5

The target stands; no gate lowered. Arithmetic: `reports/measurements/corpus_1m_arithmetic.py` (output `.txt`).
Rates are CLINICIAN_BRIEF's **assumptions** (2–3 min to write a seed, 30–45 s to validate one).
- **What binds:** G1 (≤ 50 rows per seed) needs ≥ 20,000 native seeds. G2 needs ≥ 3,000 per language, so ≥ 30,000
  across 10 combinations, and ≥ 30 per non-empty cell. The cell count is BLANK (H4, E6) and is the largest cost
  driver.
- **Reachable:** if cells per combination are ≤ about 160 and native frames allow about 17–42 variants per seed
  without breaching the near-duplicate standard. That is 30,000–48,600 seeds from 40–100 authors, **about
  1,250–3,040 author-hours**.
- **Not reachable at realistic cost:** if §9.1's 80+ domains are crossed with reporter and age group (720–1,440
  cells: **9,000–27,000 author-hours**), or if the near-duplicate standard forces ≤ 5 variants per seed (8,300 or
  more).
- **Below about 1,875 author-hours:** the 10-combination balance cannot be met at all. The largest defensible
  corpus is then per covered combination (for example Kinyarwanda alone: 150,000 rows from 3,000 seeds), meeting
  G1–G8 there and explicitly **not** FR-04-07 or §9.1 balance.

### Verification

- Targeted suites: `test_gate_evaluate.py` + `test_annotation.py` **73 passed**.
- `ruff check` / `ruff format --check` at the repo root: clean.
- **Full ML suite, alone: 211 passed, 3 skipped, 0 failed**, exit 0, 1,264 s; lowest free memory 2,041 MB. Was
  181 passed at the start of the session; +30 new tests.
- **One more defect, found while checking the README: `scripts/gate_on_current_holdout.py` ran inference before
  the gate could refuse.**
  - It called `predict_with_model` directly.
  - Test first (`tests/test_gate_script.py`, red: "inference ran on a gold set the gate cannot measure").
  - It now runs `--check-gold` first and exits 2 without loading the model.
  - Run on the real corpus: exit 2, peak RSS 486 MB (no model), no predictions file. The gold file SHA-256 prefix
    `636b7727e428` is identical to the first build.

## E8 ruled and built; A28 added; README cut to committed-script numbers (2026-09-15)

**Full ML suite result for A** (it ran to completion, not killed): **211 passed, 3 skipped, 0 failed**, 1,264 s.
The five approved commits landed: `fed9c3d`, `9c59824`, `cebad2f`, `8787314`, `00bdc71`.

**E8 — ruled: ≥ 800 CRITICAL per pure language; CRITICAL → ROUTINE gated per language, never pooled only.**
- `training/eval_spec.py` `TEST_ALLOCATION`: 400 → **800** CRITICAL per pure language.
- `check_allocation_meets_requirements()` now also checks the per-language rows: gate 7 CRITICAL, gate 8 URGENT,
  and the F1 smallest class.
- Tests first: 4 red.
  - One passed vacuously at first, so it was rewritten to patch the allocation back to 400 and require the gate 7
    shortfall to be named. That made it red.
  - Two older gate tests hard-coded 4,900 and 400; they now derive both from `spec.TEST_ALLOCATION`.
- Green: `test_eval_spec.py`, `test_gate_evaluate.py`, `test_annotation.py`, `test_gate_script.py` **87 passed,
  1 skipped**; `test_paper_numbers.py` 6 passed, 2 skipped. These are all the test files that import the spec or
  the gate.
- **Cost**, printed by `python training/eval_spec.py --report` on CLINICIAN_BRIEF's **assumed** rates:
  - **+1,600 test items** (+3,200 labels), **84–127 clinician-hours**;
  - the set goes from 6,400 to **8,000 items** (6,500 test + 1,500 calibration), 420–633 hours in all;
  - Kinyarwanda-first goes from 1,300 to **1,700 items**, 89–135 hours.
- EVAL_SET_SPEC §5, §6, §9 and §12 updated. CLINICIAN_BRIEF's Kinyarwanda estimates updated to 1,700 items: 57–85
  h writing, 14–21 h per annotator, 4–7 h adjudication.
- **E8b, open, not decided:** per-language URGENT recall and weighted/macro F1 need 570 per pure language; the
  allocation has 300 URGENT and 300 ROUTINE.
  - The allocation check names these 8 shortfalls, so the designed set is still blocked per language on gates 2,
    3 and 8.
  - Ruling E8b (627 each) adds **+2,616 test items (test 9,116) and 137–207 clinician-hours**.
- **Not updated, historical:** `TAXONOMY_SCOPE.md` §6 still costs E6/E7 against 4,900 and 1,300. Under (c) with a
  powered age axis the figures double from the new base.

**A28 added to SRS CORRECTIONS REQUIRED.**
- CRITICAL recall ≥ 0.91 and CRITICAL → ROUTINE < 1.0% have no source and no measurability check.
- Required n from `eval_spec.py`: gate 5 needs 365 gold CRITICAL per language at a true 0.95; gate 7 needs 720 at
  a true 0.2%.
- Built and reported on: 4 CRITICAL sentences.

**README (held, not committed; diff shown in this report).**
- Every number whose script was never committed is cut:
  - every model metric and interval;
  - calibration error, 93.4%, 11 of 20, latency, and 136 of 200;
  - 360 word types;
  - 82 of 165 speaker-authored;
  - **180,272 rows / 54.6% person-transforms**.
- **Conflict with an earlier instruction:** 54.6% was required in the previous README rewrite, but no committed
  script prints it. It is cut under L6. It remains in CORPUS_REBUILD §1 and TAXONOMY_SCOPE §8 with the same
  defect.
- Kept, each with its command:
  - 330,000 rows and 165 phrases (`grammatical_person.py`);
  - regenerates from seed 42 (`make verify-full`);
  - 17,942 rows from 9 sentences, and 0 of 45 cells measurable (`evaluate.py --check-gold`);
  - backend 250, frontend 146, mypy 0.

**The same L6 defect remains in reports that are not the README (listed, not edited):**
- CURRENT_CAPABILITY and MODEL_AUDIT §3–§6 quote the uncommitted Phase 0 measurements;
- CORPUS_REBUILD §1 and TAXONOMY_SCOPE §8 quote the provenance split (180,272 / 99,136 / 81,136), which
  `grammatical_person.py` does not print.

## B — item 5a tokenizer study done (`reports/TOKENIZER_STUDY.md`)

Tokenizers only: no weights, labels or training. Each checkpoint ran alone, 121–146 s each, peak RSS ≤ 1,155 MB,
available memory never below 2,441 MB. A connection drop interrupted the report before it was written; nothing
was partial, and the findings were re-verified from `results.json` before writing.

- **Sources (§10.1, `docs/SOURCES.md`):**
  - 7 checkpoints with verified licences, each at a pinned revision.
  - Serengeti, AfriBERTa small and base, and every Kinyarwanda fine-tune found have no licence: UNVERIFIED, not
    used.
- **Five of the seven share one vocabulary.** AfroXLMR mini, base and large, and XLM-R base and large, tokenize
  identically (`06d9b09d696c…`). LaBSE differs.
- **Truncation — not a defect on current text.** AfroXLMR-mini at 128 truncates 0.0% [0.0%, 0.0%] of the 330,000
  Kinyarwanda rows. The maximum is 94 tokens, and nothing exceeds 128 under any tokenizer or source. **It must be
  re-measured on natively authored pilot items**: the corpus is slot-filled from 165 phrases.
- **Kinyarwanda fertility** under the XLM-R vocabulary is 2.52 [2.50, 2.55] tokens per word, against 1.62 [1.60,
  1.64] for LaBSE.
- **Morpheme coherence: NOT YET MEASURED.** A 60-word segmentation sheet waits for a native linguist.
- **AfriBERTa-large: NOT MEASURED.** `sentencepiece` is not installed or pinned. Proposal: pin it in
  `requirements-dev.txt`.
- **Recommended `max_length` 128** (headroom over 94), re-checked on pilot items. **Shortlist:** AfroXLMR-mini,
  AfroXLMR-base, LaBSE; AfriBERTa-large undecided until measured. Final choice after 5b and a label-dependent
  evaluation.
- **Train/serve length mismatch, not fixed.** **Correction:** this is not new. MODEL_AUDIT §2 recorded it in Phase 0 ("Mismatch, currently harmless"); the session report wrongly called it a new defect.
  - v2d was fine-tuned at `max_length` 96; the backend serves with `MODEL_MAX_LENGTH` default 512
    (`backend/app/core/config.py:105`).
  - No current text exceeds 94 tokens, so no measured number is affected.
  - Proposed fix, test first: the model directory records its training `max_length`, and the backend refuses to
    start if its setting differs.
- **Conflict:** MODEL_AUDIT §2.1's "max 88 tokens" came from the uncommitted Phase 0 script. The reproducible
  figure is 94.
- Tests: `tests/test_tokenizer_study.py` **10 passed**, red first. Ruff clean.

## Rulings applied (2026-09-15): migration SQL approved, README committed, E8b, AfriBERTa, NOT REPRODUCIBLE marks

- **README committed** (`73508b6`), as approved.
- **H21 added to the register:** the Alembic head conflict with `wip/account-analytics-frontend`, yours to resolve
  before merging.
- **E8b built** (`5254ed0`): 800 / 627 / 627 per pure language. The allocation check passes, and every
  per-language gate row is measurable on the designed set.
  - **Test set 9,116; whole set 10,616 items (21,232 labels); 557–840 clinician-hours** on assumed rates (was
    6,400 items, 336–507 hours).
  - Kinyarwanda first: 2,354 items, 124–186 hours.
  - The full cost is in one table in EVAL_SET_SPEC §6. CLINICIAN_BRIEF is updated.
  - 94 dependent tests pass.
- **`sentencepiece==0.2.2` pinned** in `ml_model/requirements-dev.txt`. **AfriBERTa-large measured** (`7cc63f9`):
  Kinyarwanda 1.66 [1.64, 1.68] tokens per word; French 2.40 [2.37, 2.43], the worst measured.
  - Shortlist is now AfroXLMR-mini, AfroXLMR-base, AfriBERTa-large, LaBSE.
  - TOKENIZER_STUDY states that every distribution describes synthetic text, and that `max_length` must be
    re-measured on natively authored pilot items.
- **NOT REPRODUCIBLE marks**, figures kept and labelled, none re-derived:
  - **MODEL_AUDIT:** a header banner, plus a mark on §1.3, §1.4, §2 (except the committed label-parity test), §2.1,
    §3, §4, §5, §6, §7 and §8, each naming `scratchpad/ml_audit.py` or `scratchpad/latency_audit.py`.
  - **CURRENT_CAPABILITY:** every model figure marked † with its script. Its stale "mypy currently failing" line
    now reads met (0 errors since `994bbdf`).
  - **CORPUS_REBUILD §1:** the row-level provenance split and the 45,232 union marked. No script, committed or in
    history, prints them; `review/provenance.py` prints phrase-level categories only.
  - **TAXONOMY_SCOPE §8:** the same, plus the adult/sister split, paediatric and other-domain aggregates, the
    14,926 and the 1,141, marked †. The rest of §8 is printed by `grammatical_person.py`.
  - A check against `grammatical_person.txt` separated reprinted-in-another-format figures (18.90%, 71.82%) from
    truly unprinted ones.
- **88 vs 94 reconciled** in MODEL_AUDIT §2.1: 88 struck through and superseded by 94. 88 was the maximum of a
  random 20,000-row sample; 94 covers all 330,000 rows with a committed script.
- **Correction to my previous report:** the 96/512 train/serve mismatch is not new. MODEL_AUDIT §2 recorded it in
  Phase 0.

## C — red-flag layer built, empty term table (`809ced8`, `447c41e`, and the C3 commit)

Test-first in three steps. **Every term in every test is fictional** ("zorblax fever", "quenthari").

1. **C1, database** (`809ced8`).
   - Migration `a7c3e9f1d2b4` runs the approved SQL verbatim. Offline SQL matches it, `alembic check` finds no drift,
     and downgrade → upgrade round-trips.
   - 9 tests prove PostgreSQL refuses: any de-escalation; a changed urgency without a trigger; a reason without a
     trigger, or a trigger without a reason.
2. **C2, lexicon** (`447c41e`).
   - `data/lexicon/red_flags.csv` has the §10.6 header and **no rows** (tested).
   - The loader rejects the whole file with line numbers on: a missing `source` or `validated_by`, a bad
     concept_id / red_flag / date, a duplicate, a row with no terms, a wrong header, or a missing file.
   - Matching is whole-word, case-, accent- and whitespace-insensitive. Only `red_flag=true` rows match.
   - The reason stores concept_ids only, cut to 200 characters.
   - 27 tests. `fold()` moved to `text_fold.py`, shared with language detection.
3. **C3, wiring.**
   - `run_triage` matches the lexicon **before** calling the model (tested order: rules, then model). It stores
     `urgency_level` = CRITICAL on a match, otherwise the model's urgency, plus `model_urgency_raw`,
     `rules_layer_triggered` and `rules_layer_reason`.
   - The route takes the lexicon as a dependency.
   - Start-up validates the lexicon and **refuses to start** on an invalid file (tested).
   - Logs record concept_ids only.
   - 14 tests:
     - **no-op proof**: with the shipped empty table, every urgency × confidence stores the model's urgency, no
       trigger, no reason;
     - a fictional match forces CRITICAL for every model answer and sorts first in the CRITICAL band;
     - **fail-closed is not bypassed**: no model → 503, nothing written;
     - **property test**: 3,000 seeded cases, where adding terms never lowers urgency and the final urgency is
       never below the model's. **This test passed on first run** (it exercises C2's functions), so it is
       characterisation coverage, not red-first.

- **Suites:** full backend suite alone **300 passed** (was 250; +50), 327 s; `mypy --strict` 0 issues in 64 files;
  ruff clean.
- **Docs:** CURRENT_CAPABILITY and README no longer say "no red-flag layer exists". They say it is built, empty, and
  escalate-only. `data/lexicon/README.md` records the rules for adding terms.
- **Open, for the lead clinician (H6):** should a red-flag match enqueue a CRITICAL from rules alone when the model is
  unavailable? Today the request fails closed and nothing is written, as before.
- **Open, not built:** the staff UI does not yet show that a case was escalated by the rules layer. The data is
  stored; the display is a follow-up.

## D — item 5b: serialisation fixed (`82bf6db`); latency and memory measured; NFR unreachable on this hardware

**Micro-batching** (`82bf6db`). Correctness came before any latency measurement.
- One worker thread owns the model. Each caller owns its request object; results are assigned by position only after
  a one-result-per-input check.
- Tests use a fake forward: 15 unit tests, red first. They cover 1,000 concurrent requests and 12 adversarial
  rounds with random jitter, batch limits, wait windows and worker counts, and results never cross. A late result
  after a timeout never reaches a later request.
- A raising or wrong-count forward fails every caller in the batch; a timeout raises `InferenceTimeoutError`.
- Mutation checks: crossed results, fail-open on error, and removing the count check are each caught.
- Stable over 5 repeated runs.
- **Fail-closed path, confirmed single:** `InferenceTimeoutError` and forward errors are caught in
  `triage_service._classify` and re-raised as `TriageModelUnavailableError`, the same 503 as item 1.
  - Service-level: `test_a_batch_error_or_timeout_fails_triage_closed[error|timeout]`.
  - HTTP-level: `test_a_batched_inference_timeout_fails_closed_through_the_same_path`, which asserts
    TRIAGE_MODEL_UNAVAILABLE, Retry-After, no detail leaked, nothing written. Characterisation; it passed on first
    run.

**Measurement** (MODEL_AUDIT §3.3; `backend/scripts/benchmark_inference.py`, tests `test_benchmark_inference.py`
red first).
- Machine: i5-6200U, 2 physical / 4 logical cores, 7.8 GB, loaded (load 2.7–4.2, Chrome), about 820 MB swap in
  use. **Not the target (H15).**
- Batching changes no result: 0 of 200 argmax disagreements.

| Concurrent | Serialised p50 / p95 (ms) | req/s | Micro-batched p50 / p95 (ms) | req/s |
|---|---|---|---|---|
| 1 | 162 [157, 167] / 305 [289, 326] | 5.58 | 171 [166, 177] / 366 [344, 385] | 5.03 |
| 10 | 1,548 [1,516, 1,576] / 2,552 [2,421, 2,616] | 5.98 | 1,015 [998, 1,026] / 1,697 [1,681, 1,955] | 9.04 |
| 50 | 9,851 [9,715, 9,921] / 13,223 [13,098, 13,309] | 5.03 | 3,694 [3,685, 3,724] / 4,988 [4,911, 5,101] | 12.8 |

- **Root cause:** a CPU ceiling, with the lock making it worse. Serialised throughput is flat at about 5–6
  requests per second. Batching gives 2.5× throughput and cuts p50 at 50 concurrent from 9.9 s to 3.7 s.
- The engine adds about 7 ms: direct forward p50 158 ms against 165 ms through the engine
  (`diagnose_inference_path.py`). The older 66 ms record differs by machine state, not code. A clean idle re-run is
  needed.
- **Verdict: p50 < 150 / p95 < 200 ms at 50 concurrent is unreachable on this hardware, at any concurrency, batched
  or not.** Recorded as **SRS correction A29, a spec defect, not a model defect.**
  - The target needs about 333 req/s at 50 in flight; measured capacity is 12.8, about 26× short.
  - The hardware reasoning in A29 is labelled unmeasured. The target was **not** tuned.
- Memory at 50 concurrent: 1,382 MB, under 2 GB, but gate 15 cannot be MET without H15.
- The gate reads the new files: gate 14 NOT MET and gate 15 NOT DEMONSTRATED, each "no target hardware named, H15".

## E — train/serve `max_length` mismatch fixed

- **Contract:**
  - `<model dir>/kinyamed_training.json` records `max_length`, read before any weights load.
  - `MODEL_MAX_LENGTH` is now optional (default `None`), so the recorded length is used.
  - A configured value that differs, or a model that records no valid length, raises `ModelConfigurationError`
    through start-up: **the service refuses to start**. It never becomes a quiet 503.
  - A missing model is unchanged: it fails closed and the service stays up.
- **Existing models:** `scripts/record_training_length.py` writes the file from the training run record's
  `args.max_length`, and refuses to overwrite a different value.
  - **Applied to v2d**, one additive file in `~/kinyamed-runs/model_v2d_freeze8_lr1e-5/`: `max_length` 96,
    sourced from `last_run_v2d_freeze8_lr1e-5.json`.
  - Resolving with the length unset gives 96; setting 512 refuses with the reason.
- `.env.example` no longer sets 512. The benchmark and diagnostic scripts resolve the length the same way.
- **Tests:** `test_training_length.py`, 15 tests, red first (14 failed). Two older `test_model_classifier.py` tests
  now write the metadata their directories need, a deliberate behaviour change.
- Backend suite **335 passed**; mypy clean. MODEL_AUDIT §2 and TOKENIZER_STUDY are marked fixed; README count
  updated.
- **For you:** your local `backend/.env` sets `MODEL_MAX_LENGTH`. It is harmless while `TRIAGE_MODEL_PATH` is unset.
  Before pointing it at v2d, remove that line or set it to 96, or start-up will refuse. Not edited by me.

## Ruling H6 (2026-09-15): a red-flag match alone does NOT create a CRITICAL when the model is unavailable

**Ruled by you: NO.** When the model is unavailable, a red-flag match does not enqueue a CRITICAL. The item 1
fail-closed path stays exactly as built: 503, nothing written, and the manual-triage instruction to staff.

**Your reasoning, as given:** the red-flag table has no clinician validation behind it. An unvalidated rule creating
CRITICAL queue entries would be a new unvalidated claim, not a safety net.

**Revisit** once a clinical lead ratifies the terms (H10).

**Already enforced:**
- `run_triage` matches the lexicon and then calls the model. A model failure raises `TriageModelUnavailableError`
  before any write, whatever the match.
- Pinned by `test_a_red_flag_does_not_bypass_fail_closed` (fictional term, no model: 503, zero `triage_results`
  rows).
- No code change.

## 5c — training pipeline, ready to run; refuses below the evaluation-set minimum (2026-09-15)

**No model was trained.** Every test uses synthetic data or a tiny randomly initialised model. Nothing below is a
measurement of any KinyaMed model.

| Commit | Component |
|---|---|
| `3d84c8b`, `fbaf42b` | Cost-sensitive loss `training/cost_loss.py`: CE + w·E_p[cost]. CRITICAL→ROUTINE must be strictly the largest cost, or the matrix is refused. The default matrix (10 / 1 / 1) is **UNSOURCED (H6)**. Synthetic test: CRITICAL→ROUTINE errors cut at least fourfold across 3 seeds. |
| `877f3a0` | Temperature scaling `training/calibration.py`: golden-section on log T, fitted on the calibration split only. ECE is identical to the gate's binning (parity test). The ECE interval resamples scenarios; the test uses repeated-sentence clusters, the n=9 shape. The reliability diagram is the gate's own. `calibration_split_shortfalls` checks the calibration allocation in distinct scenarios. |
| `9d34977`, `8ebd9ed` | Thresholds `training/thresholds.py`, tuned to CRITICAL safety. Rule: CRITICAL if p_C ≥ t_c, else URGENT if p_C + p_U ≥ t_u, else ROUTINE. Gate 5 (recall, each pure language) and gate 7 (CRITICAL→ROUTINE, pooled) are hard constraints, read from `eval_spec`. The objective is expected cost; accuracy appears nowhere, and a test shows the tuned pair is less accurate than the accuracy-maximising one. A precision or URGENT recall given up for safety is a warning naming gate 4 or 8, **with no number** (L6). |
| `9d34977` | **Gate change:** `evaluate.py` scored the argmax, so tuned thresholds would never have been the scored decision. Predictions may now carry `predicted_label`, and all classification metrics score it. ECE stays on the argmax. With no column, behaviour is unchanged; gate tests 91 passed. |
| `0bd3795`, `d88f936` | Run manifest `training/run_manifest.py`. It records seed, config, sha256 and size of every input and output, the commit and a dirty flag (tracked changes plus untracked `.py`; untracked PDFs don't count), Python and package versions, CPU/RAM, and UTC times. No username or hostname; repo-relative paths. Refused and failed runs are recorded; any unreproducible reason is listed. `verify()` re-hashes inputs and outputs. |
| `4b5fe24` | Pipeline `training/pipeline.py` + `training/configs/pipeline_default.json` (the v2d run's hyperparameters). Order: (1) test split, where every pre-inference gate cell must be SUFFICIENT (all but gate 4), and calibration split, which must meet its allocation, **else REFUSE before the corpus is read**; (2) leakage across train, calibration and test: exact normalised text, scenario_id, near-duplicate at word-3-gram Jaccard ≥ 0.85, **else REFUSE**; (3) train with the cost-sensitive loss (seed-deterministic, tested on a tiny BERT); (4) temperature and (5) thresholds on calibration only (a test shows perturbing test logits changes neither); (6) write `kinyamed_training.json` (max_length, temperature, thresholds, cost matrix), test predictions with `predicted_label` that load in the gate, `thresholds.json`, the reliability SVG, and the manifest. It prints no metric; it names `training/evaluate.py` as the next step. |
| `ef0c315` | `gate_on_current_holdout.py --check-only`: builds the n=9 gold set and prints the counts with no weights. |
| `2e05521` | `make reproduce` → `ml_model/reproduce.py`, 8 steps, each checking an exit code or diffing a committed output: sample verify, `eval_spec --verify`, 1M arithmetic, `verify --scope full`, the frozen phrase-v2 split (built in a temp dir, digest-checked, then moved; the tracked split JSON is never rewritten), grammatical person, the gate's n=9 check (**exit 2**), the pipeline's n=9 refusal (**exit 2**, `reports/measurements/pipeline_n9_refusal.txt`). Printed as not covered, each with its reason: the tokenizer study (network), latency/memory (weights H16, target CPU H15), the wording inventory (a working-tree snapshot), any quality metric (no eval set). |

**Refusal on the n=9 set, demonstrated with the committed pipeline and the real trainer class** (`pipeline_n9_refusal.txt`,
byte-identical over two runs):
- Exit 2. "17,942 rows from 9 distinct source sentences".
- 38 test-split cells INSUFFICIENT DATA; the calibration split is absent.
- "leakage check: NOT RUN (refused before the training corpus was read)"; "Nothing was trained."
- Peak RSS 250 MB; no model loaded. The manifest records status `refused`, with no `train` input.

**Tests** (each file run alone):
- `test_cost_loss` 12, `test_calibration` 11, `test_thresholds` 16, `test_run_manifest` 17, `test_pipeline` 19,
  `test_gate_script` 3, `test_reproduce` 9.
- Gate-dependent files 91 passed, 2 skipped (the existing `test_paper_numbers` placeholders).
- Ruff clean. **The full ML suite was NOT re-run** (see below).

**Faults in my own work found and fixed during 5c:**
- The first clustered-ECE test clustered independent rows, which proves nothing; it now uses repeated-sentence
  clusters.
- The first near-duplicate fixture was J = 0.846, below 0.85; it now asserts its own Jaccard, and a just-below case
  is tested.
- Threshold warnings printed interval-less point estimates (`8ebd9ed`).
- A passing pipeline run printed the gate's count table; it now prints it only on refusal.

**`make reproduce` from a clean clone: first attempts killed for low memory, then 6/8 on the environment, then 8/8
PASS.** The full record is at the top of this file.

## 5c follow-up (2026-09-15, end of day): the backend serves the recorded decision rule or refuses to start (`a8c18aa`, `16968ed`)

- **Contract** (ML side, `a8c18aa`):
  - `training/thresholds.py` `RULE` is the rule text;
  - `pipeline.training_metadata()` is the only writer of `kinyamed_training.json`;
  - `tests/fixtures/decision_rule_cases.json` holds 9 golden cases (logits, temperature, thresholds → probabilities
    and decision), generated by a committed script from `calibration.softmax` and `thresholds.decide`, each kept at
    least 1e-6 from a boundary;
  - `tests/fixtures/pipeline_training_metadata.json` pins the metadata shape;
  - `tests/test_serving_contract.py` (4) proves the fixtures match the ML code, and parses the backend constant with
    `ast`.
- **Service** (`16968ed`):
  - `read_decision_rule` runs at start-up beside `resolve_max_length`;
  - `calibrated_probabilities` runs inside the forward pass;
  - `DecisionRule.decide` runs in `classify`;
  - confidence is the probability of the class served (a CRITICAL at p = 0.25 keeps its low confidence for the
    review flag, L4);
  - **start-up is refused on:** half a rule, a non-finite or non-positive temperature, a threshold outside [0, 1],
    an unknown rule text, an unknown key, or a different label order;
  - a model recording neither (v2d) is served by argmax, which is what the gate scores without a
    `predicted_label`;
  - the benchmark scripts pass the rule too.
- **Tests:** `tests/unit/test_decision_rule.py`, **red 25 failed** with the implementation stashed. The 2 that
  passed read only fixtures or existing argmax behaviour (characterisation). **Green 27 passed.**
  - `mypy --strict` caught a missing type narrowing (`TypeGuard`), fixed.
  - Full backend **362 passed**.
- **A new cross-package test failed once, and it was the test's fault.** It text-matched the backend constant, and
  ruff had wrapped the string. It now parses the source.

## SYSTEMIC RISK, recorded 2026-09-15: a decision rule can be tuned, served, and never measured

**One risk, found twice.** The decision that reaches a patient is produced in three places that could each use a
different rule:
1. where it is **tuned** (the training pipeline: temperature and thresholds on the calibration split);
2. where it is **measured** (the deployment gate on the test split);
3. where it is **served** (the backend).

Nothing tied them together:
- **The gate scored the argmax** (`evaluate.py` `Item.pred`), so a thresholded rule would have been tuned and then
  gated as a different rule (found in 5c, fixed `9d34977`).
- **The backend read only `max_length`,** so it would have served the argmax of uncalibrated probabilities, a
  third rule that neither the tuning nor the gate had seen (fixed `16968ed`).

Either gap alone gives a gate verdict about a decision no patient receives. The same class of defect as the 96/512
`max_length` mismatch: train, measure and serve silently disagree.

**What now prevents it, end to end:**

| Link | Mechanism | Test |
|---|---|---|
| Tuned → recorded | The pipeline writes temperature, thresholds and `RULE` text into `kinyamed_training.json` through one function | `test_pipeline.py` passing run; `test_serving_contract.py` metadata shape |
| Tuned → measured | Test predictions carry `predicted_label` from the same `thresholds.decide`; the gate scores it; ECE stays on the argmax | `test_thresholds.py` gate tests; `test_pipeline.py` predictions load in the gate and match `decide` |
| Recorded → served | The service applies the record exactly, or **refuses to start** | `test_decision_rule.py` (27), incl. start-up refusal through the app lifespan |
| Served = tuned, numerically | Both implementations reproduce the same 9 golden cases, incl. a threshold overturning the argmax and a temperature alone changing the decision | `test_serving_contract.py` (ML), `test_decision_rule.py` (backend) |
| Label order | Metadata `labels` must equal `CRITICAL, URGENT, ROUTINE`; the model's `id2label` is still checked at load | `test_decision_rule.py`; `test_label_parity.py` |

**Still open:**
- No pipeline-trained model exists, so this chain has run end to end only on fakes and a tiny random model.
- The first real run must confirm, on its own artefacts, that the gate's `predicted_label` equals what the running
  service returns for the same test texts. That is one integration check, recorded here as required before any
  deploy.

## Next — single action

**H1/H6: send the ethics question and the clinician questions (H6, H6a, H6b).** Engineering follow-ups, small:
- the staff UI shows red-flag escalation;
- `mypy --strict` in CI;
- the served-vs-gated integration check on the first real model (above).

## Blocked on you (unchanged)

D0 working tree · D1 spec rulings · D2 `docs/clinical/` · D3 clinician · D4 speakers · D5 target CPU ·
D6 v2d weights location · D7 `docs/compliance/` (REMEDIATION_PLAN §0).

## GATE EXCEPTION — `mypy --strict` (docs/ENGINEERING_SPEC.md §16) — CLEARED 2026-09-15

**CLEARED by `994bbdf`: 0 errors at HEAD**, re-verified after the restart ("no issues found in 62 source
files").
- **The branch started at 15, not 18.** The 18 below was measured on a working tree that included your uncommitted
  files.
- Fifteen of the 18 rows below existed on this branch, and all 15 are fixed. The three that did not exist here are
  among rows 12–16 (`analytics_service.py`): this branch has only two of those functions
  (`build_urgency_breakdown`, `build_queue_performance`), and `994bbdf` fixed both. The other three errors are
  in your uncommitted analytics functions.
  **Merging `wip/account-analytics-frontend` will need its own mypy run.**
- Rows 17 and 18 are cleared by a type suppression that is still open (item 3, follow-up).
- mypy is still not in CI.

The record below is kept as history.

**Recorded 2026-09-14. Proposed target date to clear: 2026-09-28** (not agreed yet; set your own).

§16 says `mypy --strict` blocks every commit. It does not pass: the baseline was 20 errors at the Phase 0 audit.
Commits `fb64dc2`–`86b61dd` were made under this exception. **The gate has not quietly lapsed**, because these
terms apply until it clears:
1. **No new errors.** Every commit must leave the count ≤ the previous commit's count. Measured this session:
   20 at audit → 19 after `fb64dc2` → 18 after `21e90fc`. `0ab9d60` and `86b61dd` change no backend Python, so they
   cannot move the count.
2. The list below is the whole exception. Any error not on it blocks the commit.
3. Removing an error updates this list in the same commit.
4. mypy is **not in CI** (`ci.yml` holds your uncommitted edits). Until it is, I run it by hand before each commit.

Measured with mypy (latest from PyPI) `--strict app main.py` against the **working tree**, which includes your
uncommitted backend changes. Some of these errors are in those files (e.g. `analytics_service.py`), so the count
at HEAD alone may differ.

| # | Location | Error |
|---|---|---|
| 1 | `app/core/logging.py:23` | Missing type arguments for generic type "list" [type-arg] |
| 2 | `app/core/middleware.py:123` | `add_middleware` incompatible type `type[RateLimitMiddleware]` [arg-type] |
| 3 | `app/repositories/base.py:59` | Missing type arguments for generic type "Select" [type-arg] |
| 4 | `app/repositories/analytics_repo.py:59` | "FromClause" has no attribute "delete" [attr-defined] |
| 5 | `app/repositories/analytics_repo.py:63` | "Result[Any]" has no attribute "rowcount" [attr-defined] |
| 6 | `app/repositories/analytics_repo.py:67` | "FromClause" has no attribute "delete" [attr-defined] |
| 7 | `app/repositories/analytics_repo.py:70` | "Result[Any]" has no attribute "rowcount" [attr-defined] |
| 8 | `app/repositories/user_repo.py:89` | "Result[Any]" has no attribute "rowcount" [attr-defined] |
| 9 | `app/repositories/user_repo.py:94` | "FromClause" has no attribute "delete" [attr-defined] |
| 10 | `app/repositories/user_repo.py:100` | "Result[Any]" has no attribute "rowcount" [attr-defined] |
| 11 | `app/services/queue_service.py:172` | Missing type arguments for generic type "dict" [type-arg] |
| 12 | `app/services/analytics_service.py:62` | Missing type arguments for generic type "dict" [type-arg] |
| 13 | `app/services/analytics_service.py:83` | Missing type arguments for generic type "dict" [type-arg] |
| 14 | `app/services/analytics_service.py:102` | Missing type arguments for generic type "dict" [type-arg] |
| 15 | `app/services/analytics_service.py:119` | Missing type arguments for generic type "dict" [type-arg] |
| 16 | `app/services/analytics_service.py:129` | Missing type arguments for generic type "dict" [type-arg] |
| 17 | `app/schemas/patient.py:78` | `Callable[[str \| None], str \| None]` has no attribute `__func__` [attr-defined] |
| 18 | `app/schemas/doctor.py:49` | `Callable[[str \| None], str \| None]` has no attribute `__func__` [attr-defined] |

Cleared under this exception so far: `app/services/triage_service.py:370` [return-value] (by `fb64dc2`) and
`app/routes/v1/health.py:36` [import-not-found] (by `21e90fc`).

## Phase 0 summary (for reference)

425 tests pass (213 backend, 127 ML + 2 skipped, 85 frontend). v2d: accuracy 0.7065, CRITICAL recall 0.8504
(phrase-cluster 95% CI 0.08–1.00), ECE 0.18, Kinyarwanda only. 13 of 227 matrix rows DONE-VERIFIED. Full
detail in AUDIT_REPORT, MODEL_AUDIT, DATASET_AUDIT, REQUIREMENTS_MATRIX, REMEDIATION_PLAN.

---

## SRS CORRECTIONS REQUIRED

**Source limitation.** `docs/KinyaMed_SRS_v2_0.docx` is **not in the repository**, so I could not read it.
Every SRS claim below is quoted from the SRS requirements as consolidated in `docs/ENGINEERING_SPEC.md` (section numbers
below refer to it). Claims that appear only in the docx could not be checked and are not listed.
Every "measured" value comes from a run in this session (see the Phase 0 reports for method).

### A. Statements of fact or status that the audit contradicted

| # | SRS claim (location in `docs/ENGINEERING_SPEC.md`) | Measured / found | Correction |
|---|---|---|---|
| A1 | "Backend Phase 1 Complete (94 tests passing)" (§3) | **213** backend tests pass, 0 fail; 127 ML pass + 2 skip; 85 frontend pass; **425 total** | Replace the count. Also drop "Phase 1 Complete": §15 defines Phase 1 as JWT RS256 + Google OAuth + first/last name + password+confirm; measured HS256, no OAuth, `full_name`, no confirm on sign-up |
| A2 | CI "Unit Tests: pytest (≥ 94 tests)" (§12.1) | 213 backend tests | Update the number, or state a coverage criterion instead of a count |
| A3 | "Changes from v1.0" to the data model presented as the "v2.0 AUDITED SCHEMA" (§8, §8.1) | **Only one landed: `patients.phone` is normalised to E.164** (no `country_code` column; `users` has no phone). Live schema (`alembic upgrade head`, `alembic check` clean): `users.full_name` and `patients.name` (no first/last split); no `avatar_url/oauth_provider/oauth_id/employee_id/specialty/health_centre` on users; `consultations.diagnosis` single column, `outcome` free text; no `checked_in_at`; **no `audit_logs` table**; no `refresh_tokens.oauth_provider` | Label §8 as the *target* schema, not an audited one |
| A4 | "All 11 tables" including `audit_logs`, `model_evaluations`, `analytics_daily`, `queue_entries` (§8) | Live 11 tables: `analytics, consultations, doctors, patients, password_reset_tokens, queue, refresh_tokens, sms_logs, symptom_reports, triage_results, users`. `audit_logs` and `model_evaluations` do not exist | List the actual tables, or mark the spec tables as planned |
| A5 | ML layer "AfroXLMR-mini … thread-safe singleton" (§4.2) | 100 concurrent cold calls to `get_classifier()` ran the builder **100 times** (`lru_cache` is not a lock) | Remove "thread-safe" until fixed (REMEDIATION R1.2) |
| A6 | ML layer does "language detection, confidence scoring, multilingual response generation" (§4.2) | Language detection is a marker-word counter, not the model: KW 87.7%, SW 88.3%, mixed 33.0%. Confidence is uncalibrated softmax (ECE 0.188). Response is one language slot plus a pending state; EN 0/6 and FR 0/6 templates authored | Describe what exists |
| A7 | API gateway "Nginx + Slowapi … TLS termination" (§4.2); "Slowapi: 100 req/min … 10 auth attempts per 15 min" (§6.2) | No Nginx or TLS config (`infrastructure/` has 0 files); no Slowapi. A custom in-memory limiter at 120/60 s with no auth bucket, **bypassable via X-Forwarded-For (30/30 requests passed after exhaustion)** | Correct, or mark as planned |
| A8 | Data layer "PostgreSQL 16 + Redis 7 … queue cache, OAuth token store" (§4.2) | PostgreSQL 16 ✓. **Redis is configured but never used by application code** | Remove Redis responsibilities or mark planned |
| A9 | Event stream "Apache Kafka + FastAPI WebSocket" (§4.2) and data-flow steps 9–11 (§4.3) | **No Kafka or WebSocket code.** The dashboard polls every 5 s | Mark planned |
| A10 | Infrastructure "Docker + Kubernetes + GitHub Actions + Prometheus + Grafana" (§4.2) | GitHub Actions ✓. **No Dockerfile, K8s manifest, Prometheus or Grafana config** (`infrastructure/docker`, `kafka`, `kubernetes` are empty directories) | Mark planned |
| A11 | External services "Google OAuth 2.0 + Africa's Talking SMS + HuggingFace Hub" (§4.2) | No OAuth (deferred in `docs/roadmap.md`). No Africa's Talking client (`UnconfiguredSMSProvider` returns FAILED when enabled). HF Hub used only to download the base model | Mark planned |
| A12 | Client "React 18 + TypeScript 5 + Tailwind + Material UI v5 + Vite" with "three fully separate authenticated views" (§4.2, §7.1) | React 18.3.1, TS 5.5.4 strict, Tailwind 3.4.10, Vite 5.4.2 ✓. **MUI, Zustand, React Hook Form, Zod, Recharts, Framer Motion, Axios and Playwright are not dependencies.** One staff-operated app, no patient portal | Correct the stack list |
| A13 | "Vite 5 … tree-shaking keeps MUI bundle < 200KB gzipped" (§7.1) | No MUI. Measured bundle **77.6 KB gzip** JS + 4.2 KB CSS | Reword |
| A14 | Supported languages: all 10 combinations (§4.4), triage "in any of 10 language combinations" (§4.3 step 1) | Trained model and corpus are **Kinyarwanda only** (330,000 rows, 100% kinyarwanda). 0 of 6 code-switch pairs generate. On emergency probes, **every English, French and Swahili input was classified ROUTINE** | State "Kinyarwanda only" until other languages are trained and evaluated |
| A15 | "KinyaMed-Triage dataset (1M+ examples)" (§14); target ≥ 1,000,000 (§9.1, FR-04-07) | Trained-on corpus **330,000 rows** from **165 phrases** and **360 distinct word types**. The superseded v1 corpus is 1,000,000 machine-drafted slot-filled rows (regenerates 14/14) and is not what the model used | Replace "1M+" with the actual size and the distinct-phrase count |
| A16 | Dataset "Exceeds prior African NLP medical datasets" (§9.1) | Not supported by anything in the repo; no comparison exists. With 165 phrases, "exceeds" is not defensible on content | Remove, or cite and compare on distinct content, not rows |
| A17 | Language balance "gives ≥ 10,000 per language in the test set" (§9.1) | Test (reporting) set: **17,942 rows, Kinyarwanda only, 9 distinct sentences, 4 CRITICAL**; 0 rows in EN/FR/SW/mixed | Correct |
| A18 | Deployment gate "Overall accuracy (test set, n=100,000)" (§9.2 #1) | Reporting set n = **17,942** (9 sentences) | Correct n; report distinct sentences alongside rows |
| A19 | Duplicate rate "< 2% near-duplicate (MD5 on lowercased stripped text)" (§9.1) | MD5 measures exact, not near, duplicates: **0.000%**. MinHash Jaccard ≥ 0.85: **≥ 2.77%** within train (lower bound); the repo's own scan at 0.80: **8.71%** | Separate exact from near-duplicate and report both |
| A20 | Clinical validation "1,500-example sample reviewed by 2 registered nurses; Cohen's κ ≥ 0.80" and naturalness "≥ 3.5/5" presented as dataset standards with rationale "Medical accuracy confirmed" (§9.1) | **No review, no κ, no ratings exist.** Protocols only (`ml_model/docs/protocols/d1`, `d3`) | Remove "confirmed"; mark as pending studies |
| A21 | ETAT "WHO framework used in Rwandan health centres; basis for the 3-class taxonomy" (§18) | The repo's taxonomy cites **WHO IMCI 2014** and **WHO-ICRC Basic Emergency Care 2018**, not ETAT (`ml_model/docs/triage-taxonomy.md`, `clinical-anchors.md`). No ETAT document is in the repo. No clinician has approved the taxonomy | Correct the basis, or supply the ETAT source (D2). **Update 2026-09-15:** the WHO ETAT participant manual (2005) is now in `docs/clinical/`. It contradicts §18 on two counts: ETAT covers sick children, not adults, and it is defined on examination signs, not a reported description (`TAXONOMY_SCOPE.md` §2, §2a). |
| A22 | Fine-tuned weights at `mariusbayizere/kinyamed-afro-xlmr` (§14) | Not verified (no network check made). The only credible weights (v2d) exist **only in `~/kinyamed-runs/` on the development machine**; `ml_model/saved_model/` is a different checkpoint trained on 179 rows (accuracy 0.414) that the backend refuses to load | Do not cite the HF repo until it exists with a pinned revision |
| A23 | Model "AfroXLMR-mini + **PyTorch 2.1** + **HF Transformers** [4.40]" (§4.2, §3.1) | torch **2.12.0+cpu**, transformers **5.8.1** | Update versions |
| A24 | **Four distinct triage instruments are cited as the clinical basis across the spec and code, and none is in the repository.** (1) **WHO ETAT**, the basis of the 3-class taxonomy: `docs/ENGINEERING_SPEC.md` §18 glossary (also L5, §10.2 T1, §10.4 T1). (2) **ESI**: docs/ENGINEERING_SPEC.md §18 glossary, CRITICAL = "ESI 1–2", :915 URGENT = "ESI 3", :913 ROUTINE = "ESI 4–5"; paper `related_work.tex:16`. (3) **WHO IMCI Chart Booklet 2014**: `ml_model/docs/triage-taxonomy.md:14`, `clinical-anchors.md:11`, `licensing.md:14`, paper `related_work.tex:34`, `method.tex:116`. (4) **WHO-ICRC Basic Emergency Care 2018**: `clinical-anchors.md:10`, `licensing.md:12`, paper `related_work.tex:35`, `method.tex:117`. Also cited, not as a taxonomy basis: WHO *Managing Complications in Pregnancy and Childbirth* 2017 (`related_work.tex:36`) and the Manchester Triage System (`introduction.tex:25`). | `find` over the repo: the only PDF is `ml_model/paper/main.pdf`. **No instrument's text is available to verify any category, age range or licence claim** (the licence checks in `clinical-anchors.md` say the PDFs were read, but the PDFs were not kept). ETAT (paediatric, per your 2026-09-15 finding) and ESI are different instruments for the same three classes. `language-resources.md:12` still says IMCI booklets are CC BY-NC-SA, which `triage-taxonomy.md:23` records as wrong. | Choose one basis per population (TAXONOMY_SCOPE E6); place each cited document in `docs/clinical/`; delete citations of instruments not used |
| A26 | **The concept total has five values across the repo. One number with several values is, on its own, disqualifying at review.** **68**: `ml_model/docs/clinical-anchors.md:32` ("Of the 68 general concepts"). **80**: `ml_model/docs/triage-taxonomy.md:37` ("Of the 80 new concepts"), `licensing.md:24` ("Where the 80 concepts now stand"). **126**: `triage-taxonomy.md:8` ("126 concept slots per language"), `v2-sizing.md:185`, `utterance-form-decision.md:52`, `clinician-session-guide.md:109` ("all 126 concepts"). **127**: `licensing.md:180` and `:191` ("28 of 127 concepts"), `split-authoring.md:17`, `v2-sizing.md:141`, `session-state.md:522`, `build_english_brief.py:19`, `build_swahili_brief.py:1174`, `:1206`. **128**: paper `related_work.tex:26`, `method.tex:109`, `future_work.tex:12`; `d2-clinician-review-pack.md:98`; `swahili-authoring-brief.md:11`; `session-state.md:46`, `:445`; `build_french_brief.py:2`, `:16`; `build_swahili_brief.py:2`; `build_english_brief.py:2`; `csv_to_xlsx.py:133`. | The Kinyarwanda brief `review/speaker_brief_kinyarwanda_v2.csv` has **128 distinct `concept_id`s** (256 rows), counted 2026-09-15. Some other values are subsets (68 general, 80 new) or superseded (127 before OB13 was added 2026-09-05, per `session-state.md:46`), but the documents do not say so where the number is used. The corpus itself has **165 distinct phrases**, which is neither. | Define "concept" once. Derive the count by script from the brief. Replace or explicitly date every other occurrence. Paper submission blocked with A25. |
| A25 | **Paper clinical-anchor count — BLOCKS ANY SUBMISSION.** Stated figure: "Seventy of our 128 concepts carry an anchor" (`ml_model/paper/sections/related_work.tex:26`); "128 concepts, of which 70 carry an anchor" and table total "Anchored concepts & 70" (`method.tex:109`, `:121`). Same claim in the clinician pack: "70 of 128 concepts carry a published anchor" (`ml_model/docs/protocols/d2-clinician-review-pack.md:98`). | **Actual sum:** the four table rows are 24 + 15 + 11 + 20 = 70 (`method.tex:116–119`; `related_work.tex:34–37`). But the fourth row (20) is "Clinician-defined, no WHO anchor", so **concepts with a document anchor = 24 + 15 + 11 = 50, not 70.** Other repo counts disagree: `clinical-anchors.md:35–37` IMCI 28, BEC 18, 22 unanchored, of 68 general concepts; `licensing.md:27–30` IMCI 29, clinician-defined 23, BEC 18, MCPC 10, of 80; `licensing.md:183–188` IMCI 28, 22, BEC 18, MCPC 10, "78 anchored" of 127 (that 78 also counts the 22 as anchored). The paper (128), `licensing.md` (127, 80) and `triage-taxonomy.md` (126 slots, 80 new concepts) each state a different concept total. | Re-derive every count from `review/concepts.py` / `concept_anchors.csv` with a script; count clinician-defined concepts as unanchored; one number everywhere. **No paper submission until done.** |
| A27 | **The system is called "triage", and ETAT is cited as its basis**, across the spec, README, paper, UI, API and clinician-facing documents (inventory below). | **No document in the repo authorises assigning urgency from an unexamined written report** (`TAXONOMY_SCOPE.md` §2b). ETAT, the only instrument present, is defined on examination (manual p. 3, p. 36). The system receives text and examines nobody. **Full line inventory:** `reports/measurements/triage_wording_inventory.py` → `.txt`: 895 matching lines in 153 files, most of them code identifiers. This snapshot was taken before this A27 entry and `TAXONOMY_SCOPE.md` §2b were written. Re-running now gives 972; all 77 extra lines are in those two audit reports. **Patient-facing text contains none:** 0 occurrences in `backend/app/services/patient_message.py`, `response_templates.py` and the four `ml_model/review/speaker_brief_*_v2_responses.csv` template files. | **Listed only; no wording changed, no code renamed.** Choose the construct first (`reports/CONSTRUCT.md`, lead-clinician decision), then reword from this inventory. Uses of "triage manually" that refer to **staff** triaging in person are a different thing, and may be correct as they stand. |
| A28 | **The two hard safety thresholds were specified without checking they can be measured, and neither has a source.** CRITICAL recall ≥ 0.91 in each pure language: docs/ENGINEERING_SPEC.md §9.2 #5, FR-04-04, FR-01-07, §15, §16. CRITICAL→ROUTINE < 1.0%: L3, §9.2 #7, §16. | **Required n**, from `ml_model/training/eval_spec.py`: exact Clopper–Pearson, 80% power for the 95% bound to clear the threshold. **Gate 5 (recall ≥ 0.91), gold CRITICAL per pure language:** **365** at a true recall of 0.95 (test-verified by `test_stored_minimums_are_the_derived_ones`); 1,535 at 0.93 and 145 at 0.97 (stated in the requirement's rationale, not re-run 2026-09-15). **An observed recall of exactly 0.91 never clears, at any n.** **Gate 7 (rate < 1.0%), gold CRITICAL:** **720** at a true rate of 0.2% (test-verified); 368 if zero events are observed (`test_zero_events_in_368_bounds_a_rate_below_one_percent`); 2,470 at a true 0.5% (rationale). Per language (E8), each pure language needs its own 720. **What the SRS designed:** n = 100,000 overall (§9.2 #1, `:639`) and "≥ 10,000 per language in the test set" (§9.1, `:617`). Neither size was derived from these thresholds, and no per-class count was given. What was actually built and reported on: **4 CRITICAL sentences in Kinyarwanda, 0 in any other language** (DATASET_AUDIT §10), where gate 5 needs 365 and gate 7 needs 720 per language. **Source:** none in the repository for 0.91 or 1.0%. The earlier repo gate of 0.95 is marked "Inherited; source not verified" (`paper/generated/gate_derivation.tex:25`, `training/run_records/protocol.json:241`). See C7. | Cite a clinical source for each threshold, or have the lead clinician ratify each with a written rationale (H6). Size the test set from the ratified thresholds, as EVAL_SET_SPEC does, not the reverse. Any threshold change must re-run `eval_spec.py --verify`. Never tune a threshold to the data available.  **Folded into A30 (2026-09-16); kept for history.** |
| A29 | **The latency NFR was specified without measurement against a named hardware spec**, the same failure as A28's thresholds. docs/ENGINEERING_SPEC.md FR-04-05: inference p50 < 150 / p95 < 200 / p99 < 300 ms "on CPU-only hardware" at 50 concurrent; §6.1 ML inference p50 < 150 / p95 < 200 ms; §9.2 gate 14 p50 / p95 < 150 / < 200 ms "on CPU". The end-to-end targets at 50 concurrent share the flaw: FR-01-05 triage p95 < 250 ms; §6.1 API p50 < 200 / p95 < 350 / p99 < 500 ms. None names a CPU, core count, or arrival rate; H15 is still open. | **Measured** (MODEL_AUDIT §3.3; `backend/scripts/benchmark_inference.py`; i5-6200U, 2 physical / 4 logical cores, loaded laptop, about 820 MB swap in use). **Achievable after micro-batching** — p50 / p95 in ms, 95% intervals: **1 concurrent** 171 [166, 177] / 366 [344, 385]; **10 concurrent** 1,015 [998, 1,026] / 1,697 [1,681, 1,955]; **50 concurrent** 3,694 [3,685, 3,724] / 4,988 [4,911, 5,101]; throughput 12.8 req/s at most. **Concurrency this machine supports within p50 < 150 / p95 < 200: none measured.** Even a single serialised request missed: p50 162 [157, 167], p95 305 [289, 326]. The older record (`training/latency_v2d.json`, warm p50 66 / p95 103, one request at a time) suggests one request at a time could pass on an idle machine; that needs a clean re-run. **What the stated target would require, reasoned, not measured:** with 50 requests continuously in flight, latency ≈ 50 ÷ throughput, so p50 ≤ 150 ms needs ≳ 333 req/s. Measured capacity is 12.8, about **26× short**; on the cleaner record with the measured 2.5× batching gain it is still about 9× short. If throughput scaled linearly with physical cores (optimistic, unmeasured), that is about 18–52 physical cores of this class; alternatives such as a GPU, a smaller or distilled encoder, or INT8 quantisation are **unmeasured**. Batching does not change results: 0 argmax disagreements in 200 texts. **Not a model defect:** the limit is CPU capacity against a load figure nobody derived. | Do **not** tune the target. Decide H15 with this measurement: name the target CPU (cores, RAM) and write the NFR as an **arrival rate** a health centre actually sees (patients per minute at the busiest hour, measured), not "50 concurrent" closed-loop users. Then either choose hardware to meet the NFR at that rate, or restate the NFR for the hardware chosen, with a clinical lead ruling what latency is acceptable (H6). Re-run `benchmark_inference.py` on the named machine, idle.  **Folded into A30 (2026-09-16); kept for history.** |
| A30 | **One systemic specification failure: SIX numbers in safety-critical positions, each specified with no stated source, no derivation, and no check that it means anything measurable or achievable.** (1) **CRITICAL recall ≥ 0.91** per pure language; (2) **CRITICAL→ROUTINE < 1.0%**; (3) **latency p50 < 150 ms**; (4) **p95 < 200 ms**; (5) **the 10:1 cost of a missed CRITICAL** (added 2026-09-15); (6) **FR-04-07's 1,000,000 examples** (added 2026-09-16). Sources: ENGINEERING_SPEC L3, FR-04-04/05/07/13, §6.1, §9.1, §9.2 gates 5, 7, 14, §16. | **Each fails a different check, and the sixth shows the pattern most clearly.** 1 and 2 were never checked against the test-set size needed to measure them (A28): the set actually built has 4 CRITICAL sentences against the 365 and 720 required. 3 and 4 were never measured against any named hardware (A29); on the only machine measured they are 26x beyond capacity. 5 determines the served thresholds and has no derivation at all (H6b). 6 specifies a **row count with no minimum on distinct authored seeds**, so it is satisfiable in 130 seconds by a corpus that fails **five of the nine quality gates in the same document** (G1, G2, G5, G7, G8 on the attributed split; PRELIMINARY_RESULTS). A requirement that a machine can satisfy while every quality gate beside it fails is not a requirement about quality. | For every such number: (1) a cited source or a written ratification by the named owner (H6 clinical, H6b cost, H15 hardware); (2) the derivation of what must be true for it to be measurable — for FR-04-07, **a minimum on distinct authored seeds per language, which is what G2 already states at 3,000**, with the row count following from it rather than leading; (3) only then the gate. Never lower a number to make it pass, and never adopt one without step 2. A28 and A29 are folded into this entry. |

#### A27 inventory — where the system is *described* as triage or as ETAT-based

Curated from the script output. It covers descriptions and visible strings; code identifiers are counted, not
listed. Line numbers are as of 2026-09-15.

**Specification — `docs/ENGINEERING_SPEC.md`** (committed 2026-09-15; it keeps the source's triage wording, so these
still stand. Before that date they were cited by line number in a local, uncommitted file.)
- ETAT as basis or source:
  - §18 glossary: ETAT as the "WHO framework used in Rwandan health centres; basis for the 3-class taxonomy";
  - L5: the triage taxonomy comes from WHO materials in `docs/clinical/`;
  - §10.2 T1 and §10.4 T1 "terminology and taxonomy": "WHO ETAT".
- System named as triage:
  - the title "medical triage and patient queue system";
  - L1 "**triage prioritisation only**";
  - §4.3 "Triage data flow";
  - §4.1 "Manual triage causes a ~47-minute delay" (the problem statement, unsourced, C2);
  - §14 and §18 dataset name "KinyaMed-Triage".
- As a feature name in requirements: §4.2, §4.3, FR-01-05, §6.1 ("Triage API response"), §6.3 ("ML model not
  loaded"), §8.2 `triage_results`, §13, FR-04-03.

**Repository README — `README.md`**
- `:8` "AI-powered medical triage and patient queue system"
- `:24` "Triage endpoint"
- `:26` "Triage intake"
- `:252` "FastAPI triage service"
- `:134` "Under-triage", used as the failure-mode term

**Paper — `ml_model/paper/`.** ETAT: 0 occurrences. The paper frames the work as triage and positions it
against ESI and MTS.
- `main.tex:95` title "Kinyarwanda triage classification: results"
- `sections/abstract.tex:14–17` "Triage decides who is seen first … a classifier for three-level urgency triage
  from patient-voice Kinyarwanda"; `:46` "patient-voice triage dataset"
- `sections/introduction.tex:23–25` "Triage systems support that decision … the Emergency Severity Index, the
  Manchester Triage System"; `:30` "three-level urgency triage"; `:79` "medical triage dataset"
- `sections/related_work.tex:12–20` subsection "Triage instruments"; `:91` "patient-voice medical triage dataset"
- `sections/system.tex:45` "The triage endpoint accepts a free-text symptom description … places the patient in a
  queue ordered by clinical priority"
- `generated/results_table.tex:22` caption "Triage performance of the reported model"
- Over- and under-triage as terms: `results.tex:50`, `sections/discussion.tex:26`, `:33–34`,
  `sections/future_work.tex:64`, `sections/limitations.tex:38`, `:137`, `:144`,
  `generated/gate_derivation.tex:25`, `generated/finding_gate_degeneracy.tex:23`

**Staff-facing UI strings — `frontend/`**
- `index.html:6` page title "KinyaMed — triage"
- `src/components/Layout.tsx:6` navigation label "Triage"
- `src/components/TriageOfflineAlert.tsx:27` "Automated triage is offline"
- `src/components/TriageOfflineBanner.tsx:39` "Automated triage offline — triage manually"; the second half refers
  to staff triage
- `src/components/PatientMessage.tsx:31` "not a triage result"
- `src/__design__/main.tsx:90` "Triage view (empty form)" (design harness only)
- The e2e fixture `e2e/fixtures/triage-model-unavailable.json` mirrors the API message below

**API strings and contract — `backend/`**
- `main.py:68` OpenAPI description "AI-powered multilingual medical triage for Kinyarwanda speakers."
- `app/routes/v1/triage.py:16` path `/api/v1/triage`, OpenAPI tag "Triage"; `:36`, `:87` endpoint docstrings
- `app/core/exceptions.py:119–120` error message shown to staff: "Automated triage is unavailable … Triage this
  patient manually now"; `:122` code `TRIAGE_MODEL_UNAVAILABLE`; `:124` `manual_triage_required`; `:98`
  "Triage service error"; `:104` code `TRIAGE_NOT_FOUND`
- `app/routes/v1/health.py:54` readiness docstring "whether automated triage is available"
- Analytics response fields `total_triage_done` (`app/schemas/analytics.py:19`) and `total_triaged` (`:64`;
  model `app/models/analytics.py:31`); description "Share of all triaged cases" (`app/schemas/analytics.py:14`)
- Log text `main.py:52` and `app/services/model_classifier.py:137` "triage patients manually" (staff triage)
- Module docstrings: `app/services/triage_service.py:1` "Symptom triage."; `app/models/triage_result.py:1` "AI triage
  outcomes"; `app/core/logging.py:3` "the triage system"

**Clinician-, speaker- and externally facing documents**
- `reports/CLINICIAN_BRIEF.md:1` "a triage evaluation set"; `:16`, `:21`; `:53–54` names "the WHO ETAT document"
  as the guidance to supply
- `reports/CURRENT_CAPABILITY.md:19` "triage is refused and staff are told to triage manually"
- `ml_model/docs/invitation-to-review.md:1` "Helping build a Kinyarwanda medical triage tool"
- `ml_model/docs/moh-request.md:44` "multilingual medical triage … AI-assisted pre-screening" (a letter to the
  MoH)
- `ml_model/docs/outreach-digital-umuganda.md:30`, `:34`, `:71`, `:96` "Kinyarwanda triage corpus", "dataset for
  clinical triage", "triage taxonomy"
- `ml_model/docs/triage-taxonomy.md:1` "Triage concept taxonomy — for clinician sign-off"; `:76`
- `ml_model/docs/clinician-session-guide.md:124`
- `ml_model/docs/protocols/d7-eval-set-annotation-protocol.md:59` label source "(e.g. ETAT)"; `:66–68` B1 ETAT, B2
  triage protocol, B3 adult triage tool; `:71–72`
- `ml_model/docs/protocols/d2-clinician-review-pack.md:84` "Does fetal demise belong in a triage taxonomy"
- `ml_model/review/clinician_pack/sheet1_clinical.csv:21–22` and the speaker briefs: Kinyarwanda `:40`, `:48`,
  `:112`, `:188–189`, `:202–203`; Swahili `:186–187`; French `:102`, `:186`. These are reviewer notes
  ("belongs in the triage taxonomy", "where triage still helps").
- Project documents:
  - `ml_model/docs/roadmap.md:8` "triage classifier";
  - `ml_model/docs/STATUS.md:33`;
  - `ml_model/docs/licensing.md:96`, `:109`;
  - `ml_model/docs/clinical-anchors.md:59`;
  - `ml_model/docs/language-resources.md:18`, `:23`;
  - `docs/frontend-limitations.md:26`, `:43`, `:66`, `:68`, `:80`, `:104`.

**Audit and planning reports (mine).**
- `reports/EVAL_SET_SPEC.md:182` "national triage protocol"; `:250–252` B1–B3 ETAT and triage tools
- `reports/CORPUS_REBUILD.md:28–29`
- REQUIREMENTS_MATRIX, AUDIT_REPORT, MODEL_AUDIT and REMEDIATION_PLAN: 51 lines together. These largely quote the
  spec; see the `.txt`.

**Code identifiers (counted, not listed; renaming not proposed yet).**
- Backend source: 236 lines in 35 files. Includes the table `triage_results`, `TriageResult`, `triage_service`,
  `TRIAGE_MODEL_PATH`, and the `/api/v1/triage` path.
- Frontend source: 49 lines in 16 files.
- Tests: backend 174 lines in 20 files, frontend 54 in 8.
- Migrations: 16 lines in 2 files.
- ML code and run records: 35 lines in 12 files.
- **Renaming the table needs a migration, and renaming the path breaks the API contract. Both require your
  approval (L14).**

### B. Performance and quality stated as system behaviour, with measured values

The SRS gives these as targets. They are listed because a reader of the SRS could take them as properties of
the system. None is met where measurable.

| # | SRS statement | Measured |
|---|---|---|
| B1 | Triage end-to-end p95 < 250 ms (§4.3), API p50 < 200 / p95 < 350 / p99 < 500 ms @ 50 users (§6.1) | HTTP, v2d, 1 worker: c=1 p50 **363** / p95 **1,501** ms; c=50 p50 **34,067** ms, **136 of 200 → HTTP 503** (DB pool exhausted). Host was swapping |
| B2 | Inference p50 < 150 / p95 < 200 ms CPU (§6.1, FR-04-05) | In-process c=1 p50 **132** / p95 **217** ms; c=10 p50 **1,566** ms; c=50 p50 **7,939** ms (single inference lock). Repo record on the same CPU: p50 66 / p95 103 ms warm, cold 1,341 ms |
| B3 | Memory < 2 GB @ 50 concurrent (§9.2 #15) | **1,416 MB** server high-water mark — met |
| B4 | Overall accuracy ≥ 87% (FR-01-07) / ≥ 82% (§9.2) | **0.7065** |
| B5 | CRITICAL recall ≥ 0.91 in each pure language | Kinyarwanda **0.8504** (phrase-cluster 95% CI 0.077–1.000); EN/FR/SW not measurable |
| B6 | CRITICAL→ROUTINE < 1.0% | 0.00% on 4 CRITICAL sentences (not evidence); **11 of 20** emergency probe inputs → ROUTINE |
| B7 | Weighted F1 ≥ 0.83 / Macro F1 ≥ 0.80 / CRITICAL precision ≥ 0.88 / CRITICAL F1 ≥ 0.89 / URGENT recall ≥ 0.86 | **0.6953 / 0.7724 / 0.6633 / 0.7453 / 0.4963** |
| B8 | Kinyarwanda accuracy ≥ 80% | **0.7065** |
| B9 | Language detection ≥ 92% pure / ≥ 85% mixed (FR-01-06, FR-04-08) | KW **87.7%**, SW **88.3%**, EN 100%, FR 100%, mixed **33.0%** (on generated v1 text) |
| B10 | ECE ≤ 0.05; 0.75 review threshold meaningful (§9.2, FR-04-03) | ECE **0.179** (stopping split), **0.188** (reporting); **93.4%** of predictions are below 0.75 |
| B11 | "ML model not loaded → 503 … manual triage mode" (§6.3) | Before today: silently served a keyword matcher (CRITICAL recall 0.057). **After increment 1 item 1 (uncommitted): 503 + Retry-After + manual-triage instruction, verified** |
| B12 | "No PII in logs" (§6.2, L11) | **336** log lines with a full phone number in a 501-request run; queue API returns phones unmasked (fix = increment 1 item 3) |

### C. Figures with no source anywhere in the repository (verify and cite, or remove)

I did not check these against external sources (L16). They are listed because nothing in the repo supports
them and a reviewer will ask.

| # | Claim | Status |
|---|---|---|
| C1 | "1 doctor per ~14,000 patients (WHO minimum 1:1,000)" (§4.1) | no citation in repo |
| C2 | "Manual triage causes ~47-minute delay before urgency assessed" (§4.1) | no citation in repo |
| C3 | "93%+ speak Kinyarwanda"; "14M+ Rwandans" (§4.1, §4.4) | no citation in repo |
| C4 | "40%+ of rural patients lack smartphone or reliable data" (§4.1) | no citation in repo |
| C5 | "AfroXLMR … pre-trained on 17 African languages (Alabi et al., 2022)" (§18) | not verified; no `docs/SOURCES.md` |
| C6 | Rwanda data-protection law reference (repo cites Law 058/2021, `docs/roadmap.md`) | not verified (L10, D7) |
| C7 | Clinical threshold CRITICAL recall 0.91 (SRS) vs 0.95 (repo, marked "source unverified") | neither sourced; needs a clinician (D3) |

---

## BLOCKED ON HUMAN INPUT

Recorded 2026-09-14. **Nothing below can be engineered around.** Each needs a document, a person or a decision.
Sources: REMEDIATION_PLAN §0 (D0–D7), EVAL_SET_SPEC §11–12 (B1–B7, E1–E5), MODEL_AUDIT, and this file.

### Before contacting anyone

| # | What | Needs exactly | Who supplies | Blocks downstream |
|---|---|---|---|---|
| H1 | Ethics for the clinician work (B7) | Written answer from each clinician's institution: does authoring and labelling **invented** vignettes need ethics review or management approval? | Clinicians' institutions (research office / medical director) | Engaging any clinician (H6–H9) |
| H2 | Real-patient approval (D7) | Rwanda NHRC/IRB approval and the current data-protection instrument, verified (the repo cites Law 058/2021; unverified), placed in `docs/compliance/` | You, with NHRC / institutional IRB | Any real-patient data, prospective validation, deployment |

### Clinical documents — for `docs/clinical/`, full text, not summaries

| # | What | Needs exactly | Who supplies | Blocks downstream |
|---|---|---|---|---|
| H3 | WHO ETAT (B1) | **Partly cleared 2026-09-15.** The WHO 2005 participant manual has been read (`TAXONOMY_SCOPE.md` §2): children only, no upper age stated, examination-based, no remote triage. **Still needed:** the edition actually used in Rwandan facilities (the manual does not mention Rwanda), the ETAT+ materials, and a source for the upper age limit. Whether text can carry any ETAT sign is now an H6 question (§2a). | Lead clinician / RBC | Label definitions (D7 protocol §3); presentation types |
| H4 | National triage protocol (B2, B3) | MoH/RBC triage protocol for health centres and district hospitals, adult and paediatric, **with its mapping to CRITICAL/URGENT/ROUTINE**; the adult tool if not ETAT | Lead clinician / RBC / MoH | Domain axis of the eval grid; category mapping; clinical lexicon (§10.6); red-flag layer content (L2) |
| H5 | Obstetric guidance and referral data (B4, D2) | RBC maternal/obstetric danger signs; emergency numbers; referral pathways | RBC / lead clinician | Obstetric presentation type; any patient text beyond the generic escalation line |

### People

| # | What | Needs exactly | Who supplies | Blocks downstream |
|---|---|---|---|---|
| H6 | Lead clinician (B5, D3) | Approve the category mapping and worked examples (≥2 per label, ≥3 boundary pairs per line). Ratify the unsourced numbers: CRITICAL recall 0.91 (old charter 0.95), CRITICAL→ROUTINE < 1%, **review threshold 0.75**. Ratify the 2d design: NEEDS REVIEW above URGENT; low-confidence CRITICAL stays CRITICAL. Rule on the taxonomy pack `ml_model/docs/protocols/d2-clinician-review-pack.md` (e.g. is an unstoppable nosebleed CRITICAL?) | A registered clinician practising in Rwanda | Protocol §3–4; the pilot; every gate verdict; the queue design's clinical basis |
| H6a | Lead clinician: **is there a validated report-based urgency instrument?** (added 2026-09-15) | **Question:** does any **validated** instrument exist for assigning urgency from a symptom report **without examination**, for example a telephone or nurse-advice-line triage protocol? **Is any such protocol in use in Rwanda?** If yes, the document itself, cited by section and page and placed in `docs/clinical/`, with its validation evidence and its population (age range). **If yes, that instrument replaces ETAT as the clinical anchor.** **UNVERIFIED LEAD:** the example is yours, not a finding. I have not verified that any such instrument exists, is validated, or is used in Rwanda, and nothing in the repo mentions one (`TAXONOMY_SCOPE.md` §2b). Do not cite one until the document is in hand (L5, L16). | Lead clinician (H6); RBC / MoH (H4) | The clinical anchor for labels (D7 §3); whether `reports/CONSTRUCT.md` is needed at all or is superseded by that instrument; E6; A27 rewording |
| H6b | Lead clinician: **what relative cost should a missed CRITICAL carry against a false alarm?** (added 2026-09-15) | **Question:** how many false CRITICAL alerts (a non-critical patient escalated, a staff interruption) is it acceptable to raise to avoid missing one true CRITICAL (sent to ROUTINE)? And how do URGENT↔ROUTINE and URGENT↔CRITICAL errors compare? **This is a clinical judgement about alert fatigue versus missed emergencies, not an engineering constant.** The answer should come with its reasoning, and should say whether it differs by setting (health centre or hospital) or age group. **Current state:** CRITICAL→ROUTINE costs 10.0 and every other error 1.0 (`training/cost_loss.py`), UNSOURCED (A30). Only the ordering (a missed CRITICAL is the worst error) is required by docs/ENGINEERING_SPEC.md L3. No number is proposed here: I will not suggest one. | Lead clinician (H6), ideally with the nurses who will receive the alerts | The cost matrix (training objective and threshold choice); every served decision of a pipeline-trained model (A30); the review-load estimate for staff |
| H7 | Kinyarwanda clinicians (B6, D4) — first | Authors for about 1,300 items. Two annotators (about 11–16 h each, estimated). One adjudicator. Nobody labels their own items. | Native-speaker clinicians (see CLINICIAN_BRIEF) | Kinyarwanda test set, κ, gates 5 (KW) and 9, calibration, and any retraining (R5) |
| H8 | EN / FR / SW clinicians (B6, D4) | The same roles per language. Swahili needs TZ and KE variants. | Native-speaker clinicians | Gates 5 (EN/FR/SW) and 10–12. §16's hard gate needs all four. |
| H9 | Bilingual raters per mixed pair (D4) | Authors and annotators for 6 code-switch pairs; naturalness ratings ≥ 2 raters per pair | Bilingual speakers of each pair | Gate 13; the code-switching claim |
| H10 | Lexicon and red-flag validators | T1 validation of lexicon rows with colloquial variants. Validation of the 20 audit probe phrases (now `validated_by=NONE`). | Native-speaker clinicians (H6–H8) | L2 red-flag layer (R1.3); red-flag safety suite 100% gate |
| H11 | Patient receipt translations | KW / FR / SW versions of the receipt and escalation line (`backend/app/services/patient_message.py`, English only), speaker-authored or speaker-approved | Native speakers; clinician check on the escalation wording | Patients who do not read English |

### Decisions only you can make

| # | What | Needs exactly | Blocks downstream |
|---|---|---|---|
| H12 | E1–E7 (EVAL_SET_SPEC §12, TAXONOMY_SCOPE §6) | Yes/no on each: E1 interval decision rule; E2 pooled mixed accuracy with per-pair floor; E3 distinct-item minimums instead of n=100,000; E4 ECE on the test set, temperature fitted on the calibration split; E5 Kinyarwanda first; **E6 scope option (a) paediatric only / (b) adult only / (c) both with age routing; E7 under (c), age group powered or coverage-only** | Freezing the spec; quota sheets for authors (H7); every protocol §3 definition |
| H13 | Governing spec (D1) | A ruling on the 9 conflicts (a)–(i) between the old ml_model charter file and `docs/ENGINEERING_SPEC.md` v2.0. Also: 87% vs 82% accuracy, and 13px vs 14px minimum text. | R1.3, R3, R5–R7; schema and auth work |
| H14 | Your uncommitted work (D0) | Commit or stash your 19 modified files, 1 deleted file and untracked files (`queue_repo.py`, `hooks.ts`, `types.ts`, the password-reset migration, CI). | Folding the band fields into `QueueEntry`; putting mypy in CI (`ci.yml`); clean commits |
| H15 | Target CPU (D5) | Cores, RAM, whether shared | Gates 14–15 verdicts |
| H16 | v2d weights (D6) | Publish with pinned revision and SHA-256, or keep private and document where | `make reproduce`; model card; paper reproducibility |
| H17 | mypy exception date | Agree or replace the proposed 2026-09-28 | §16 commit-gate compliance |
| H18 | History before push | Squash `2db26c8`+`fed85d7` (history rewrite, needs your explicit yes, L14) or leave with the bisect note | Pushing the branch |
| H19 | SRS document | Apply "SRS CORRECTIONS REQUIRED" to `KinyaMed_SRS_v2_0.docx` (not in repo; a copy sits in `~/Downloads`, not opened by me). **Add: §18 cites both ETAT (paediatric, per your finding) and ESI as the basis of the same 3 classes.** | Anyone reading the SRS |
| H21 | **Alembic head conflict before merging `wip/account-analytics-frontend`** (recorded 2026-09-15; yours to resolve) | That branch's `f1a2b3c4d5e6_add_password_reset_tokens.py` and this branch's red-flag migration both take `e77159c3482a` as parent. Merging gives two Alembic heads, and `alembic upgrade head` refuses. **Needs:** a merge revision (`alembic merge`), or re-parenting one migration, before the merge. The downgrade path through both must be tested. | Merging the WIP branch; any deploy |

### Facts needing a document before use (L5)

| # | Fact | Status | Needs exactly | Blocks downstream |
|---|---|---|---|---|
| H20 | Rwanda's emergency / ambulance service is **SAMU**, reached on **912** (reported by you, 2026-09-15) | **Unconfirmed. Must not be hardcoded or shown to anyone** until confirmed. Not present anywhere in the code today. | A document in `docs/clinical/` (MoH/RBC) that states the service name and number, cited with section and page, plus the date it was checked, since numbers change | Any patient- or staff-facing escalation text naming a service or number; the escalation line stays generic until then |

**Order that unblocks the most:** H1 → H6 with H3–H5 → H12 → H7 pilot (60 items) → the rest. H2 is needed
before any real patient, not before the evaluation set.


## 2026-09-19 — sweep abandoned, English and French arms, Table 1 column

**Resume from here.**

**SWEEP (Part C): ABANDONED for v1, cost recorded, artefacts kept.**
- Measured: 11.1 s/step at 4 threads, 9.5 at 2 (4 threads is ~17% SLOWER, memory
  contention). One arm = 174 min; fifteen arms = ~43 hours.
- Reached step 600/940 on `seeds010_rep1` before the machine rebooted at 12:50,
  the third reboot that day. No resume-within-arm path, so no measurement.
- Recorded in §7.4 beside the prediction, which is UNCHANGED.
- KEPT and committed: `dataset/sweep/` (15 arms + manifests),
  `review/build_sweep_arms.py`, `review/run_sweep.py`,
  `tests/test_sweep_arms.py` (7 tests). Ready to run on other hardware.
- Arms are 3,000 rows, not 30,000: the generator's per-seed output varies 21-fold
  (386 to 8,129, median 1,146), so a 30,000 budget selects for large seeds and
  skews class mix. 3,860 is the ceiling at which all 150 phrases qualify.

**ENGLISH AND FRENCH ARMS: authored, copied, measured.**
- `dataset/labelled/triage_EN_FR_ALL.csv`, sha256 b970b3ce, 2,400 rows.
- English 2,302 distinct / 1,905 types / TTR 0.0809.
  French 2,301 distinct / 2,332 types / TTR 0.0919. (2,332, not 2,333.)
- Zero clinical-record voice in English.
- Gates run on all three arms: G1 PASS everywhere; G2 FAILS everywhere
  (EN/FR 2,400 seeds vs 3,000 floor, shortfall 600; KW 2,282, shortfall 718);
  G3 and G6 NOT COMPUTABLE; G5/G7/G8 fail on EMPTY provenance fields, which is
  deliberate and must stay empty until real provenance is supplied.
- Opener concentration: KW 1,578 distinct openers, 3.9% top-1, 14.8% top-10;
  EN 931 / 6.6% / 25.7%; FR 895 / 6.7% / 29.2%. No verdict: C3 has no floor.

**TABLE 1: meaning kept, column added.** It still means "what the generator can
emit". New `Authored` column shows 2,302 and 2,301 sentences that exist and that
the generator cannot use. English and French remain at 0 rows.

**FOUR-LANGUAGE FRAMING: written.** Abstract, introduction and §3.3 now say
sentences are authored in three arms and rows generate in one, because the frame
slots the other two need do not exist. §3.3 states the distance concretely:
three frame slots (openers, contexts, closers), not one further sentence.

**NINTH recorded-but-unread instance: C3**, whose floor is a fraction of a pilot
that has never run. Shares its shape with the G6 stub: neither would be caught by
running them, because NOT COMPUTABLE is indistinguishable from a gate correctly
declining on thin data.

**NEXT ACTION:** the paper is coherent and pushed; the compile is the open loop.
Pages 17 and 31 were fixed by the regeneration (fingerprint a288e8ca) but have
not been recompiled since. Rebuild the zip, compile, and re-run the bounding-box
analysis.

**GATE NAMING, because the two prefixes are the same nine gates.**
`dataset/corpus_gates.py` calls them G1-G9; the paper calls them C1-C9 (e.g.
limitations.tex "C1's cap on rows per seed and C2's floor on distinct seeds" is
the code's G1 and G2). Same numbering, same order. The gate results above use
the code's prefix.

## 2026-09-19 — the paper compiles

**Measured by the author on a real TeX engine, not by me.** I have no TeX engine
on this machine and have verified none of it; it is recorded here as their
measurement, against archive sha256 `009fa892`.

- compiles, exit 0, **36 pages**
- **0 undefined references, 0 undefined citations** — so the duplicate
  `sec:limitations` fix and the acl_natbib change both hold, and the eight
  undefined refs reported earlier were the first-pass artefact of a document
  that never finished a run
- **2 Overfull \hbox, unchanged, both inside table cells**
- the three takeaway boxes render as intended: slate accent bar, pale tint,
  triangle marker, bold heading running into the body
- Figure 1 renders with the 3,000-seed floor marked
- no tcolorbox/xcolor clash

**OPEN, AND THE ONLY THING BLOCKING THE ARCHIVE:** `paper/main.bbl` exists on the
author's machine and on no other. It is not in this repository and not anywhere
on this filesystem. arXiv does not run bibtex, so an archive without it renders
every citation as `[?]` however cleanly it compiles locally.

**NEXT ACTION:** put `main.bbl` at `kinyamed/ml_model/paper/main.bbl`, then run
`python paper/build_archive.py`. It refuses to build without it, prints the
listing and the sha256 from the archive it actually wrote, and excludes
`generated/full_text.txt`. Do not build the archive from a shell `zip` line
again: that is how `main.bbl` was dropped silently for two commits.
