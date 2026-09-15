# KinyaMed — Phase 0 audit report

**Date** 2026-09-14 · **Branch** `audit-p0-p1-and-frontend` @ `7ef50c0` + uncommitted working tree ·
**Auditor** Claude (Opus 5) acting under docs/ENGINEERING_SPEC.md §3 · **Mode** read-and-measure; no feature code touched.

Companion reports: [REQUIREMENTS_MATRIX](REQUIREMENTS_MATRIX.md) · [MODEL_AUDIT](MODEL_AUDIT.md) ·
[DATASET_AUDIT](DATASET_AUDIT.md) · [REMEDIATION_PLAN](REMEDIATION_PLAN.md) · [STATE](STATE.md)

---

## The five findings most likely to sink this project, ranked

### 1. The running system tells a patient who cannot breathe that it is safe to wait — and nothing catches it

With the trained model (v2d) loaded, I posted `"sinshobora guhumeka"` to `POST /api/v1/triage`. That phrase
appears in the backend's own red-flag list as the Kinyarwanda for "cannot breathe"
(`backend/app/services/triage_service.py:92`). The API returned **`urgency_level: ROUTINE`**, queued the patient as
ROUTINE, and returned the speaker-authored ROUTINE message, glossed in its brief as *"Not urgent — make an
appointment… it is safe to wait"*, with `response_pending: false`. The ROUTINE SMS was rendered for dispatch.

It is not a one-off. On a 20-input probe of emergency phrases, **11 went to ROUTINE**. That includes
"kugagara" (convulsing) and **every** English, French and Swahili input: "He is unconscious", "douleur
thoracique, je ne peux pas respirer", "nina maumivu ya kifua na siwezi kupumua". Some of these came back at the
probe's highest confidences (MODEL_AUDIT §6.1).

The safety architecture the laws require does not exist:

- **L2 violated.** There is no rules layer in front of the model. The red-flag terms are only used by a keyword
  classifier that runs *instead of* the model. Measured as a classifier, that fallback catches **5.7%** of
  held-out CRITICAL cases and sends **94.3%** of them to ROUTINE.
- **L4 violated.** There is no `requires_human_review`. `MODEL_CONFIDENCE_THRESHOLD` is referenced by zero lines
  of application code.
- **Silent fallback.** Outside `ENVIRONMENT=production` the API falls back to the keyword classifier without
  failing (this includes staging). A model exception returns HTTP 500 instead of a review state.
- **`/ready` misreports the model.** It imports a module that does not exist, so it always reports
  `ml_model: not_installed`, even with v2d loaded.

### 2. The model fails every threshold it can be measured on, and the test set cannot certify safety anyway

v2d, re-run on the frozen held-out reporting set, reproduces its recorded numbers exactly:

| Metric | Measured | Threshold |
|---|---|---|
| Accuracy | 0.7065 | 0.82 |
| Macro F1 | 0.7724 | 0.80 |
| CRITICAL recall | 0.8504 | 0.91 |
| CRITICAL precision | 0.6633 | 0.88 |
| URGENT recall | 0.4963 | 0.86 |
| ECE | 0.18 | 0.05 |

It even underfits its *training* rows: accuracy 0.743.

That "held-out set" is **17,942 rows built from 9 sentences, 4 of them CRITICAL, all Kinyarwanda**. Bootstrapping
over the sentences puts the 95% CI on CRITICAL recall at **[0.08, 1.00]**. The reported 0% CRITICAL→ROUTINE rate
is therefore not evidence of anything.

**4 of the 15 deployment-gate metrics cannot be measured at all** (English, French, Swahili and mixed-language
accuracy have no evaluation data), and CRITICAL recall can be measured in only 1 of the 4 languages it is required in. Because 93% of predictions
fall below 0.75 confidence, a review threshold would flag nearly every patient. No retraining fixes this. Only
many distinct, clinician-labelled sentences per language do.

### 3. The specification and the repository describe two different products, under conflicting rules

The code was built to an earlier charter, the ml_model charter file. It is **deleted in the working tree and not
committed**. The engineering specification v2.0 (`docs/ENGINEERING_SPEC.md`) contradicts that charter's standing rules in at least nine places (REMEDIATION_PLAN
D1), for example:

- **Response text:** "patient-facing text is speaker-authored or absent" vs "all 4 responses non-null".
- **Corpus size:** "size follows content" vs "≥ 1,000,000 rows".
- **Phone numbers:** non-unique on purpose (shared household handsets) vs `UNIQUE(phone)`.
- **Triage access:** authenticated only vs anonymous submission.
- **Frontend:** a hand-built Tailwind app vs an MUI stack.

Against v2.0, **13 of 227 traceability rows are DONE-VERIFIED**. The rest are MISSING, INCORRECT or PARTIAL, not
broken.

Other status claims are wrong too:

- The SRS says "94 tests passing". I measured **425 passing** (213 backend, 127 ML plus 2 skipped, 85 frontend)
  and 0 failures.
- The root README contradicts itself (L6). It says "no model has been trained … no accuracy claims" and also
  "Macro F1 0.7724". It still describes the superseded 1M-row, 5-language v1 corpus.

Until you decide which rules govern, most remediation work would be rework.

### 4. There is no clinical, linguistic or legal ground truth in the repository

These are all absent:

- `docs/clinical/`: no MoH/RBC/ETAT source, emergency numbers or referral pathways. **L5 is BLOCKED.**
- `docs/compliance/`: no IRB or data-protection status. **L10 is BLOCKED.**
- `data/lexicon/`, `docs/SOURCES.md`, the SRS docx.

Everything that should rest on those sources is unsourced or unratified:

- The red-flag term list.
- The gate thresholds. The repo uses CRITICAL recall 0.95 and marks it "source unverified"; the spec says 0.91.
- The urgency taxonomy (no clinician has signed it off).
- 3 of 4 languages. English and French are unreviewed machine drafts; Swahili has 0 authored phrases.

No inter-rater agreement (κ) exists, and no naturalness rating exists. The fix for finding 1 (a lexicon-driven
rules layer) and for finding 2 (a real test set) is **blocked on people and documents only you can supply**. The
repo has already written the protocols for them (`ml_model/docs/protocols/d1…d6`).

### 5. Decisions cannot be traced, patient data leaks, and the service collapses under load

- **No audit trail.** There is no `audit_logs` table (FR-03-09).
- **No model version on decisions.** `triage_results` has no `model_version`, so no triage can be tied to the
  model that produced it. L3 per-version CRITICAL→ROUTINE logging is impossible.
- **No field feedback.** There are no consultation endpoints and no "AI was wrong" capture, so a field
  CRITICAL→ROUTINE error can never be observed.
- **PII leaks (L11).** A 501-request load run produced **336 log lines containing the full phone number**
  (`sms_stubbed … to=`). `GET /queue` returns phones unmasked.
- **Rate limits are bypassable.** The limiter trusts client-supplied `X-Forwarded-For`: 30 of 30 requests passed
  after the limit was exhausted. There is no auth-specific 10 / 15 min bucket.
- **Security gaps:**
  - No CSP or HSTS headers.
  - HS256, not RS256.
  - `pip-audit` found **25 known vulnerabilities in 3 backend packages** (PyJWT 2.10.1, python-multipart 0.0.20,
    pydantic-settings).
  - `npm audit` found **7**, including 1 critical.
  - No security scanning in CI.
  - `mypy --strict` has 20 errors.
- **Collapse under load.** At 50 concurrent triage requests, p50 was 34 s and **136 of 200 requests got HTTP
  503**. The cause is the DB pool running dry while requests queue on a single inference lock. Even with one
  user, HTTP p95 was 1.5 s against a 350 ms target, measured under memory pressure.

---

## A. Scope, method, environment

### A.1 What was executed

| Action | Result |
|---|---|
| Backend `pytest` (PostgreSQL 16 test DB) | **213 passed, 0 failed, 0 skipped**, 294 s; coverage **93%** (`model_classifier.py` 41%) |
| ML `pytest` | **127 passed, 2 skipped** (paper-number placeholders, correctly skipped once a run fills them), 2,660 s |
| Frontend `vitest` | **85 passed** (6 files), 62 s |
| `tsc -b` (strict + `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes`) | clean; `any` = 0; `@ts-expect-error` = 2 (tests, documented) |
| `vite build` | JS 253.6 KB raw / **77.6 KB gzip**; CSS 4.2 KB gzip |
| `ruff check` / `ruff format --check` (0.16.6) | clean / 204 files formatted |
| `mypy --strict app main.py` | **20 errors in 11 files** (incl. `import-not-found: app.ml.model_loader`) |
| `npm audit` | **7** (1 critical `vitest ≤ 3.2.5`, 5 high incl. `postcss ≤ 8.5.22`, 1 moderate) — dev dependencies |
| `pip-audit` backend / ML requirements | **25 / 3** known vulns (backend: PyJWT 2.10.1, python-multipart 0.0.20, pydantic-settings 2.14.1; ML: transformers 5.8.1, setuptools 81.0.0); torch `+cpu` not auditable |
| Alembic on empty DB: `upgrade head` → `check` → `downgrade base` → `upgrade head` | all clean; `check` "No new upgrade operations"; after downgrade only `alembic_version` remains, 0 enums, 0 sequences |
| API boot (default config), probes `/health`, `/ready`, `/`, `/openapi.json`, unauthenticated calls | boots; **1 warning** "SECRET_KEY is a known placeholder value" (dev); 40 paths / 50 operations; no consultations, no websocket |
| API boot with v2d; with `ml_model/saved_model` | v2d loads (warm-up 79–212 ms); `saved_model` refused on `id2label`, falls back to keyword baseline; `/ready` says `not_installed` in both |
| Model inference, calibration, CIs, probes, latency | MODEL_AUDIT |
| Dataset profiling, dedup, leakage, shortcut probe | DATASET_AUDIT |
| `verify.py --scope sample` / `--scope full` | 6/6 PASS / **14/14 PASS** (815 s) |

**Host.** Intel i5-6200U (2C/4T), 7.6 GiB RAM, Ubuntu 24.04 / Linux 7.0, Python 3.11.9, Node 18.19.1, PostgreSQL 16,
Redis active (unused by the app), Docker daemon **not running**. Browsers held ~3 GB throughout and 2–3 GB of swap was
in use — latency numbers are upper bounds.

**Not executed, and why:** gitleaks (not installed; pattern scan of history done instead, §B.7), OWASP ZAP,
Lighthouse, browser Axe, keyboard walkthrough, Playwright (no browser automation on host), Locust (thread-based load
used instead), Docker builds (no Dockerfiles exist; daemon off), Kubernetes/Kafka/WebSocket (none exist), CI run
observation (`gh` not installed), `EXPLAIN ANALYZE` on production-shaped data (only the empty/test schemas exist).

**Side effects on your machine, all outside git:** recreated DB `kinyamed_test` (the suite does this itself);
created DB `kinyamed_audit_migr` and seeded it with one synthetic admin, one synthetic patient and 365 synthetic
triages; rebuilt `frontend/dist/` (git-ignored); tools installed into the session scratchpad only. **Nothing under
`kinyamed/` was modified except creating `reports/`.** You may want to `DROP DATABASE kinyamed_audit_migr;` — I did
not, to leave the evidence inspectable.

### A.2 Repository inventory

**Git.** 146 commits. Branches: `main`, `audit-p0-p1-and-frontend` (3 commits ahead of `main`, in sync with origin),
`rbc-attestation-corpus`. `main` = `origin/main`. **Working tree at audit start: 19 modified, 1 deleted
(the ml_model charter file), 21 untracked** — including a new migration `f1a2b3c4d5e6`, 3 new test files, 6 new
routes and CI changes. Every measurement in this audit is of the working tree, not of HEAD.

**LOC (tracked source, excluding generated data):**

| Area | Lines |
|---|---|
| `backend/app` | 6,392 |
| `backend/tests` | 2,554 |
| `backend/migrations` | 463 |
| `frontend/src` | 4,303 |
| `ml_model/dataset` | 5,083 |
| `ml_model/training` | 2,427 |
| `ml_model/tests` | 2,798 |
| `ml_model/review` | 8,162 |
| `ml_model/paper` (.tex) | 1,640 |
| `.github` | 241 |
| **`infrastructure/`** | **0** (three empty directories: docker, kafka, kubernetes) |

**Versions: specified vs installed**

| Component | Spec | Installed / pinned | |
|---|---|---|---|
| React | 18 | 18.3.1 | ✓ |
| TypeScript | 5 strict | 5.5.4 strict | ✓ |
| Tailwind | yes | 3.4.10 | ✓ |
| MUI | v5 | **absent** | ✗ |
| Vite | 5 | 5.4.2 | ✓ |
| FastAPI | yes | 0.136.1 | ✓ |
| Python | 3.11 | 3.11.9 | ✓ |
| PostgreSQL | 16 | 16 | ✓ |
| Redis | 7 | server running, **client unused** | ✗ |
| Kafka | yes | **absent** (config keys only) | ✗ |
| PyTorch | 2.1 | **2.12.0+cpu** | differs (newer) |
| Transformers | 4.40 | **5.8.1** | differs (major version) |
| SQLAlchemy / Alembic | yes | 2.0.49 / 1.18.4 | ✓ |
| Pydantic | v2 | 2.13.4 | ✓ |
| Slowapi | yes | **absent** (custom middleware) | ✗ |

Dependency health: no backend lockfile (transitive deps float); ML pins exact.

---

## B. Findings by area, severity-ranked

Severity: **S1** could harm a patient or invalidate the project's claims · **S2** blocks deployment or publication ·
**S3** real debt.

### B.1 Test suite — verifying "94 tests passing"

- **S2 — The claim is false in the good direction.** 425 tests pass (213 + 127 + 85). None fail or error.
- **S1 — No test that asserts a triage *outcome* ever runs the model.** Every backend integration test on triage
  (`test_full_triage_path.py`, `test_triage_routes.py`) runs the keyword baseline, because `conftest.py` never sets
  `TRIAGE_MODEL_PATH`. Examples: "critical overtakes routine", "critical is quoted no wait". The green suite
  certifies queue mechanics, not triage.
- **Vacuous tests.**
  - No `xfail`, no mocked unit-under-test.
  - One test without an assertion:
    `ml_model/tests/test_leakage.py::test_a_declared_concept_group_with_no_phrases_yet_does_not_raise`. This is a
    legitimate no-raise test.
  - Five tests skip conditionally if the sibling package is absent. They ran here.
  - `test_rate_limit.py`'s fixture loop claims to reset limiter state but does nothing (`break` only). The tests
    still pass because a fresh app is built.
- **Coverage gaps.** `model_classifier.py` 41%, `routes/v1/users.py` 76%, `core/database.py` 56%.

### B.2 Does it run? API

- Boots with 1 warning (placeholder `SECRET_KEY`, tolerated in development by design).
- **S1** `/ready` misreports the model (finding 1). **S1** Anonymous `POST /triage` → 401, contrary to FR-05-07
  (a design conflict, not a bug). **S2** No consultation, correction, audit, websocket or metrics endpoints.
- **S2** Concurrency collapse at 50 users (finding 5; MODEL_AUDIT §3.2).
- **S3** Model load at startup took 66–77 s under swap; the service answers `/health` only after it (no separate
  "starting" state).

### B.3 Data model (§3.4)

Live schema = migrations = models (`alembic check` clean). Diff against §8 is table-by-table in the matrix (DM-01…11).
Highlights:

- **S1** `triage_results` has no `model_version`, `probabilities`, `requires_human_review` or rules-layer fields.
- **S2** No `audit_logs`. No `model_evaluations`.
- `consultations` has no API. `password_reset_tokens` is the 11th table instead.
- The split into `first_name`/`last_name` was never applied: `users.full_name` and `patients.name` remain. Phone
  numbers are stored in E.164 (Rwandan normalisation), with no `country_code` column.
- `password_hash` is NOT NULL and there are no OAuth columns, so the conditional CHECK the spec asks about is moot.
- `UNIQUE(email)` ✓. `UNIQUE(patients.phone)` is **deliberately absent** (shared handsets; needs your ruling).
- **`queue.queue_number` is globally unique** from a Postgres sequence. It never resets per day, so the CAT/UTC
  question does not arise yet. Positions are derived on read, never stored, which is better than the spec.
- Well designed: the DB-level CHECK `ck_users_role_link_consistency` (tested), ON DELETE RESTRICT on consultation
  authorship, and status-transition rules.
- N+1: asserted for the queue list only (`test_queue_read_does_not_issue_a_query_per_row`, passed).
- `EXPLAIN ANALYZE` was not run: there is no production-shaped data. The composite index
  `ix_queue_live_order (status, priority, created_at)` matches the live-queue query.
- Triage writes report, result and queue entry in one commit (`triage_service.py:399-421`). There is no rollback
  test and no audit row.

### B.4 ML system

MODEL_AUDIT in full. Additional S1s beyond findings 1–2:

- **S1 Serving uses a different checkpoint depending on which path you configure.** `ml_model/saved_model/` is a
  May checkpoint trained on 179 rows. It scores near chance (accuracy 0.414, CRITICAL→ROUTINE 20.3%) and is
  unloadable. The real v2d weights exist only in `~/kinyamed-runs/`. The base-model revision is not pinned.
- **S2 Singleton not thread-safe.** 100 concurrent cold `get_classifier()` calls produced 100 builder invocations
  (mitigated today by the lifespan warm-up).
- **S2 Language detection is below threshold.** Measured on generated v1 text: Kinyarwanda 87.7%, Swahili 88.3%,
  mixed **33.0%**. No confidence is produced.
- **S3** Serving `MODEL_MAX_LENGTH=512` vs training 96. This measured 0% disagreement on this corpus.
- Checked and fine:
  - **Truncation:** 0% of rows over 96 tokens in any language (Kinyarwanda 2.66 chars/token vs English 3.89).
  - **Label order:** correct and guarded.
  - **Softmax:** applied once.

### B.5 Dataset

DATASET_AUDIT in full. S2:

- 330,000 Kinyarwanda-only rows; 165 phrases; **360 word types**.
- No per-row provenance, no κ, no datasheet.
- A label shortcut is baked into the frames: "thank you" closers appear on 0% of CRITICAL rows vs 18% of the
  others.
- Leakage control is sound (0 exact, 0 phrase, 0 near-duplicate across splits).

### B.6 Security (§3.7) — probes run in-process against the real middleware

| Check | Result | Sev |
|---|---|---|
| JWT algorithm / rotation story | HS256 shared secret (`core/config.py:66`); no `kid`, no rotation | S2 |
| Refresh rotation + reuse detection | ✓ rotation; reuse revokes **all** user sessions (tested) | — |
| Refresh cookie | httpOnly ✓, path-scoped ✓, **SameSite=lax** (spec strict), stored by `jti` not hash | S3 |
| Google ID token JWKS verification | not applicable — no OAuth | — |
| Login rate limit 10 / 15 min | **absent** — single global 120 / 60 s bucket; with limit set to 10 the 11th request → 429 + `Retry-After` ✓ | S2 |
| Rate-limit key | **client-controlled `X-Forwarded-For`** → 30 / 30 requests accepted after exhaustion by rotating the header | **S1** |
| Security headers | CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy: **all absent** | S2 |
| Raw SQL | only `SELECT 1` in health probe | — |
| PII in logs | **336 lines** with E.164 phone in a 501-request run (`sms_service.py:55`) | **S1** |
| Access token storage (frontend) | `localStorage` (documented trade-off, `frontend/src/lib/auth.ts:3`) | S3 |
| Password reset | hashed single-use token, no enumeration (tested); 30 min SMS, not 10 min email OTP | — |
| ZAP baseline | not run (no tool) | — |

### B.7 Secrets and git health

- `backend/.env` is **untracked** (earlier `docs/AUDIT.md` §3.3 said committed — stale).
- History pattern scan (`git log --all -p`) found only placeholders:
  - An editor backup `.env.example~` was committed in `322a9a6`, then untracked in `1d69a8e`. It holds only
    placeholder values.
  - `postgresql://postgres:password@…` from `.env.example` in `bc02741`.
- The local `.env` holds a `SECRET_KEY` that is on the app's own known-placeholder list.
- **gitleaks was not run.** Treat "no secrets" as UNVERIFIED until it is.

### B.8 Frontend

- **Well built:**
  - Strict TypeScript, 0 `any`, 77.6 KB gzip.
  - Contrast ratios computed in tests.
  - `aria-live` queue announcer.
  - Offline vs error states distinguished.
  - The model score is honestly labelled "uncalibrated softmax value, not a probability".
- **Missing against v2.0:**
  - It is a single staff-operated app. There is no patient portal and no role-separated views.
  - No MUI, no motion, no undo (a `confirm` dialog is used instead), no WebSocket (5 s polling), no filters.
  - No detail drawer, no consultation form, no correction flow.
  - No E2E or browser a11y tests.
- **Not verified:**
  - The Doctor view offers "Done" on WAITING rows, but the API only allows IN_PROGRESS→DONE. This probably causes
    a 409 in the UI; I did not exercise it.
  - Lighthouse, 3G, keyboard walkthrough and the 320 px check were not run (no browser tooling on host). Recorded
    as BLOCKED/UNVERIFIED in the matrix.

### B.9 Infrastructure and CI

- `infrastructure/` contains **no files**: no Dockerfiles, K8s manifests, probes, Nginx/TLS, Prometheus or Grafana.
- CI (`.github/workflows/ci.yml`, with 32 uncommitted lines) runs ML reproducibility, the ML tests, backend tests
  on a Postgres service, frontend typecheck/test/build, ruff and hygiene. **Not observed running.**
- **The ML evaluation gate is aspirational.** No job runs `evaluate.py`. The weights are git-ignored, so a
  path-triggered gate on `saved_model/` could never fire. No gate has ever blocked a model in CI. The repo's local
  3-condition gate did correctly reject v2c.
- No security, Docker, staging or deploy stages. `mypy` is not in CI.

### B.10 Contradictions inside the engineering specification v2.0 (`docs/ENGINEERING_SPEC.md`) (you asked me to call these out)

1. **Accuracy:** 87% (FR-01-07) vs 82% (§9.2 gate). Proposal: keep 87% as the target and 82% as the floor, as
   you already suggest.
2. **Font size:** 13 px / 12 px type steps (§7.3) vs "no text below 14 px" (§6.4). Proposal: a 16 px rem base
   with steps ≥ 0.875 rem.
3. **CRITICAL recall:** 0.91 (§9.2) vs the repo's 0.95 (unsourced). Proposal: keep the stricter value until a
   clinician rules; never lower it on no evidence.
4. **Response text:** "All 4 responses non-null" (FR-01-08) vs §10.2 "no Kinyarwanda example without native-speaker
   approval" and L1. As written they cannot both hold until speakers author EN/FR text.
5. **Email duplicate check:** "Real-time duplicate email check" (§7.4) is an account-enumeration oracle, in tension
   with the no-enumeration security requirement (§6.2 "no email enumeration").
6. **Deduplication:** "MD5 dedup < 2%" is satisfied trivially by a generator that never repeats a combination.
   The metric cannot detect the diversity problem the spec itself warns about (§3.6).
7. **Metrics source:** FR-03-05 wants model metrics "computed from doctor correction data". Corrections are a
   biased sample (doctors only correct what they notice), so they cannot replace a held-out set. Keep both.
8. **Latency target:** p95 < 200 ms inference on "CPU-only hardware" is undefined without a named CPU (D5). At 50
   concurrent users a single-process CPU model cannot meet it without batching or replicas.

---

## C. What is genuinely good and should not be traded away

- **Reproducibility.** Frozen manifests with SHA-256; `verify.py` re-derives from seed 42; the v2d metrics
  reproduced to six decimal places in this audit.
- **Leakage control.** Phrase-group closure holds: 0 exact, 0 phrase, 0 near-duplicate overlap on re-check.
- **Honesty discipline.**
  - Protocols for the six human studies are written, with `\PENDING{}` markers instead of invented values.
  - The 3-condition gate documents which thresholds are unsourced.
  - The refusal to machine-draft patient-facing clinical text is the right instinct. It needs a safety layer
    around it, not replacement.
- **Defence in depth where it exists.**
  - The DB CHECK on role/link consistency.
  - The label-order refusal in the model loader, which caught `saved_model`.
  - Refresh-token reuse detection, non-enumerating password reset, and production config hardening.
- **Test intent.** 425 tests, 93% backend coverage, real PostgreSQL rather than SQLite, and a frontend under strict
  TypeScript with computed contrast tests.

---

## D. What I need from you (all BLOCKED items)

1. **D0** Commit or stash the working tree.
2. **D1** Which spec governs, rule by rule (REMEDIATION_PLAN §0).
3. **D2** `docs/clinical/` source documents.
4. **D3** A named clinician.
5. **D4** Native-speaker reviewers.
6. **D5** Target CPU spec.
7. **D6** Where the v2d weights live.
8. **D7** `docs/compliance/`.
9. **Optional:** permission to install gitleaks, Playwright and Lighthouse on this host to close the unexecuted
   §3.7 checks.
