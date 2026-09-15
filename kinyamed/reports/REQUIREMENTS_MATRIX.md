# Requirements traceability matrix — Phase 0

Audit date 2026-09-14. Branch `audit-p0-p1-and-frontend` @ `7ef50c0` plus the uncommitted working tree
(19 modified, 1 deleted, 21 untracked files at audit start — see AUDIT_REPORT §A.2). Paths are relative to `kinyamed/`.

**Status key** (docs/ENGINEERING_SPEC.md §3.3): `DONE-VERIFIED` = code + passing test + **executed by me in this audit**;
`DONE-UNVERIFIED`; `PARTIAL`; `MISSING`; `INCORRECT` (exists but contradicts the spec); `BLOCKED` (needs
something only the maintainer can supply). Only `DONE-VERIFIED` counts as done.

**Executed in this audit:** backend pytest (213 passed / 0 failed / 0 skipped, 294 s, coverage 93%),
ML pytest (127 passed / 2 skipped, 2,660 s), frontend vitest (85 passed), `tsc` strict, `vite build`,
`ruff`, `mypy --strict`, `npm audit`, alembic upgrade → downgrade base → upgrade, API boot + HTTP probes,
`verify.py --scope sample` (6/6), v2d inference on the frozen reporting set, language-detector and
keyword-baseline measurement, rate-limit / singleton / header probes. `pip-audit`. Not executed (tool absent or
infra absent): gitleaks, OWASP ZAP, Lighthouse, Axe-in-browser,
Playwright, Locust, Docker builds, Kubernetes, Kafka, WebSocket.

**Headline:** 227 requirement rows (plus the 12-row law snapshot in §13). Status counts: **DONE-VERIFIED 13**, DONE-UNVERIFIED 14, PARTIAL 61, INCORRECT 36, MISSING 80, BLOCKED 4 across 208 non-gate rows; the 19 deployment-gate rows (§10) are scored MET 2 / NOT MET 11 / NOT MEASURABLE 4 / NOT DEFENSIBLY MET 1 / MISSING 1. The codebase is a coherent,
well-tested system built to a *different, earlier specification* (the deleted ml_model charter file
charter, Kinyarwanda-first, staff-operated intake). Most v2.0 rows are therefore `MISSING` or
`INCORRECT` against this document, not broken.

Priority column: M/S/C from the spec; `L` = law-derived mandatory addition.

---

## 1. FR-01 — Patient portal

| Req ID | Requirement | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| FR-01-01 | Register: first/last name, country-code phone, age, gender, district | M | INCORRECT | `backend/app/schemas/auth.py:28` `RegisterRequest` has `full_name`, `phone`, `age`, `gender`, `location`; `frontend/src/routes/SignUp.tsx`; test `integration/test_auth.py::test_registration_creates_a_patient_login_and_chart` (ran, pass) | Single `full_name`; no country selector; `patients.phone` **not unique** by design (`models/patient.py:31` shared handsets) so no 409 on duplicate phone; <3 s not measured | Med — spec conflicts with a deliberate product decision (shared handsets) that needs your ruling |
| FR-01-02 | Password + confirm, live strength meter, 8+/upper/digit/special | M | INCORRECT | `schemas/auth.py:15` `PasswordStr` min 12, max 72, **no character-class rules**; test `test_weak_passwords_are_rejected` (ran) | No confirm on sign-up API; no strength meter (grep `strength` in `frontend/src`: 0 hits); policy differs (length-only, NIST-style) | Low — current policy is defensible; spec needs a decision |
| FR-01-03 | Google OAuth sign-in | M | MISSING | `docs/roadmap.md` "Google OAuth 2.0 sign-in — deferred 2026-09-11"; `routes/Login.tsx:28` comment | No endpoints, no client, no users.oauth_* columns | Med — also flagged by repo as a Law 058/2021 data-residency question |
| FR-01-04 | 249-country searchable flag selector | M | MISSING | `schemas/patient.py:15` accepts Rwandan local or raw E.164 only | No selector | Low |
| FR-01-05 | Free text in 10 language combinations, p95 < 250 ms @ 50 users | M | PARTIAL | `routes/v1/triage.py:22`; HTTP latency measured, see MODEL_AUDIT §3 | Model trained on Kinyarwanda only (330,000 rows, 1 language); 0 of 6 code-switch pairs; requires JWT | **High** — 3 of 4 languages and all mixed input are out-of-distribution |
| FR-01-06 | Live language badge, 300 ms debounce, ≥ 92% on 10 combos | M | INCORRECT | Detector `services/triage_service.py:295` (marker-word counts); measured on regenerated v1 text: EN 100%, FR 100%, **KW 87.7%**, **SW 88.3%**, **mixed 33.0%** (n=3,000 each; AUDIT §B.4) | No live badge in UI; accuracy below 92%/85%; no dedicated eval set | High — detection drives response language |
| FR-01-07 | CRITICAL/URGENT/ROUTINE + confidence + per-class probabilities; acc ≥ 87%, CRITICAL recall ≥ 91% per pure language | M | INCORRECT | `schemas/triage.py:35` returns `confidence_score` only — **no probabilities**; v2d accuracy 0.7065, CRITICAL recall 0.8504 (MODEL_AUDIT §4) | Probabilities absent; thresholds not met; EN/FR/SW not measurable (no data) | **Critical** |
| FR-01-08 | Response in all 4 languages simultaneously, all non-null | M | INCORRECT | `services/response_templates.py:82` returns explicit PENDING; `triage_results.ai_response_rw` only column; test `test_a_patient_response_is_never_invented` (ran) | Deliberately unfilled: KW and SW app/SMS templates authored, **EN 0/6, FR 0/6** (`ml_model/docs/STATUS.md`). Direct conflict with the repo's standing rule "speaker-authored or absent" | High — needs your ruling; filling with machine text would violate L1/§10.2 |
| FR-01-09 | SMS confirmation within 5 s | M | PARTIAL | `services/sms_service.py:85`; `UnconfiguredSMSProvider` returns FAILED when enabled (`:61`); tests `test_sms_service.py` (ran, 8 pass) | No Africa's Talking client; flag off; sends nothing without an authored template | Med |
| FR-01-10 | Patient sees live position, 30 s refresh | M | PARTIAL | `GET /api/v1/queue/me` (`routes/v1/queue.py:77`); test `test_patient_can_triage_themselves_and_see_only_their_own_place` (ran) | No patient portal UI; staff board polls at 5 s (`api/hooks.ts:38`) | Med |
| FR-01-11 | Responsive 320–1536 px, 44 px targets | M | DONE-UNVERIFIED | `docs/frontend-limitations.md` §3 ("checked at 360, 414, 768, 1024"); `src/__tests__/spacing-scale.test.ts` (ran, 31 pass — token-level only) | 320 px not tested; no browser test run by me | Low |
| FR-01-12 | Every submission queryable in admin analytics ≤ 60 s | M | PARTIAL | `GET /analytics/language-breakdown`, `/urgency-over-time` read live tables (`routes/v1/analytics.py`); tests `test_analytics_series.py` (ran, 11 pass) | No retraining export pipeline | Low |
| FR-01-13 | Voice input (Web Speech API) | C | MISSING | grep `SpeechRecognition`: 0 | — | Low |
| FR-01-14 | SMS-only 3-exchange triage | S | MISSING | No inbound SMS webhook | — | Med (feature-phone users excluded) |

## 2. FR-02 — Doctor dashboard

| Req ID | Requirement | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| FR-02-01 | Email+password OR Google; identical JWT with DOCTOR role | M | PARTIAL | `routes/v1/auth.py:92`; `test_doctor_can_work_the_queue` (ran) | Password path only | Low |
| FR-02-02 | Sort CRITICAL→URGENT→ROUTINE, arrival within group | M | DONE-VERIFIED | `repositories/queue_repo.py:21` `_QUEUE_ORDER = (priority, created_at, id)`; tests `test_critical_patient_overtakes_earlier_routine_patients`, `test_equal_urgency_keeps_arrival_order`, `test_the_queue_orders_critical_before_routine` (all ran, pass) | No property-based test over random sequences (see §13 mandatory suites) | Low |
| FR-02-03 | WebSocket real-time, new card ≤ 1 s | M | MISSING | `frontend/src/api/hooks.ts:3` "polled rather than pushed because the API has no websocket" | 5 s poll | Med |
| FR-02-04 | CRITICAL pulsing border + audible alert | M | PARTIAL | `components/QueueAnnouncer.tsx` (aria-live; tests ran, 7 pass); `animate-pulse` only on skeleton loaders (`components/ui.tsx:160`) | No pulse on CRITICAL, no sound | Med |
| FR-02-05 | Detail panel: full text, 4 responses, gauge, probabilities, first+last name, **masked phone**, location | M | INCORRECT | `routes/v1/queue.py:41` returns `patient_phone` **unmasked** to staff UI; no detail drawer | Phone unmasked; no probabilities; no 4-language responses | High (L11) |
| FR-02-06 | One-click WAITING→IN_PROGRESS→DONE, 5 s undo | M | PARTIAL | `models/queue.py:44` transitions; `test_status_transition_is_validated` (ran); `routes/Doctor.tsx:60` `window.confirm` instead of undo | No undo (explicitly declined in code comment) | Low |
| FR-02-07 | Assign self or on-duty colleague; name shown | M | PARTIAL | `services/queue_service.py:191`; tests `test_assigning_an_off_duty_doctor_is_refused`, `test_assignment_starts_the_consultation` (ran) | Response has `doctor_id` only, not name; no "assign self" shortcut | Low |
| FR-02-08 | Inline consultation record, outcome enum, autosave | M | MISSING | `models/consultation.py` table exists; **no route, service or UI** (OpenAPI: 0 consultation paths, AUDIT §B.2) | Entire feature | High — no clinical outcome is ever recorded, so FR-03-05 has no data |
| FR-02-09 | Sticky stats header incl. avg wait, on-duty count | M | PARTIAL | `routes/Queue.tsx` 3 urgency count tiles; `routes/Doctor.tsx` on-duty count | No sticky header, no avg wait on board | Low |
| FR-02-10 | Composable filters, URL-synced | S | MISSING | — | — | Low |
| FR-02-11 | Search by name/phone ≤ 200 ms | S | PARTIAL | `GET /patients?search=` (`routes/v1/patients.py:41`), tested `test_patient_routes.py` (ran) | Not on the queue; full name only | Low |
| FR-02-12 | "Mark AI wrong" correction → retraining | S | MISSING | No `is_ai_correct`/`ai_correction` columns or endpoint | — | High for L3: no way to observe CRITICAL→ROUTINE in the field |
| FR-02-13 | Doctor toggles **own** on-duty | M | INCORRECT | `routes/v1/doctors.py:77` any staff may toggle **any** doctor | No ownership check | Low |
| FR-02-14 | WCAG AA, keyboard, urgency text not colour | S | DONE-UNVERIFIED | `components/UrgencyBadge.tsx`; `src/__tests__/a11y.test.tsx` (vitest-axe, ran, 10 pass in jsdom); `contrast.test.ts` (26 pass) | jsdom axe ≠ browser axe; no keyboard walkthrough run | Low |

## 3. FR-03 — Admin panel

| Req ID | Requirement | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| FR-03-01 | Admin creates doctors with full profile; 409 on dup email; welcome email | M | PARTIAL | `schemas/doctor.py` name/email/specialty/is_on_duty; `test_doctor_routes.py` (ran); `POST /users` | No employee_id/phone/health_centre; no email sender (`docs/roadmap.md`) | Low |
| FR-03-02 | Deactivate; blocked on every login method | M | DONE-VERIFIED | `routes/v1/users.py:40`; `services/auth_service.py:162`, `core/dependencies.py:53`; tests `test_deactivated_account_cannot_log_in`, `test_deactivating_an_account_revokes_its_access` (ran, pass) | OAuth path does not exist, so "any method" = password + existing tokens | Low |
| FR-03-03 | Charts: bar, donut, pie, 7×24 heatmap, word cloud; shared date picker | M | PARTIAL | `routes/Dashboard.tsx` (cases per day, throughput, wait by acuity, acuity mix, quoted vs measured, language); `components/charts.tsx` | No heatmap, no word cloud, no date-range picker; < 2 s not measured | Low |
| FR-03-04 | CSV export | S | MISSING | — | — | Low (and L11 scrubbing needed when built) |
| FR-03-05 | Model performance dashboard from doctor corrections | M | MISSING | No corrections data (FR-02-12) | — | High |
| FR-03-06 | System health panel (p50/95/99, Kafka lag, pool, Redis, uptime) | M | MISSING | `/health`, `/ready` only; `/ready` misreports model (see §6.3) | No metrics exporter | Med |
| FR-03-07 | Configurable confidence threshold, audited | S | MISSING | `MODEL_CONFIDENCE_THRESHOLD` defined in `core/config.py:101`, **referenced by 0 lines of app code** (grep, AUDIT §B.6) | Dead setting | High (L4) |
| FR-03-08 | SMS delivery log, retry, DELIVERED webhook | S | PARTIAL | `models/sms_log.py` (PENDING/SENT/FAILED/SKIPPED); analytics "Patient messages" card | No DELIVERED, no retry endpoint, no webhook, no masked recipient column | Low |
| FR-03-09 | Full audit log of every write | M | MISSING | No `audit_logs` table (`alembic check` clean against 11 tables that exclude it); structlog events only | Entire feature | **High** — clinical accountability |

## 4. FR-04 — ML system

| Req ID | Requirement | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| FR-04-01 | Thread-safe singleton, loaded once | M | PARTIAL | `services/triage_service.py:356` `@lru_cache`; warmed in `main.py` lifespan. Probe: 100 threads on a cold cache → builder invoked **100×**, 2 distinct instances (AUDIT §B.6) | `lru_cache` is not a lock. Safe today only because lifespan calls it first | Med — a reload path would load 100× 470 MB |
| FR-04-02 | InferenceResult 7 fields, no nulls | M | INCORRECT | `triage_service.py:40` `Classification` has urgency, possible_conditions, confidence, advice_rw | Missing probabilities, language confidence, model version, duration | High |
| FR-04-03 | conf < threshold → `requires_human_review=True` | M | MISSING | No column, no code path; threshold unused | — | **Critical** (L4) |
| FR-04-04 | CRITICAL recall ≥ 0.91 per pure language; CI blocks | M | INCORRECT | v2d CRITICAL recall 0.8504 (phrase-cluster 95% CI [0.077, 1.000]) on Kinyarwanda only; repo gate uses 0.95 (`ml_model/training/evaluate.py` `MINIMUM_CRITICAL_RECALL`); no CI stage runs it | Not met; 3 languages unmeasurable; no CI gate | **Critical** |
| FR-04-05 | p50 < 150, p95 < 200, p99 < 300 ms CPU | M | INCORRECT (NOT MET) | c=1 p50 132 / p95 217 / p99 258 ms; c=50 p50 7.9 s (MODEL_AUDIT §3.1); target CPU undefined (BLOCKED D5) | Lock serialises all inference; Locust not run | Med |
| FR-04-06 | `evaluate.py` LaTeX with all 15 metrics | M | PARTIAL | `ml_model/training/evaluate.py:216-531` emits macros/tables for accuracy, F1s, per-class, confusion | Not all 15 (no per-language, latency/memory not in table, no CIs); LaTeX compile not run by me | Low |
| FR-04-07 | ≥ 1,000,000 unique rows across 10 combos, MD5 dedup < 2% | M | INCORRECT | v2 corpus 330,000 rows, **1 language**, 165 phrases (DATASET_AUDIT §2); v1 1M corpus regenerable but superseded and machine-drafted | Size and language coverage | **Critical** for the paper claim |
| FR-04-08 | Lang-ID ≥ 92% pure, ≥ 85% mixed | M | INCORRECT | See FR-01-06 measurements | Below threshold; no eval set | High |
| FR-04-09 | 4 responses non-empty for every result | M | INCORRECT | See FR-01-08 | — | High |
| FR-04-10 | Admin-triggered retraining + canary | C | MISSING | — | — | Low |
| FR-04-11 | Deterministic escalate-only red-flag layer **before** the model, 4 languages, lexicon-sourced | L | **INCORRECT** | `triage_service.py:92` `CRITICAL_TERMS` exist but are used **only by `KeywordClassifier`**, which runs *instead of* the model, never before it (`model_classifier.py:175`). Measured as a classifier on the held-out set: CRITICAL recall **0.0566**, CRITICAL→ROUTINE **94.3%** (n=17,942). Red-flag probe on v2d: MODEL_AUDIT §6 | No pre-model layer; no lexicon (`data/lexicon/` absent); term list unsourced (L5) | **Critical** (L2) |
| FR-04-12 | Temperature-scaling calibration, ECE, reliability diagram | L | MISSING | `model_classifier.py:38` docstring: "never calibrated". Measured ECE 0.188 (reporting), 0.179 (stopping split) (MODEL_AUDIT §5) | No calibration step | High |
| FR-04-13 | Cost-sensitive objective | L | PARTIAL | `README.md` "weights the loss by inverse class frequency"; `train_holdout.py` | Inverse-frequency ≠ asymmetric CRITICAL→ROUTINE cost; thresholds are argmax | High |

## 5. FR-05 — Authentication and authorisation

| Req ID | Requirement | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| FR-05-01 | PATIENT/DOCTOR/ADMIN at API; 403 on wrong role; no self-elevation | M | DONE-VERIFIED | `core/dependencies.py:63`; `test_authorization.py` 29 tests (ran, pass) incl. `test_patient_cannot_read_the_queue`, `test_role_link_consistency_is_enforced_by_the_database`; `PATCH /auth/me` rejects role (`test_password_reset.py` ran) | Not "all 30+ endpoints × roles" exhaustively | Low |
| FR-05-02 | Email+password registration with first/last/phone/confirm | M | PARTIAL | See FR-01-01/02 | — | Low |
| FR-05-03 | Google ID token verified against JWKS | M | MISSING | — | — | Med |
| FR-05-04 | OAuth link by email | M | MISSING | — | — | Med |
| FR-05-05 | Access JWT 15 min, **RS256**, claims id/role/first name/email | M | INCORRECT | `core/config.py:66` `JWT_ALGORITHM="HS256"`; claims sub/role/type/jti/iat/exp (`core/security.py:89`); expiry 15 min; tests `test_a_tampered_token_is_rejected`, `test_a_refresh_token_is_not_accepted_as_an_access_token` (ran) | HS256 shared secret; no first name/email claim; no key rotation | Med |
| FR-05-06 | Refresh 7 d, **bcrypt-hashed**, httpOnly **SameSite=Strict** | M | INCORRECT | 7 d ✓; httpOnly ✓ (`test_refresh_token_is_httponly_and_scoped` ran); stored by **`jti` (the token itself is a JWT), not a hash** (`models/user.py:98`); `REFRESH_COOKIE_SAMESITE` default **"lax"** (`config.py:76`) | SameSite and storage differ | Med |
| FR-05-07 | Anonymous triage without JWT, patient by phone | M | INCORRECT | `routes/v1/triage.py:26` `user: CurrentUser`; probe `POST /api/v1/triage` without header → **401** (AUDIT §B.2); test `test_every_data_endpoint_requires_authentication[POST-/api/v1/triage]` asserts the opposite of the spec | Conflicts with the design | Med — needs ruling (anonymous endpoint + rate limit + abuse) |
| FR-05-08 | PATIENT JWT → 403 on queue/consultations/doctors/analytics | M | DONE-VERIFIED | `test_patient_cannot_read_the_queue`, `test_patient_cannot_read_analytics`, `test_patient_cannot_manage_doctors` (ran, pass) | `/consultations/` does not exist | Low |
| FR-05-09 | Login 10 / 15 min per IP, 429 + Retry-After | M | INCORRECT | One global limiter 120 req / 60 s (`config.py:80`), no auth-specific bucket; probe: keyed on client-supplied **`X-Forwarded-For`** → 30/30 requests accepted after exhaustion by rotating the header (AUDIT §B.6); in-memory per process | Bypassable; wrong thresholds | **High** |
| FR-05-10 | Logout via Redis blocklist; Google revoke | M | PARTIAL | DB revocation (`auth_service.py:211`); `test_logout_revokes_the_session` (ran) | No Redis (Redis configured but unused anywhere: grep `redis` in `app/` → config only) | Low — DB revocation is sound |
| FR-05-11 | 8 chars + classes; bcrypt cost 12 | M | PARTIAL | Cost 12 default, enforced in production (`config.py:151`, `test_production_requires_a_strong_bcrypt_cost` ran); policy length-only min 12 | Character classes absent; no timing test | Low |
| FR-05-12 | 6-digit email OTP, 10 min | S | INCORRECT | `auth_service.py:273` 32-byte URL-safe token, **SMS**, **30 min**, hash stored, single use; `test_password_reset.py` 16 tests (ran) | Different channel/format/TTL | Low — current design is arguably stronger; SMS body contains token (not logged) |
| FR-05-13 | Refresh rotation + reuse detection revokes family | L | DONE-VERIFIED | `auth_service.py:185` reuse → `revoke_all_for_user`; tests `test_refresh_rotates_the_token`, `test_reusing_a_rotated_refresh_token_ends_every_session` (ran, pass) | Revokes *all user sessions*, not a family (stricter); no `family_id` column | Low |

## 6. Non-functional requirements

### 6.1 Performance

| Req ID | Requirement | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| NFR-P-01 | Triage API p50<200 p95<350 p99<500 @ 50 users | M | INCORRECT (NOT MET) | Measured over HTTP with v2d: c=1 p50 363 / p95 1,501 ms; c=50 p50 34 s with **136/200 HTTP 503** (DB pool exhausted while requests wait on the model lock) — MODEL_AUDIT §3.2; threads not Locust; host under swap | No Prometheus histogram | **High** |
| NFR-P-02 | Inference p50<150 p95<200 CPU | M | INCORRECT (NOT MET) | In-process c=1 p50 132 / p95 217 ms; c=10 p50 1,566 ms (single `threading.Lock`) — MODEL_AUDIT §3.1 | Serialised inference | Med |
| NFR-P-03 | WebSocket update < 1 s | M | MISSING | — | — | Med |
| NFR-P-04 | Portal FCP < 1.5 s on 3G | M | BLOCKED | Lighthouse not installed on audit host | No measurement | Low |
| NFR-P-05 | TTI < 3.0 s; JS < 200 KB gz | M | PARTIAL | `vite build` measured JS **77.6 KB gz** + CSS 4.2 KB gz (no MUI in tree) | TTI not measured | Low |
| NFR-P-06 | Dashboard render < 500 ms @ 200 patients | M | MISSING | No perf test | — | Low |
| NFR-P-07 | DB p99 < 50 ms; zero N+1 | M | PARTIAL | `test_queue_read_does_not_issue_a_query_per_row` (ran, pass) | Query counts asserted for queue only; no EXPLAIN on seeded data | Low |
| NFR-P-08 | Country selector < 100 ms | M | MISSING | No selector | — | Low |
| NFR-P-09 | OAuth < 3 s | M | MISSING | — | — | Low |
| NFR-P-10 | Uptime ≥ 99.5% | M | MISSING | No deployment, no probe | — | Med |

### 6.2 Security

| Req ID | Requirement | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| NFR-S-01 | TLS 1.3, HSTS | M | MISSING | No Nginx/TLS config (`infrastructure/` has 0 files); probe: no `Strict-Transport-Security` header | — | Med |
| NFR-S-02 | No secrets in VCS; gitleaks in CI | M | PARTIAL | `.env` untracked (`git ls-files`); history pattern-scan found only placeholders (AUDIT §B.7); **gitleaks not installed, not in CI** | Scanner not run | Med |
| NFR-S-03 | Google ID token JWKS verification | M | MISSING | — | — | — |
| NFR-S-04 | Zero raw SQL | M | DONE-UNVERIFIED | grep `text(` in `app/`: only `SELECT 1` in `routes/v1/health.py` | ZAP not run | Low |
| NFR-S-05 | XSS: CSP header, DOMPurify | M | PARTIAL | React escaping; probe: **no CSP header**; no `dangerouslySetInnerHTML` (grep 0) | CSP absent; token in `localStorage` (`frontend/src/lib/auth.ts:3`) | Med |
| NFR-S-06 | CSRF | M | DONE-UNVERIFIED | Bearer header on writes; refresh cookie path-scoped (`routes/v1/auth.py:38`) | SameSite=lax; no CSRF test | Low |
| NFR-S-07 | Rate limiting 100/min write, 10/15 min auth | M | INCORRECT | See FR-05-09 | XFF bypass | High |
| NFR-S-08 | Data minimisation; no PII in logs | M | **INCORRECT** | Measured in this run: `sms_stubbed ... to=+250788123456` (`services/sms_service.py:55`) in backend test output; HTTP load log count in MODEL_AUDIT §3; queue API returns unmasked phone | L11 violated | **High** |
| NFR-S-09 | OAuth account security | M | MISSING | — | — | — |
| NFR-S-10 | Dependabot, pip-audit, npm audit, trivy | M | INCORRECT | `npm audit`: **7 vulns (1 critical vitest ≤3.2.5, 5 high incl. postcss, 1 moderate)**; `pip-audit` (run by me): **25 known vulns in 3 backend runtime packages** — PyJWT 2.10.1, python-multipart 0.0.20, pydantic-settings 2.14.1 — and 3 in ML (transformers 5.8.1, setuptools 81.0.0); none of these scanners in CI (`.github/workflows/ci.yml`) | Upgrade PyJWT/python-multipart (runtime, auth-path) first | **High** (runtime auth deps) |

### 6.3 Reliability

| Req ID | Scenario | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| NFR-R-01 | ML model not loaded → 503 + manual triage | M | INCORRECT | `model_classifier.py:175` falls back to **keyword baseline** silently-with-log outside production; production refuses to boot (`test_production_refuses_to_start_on_the_baseline` ran). A runtime inference exception propagates as 500; no PENDING state; `/ready` imports non-existent `app.ml.model_loader` (`routes/v1/health.py:36`, mypy `import-not-found`) so it **always reports `ml_model: not_installed`** — probe returned that with model loaded (MODEL_AUDIT §3) | Fail-unsafe in dev/staging (baseline C→R 94.3%); readiness never gates on model | **Critical** (L4) |
| NFR-R-02 | Google OAuth unavailable | M | MISSING | — | — | — |
| NFR-R-03 | DB lost → retry 3× backoff | M | PARTIAL | `pool_pre_ping=True` (`core/database.py:21`) | No retry/backoff; no kill test | Med |
| NFR-R-04 | Redis unavailable fallback | M | MISSING | Redis unused | — | Low |
| NFR-R-05 | Kafka consumer failure, DLQ | M | MISSING | No Kafka code (`KAFKA_*` settings only) | — | Med |
| NFR-R-06 | SMS failure → FAILED + retry | M | PARTIAL | `sms_service.py:144` records FAILED; `test_unconfigured_provider_fails_loudly` (ran) | No retry | Low |
| NFR-R-07 | Pod crash / readiness | M | MISSING | No K8s manifests | — | Med |

### 6.4 Accessibility

| Req ID | Requirement | Pri | Status | Evidence | Gap | Risk |
|---|---|---|---|---|---|---|
| NFR-A-01 | Contrast ≥ 4.5:1 / 3:1 | M | DONE-VERIFIED | `src/__tests__/contrast.test.ts` computes WCAG ratios over the Tailwind token pairs (ran, 26 pass) | Tokens are the repo's own palette, not §7.2's | Low |
| NFR-A-02 | Urgency = colour + icon + text | M | PARTIAL | `components/UrgencyBadge.tsx` text + colour; `a11y.test.tsx` (ran) | Icon not verified | Low |
| NFR-A-03 | Keyboard-only full flow | M | BLOCKED | No browser automation on host | — | Low |
| NFR-A-04 | Screen reader; `aria-live=assertive` for CRITICAL | M | PARTIAL | `components/QueueAnnouncer.tsx`; `QueueAnnouncer.test.tsx` (ran, 7 pass) | NVDA session not run | Low |
| NFR-A-05 | Country selector a11y | M | MISSING | — | — | — |
| NFR-A-06 | 44×44 touch targets | M | DONE-UNVERIFIED | commit `7ef50c0` "the 44px targets were fiction" + `spacing-scale.test.ts` | Not measured in a browser | Low |
| NFR-A-07 | rem, ≥ 14 px, 200% zoom | M | PARTIAL | Tailwind rem scale | `text-xs` (12 px) used widely, e.g. `routes/Queue.tsx`, `routes/Triage.tsx` | Low |
| NFR-A-08 | prefers-reduced-motion | M | MISSING | grep 0 hits | Few animations exist | Low |

## 7. UI/UX component specifications

The frontend is **React 18 + TypeScript 5.5 strict + Tailwind 3 + TanStack Query + React Router**, hand-built components.
**MUI, Zustand, React Hook Form, Zod, Recharts, Framer Motion, Axios, Playwright are not dependencies** (`frontend/package.json`).
It is a single staff-operated application (triage intake, queue, doctor board, dashboard, settings), not three role-separated
views; there is no patient-facing portal. Every row below is scored against that reality.

### 7.1 Stack

| Req ID | Item | Status | Evidence / gap |
|---|---|---|---|
| UI-STACK-01 | React 18 | DONE-VERIFIED | `react 18.3.1`; build + 85 tests ran |
| UI-STACK-02 | TypeScript 5 strict, no `any` | DONE-VERIFIED | `tsconfig.app.json` `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`; `tsc -b` exit 0; `any` count 0; `@ts-expect-error` 2 (both tests, commented) |
| UI-STACK-03 | Tailwind CSS | DONE-UNVERIFIED | `tailwindcss 3.4.10` |
| UI-STACK-04 | Material UI v5 | MISSING | not a dependency |
| UI-STACK-05 | Vite 5 | DONE-VERIFIED | `vite 5.4.2`, build ran 21 s |
| UI-STACK-06 | TanStack Query | DONE-UNVERIFIED | `@tanstack/react-query 5.51.23` |
| UI-STACK-07 | Zustand | MISSING | — |
| UI-STACK-08 | React Hook Form + Zod | MISSING | — |
| UI-STACK-09 | Recharts | MISSING | hand-rolled SVG `components/charts.tsx` |
| UI-STACK-10 | Framer Motion | MISSING | — |
| UI-STACK-11 | Axios | MISSING | `fetch` wrapper `api/client.ts` |
| UI-STACK-12 | Playwright | MISSING | — |
| UI-TOK | §7.2 colour tokens in one MUI theme, no hex in components | INCORRECT | Repo palette in `tailwind.config.js` (e.g. CRITICAL `#a2120b`, not `#DC2626`); hex literals in components: 0 (2 in comments) |
| UI-TYPO | §7.3 type scale (Inter/JetBrains Mono/Noto Sans) | PARTIAL | `tnum`/text scale in Tailwind; 12 px used; spec itself conflicts (13/12 px vs ≥ 14 px rule) — flagged in AUDIT |

### 7.4 Registration / login form (all fields)

| Req ID | Field | Status | Evidence / gap |
|---|---|---|---|
| UI-FORM-01 | First Name | MISSING | single full name (`routes/SignUp.tsx`) |
| UI-FORM-02 | Last Name | MISSING | — |
| UI-FORM-03 | Email + async duplicate check | PARTIAL | email field; duplicate reported on submit (`test_duplicate_email_is_rejected` ran) — an async "is taken" probe would be an enumeration oracle, conflicting with the repo's no-enumeration rule |
| UI-FORM-04 | Phone (flag + dial + local) | MISSING | plain text phone |
| UI-FORM-05 | Password + strength meter | PARTIAL | field present; no meter |
| UI-FORM-06 | Confirm password | PARTIAL | present on password reset (`routes/NewPassword.tsx`); **absent on sign-up** (`routes/SignUp.tsx:98` single password field) |
| UI-FORM-07 | Age | DONE-UNVERIFIED | `RegisterRequest.age` |
| UI-FORM-08 | Gender enum (M/F/Non-binary/Prefer not) | INCORRECT | `schemas/patient.py:18` `male/female/other/unknown`; `RegisterRequest.gender` is free `str` |
| UI-FORM-09 | District autocomplete (30 districts) | MISSING | `location` free text |
| UI-FORM-10 | Google Sign-In button | MISSING | removed deliberately |
| UI-FORM-11 | OR divider | MISSING | — |

### 7.5 Patient portal components

| Req ID | Component | Status | Evidence / gap |
|---|---|---|---|
| UI-PP-01 | Language selector (KW/EN/FR/SW/AUTO) | MISSING | — |
| UI-PP-02 | Symptom input, rotating placeholder, ≥ 10 chars | PARTIAL | `routes/Triage.tsx` textarea (staff-facing); API min 3 chars (`schemas/triage.py:19`) vs spec/table 10 |
| UI-PP-03 | Language detection badge | PARTIAL | detected language shown after submit only |
| UI-PP-04 | AI processing skeleton | PARTIAL | "Assessing…" button state |
| UI-PP-05 | Urgency result card + confidence bar | PARTIAL | `UrgencyBadge` + score explicitly labelled "uncalibrated softmax value, not a probability" (`routes/Triage.tsx`) — more honest than the spec's bar |
| UI-PP-06 | Multilingual response tabs | INCORRECT | `components/PendingResponse.tsx` shows single-language or PENDING |
| UI-PP-07 | Queue widget "position #3 of 12" | PARTIAL | position shown post-submit |
| UI-PP-08 | SMS confirmation preview | MISSING | — |
| UI-PP-09 | Errors in patient's language with next step | PARTIAL | English `Alert`s; offline vs error distinguished (`routes/Queue.tsx`) |

### 7.6 Doctor dashboard components

| Req ID | Component | Status | Evidence / gap |
|---|---|---|---|
| UI-DD-01 | Sticky stats AppBar chips | PARTIAL | count tiles, not sticky, not filter-on-click |
| UI-DD-02 | Queue board animated list | PARTIAL | `QueueTable`/`QueueCards`/`QueueDenseTable`; no animation |
| UI-DD-03 | Patient card (name, lang chip, 80-char preview, wait, doctor, status) | PARTIAL | tested `QueueTable.test.tsx` (ran, 8 pass); no assigned-doctor name |
| UI-DD-04 | Critical alert snackbar + sound | PARTIAL | `QueueAnnouncer` live region; no snackbar/sound |
| UI-DD-05 | Detail drawer 480 px | MISSING | — |
| UI-DD-06 | Confidence gauge colour bands | MISSING | deliberately not rendered as probability |
| UI-DD-07 | Doctor assignment autocomplete + self-assign | PARTIAL | `<select>` of on-duty doctors (`routes/Doctor.tsx`) |
| UI-DD-08 | Consultation form + autosave | MISSING | no API |
| UI-DD-09 | AI correction flow | MISSING | — |
| UI-DD-10 | Filter + search, URL sync | MISSING | — |
| UI-DD-11 | Status transition + undo toast | PARTIAL | "Seeing now" / "Done" + `window.confirm`; offers "Done" on WAITING rows although the API only allows IN_PROGRESS→DONE (`models/queue.py:45`) — not exercised by me |

### 7.7 Responsive breakpoints

| Req ID | Breakpoint | Status | Evidence / gap |
|---|---|---|---|
| UI-BP-xs | 320 px single column, 48 px targets | DONE-UNVERIFIED | not tested at 320 (limitations doc lists 360) |
| UI-BP-sm | 375 px | DONE-UNVERIFIED | — |
| UI-BP-md | 768 px | DONE-UNVERIFIED | `routes/Doctor.tsx` comment: table overflow fixed at 768 |
| UI-BP-lg | 1024 px three-column | PARTIAL | cards→table switch at `lg`; no 3-column layout |
| UI-BP-xl | 1280 px analytics sidebar | MISSING | — |
| UI-BP-2xl | 1536 px, 1400 px max width | DONE-UNVERIFIED | — |

### 7.8 Animation and motion

| Req ID | Element | Status |
|---|---|---|
| UI-MO-01 | CRITICAL border pulse | MISSING |
| UI-MO-02 | New card enter | MISSING |
| UI-MO-03 | Urgency result reveal | MISSING |
| UI-MO-04 | Detail drawer slide | MISSING |
| UI-MO-05 | Critical alert banner | MISSING |
| UI-MO-06 | Language badge crossfade | MISSING |
| UI-MO-07 | Queue FLIP reorder | MISSING |
| UI-MO-08 | Stats counter spring | MISSING |
| UI-MO-09 | Tab switch | MISSING |
| UI-MO-10 | prefers-reduced-motion | MISSING (moot while there is no motion) |

## 8. Data model — the 11 tables

Live schema = `alembic upgrade head` on an empty PostgreSQL 16 database, executed; `alembic check` reported
"No new upgrade operations detected" (models ≡ migrations); `downgrade base` left only `alembic_version`, zero
enums, zero sequences; re-upgrade clean. **Live tables (11):** `analytics, consultations, doctors, patients,
password_reset_tokens, queue, refresh_tokens, sms_logs, symptom_reports, triage_results, users`.

| Req ID | Table (spec) | Status | Evidence | Gap vs §8 | Risk |
|---|---|---|---|---|---|
| DM-01 | `users` | INCORRECT | `models/user.py:34` | `full_name` not first/last; `hashed_password` NOT NULL, no oauth_provider/oauth_id/avatar_url/employee_id/specialty/health_centre/phone; has `patient_id`/`doctor_id` + DB CHECK `ck_users_role_link_consistency` (tested) | Med |
| DM-02 | `patients` | INCORRECT | `models/patient.py:17` | `name` not first/last; phone **not UNIQUE** (deliberate); no country_code; `location` not district; gender free string; age CHECK 0–130 (spec >0 <130) | Med |
| DM-03 | `symptom_reports` | PARTIAL | `models/symptom_report.py` | no language_confidence, no input_method, no LENGTH ≥ 10 CHECK; `language_detected` String(20) not enum | Low |
| DM-04 | `triage_results` | INCORRECT | `models/triage_result.py:42` | no probabilities JSONB, only `ai_response_rw` (nullable), no requires_human_review, **no model_version**, no rules_layer_triggered/reason, no model_urgency_raw; confidence nullable | **High** — cannot tell which model produced a decision (L3 per-version logging impossible) |
| DM-05 | `queue_entries` | PARTIAL | table `queue`, `models/queue.py:63` | `queue_number` globally UNIQUE via sequence (never resets per day; spec: per calendar day); no stored `queue_position` (derived on read — better); `started_at` ≈ `checked_in_at`; `completed_at` set on DONE/CANCELLED (tested); extra CANCELLED status | Low |
| DM-06 | `consultations` | INCORRECT | `models/consultation.py:17` | single `diagnosis`, free-text `outcome`, no follow_up_date / is_ai_correct / ai_correction; FK to `doctors` not `users`; **no API** | High |
| DM-07 | `sms_logs` | PARTIAL | `models/sms_log.py:26` | no phone_sent_to, delivered_at, retry_count, DELIVERED; SKIPPED added; `provider_message_id` **not indexed** | Low |
| DM-08 | `analytics_daily` | INCORRECT | table `analytics` | cumulative totals (noted in `routes/v1/analytics.py:69`); API writes via `POST /analytics/daily/snapshot` (spec: computed only); no JSONB breakdowns, median, peak_hour | Low |
| DM-09 | `model_evaluations` | MISSING | — | Run records are JSON files (`ml_model/training/run_records/`) not a table; no single-active index | Med |
| DM-10 | `refresh_tokens` | PARTIAL | `models/user.py:88` | `jti` + `revoked_at` instead of token_hash/is_revoked; no created_by_ip, oauth_provider, family_id; `expires_at` indexed ✓ | Low |
| DM-11 | `audit_logs` | MISSING | — | Replaced in practice by `password_reset_tokens` in the count of 11 | **High** (FR-03-09) |
| DM-X1 | `TimestampedModel` id/created_at/updated_at | DONE-VERIFIED | `models/base.py:17`; migration `bbb8e77ab79d`; alembic up/down/check executed | `updated_at` via ORM `onupdate` only, no DB trigger (raw writes won't bump it) | Low |
| DM-X2 | Every change via Alembic with tested downgrade | DONE-VERIFIED | executed upgrade→downgrade base→upgrade on empty DB, all 4 revisions | Downgrade not in CI | Low |
| DM-X3 | Atomic triage write (report+result+queue+audit) | PARTIAL | `services/triage_service.py:399-421` single commit; `test_triage_records_the_full_chain` (ran) | No rollback test; no audit row | Med |
| DM-X4 | Race-safe queue number | DONE-UNVERIFIED | Postgres sequence `queue_number_seq`; `test_queue_numbers_are_never_reused` (ran, sequential only) | No concurrent test | Low |

## 9. Dataset standards (§9.1)

| Req ID | Standard | Status | Evidence (DATASET_AUDIT) |
|---|---|---|---|
| DS-01 | ≥ 1,000,000 unique after dedup | INCORRECT | v2 (trained-on) corpus: 330,000 rows; README still describes the superseded v1 1M corpus |
| DS-02 | Pure languages 10–15% each; mixed 40–60% | INCORRECT | v2: kinyarwanda 100% |
| DS-03 | Class balance 28–38 / 32–42 / 28–38 | DONE-VERIFIED | v2 re-counted over all rows: CRITICAL 33.0%, URGENT 34.0%, ROUTINE 33.0% |
| DS-04 | 80+ domains, ≥ 500 per domain | INCORRECT | 9 domains; smallest family 432 rows (`URGENT:neurological`) |
| DS-05 | Duplicate rate < 2% | PARTIAL | Exact MD5 (lower/strip) **0 / 330,000**; MinHash J ≥ 0.85 within-train **2.77%** (lower bound; repo's 0.80 scan 8.71%); only 165 phrases / 360 word types — dedup passes by construction and says nothing about diversity (DATASET_AUDIT §3, §5) |
| DS-06 | Length 20–512 chars | DONE-VERIFIED | min 31, median 132, max 272 chars; 0 rows out of bounds (measured over all 330,000) |
| DS-07 | 1,500-row nurse review, κ ≥ 0.80 | BLOCKED | protocol `ml_model/docs/protocols/d1-annotation-protocol.md`; no second annotator, no clinician |
| DS-08 | Code-switch naturalness ≥ 3.5/5 | BLOCKED | 0 mixed rows in v2; instrument `d3-speaker-rating-instrument.md` |
| DS-09 | Release CSV+Parquet, CC BY 4.0, datasheet | MISSING | no datasheet; no Parquet; licence not declared per row |

## 10. Deployment gate — the 15 metrics (§9.2)

Measured on v2d, frozen phrase-holdout **reporting** subset (Kinyarwanda only). CIs: MODEL_AUDIT §4.

| Req ID | Metric | Threshold | Measured | Status |
|---|---|---|---|---|
| GATE-01 | Overall accuracy (n=100,000) | ≥ 82% | 0.7065 (n=17,942 rows / 9 distinct phrases) | NOT MET |
| GATE-02 | Weighted F1 | ≥ 0.83 | 0.6953 | NOT MET |
| GATE-03 | Macro F1 | ≥ 0.80 | 0.7724 | NOT MET |
| GATE-04 | CRITICAL precision | ≥ 0.88 | 0.6633 | NOT MET |
| GATE-05 | CRITICAL recall, each pure language | ≥ 0.91 | KW 0.8504; EN/FR/SW no data | NOT MET (KW) / NOT MEASURABLE (EN, FR, SW) |
| GATE-06 | CRITICAL F1 | ≥ 0.89 | 0.7453 | NOT MET |
| GATE-07 | CRITICAL→ROUTINE FN rate | < 1.0% | 0.00% on the reporting set (0 of 8,962) | NOT DEFENSIBLY MET — only 4 CRITICAL phrases in the set; red-flag probe sent 11 of 20 emergency inputs to ROUTINE (MODEL_AUDIT §6) |
| GATE-08 | URGENT recall | ≥ 0.86 | 0.4963 | NOT MET |
| GATE-09 | Kinyarwanda accuracy | ≥ 80% | 0.7065 | NOT MET |
| GATE-10 | English accuracy | ≥ 86% | — | NOT MEASURABLE (no English eval data) |
| GATE-11 | French accuracy | ≥ 84% | — | NOT MEASURABLE |
| GATE-12 | Swahili accuracy | ≥ 80% | — | NOT MEASURABLE |
| GATE-13 | Mixed-language accuracy | ≥ 82% | — | NOT MEASURABLE (0 mixed rows) |
| GATE-14 | Latency p50/p95 CPU | < 150 / < 200 ms | in-process c=1 p50 132 / p95 217 ms; c=50 p50 7,939 / p95 8,834 ms | NOT MET |
| GATE-15 | Memory @ 50 concurrent | < 2 GB | 1,416 MB server HWM (1,431 MB in-process) | MET |
| GATE-X1 | Red-flag suite 100% | 100% | no suite exists | MISSING |
| GATE-X2 | ECE ≤ 0.05 (validation) | ≤ 0.05 | 0.179 (stopping split) | NOT MET |
| GATE-X3 | Lang-ID ≥ 92% / ≥ 85% | — | KW 87.7%, SW 88.3%, mixed 33.0% (v1 text) | NOT MET |
| GATE-X4 | No split leakage | 0 | exact 0, phrase 0 (manifest + re-check, DATASET_AUDIT §4) | MET (phrase split) |

## 11. CI/CD stages (§12.1)

`.github/workflows/ci.yml` (working tree, +32 uncommitted lines) has jobs: reproducibility, reproducibility-full,
training-tests, hygiene, backend, frontend, lint. **I could not observe a CI run** (`gh` not installed; no network
check performed) — every row is at most DONE-UNVERIFIED for "runs in CI".

| Req ID | Stage | Status | Evidence / gap |
|---|---|---|---|
| CI-01 | Lint + type check (ruff, mypy strict, eslint, tsc, prettier) | PARTIAL | ruff check + format in CI (ran locally: clean, 204 files); `tsc` via `npm run typecheck` (ran: clean). **mypy strict not in CI and fails: 20 errors in 11 files**; no eslint/prettier config |
| CI-02 | Unit tests (pytest ≥ 94, vitest) | DONE-UNVERIFIED | jobs `backend`, `frontend`, `training-tests`; locally 213 + 127 + 85 pass. No coverage report in CI |
| CI-03 | Integration (ephemeral PG + Redis + Kafka, OAuth mock) | PARTIAL | Postgres service container in `backend` job; no Redis/Kafka/OAuth |
| CI-04 | Security scan (pip-audit, npm audit, trivy, gitleaks) | MISSING | none |
| CI-05 | ML evaluation gate on `saved_model/` changes | MISSING | no job invokes `evaluate.py`; weights are git-ignored so a path trigger could never fire |
| CI-06 | Docker build + GHCR | MISSING | no Dockerfile (`infrastructure/docker/` empty) |
| CI-07 | Staging deploy + smoke | MISSING | — |
| CI-08 | Production deploy, K8s rolling, auto-rollback | MISSING | `infrastructure/kubernetes/` empty |

## 12. Test types (§13)

| Req ID | Test type | Status | Evidence / gap |
|---|---|---|---|
| TT-01 | Unit: services (100% of methods) | PARTIAL | service coverage 89–98% except `model_classifier.py` **41%**; SMS in 4 languages not tested (EN/FR templates absent) |
| TT-02 | Unit: ML inference | PARTIAL | `tests/unit/test_model_classifier.py` tests only production refusal; singleton, threshold, 4 responses, C→R: none. ML package `test_checkpoint.py` (9, ran) covers training resume |
| TT-03 | Unit: auth JWT + OAuth | PARTIAL | JWT/refresh/rotation/logout tested (ran); OAuth none; bcrypt timing none |
| TT-04 | Unit: repositories on all 11 tables | PARTIAL | exercised through integration tests on real Postgres (deliberately not SQLite, `conftest.py` docstring); no audit_log assertion possible |
| TT-05 | Integration: API, 403 on all protected endpoints, 429 | PARTIAL | `test_authorization.py` 29 (ran); **every triage integration test runs the keyword baseline, never the model** (`TRIAGE_MODEL_PATH` unset in `conftest.py`) |
| TT-06 | Integration: OAuth flow | MISSING | — |
| TT-07 | Integration: Kafka + WebSocket | MISSING | — |
| TT-08 | Performance: Locust | MISSING | ML latency script `ml_model/training/latency.py` exists (in-process only) |
| TT-09 | Frontend unit (Vitest + RTL) | PARTIAL | 6 files / 85 tests (ran); no PhoneField/PasswordStrength/Google button (components don't exist) |
| TT-10 | Frontend E2E Playwright × 3 browsers | MISSING | `docs/frontend-limitations.md` §4 |
| TT-11 | Accessibility Axe + Playwright | PARTIAL | `vitest-axe` in jsdom (ran, 10 pass) |
| TT-12 | Security ZAP + gitleaks | MISSING | — |
| TT-13 | ML evaluation gate | PARTIAL | `evaluate.py` 3-condition gate exists and is honest about unsourced thresholds; not the 15-metric gate; not in CI; never demonstrated blocking in CI |
| TT-M1 | Clinical safety regression corpus (append-only) | MISSING | — |
| TT-M2 | Queue invariant property test | MISSING | example-based ordering tests only |
| TT-M3 | PII leak scan (logs, Kafka, errors, CSV) | MISSING | a scan would fail today (NFR-S-08) |
| TT-M4 | Audit completeness per write endpoint | MISSING | no audit table |

## 13. Laws (§2) — compliance snapshot

| Law | Status | Evidence |
|---|---|---|
| L1 triage only + escalation instruction | PARTIAL | model predicts urgency only; `possible_conditions=""` for the model, but **the keyword baseline returns diagnosis-like strings** ("Possible malaria, typhoid or other infection", `triage_service.py:337`) into `triage_results.possible_conditions` and the API response; no escalation line (templates pending) |
| L2 red-flag layer before model, escalate-only | **VIOLATED** | FR-04-11 |
| L3 CRITICAL→ROUTINE < 1% logged per model version | **VIOLATED** | no `model_version` on results; C→R 0.00% on the reporting set (0 of 8,962) measured |
| L4 fail safe to human review | **VIOLATED** | NFR-R-01, FR-04-03 |
| L5 clinical sources from `docs/clinical/` | **BLOCKED** | `docs/clinical/` absent; `CRITICAL_TERMS` unsourced |
| L6 no unmeasured metric published | **VIOLATED** | root `README.md` states both "Macro F1 0.7724 … CRITICAL recall 0.8504" **and** "No model has been trained on the leakage-controlled splits yet … no accuracy claims"; also "1,000,000 rows … 184 seed phrases", "make test — 41 tests" — all stale against disk |
| L7 no faked gates | COMPLIANT (observed) | no stubbed/xfail tests; 1 no-assert test (`ml_model/tests/test_leakage.py::test_a_declared_concept_group_with_no_phrases_yet_does_not_raise`, intentionally a no-raise test) |
| L8 frozen hashed splits + leakage check | COMPLIANT | manifests with SHA-256; sample verify 6/6 executed; leakage re-checked |
| L9 no real patient data | COMPLIANT (observed) | corpus is generated |
| L10 approvals before real-patient ingestion | BLOCKED | `docs/compliance/` absent; no real-patient ingestion built |
| L11 no PII in logs | **VIOLATED** | NFR-S-08 |
| L12 no secrets in VCS, gitleaks in CI | PARTIAL | NFR-S-02 |
