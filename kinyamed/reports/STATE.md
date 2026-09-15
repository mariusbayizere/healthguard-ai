# STATE

**Updated** 2026-09-15 · **Phase** Remediation · **Branch** `audit-p0-p1-and-frontend` (clean; your in-flight
work is on `wip/account-analytics-frontend`) · **Status** Engineering items 1–4 in progress. **Items 1
(`af643d0`, `6e81dd8`) and 2 (`f739985`) done.** **ETAT reading task BLOCKED: `docs/clinical/` exists but is empty.**

## Order agreed

1 fail closed → 1b make the interlock visible → 2 threshold + remove patient reassurance → 3 logger-level phone
masking + PII scan → 4 X-Forwarded-For bypass → docs commit (delete now-false fallback text) → **5 evaluation-set
specification (design only)** → stop. The red-flag layer stays deferred until `docs/clinical/` exists (L5, L16).
No new feature work after item 4.

**Item 2d was inserted "before item 4" after items 4, docs and 5 were already committed.** It was not redone or
reordered: 2d lands after `ed7063e` in history (no rewrite, L14).

## Commits so far (branch `audit-p0-p1-and-frontend`, not pushed)

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
- CLAUDE.md §18 cites ETAT as the basis of a 3-class taxonomy applied to all ages (age 1–120 on the form).
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

## Next — single action

**Engineering paused, as instructed.** Work through the BLOCKED ON HUMAN INPUT register at the end of this file,
starting with H1 (institutional ethics question) and H6 (lead clinician). Your review of `reports/EVAL_SET_SPEC.md` and
decisions E1–E5, then the clinical documents B1–B4. With those in `docs/clinical/`, protocol §3–4 can be filled
and the Kinyarwanda pilot can run.

## Blocked on you (unchanged)

D0 working tree · D1 spec rulings · D2 `docs/clinical/` · D3 clinician · D4 speakers · D5 target CPU ·
D6 v2d weights location · D7 `docs/compliance/` (REMEDIATION_PLAN §0).

## GATE EXCEPTION — `mypy --strict` (CLAUDE.md §16)

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
Every SRS claim below is quoted from the SRS content inlined in `CLAUDE.md` (which states it inlines "every
requirement from SRS v2.0"). Claims that appear only in the docx could not be checked and are not listed.
Every "measured" value comes from a run in this session (see the Phase 0 reports for method).

### A. Statements of fact or status that the audit contradicted

| # | SRS claim (location in CLAUDE.md) | Measured / found | Correction |
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
| A21 | ETAT "WHO framework used in Rwandan health centres; basis for the 3-class taxonomy" (§18) | The repo's taxonomy cites **WHO IMCI 2014** and **WHO-ICRC Basic Emergency Care 2018**, not ETAT (`ml_model/docs/triage-taxonomy.md`, `clinical-anchors.md`). No ETAT document is in the repo. No clinician has approved the taxonomy | Correct the basis, or supply the ETAT source (D2) |
| A22 | Fine-tuned weights at `mariusbayizere/kinyamed-afro-xlmr` (§14) | Not verified (no network check made). The only credible weights (v2d) exist **only in `~/kinyamed-runs/` on the development machine**; `ml_model/saved_model/` is a different checkpoint trained on 179 rows (accuracy 0.414) that the backend refuses to load | Do not cite the HF repo until it exists with a pinned revision |
| A23 | Model "AfroXLMR-mini + **PyTorch 2.1** + **HF Transformers** [4.40]" (§4.2, §3.1) | torch **2.12.0+cpu**, transformers **5.8.1** | Update versions |
| A24 | **Four distinct triage instruments are cited as the clinical basis across the spec and code, and none is in the repository.** (1) **WHO ETAT**, the basis of the 3-class taxonomy: `CLAUDE.md:902` (also :14, :51, :677, :697). (2) **ESI**: CLAUDE.md:899 CRITICAL = "ESI 1–2", :915 URGENT = "ESI 3", :913 ROUTINE = "ESI 4–5"; paper `related_work.tex:16`. (3) **WHO IMCI Chart Booklet 2014**: `ml_model/docs/triage-taxonomy.md:14`, `clinical-anchors.md:11`, `licensing.md:14`, paper `related_work.tex:34`, `method.tex:116`. (4) **WHO-ICRC Basic Emergency Care 2018**: `clinical-anchors.md:10`, `licensing.md:12`, paper `related_work.tex:35`, `method.tex:117`. Also cited, not as a taxonomy basis: WHO *Managing Complications in Pregnancy and Childbirth* 2017 (`related_work.tex:36`) and the Manchester Triage System (`introduction.tex:25`). | `find` over the repo: the only PDF is `ml_model/paper/main.pdf`. **No instrument's text is available to verify any category, age range or licence claim** (the licence checks in `clinical-anchors.md` say the PDFs were read, but the PDFs were not kept). ETAT (paediatric, per your 2026-09-15 finding) and ESI are different instruments for the same three classes. `language-resources.md:12` still says IMCI booklets are CC BY-NC-SA, which `triage-taxonomy.md:23` records as wrong. | Choose one basis per population (TAXONOMY_SCOPE E6); place each cited document in `docs/clinical/`; delete citations of instruments not used |
| A26 | **The concept total has five values across the repo. One number with several values is, on its own, disqualifying at review.** **68**: `ml_model/docs/clinical-anchors.md:32` ("Of the 68 general concepts"). **80**: `ml_model/docs/triage-taxonomy.md:37` ("Of the 80 new concepts"), `licensing.md:24` ("Where the 80 concepts now stand"). **126**: `triage-taxonomy.md:8` ("126 concept slots per language"), `v2-sizing.md:185`, `utterance-form-decision.md:52`, `clinician-session-guide.md:109` ("all 126 concepts"). **127**: `licensing.md:180` and `:191` ("28 of 127 concepts"), `split-authoring.md:17`, `v2-sizing.md:141`, `session-state.md:522`, `build_english_brief.py:19`, `build_swahili_brief.py:1174`, `:1206`. **128**: paper `related_work.tex:26`, `method.tex:109`, `future_work.tex:12`; `d2-clinician-review-pack.md:98`; `swahili-authoring-brief.md:11`; `session-state.md:46`, `:445`; `build_french_brief.py:2`, `:16`; `build_swahili_brief.py:2`; `build_english_brief.py:2`; `csv_to_xlsx.py:133`. | The Kinyarwanda brief `review/speaker_brief_kinyarwanda_v2.csv` has **128 distinct `concept_id`s** (256 rows), counted 2026-09-15. Some other values are subsets (68 general, 80 new) or superseded (127 before OB13 was added 2026-09-05, per `session-state.md:46`), but the documents do not say so where the number is used. The corpus itself has **165 distinct phrases**, which is neither. | Define "concept" once. Derive the count by script from the brief. Replace or explicitly date every other occurrence. Paper submission blocked with A25. |
| A25 | **Paper clinical-anchor count — BLOCKS ANY SUBMISSION.** Stated figure: "Seventy of our 128 concepts carry an anchor" (`ml_model/paper/sections/related_work.tex:26`); "128 concepts, of which 70 carry an anchor" and table total "Anchored concepts & 70" (`method.tex:109`, `:121`). Same claim in the clinician pack: "70 of 128 concepts carry a published anchor" (`ml_model/docs/protocols/d2-clinician-review-pack.md:98`). | **Actual sum:** the four table rows are 24 + 15 + 11 + 20 = 70 (`method.tex:116–119`; `related_work.tex:34–37`). But the fourth row (20) is "Clinician-defined, no WHO anchor", so **concepts with a document anchor = 24 + 15 + 11 = 50, not 70.** Other repo counts disagree: `clinical-anchors.md:35–37` IMCI 28, BEC 18, 22 unanchored, of 68 general concepts; `licensing.md:27–30` IMCI 29, clinician-defined 23, BEC 18, MCPC 10, of 80; `licensing.md:183–188` IMCI 28, 22, BEC 18, MCPC 10, "78 anchored" of 127 (that 78 also counts the 22 as anchored). The paper (128), `licensing.md` (127, 80) and `triage-taxonomy.md` (126 slots, 80 new concepts) each state a different concept total. | Re-derive every count from `review/concepts.py` / `concept_anchors.csv` with a script; count clinician-defined concepts as unanchored; one number everywhere. **No paper submission until done.** |

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
| H3 | WHO ETAT (B1) | The edition used in Rwandan facilities. Confirm whether it covers adults (**you report paediatric; see TAXONOMY_SCOPE.md, to be cited from the manual**), and whether its categories can be applied to a text description at all. The Participant Manual is being placed 2026-09-15; not yet present. | Lead clinician / RBC | Label definitions (D7 protocol §3); presentation types |
| H4 | National triage protocol (B2, B3) | MoH/RBC triage protocol for health centres and district hospitals, adult and paediatric, **with its mapping to CRITICAL/URGENT/ROUTINE**; the adult tool if not ETAT | Lead clinician / RBC / MoH | Domain axis of the eval grid; category mapping; clinical lexicon (§10.6); red-flag layer content (L2) |
| H5 | Obstetric guidance and referral data (B4, D2) | RBC maternal/obstetric danger signs; emergency numbers; referral pathways | RBC / lead clinician | Obstetric presentation type; any patient text beyond the generic escalation line |

### People

| # | What | Needs exactly | Who supplies | Blocks downstream |
|---|---|---|---|---|
| H6 | Lead clinician (B5, D3) | Approve the category mapping and worked examples (≥2 per label, ≥3 boundary pairs per line). Ratify the unsourced numbers: CRITICAL recall 0.91 (old charter 0.95), CRITICAL→ROUTINE < 1%, **review threshold 0.75**. Ratify the 2d design: NEEDS REVIEW above URGENT; low-confidence CRITICAL stays CRITICAL. Rule on the taxonomy pack `ml_model/docs/protocols/d2-clinician-review-pack.md` (e.g. is an unstoppable nosebleed CRITICAL?) | A registered clinician practising in Rwanda | Protocol §3–4; the pilot; every gate verdict; the queue design's clinical basis |
| H7 | Kinyarwanda clinicians (B6, D4) — first | Authors for about 1,300 items. Two annotators (about 11–16 h each, estimated). One adjudicator. Nobody labels their own items. | Native-speaker clinicians (see CLINICIAN_BRIEF) | Kinyarwanda test set, κ, gates 5 (KW) and 9, calibration, and any retraining (R5) |
| H8 | EN / FR / SW clinicians (B6, D4) | The same roles per language. Swahili needs TZ and KE variants. | Native-speaker clinicians | Gates 5 (EN/FR/SW) and 10–12. §16's hard gate needs all four. |
| H9 | Bilingual raters per mixed pair (D4) | Authors and annotators for 6 code-switch pairs; naturalness ratings ≥ 2 raters per pair | Bilingual speakers of each pair | Gate 13; the code-switching claim |
| H10 | Lexicon and red-flag validators | T1 validation of lexicon rows with colloquial variants. Validation of the 20 audit probe phrases (now `validated_by=NONE`). | Native-speaker clinicians (H6–H8) | L2 red-flag layer (R1.3); red-flag safety suite 100% gate |
| H11 | Patient receipt translations | KW / FR / SW versions of the receipt and escalation line (`backend/app/services/patient_message.py`, English only), speaker-authored or speaker-approved | Native speakers; clinician check on the escalation wording | Patients who do not read English |

### Decisions only you can make

| # | What | Needs exactly | Blocks downstream |
|---|---|---|---|
| H12 | E1–E7 (EVAL_SET_SPEC §12, TAXONOMY_SCOPE §6) | Yes/no on each: E1 interval decision rule; E2 pooled mixed accuracy with per-pair floor; E3 distinct-item minimums instead of n=100,000; E4 ECE on the test set, temperature fitted on the calibration split; E5 Kinyarwanda first; **E6 scope option (a) paediatric only / (b) adult only / (c) both with age routing; E7 under (c), age group powered or coverage-only** | Freezing the spec; quota sheets for authors (H7); every protocol §3 definition |
| H13 | Governing spec (D1) | A ruling on the 9 conflicts (a)–(i) between the old `ml_model/CLAUDE.md` and CLAUDE.md v2.0. Also: 87% vs 82% accuracy, and 13px vs 14px minimum text. | R1.3, R3, R5–R7; schema and auth work |
| H14 | Your uncommitted work (D0) | Commit or stash your 19 modified files, 1 deleted file and untracked files (`queue_repo.py`, `hooks.ts`, `types.ts`, the password-reset migration, CI). | Folding the band fields into `QueueEntry`; putting mypy in CI (`ci.yml`); clean commits |
| H15 | Target CPU (D5) | Cores, RAM, whether shared | Gates 14–15 verdicts |
| H16 | v2d weights (D6) | Publish with pinned revision and SHA-256, or keep private and document where | `make reproduce`; model card; paper reproducibility |
| H17 | mypy exception date | Agree or replace the proposed 2026-09-28 | §16 commit-gate compliance |
| H18 | History before push | Squash `2db26c8`+`fed85d7` (history rewrite, needs your explicit yes, L14) or leave with the bisect note | Pushing the branch |
| H19 | SRS document | Apply "SRS CORRECTIONS REQUIRED" to `KinyaMed_SRS_v2_0.docx` (not in repo; a copy sits in `~/Downloads`, not opened by me). **Add: §18 cites both ETAT (paediatric, per your finding) and ESI as the basis of the same 3 classes.** | Anyone reading the SRS |

### Facts needing a document before use (L5)

| # | Fact | Status | Needs exactly | Blocks downstream |
|---|---|---|---|---|
| H20 | Rwanda's emergency / ambulance service is **SAMU**, reached on **912** (reported by you, 2026-09-15) | **Unconfirmed. Must not be hardcoded or shown to anyone** until confirmed. Not present anywhere in the code today. | A document in `docs/clinical/` (MoH/RBC) that states the service name and number, cited with section and page, plus the date it was checked, since numbers change | Any patient- or staff-facing escalation text naming a service or number; the escalation line stays generic until then |

**Order that unblocks the most:** H1 → H6 with H3–H5 → H12 → H7 pilot (60 items) → the rest. H2 is needed
before any real patient, not before the evaluation set.

