# Senior engineering audit — 2026-09-09

Every finding was verified against the repository today, not recalled. Findings
are ordered by consequence, not by area. Each carries the fix.

Work I wrote myself is marked **[mine]** and is not softened. Three of the five
severity-1 findings are mine.

---

## Severity 1 — would be blocked in review at a serious shop

### 1.1 CI does not run the backend or the frontend at all **[mine, partly]**

`.github/workflows/ci.yml` has ten steps across three jobs. Every one of them is
the ML package: `make verify`, `make verify-full`, `check-attribution`, and the
`ml_model` pytest suite. Grepping the workflow for `backend`, `npm`, `frontend`
or `vitest` returns nothing.

So the 156 backend tests and the 6 frontend tests run **only when someone
remembers to run them locally**. I pushed a red HEAD earlier today by skipping a
gate; the reason that was possible is that no automation would have caught it.

**Fix.** Add two jobs. Backend: `pip install -r requirements-dev.txt && pytest`.
Frontend: `npm ci && npm run typecheck && npm run test && npm run build`. Both
on every push. The ML jobs are well built and should be the model for these.

### 1.2 No linter or formatter in 15,585 lines of Python

No `pyproject.toml`, `.ruff.toml`, `setup.cfg` or `.flake8` in either package.
Nothing enforces import order, unused names, line length, or the hundred small
consistencies a reviewer otherwise has to carry by hand. The code is unusually
disciplined for a codebase with no linter, which is a compliment to whoever
wrote it and not a substitute.

**Fix.** `ruff` with `select = ["E","F","I","B","UP","SIM","RUF"]`, line length
88, and `ruff format`. Run it in CI as a separate job so a style failure is
distinguishable from a test failure. Expect a large first diff; land it as one
commit that changes nothing else.

### 1.3 The urgency ordering exists in five independent copies **[mine, one of them]**

```
ml_model/dataset/process_dataset.py:9      {"CRITICAL": 0, "URGENT": 1, "ROUTINE": 2}
ml_model/dataset/build_dataset.py:170      {"CRITICAL": 0, "URGENT": 0, "ROUTINE": 0}
backend/app/models/triage_result.py        UrgencyLevel.priority
backend/tests/integration/test_full_triage_path.py:59   {"CRITICAL": 0, ...}   [mine]
frontend/src/api/types.ts                  URGENCY_RANK                        [mine]
```

This is precisely the failure that already cost this project a day: two copies
of `MINIMUM_CRITICAL_RECALL` in `evaluate.py` and `train_holdout.py`, where
changing the safety threshold in one would silently not apply in the other. I
found and fixed that one, then added two more copies of the same shape while
writing tests and a frontend.

**Fix.** The backend enum is the source of truth. Export the ordering from a
single module, have the test import it, and generate the frontend constant from
the OpenAPI schema alongside `schema.gen.ts` rather than hand-writing it. A
cross-language constant cannot be DRY by import, so it must be DRY by
generation.

### 1.4 `GET /triage/{id}` returned a wrong `response_pending` for its whole life **[mine]**

Found today while adding `queue_id`. The read path never called
`response_templates.resolve()`, so it returned the schema default
`response_pending=True` unconditionally. A triage that **had** a
speaker-authored Kinyarwanda response reported that none existed when fetched
back.

No test caught it because the integration tests only exercised the response
slot on the **write** path. The read path was asserted for `urgency_level`
only.

**Fixed today.** The remaining lesson is the test gap: when a field is added to
a schema shared by two handlers, both handlers need a test. Added to the read
path now.

### 1.5 `KeywordClassifier` is still the production default

`get_classifier()` falls back to a keyword scorer whenever `TRIAGE_MODEL_PATH`
is unset, and unset is the default. A deployment that forgets one environment
variable runs a hand-written keyword matcher that was **never evaluated against
the holdout** — no macro F1, no CRITICAL recall, nothing — while logging
cheerfully and serving triage decisions.

The fallback is right for a dev machine and wrong for production, and nothing
distinguishes the two.

**Fix.** `if settings.ENVIRONMENT == "production" and not settings.TRIAGE_MODEL_PATH:
raise` at startup. Fail to boot rather than boot degraded. The deployment
runbook already says "if the log names the baseline, stop" — that instruction
should be a startup assertion, not a human step.

---

## Severity 2 — real debt, would attract review comments

### 2.1 `review/build_swahili_brief.py` is 1,092 lines **[mine]**

The second-largest file in the ML package. It does CLI parsing, frozen-v1
import, gloss derivation, collapse resolution, person-note restatement, hold
arbitration, relation-set naming, CSV emission and a no-Swahili invariant
check. Nine responsibilities.

It is heavily commented, which makes it readable and does not make it well
structured. A reader wanting the collapse rules must scroll past the gloss
overrides.

**Fix.** Split into `briefs/spine.py` (read and validate the spine),
`briefs/glosses.py`, `briefs/rulings.py` (holds, applies, relations), and
`briefs/emit.py`. The declared maps stay data; the logic moves out from under
them.

### 2.2 The four brief builders are near-duplicates

`build_english_brief.py`, `build_french_brief.py` and `build_swahili_brief.py`
share their spine read, their EX positional mapping, their collapse derivation
and their merge-preserving-authored-columns logic, with per-language
divergence. The Swahili one was written by copying the French one.

The evidence this is a problem: the derived collapse set was fixed in the French
builder, then had to be fixed **again** in the English one, where it found five
collapses the hardcoded list had missed.

**Fix.** One `BriefBuilder` with a per-language policy object. The divergences
that matter — authoring versus review, candidate columns, the no-Swahili
invariant — become explicit configuration rather than diff noise.

### 2.3 Six broad `except Exception` handlers, four of them justified

```
health.py:28            a probe reports, never raises        JUSTIFIED
sms_service.py:133      carrier failure is recorded          JUSTIFIED
sms_service.py:160      background work must not crash       JUSTIFIED
model_classifier.py:168 a bad artefact must not take the service down   [mine] JUSTIFIED
middleware.py:43        UNEXPLAINED
database.py:51          UNEXPLAINED
```

Four carry a `# noqa: BLE001` and a reason, which is the right pattern. Two do
not.

**Fix.** Narrow the two, or document them the way the other four are. A bare
`except Exception` with no comment is indistinguishable from an oversight.

### 2.4 Frontend has no end-to-end test and no accessibility test **[mine]**

Six component tests. Nothing exercises the router, the auth redirect, the query
layer, or a real request. Nothing checks contrast, focus order, or that the
urgency badges are announced.

Given the design brief was explicitly about legibility under stress, the
absence of an automated accessibility check is a gap I should have closed while
the reasoning was fresh.

**Fix.** Playwright for one path: log in, submit a triage, see the row appear
in the queue, assign a doctor. `vitest-axe` on the three views. Neither is
large.

### 2.5 `MINIMUM_SWITCHABLE_TERMS = None` reads as an oversight **[mine]**

It is a deliberate refusal — the value is undecided, so the gate declines — and
the comment says so at length. But a reader scanning the module sees a `None`
constant and a function that always raises, and the most likely conclusion is
"unfinished".

**Fix.** Make the refusal a named type rather than a null:
`MINIMUM_SWITCHABLE_TERMS: int | Undecided = UNDECIDED`, where `UNDECIDED` is a
sentinel whose repr says why. The intent then survives a reader who does not
read the comment.

### 2.6 `dataset/vocabulary.py` is 1,228 lines of mostly data

Data and code in one module. The phrase inventory, relation sets, frame slots
and the helpers that read them all live together, so importing a constant pulls
in the whole corpus.

**Fix.** Move the inventories to a data file the module loads, or split
`vocabulary/` into `phrases.py`, `relations.py`, `frames.py`. This one is
lower priority because the file is frozen and reproducibility depends on it not
moving — do it at the v3 boundary, not before.

---

## Severity 3 — worth fixing, not urgent

### 3.1 No API client generation is actually wired **[mine]**

`package.json` has an `api:types` script and `src/api/types.ts` says the
generated file supersedes it, but `schema.gen.ts` does not exist and nothing
enforces its regeneration. The hand-written types are exactly the drift risk the
comment warns about.

**Fix.** Run the generation against a live backend, commit the output, and add a
CI step that regenerates and fails on a diff.

### 3.2 Secrets posture is warn-only in development

`config.py` warns when `SECRET_KEY` is a known placeholder and blocks only in
production. Reasonable, but the warning appears on every test run and every
local command, which is how a warning becomes invisible.

**Fix.** Suppress it under pytest, keep it loud everywhere else.

### 3.3 `.env` is committed to the repository

`backend/.env` exists alongside `.env.example`. It appears to hold development
values only, but a committed `.env` is a habit that eventually commits a real
secret.

**Fix.** Remove from tracking, add to `.gitignore`, keep `.env.example`.

### 3.4 No dependency pinning for the backend beyond `requirements.txt`

No lockfile. `requirements.txt` pins versions, which is most of the benefit, but
transitive dependencies float.

**Fix.** `pip-compile` to a `requirements.lock`, or move to `uv`.

### 3.5 The paper has no conclusion section **[mine]**

Nineteen pages of complete sections with no closing argument. The `\PENDING{}`
markers are deliberate absences; a missing conclusion just reads as unfinished.

**Fix.** Write it. It is hours, not a day.

---

## What is genuinely good, and should not be traded away

Naming these because an audit that lists only faults gives a false picture, and
because the next person to touch this should know what the load-bearing parts
are.

- **The reproducibility apparatus.** `make verify-full` re-deriving 14 digests
  from seed 42, frozen manifests with digests, the atomic writer that refuses
  to write an empty file. This is better than most production ML.
- **The leakage guarantee.** Phrase-group closure over containment and ordered
  subsequence, plus the concept-level union that no similarity rule could
  produce. The project found and documented that its own earlier holdout leaked
  100% and recorded it rather than quietly fixing it.
- **The provenance discipline.** Per-phrase source columns, the refusal to write
  patient-facing text without a speaker, `\PENDING{}` markers for unrun studies.
  The paper's numbers are emitted from a verified run and cannot be typed by
  hand.
- **The test suite's intent.** `test_paper_numbers.py` caught a missing data
  digest in my emitter; `test_fingerprint_changes_with_any_trajectory_input`
  caught four unchecked fields. These tests were written to catch classes of
  error, not to raise coverage, and it shows.

---

## Ordered plan

1. CI runs backend and frontend (1.1) — half a day, and it is the one that
   prevents recurrence of everything else.
2. Ruff, one landing commit (1.2).
3. Production refuses to boot on the keyword baseline (1.5).
4. Single source for the urgency ordering, generated across the boundary (1.3).
5. Playwright path plus axe (2.4).
6. Split the brief builders (2.1, 2.2).

Items 1, 2 and 3 are a day between them and remove the three ways this
repository can currently ship something wrong without anyone noticing.
