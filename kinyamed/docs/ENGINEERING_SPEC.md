# KinyaMed engineering specification — medical triage and patient queue system

**Version** 2.0 (consolidated 2026-09-15) · **Scope** the engineering standards, safety laws, requirements, dataset
standards and deployment gates that code, tests and reports in this repository cite as `ENGINEERING_SPEC`.

This document consolidates the project's engineering requirements, including those taken from the Software
Requirements Specification v2.0 (`KinyaMed_SRS_v2_0.docx`, not in the repository). Section and law numbers are
stable: a citation such as "ENGINEERING_SPEC L2" or "ENGINEERING_SPEC §9.2 gate 5" refers to the numbered item
below. Sections that no file cites are not reproduced here.

**Numbers without a source.** Several numbers below sit in safety-critical positions with no stated clinical or
operational source, no derivation, and no check that they can be measured or met. They are marked
**[unsourced]** and are recorded as one systemic specification failure in `reports/STATE.md` (SRS corrections
A28, A29, A30). Where this document and a report disagree about a number's status, the report's measurement wins;
the number is never lowered to make a gate pass.

---

## §1 Priorities and practitioner standards

**Priority order when concerns conflict:** patient safety > correctness > performance > aesthetics > speed of
delivery.

| Discipline | Standard |
|---|---|
| Software engineering | Typed, tested, observable code that a staff-level reviewer would approve without comment. No dead code, no unexplained TODO, no silent failure path. |
| Interface and experience design | Designed for a nurse with 40 seconds and a patient on a 320 px feature phone over 3G. WCAG 2.1 AA is a functional requirement. |
| Machine learning | Every metric is a claim that must survive peer review. No number is reported that was not measured on a held-out set the model was not trained on. |

The intended audience of results is both academic reviewers and health workers; both penalise unverified claims.

## §2 Laws

The laws override every other section.

### §2.1 Clinical safety

- **L1** The system performs **triage prioritisation only**. It never diagnoses, never prescribes and never
  discourages care. Every patient-facing output ends with an escalation instruction in the patient's language.
- **L2** A deterministic **red-flag rules layer** runs **before** the ML model and can only **escalate**, never
  de-escalate. A red-flag term in any supported language forces CRITICAL whatever the model outputs, and the model
  can never override this layer. (Terms come from the validated lexicon, §10.6. The layer is built with an empty
  term table until terms are clinically validated; a ruling of 2026-09-15 keeps triage fail-closed when the model
  is unavailable, whatever the match: `reports/STATE.md`, ruling H6.)
- **L3** A CRITICAL case classified ROUTINE is a **P0 incident class**. Its measured rate must stay below 1.0%
  **[unsourced]** and is logged per model version permanently. In any cost-sensitive objective, CRITICAL→ROUTINE is
  strictly the most expensive error.
- **L4** When the model is unavailable, uncertain, or below threshold the system **fails safe**: the case requires
  human review and is surfaced to a clinician; it is never silently assigned ROUTINE.
- **L5** Emergency numbers, referral pathways and the triage taxonomy come from documents in `docs/clinical/`
  (Rwanda MoH / RBC / WHO). They are never written from memory. If the document is absent, the work stops until it
  is supplied.

### §2.2 Truth in measurement

- **L6** No metric appears in a README, model card, paper, dashboard or commit unless a reproducible, committed
  script produced it on a held-out set. A metric that has not been run is written `NOT YET MEASURED`. No number is
  typed into prose by hand where a script can emit it.
- **L7** No test is fabricated, stubbed or hard-coded to make a gate pass. A gate failure reported honestly is a
  good outcome; a faked pass is disqualifying.
- **L8** Data splits are created once, hashed, committed and never regenerated. A leakage check (exact and
  near-duplicate, across splits) runs before every training run and its result is printed.

### §2.3 Data and privacy

- **L9** No real patient data in the repository, ever. Development uses synthetic or consented de-identified data.
- **L10** Work with real patients requires Rwanda National Health Research Committee / IRB approval and compliance
  with Rwanda's personal data protection law, with the current instrument verified, not cited from memory. Until
  approvals are in `docs/compliance/`, real-patient ingestion is not built.
- **L11** No personally identifying information in logs, errors, event payloads, analytics or exported CSVs. Phone
  numbers are masked everywhere except their stored column. A test asserts this.
- **L12** No secrets in version control. Secret scanning runs in CI; only `.env.example` is committed.

### §2.4 Engineering discipline

- **L13** Smallest verifiable increments. One concern per commit. Conventional commit messages.
- **L14** No force-push, history rewrite, table drop or destructive migration without the maintainer's explicit
  approval of the exact SQL or command.
- **L15** Red, green, refactor: the failing test is written first.
- **L16** Uncertainty about a clinical, legal or linguistic fact stops the work until a qualified person answers.
  Guessing is not permitted. Questions only a person can answer are recorded with what they block.

## §3 Audit standards

### §3.1 Repository inventory

The audit records the repository tree and size per directory; installed versus specified versions (React 18,
TypeScript 5 strict, Tailwind, MUI v5, Vite 5, FastAPI, Python 3.11, PostgreSQL 16, Redis 7, Kafka, PyTorch 2.1,
Transformers 4.40, SQLAlchemy, Alembic, Pydantic v2); dependency health (`pip-audit`, `npm audit`); and git health
(branches, uncommitted work, secret scan over all history).

### §3.2 Does it run

The audit executes, rather than infers: boots the API, runs the full suites with actual counts, identifies vacuous
tests, and migrates an empty database to head and back.

### §3.3 Requirement status

Each requirement is recorded with one status. **DONE-VERIFIED**: code, a passing test, and the auditor executed it.
**DONE-UNVERIFIED**, **PARTIAL**, **MISSING**, **INCORRECT**, **BLOCKED** otherwise. Only DONE-VERIFIED counts as
done.

### §3.5 Machine-learning system audit

1. **Provenance.** The exact checkpoint (repository and revision), whether it is fine-tuned, and the training
   script, configuration, seed and logs. Absent any of these the model is unreproducible and its status INCORRECT.
2. **Correctness.** A single model instance under concurrency; every inference result complete; probabilities that
   sum to 1 with softmax applied once; the token-length distribution per language and the share truncated at the
   serving length; the model's label order checked against training (an off-by-one inverts urgency silently).
3. **Performance** on a named target CPU: latency p50/p95/p99 at 1, 10 and 50 concurrent requests; peak memory at 50
   concurrent; cold-start time.
4. **Quality** on a held-out test set, per language: every §9.2 metric with a 95% bootstrap interval; confusion
   matrices; CRITICAL→ROUTINE rate with its interval; calibration (reliability diagram and expected calibration
   error); a clustered analysis of errors.
5. **Verdict** per threshold: MET, NOT MET, or NOT MEASURABLE with the reason. A threshold is never tuned downward to
   manufacture a pass.

### §3.6 Dataset audit

Existence, size, origin and generation method; per-row provenance (`source`, `generation_method`, `validated_by`,
`licence`); **deduplication both exact (MD5 on lower-cased, stripped text) and near-duplicate (MinHash/SimHash at
Jaccard ≥ 0.85), both rates reported**; template collapse (how many distinct templates produce the rows); language,
class and domain balance; length bounds and token-length reality; cross-split leakage; and a linguistic quality
sample per language.

## §4 Product context

### §4.1 Problems addressed, as specified

| Problem | As specified | Stated consequence |
|---|---|---|
| Physician shortage | 1 doctor per ~14,000 patients (WHO minimum 1:1,000) **[unsourced in the repository]** | Manual triage causes a ~47-minute delay before urgency is assessed **[unsourced]** |
| Language exclusion | 93%+ speak Kinyarwanda; medical AI is English-only **[unsourced]** | Kinyarwanda speakers receive no AI assistance |
| No queue intelligence | No automated urgency sorting or wait visibility | Critical cases wait behind routine cases |
| Code-switching ignored | Speakers mix Kinyarwanda, English and French mid-sentence | Mixed-language input fails in existing systems |
| Feature-phone exclusion | 40%+ of rural patients lack a smartphone or reliable data **[unsourced]** | Web-only systems exclude the most vulnerable |

### §4.2 Architecture, as specified

| Layer | Technology | Responsibility |
|---|---|---|
| Client | React 18, TypeScript 5 (strict), Tailwind CSS, Material UI v5, Vite | Patient portal, clinician dashboard, admin panel |
| API gateway | FastAPI (Python 3.11), Uvicorn, Nginx, rate limiting | REST API v1, routing, rate limits, CORS, TLS, OpenAPI |
| Business logic | Service layer, repository pattern, Pydantic v2 | Triage orchestration, queue, SMS, analytics |
| ML inference | AfroXLMR-mini, PyTorch 2.1, Hugging Face Transformers, a single shared model instance | Urgency classification, language detection, confidence, responses in four languages |
| Data | PostgreSQL 16, Redis 7, Alembic, SQLAlchemy | Persistence, queue cache, token store, schema versioning |
| Event stream | Apache Kafka, WebSocket | Real-time CRITICAL alerts, clinician notifications, audit trail |
| Infrastructure | Docker, Kubernetes, GitHub Actions, Prometheus, Grafana | Containers, orchestration, deploys, metrics, logging |
| External services | Google OAuth 2.0, Africa's Talking SMS, Hugging Face Hub | Sign-in, SMS to feature phones, model weights |

### §4.3 Triage data flow and latency budget, as specified

End-to-end p95 < 250 ms **[unsourced]**. Budget per step: TLS and rate limit < 5 ms; authentication < 3 ms; language
detection < 10 ms; model < 150 ms; one atomic transaction writing the symptom report, triage result, queue entry and
audit row < 20 ms; queue position < 5 ms; SMS < 200 ms (asynchronous); event publish < 5 ms; push to dashboards
< 50 ms. The queue orders CRITICAL, then URGENT, then ROUTINE.

### §4.4 Supported languages

Four pure languages: Kinyarwanda, English, French, Swahili. Six code-switching pairs: Kinyarwanda + English,
Kinyarwanda + French, Kinyarwanda + Swahili, English + French, English + Swahili, French + Swahili.

## §5 Functional requirements cited in this repository

| ID | Requirement | Acceptance criterion |
|---|---|---|
| FR-01-01 | A patient registers with first and last name, E.164 phone with country code, age, gender and district | Registration < 3 s; E.164 stored; duplicate phone → 409; fields validated before submit |
| FR-01-03 | A patient signs in with Google through OAuth 2.0 | OAuth flow < 3 s; Google profile (first name, last name, email, avatar) stored; no password for OAuth users |
| FR-01-05 | A patient submits symptom text in any of the ten language combinations as free-form input | Triage result within 250 ms p95 under 50 concurrent users **[unsourced]** |
| FR-01-06 | Real-time language detection badge as the patient types (300 ms debounce) | Detection accuracy ≥ 92% on all ten combinations **[unsourced]** |
| FR-01-07 | Urgency returned as CRITICAL / URGENT / ROUTINE with confidence and per-class probabilities | Overall accuracy ≥ 87% (product target; §9.2 sets an 82% deployment floor, a recorded internal contradiction) **[unsourced]**; CRITICAL recall ≥ 91% in all four pure languages **[unsourced]** |
| FR-01-08 | The response is generated in all four pure languages at once (Kinyarwanda, English, French, Swahili) | All four response fields non-null and non-empty in every API response |
| FR-04-03 | Predictions below a configurable confidence threshold (default 0.75 **[unsourced]**) require human review and warn on the dashboard | The flag is visible on the card, with a warning icon on low confidence |
| FR-04-04 | CRITICAL recall ≥ 0.91 in each pure language before any model version deploys | The evaluation script confirms per language; CI blocks deploy otherwise **[unsourced, A28]** |
| FR-04-05 | Inference latency p50 < 150 ms, p95 < 200 ms, p99 < 300 ms on CPU-only hardware | Load test at 50 concurrent on the target hardware **[unsourced; not met on the only machine measured, A29]** |
| FR-04-07 | The dataset generator produces ≥ 1,000,000 unique, deduplicated examples across all ten language combinations | Duplicate rate < 2%; statistics reported |
| FR-04-08 | Language detection ≥ 92% on pure languages and ≥ 85% on each of the six code-switching pairs **[unsourced]** | A dedicated language-identification evaluation set in the evaluation script |
| FR-04-09 | A response in all four pure languages for every triage result, whatever the input language | All four fields non-empty in integration tests across all urgency classes and input languages |
| FR-04-11 | The deterministic red-flag rules layer of L2, escalate-only, before the model, all four languages, sourced from the §10.6 lexicon | 100% pass on the red-flag regression suite is a deploy gate |
| FR-04-12 | Confidence calibration by temperature scaling on a validation (calibration) split, with published ECE and reliability diagram | A review threshold on uncalibrated scores is meaningless |
| FR-04-13 | A cost-sensitive training objective that penalises CRITICAL→ROUTINE far more than adjacent-class errors; decision thresholds tuned to the safety metric, not to accuracy | The magnitude of the cost ratio is **[unsourced, A30; clinical question H6b]** |
| FR-05-07 | Anonymous symptom submission: the triage endpoint accepts a patient without a sign-in token, identified by phone | The endpoint is callable with no Authorization header; the patient is retrieved or created by phone |

## §6 Non-functional requirements

### §6.1 Performance targets

| Metric | Target | Measurement |
|---|---|---|
| Triage API response | p50 < 200 ms · p95 < 350 ms · p99 < 500 ms **[unsourced]** | Server histogram under 50-concurrent load |
| ML inference latency | p50 < 150 ms · p95 < 200 ms on CPU **[unsourced, A29]** | Per-request timing |
| Queue update to browser | < 1 s end to end | Integration test with millisecond timestamps |
| Memory under 50 concurrent requests | < 2 GB | Measured on the target hardware |

### §6.2 Security requirements

TLS 1.3 with HSTS; no secrets in version control, secret scanning in CI; Google ID tokens verified server-side
against Google's published keys with `aud`, `iss` and `exp` checked; parameterised queries only; XSS protection and a
content security policy; CSRF protection through SameSite=Strict refresh cookies and bearer tokens; rate limits of
100 write requests per minute per IP and 10 authentication attempts per 15 minutes per IP; data minimisation with no
PII in logs; dependency and container scanning with zero high-severity CVEs.

### §6.3 Reliability: failure scenarios

| Scenario | Required behaviour |
|---|---|
| ML model not loaded | Triage is not assigned by the system; 503 with Retry-After; clinicians notified; manual triage mode |
| Google OAuth unavailable | Email and password sign-in still works |
| Database connection lost | Retries with backoff, then 503; the pool reconnects |
| Redis unavailable | Falls back to database-only state; no crash |
| Event consumer failure | Offset not committed; dead-letter queue; no message lost |
| SMS provider failure | Status FAILED, retry queued, visible to staff |
| Service instance crash | Restarted; readiness gates traffic |

## §7 Interface requirements

### §7.1 Frontend stack, as specified

React 18, TypeScript 5 (strict, no `any`), Tailwind CSS (layout), Material UI v5 (components), Vite 5 (bundle under
200 KB gzipped), TanStack Query, Zustand, React Hook Form with Zod, Recharts, Framer Motion (respecting reduced
motion), Axios, and Playwright end-to-end tests on Chromium, Firefox and WebKit. No hex colour literal appears inside
a component; design tokens live in one theme file.

### §7.4 Registration form, age field

Age: integer 1–120, required for patients, optional for clinicians.

## §8 Data model

All tables have `id`, `created_at` and `updated_at`. Every schema change is an Alembic migration with a tested
downgrade.

### §8.1 Changes from the first data model

Names split into first and last name on `users` and `patients`; phones stored in E.164 with country code; OAuth
fields and clinician fields on `users`; `district` on `patients`; provisional and final diagnosis, follow-up date and
outcome on `consultations`; check-in and completion timestamps on `queue_entries`; a new `audit_logs` table recording
every state-changing operation with before and after values; `oauth_provider` on `refresh_tokens`.

### §8.2 Tables (cited fields)

- **`patients`**: `age` nullable with `CHECK (age > 0 AND age < 130)`; first and last name required; E.164 phone
  unique.
- **`triage_results`**: urgency (CRITICAL / URGENT / ROUTINE), confidence in [0, 1], per-class probabilities summing
  to 1, and, required by L2 and L3, `rules_layer_triggered`, `rules_layer_reason`, `model_urgency_raw`, so an
  escalation by the rules layer is distinguishable from a model prediction in every audit and retraining set.
- **`model_evaluations`**: every quality metric per model version, with `dataset_hash`, `code_commit`, `seed`,
  `calibration_ece` and `critical_to_routine_fnr` for reproducibility; exactly one active version.

## §9 Machine-learning requirements

### §9.1 Dataset standards

| Requirement | Specification |
|---|---|
| Size | ≥ 1,000,000 unique examples after deduplication |
| Language balance | Each pure language 10–15% of the total; mixed combinations 40–60% combined |
| Class balance | CRITICAL 28–38% · URGENT 32–42% · ROUTINE 28–38% |
| Domain coverage | All 80+ medical domains; at least 500 examples per domain |
| Duplicates | < 2% near-duplicate |
| Length | ≥ 20 and ≤ 512 characters |
| Clinical validation | A stratified sample of 1,500 reviewed by two registered nurses; Cohen's κ ≥ 0.80, **reported per language** |
| Code-switching naturalness | All six pairs present; mean naturalness ≥ 3.5 / 5 from bilingual raters |
| Release | CSV and Parquet, CC BY 4.0, with a datasheet (Gebru et al., 2021) |

Also required: near-duplicate detection by MinHash/SimHash at Jaccard ≥ 0.85 in addition to MD5; effective
diversity reported (distinct templates, type-token ratio, lexical entropy per language, length per class); per-row
provenance including `variant` for Swahili and `matrix_language` for code-switched rows; frozen, hashed splits
(L8).

### §9.2 Deployment gate: the 15 metrics

The evaluation script confirms every metric before any deployment, each with a 95% interval; deployment is blocked
if any is below threshold. **Every threshold below is [unsourced]** (A30). The sample sizes needed to measure them
are derived in `ml_model/training/eval_spec.py`, which supersedes the n = 100,000 stated in the SRS.

| # | Metric | Threshold |
|---|---|---|
| 1 | Overall accuracy | ≥ 82% |
| 2 | Weighted F1 | ≥ 0.83 |
| 3 | Macro F1 | ≥ 0.80 |
| 4 | CRITICAL precision | ≥ 0.88 |
| 5 | **CRITICAL recall, in EACH of the four pure languages** (hard minimum) | ≥ 0.91 |
| 6 | CRITICAL F1 | ≥ 0.89 |
| 7 | **CRITICAL → ROUTINE false-negative rate** (hard limit) | < 1.0% |
| 8 | URGENT recall | ≥ 0.86 |
| 9 | Kinyarwanda accuracy | ≥ 80% |
| 10 | English accuracy | ≥ 86% |
| 11 | French accuracy | ≥ 84% |
| 12 | Swahili accuracy | ≥ 80% |
| 13 | Mixed-language accuracy (mean of six pairs) | ≥ 82% |
| 14 | Inference latency p50 / p95 on CPU | < 150 ms / < 200 ms |
| 15 | Memory under 50 concurrent requests | < 2 GB |

**Additional gates:** red-flag safety suite 100% pass; expected calibration error reported and ≤ 0.05; language
identification ≥ 92% on pure languages and ≥ 85% on mixed; no split leakage.

## §10 Language, data and model sourcing

### §10.1 Source verification, before any external model or corpus is used

1. It exists: the URL or repository resolves, and the exact revision is recorded.
2. Its licence permits the intended use (commercial, clinical, derivative, redistribution).
3. Its own training data has a citable provenance.
4. It is smoke-tested on this project's data before adoption.
5. It is logged in `docs/SOURCES.md`: name, URL, revision, licence, date verified, use, verdict.

A resource that cannot be verified is not used and not cited.

### §10.2 Kinyarwanda source tiers

| Tier | Sources | Permitted use |
|---|---|---|
| T1, authoritative | Digital Umuganda (validated corpora and terminology work); Rwanda MoH / RBC clinical materials; WHO ETAT materials; native Kinyarwanda-speaking clinicians and nurses | Gold labels, evaluation sets, terminology ground truth, final arbitration |
| T2, assistive, human-reviewed | Verified Kinyarwanda-capable models and tools (ASR, multilingual encoders, translation models) | Candidate generation, augmentation, back-translation. Never a gold label without T1 review. |
| T3, draft only | General-purpose large language models | Candidate phrasings that a T1 reviewer accepts, edits or rejects; tagged `generation_method=llm_draft` and unusable until `validated_by` is set |

No Kinyarwanda example enters the evaluation set without native-speaker approval. Text is authored natively, or
translated with T1 review; English-first authoring followed by machine translation is not acceptable, and which
route was used is recorded.

### §10.3 Swahili source tiers

T1: validated public corpora and native Swahili-speaking clinicians with Tanzanian and Kenyan variants represented.
T2: verified Swahili-capable models, each verified first. T3: general-purpose models, drafts only, as §10.2. Dialect
is a first-class variable: `variant` is recorded per row and accuracy is reported per variant.

### §10.4 English and French clinical sources

T1 for terminology and taxonomy: WHO ETAT, ICD-11, SNOMED CT and UMLS (licensing checked before redistribution),
Rwandan MoH protocols; for French, HAS / CISMeF resources. T2: biomedical encoders to benchmark against. Commercial
clinical AI systems are comparators only; their outputs are never ingested as training data.

### §10.5 Code-switching

Mixed examples are authored or validated by bilingual speakers of that specific pair, never assembled by
interleaving words from two monolingual sentences. Naturalness is rated 1–5 by at least two bilingual raters per
pair, with inter-rater agreement and the matrix-language distribution reported per pair.

### §10.6 Clinical lexicon

A four-language aligned lexicon in `data/lexicon/` with the columns
`concept_id | icd11_or_snomed | en | fr | sw | rw | rw_colloquial_variants[] | sw_variant | register | red_flag(bool) | source | validated_by | date`.
It records how patients actually speak, not only formal terms. Red-flag concepts are marked; **this table is the
source of truth for the L2 rules layer.** Every row cites a source and a T1 validator.

### §10.7 Dataset construction

Six stages: clinician-authored native seeds; controlled expansion under explicit diversity constraints; validation
sampling (≥ 1,500 items, two nurses, κ per language); adversarial and hard cases; deduplication, leakage check and
frozen hashed splits; datasheet and per-row provenance. If a defensible 1,000,000 cannot be reached under this
protocol, the largest defensible size and its quality profile are reported instead; the count is never padded.

### §10.8 Model strategy

Candidate encoders are benchmarked on the project's own test set (accuracy against latency against memory) and
chosen on evidence. Confidence is calibrated by temperature scaling before any review threshold is set, with the
reliability diagram and ECE published. The training objective is cost-sensitive (FR-04-13), with thresholds tuned to
the safety metric. Everything is versioned: seed, configuration, data hash, code commit, environment. A result that
cannot be re-run is not a result. Patient-facing responses are templates authored by T1 reviewers, not free
generation.

## §12 Infrastructure

### §12.1 CI/CD pipeline, as specified

| Stage | Trigger | Pass criteria |
|---|---|---|
| Lint and type check | every push, any branch | zero lint, type or format errors |
| Unit tests | every push | all pass; coverage report |
| Integration tests | push to develop or main | all pass, with ephemeral PostgreSQL, Redis and Kafka |
| Security scan | push to main | zero high-severity CVEs; no secrets |
| ML evaluation gate | any change to saved model files | deployment blocked if any §9.2 metric is below threshold; report uploaded |
| Docker build | push to main | images build within size limits |
| Staging deploy | merge to main | smoke tests and readiness pass |
| Production deploy | manual approval after staging | rolling update; automatic rollback on failed readiness |

The ML gate must be shown blocking a deliberately bad model; a gate that has never blocked anything is untested.

## §13 Testing

Mandatory suites beyond unit and integration tests:
- **Clinical safety regression:** a fixed, append-only corpus of red-flag phrases in all four languages and six
  mixed pairs that must always classify CRITICAL; 100% pass is a deploy gate.
- **Queue invariant property test:** for any arrival sequence, no ROUTINE precedes an unserved CRITICAL.
- **PII leak test:** logs, event payloads, API error bodies and exported CSVs are scanned for phone patterns and full
  names.
- **Audit completeness test:** every state-changing endpoint produces exactly one audit row.

## §14 Research artefacts and reproducibility

Planned artefacts: the **KinyaMed-Triage** dataset (CSV and Parquet, CC BY 4.0) with a datasheet; the fine-tuned
model weights and a model card; the training and evaluation pipeline; the full system source; the clinical lexicon
of §10.6 as a standalone contribution.

A reviewer with the repository and a CPU reproduces every reported number with one command, `make reproduce`, from
a clean clone.

## §15 Roadmap and phase gates, as specified

| Phase | Focus | Gate |
|---|---|---|
| 0 | Audit | Audit reports delivered; remediation plan approved |
| 1 | Authentication: JWT RS256, Google OAuth, first and last name, E.164, password with confirmation, bcrypt cost 12, rate limiting | All FR-05 tests pass; Google sign-in verified in an integration test |
| 2 | Lexicon (§10.6) and dataset | All §9.1 standards confirmed; κ ≥ 0.80 per language; provenance complete |
| 3 | Model training and integration | All §9.2 metrics met with intervals; CRITICAL recall ≥ 0.91 per pure language; red-flag suite 100%; p95 < 200 ms |
| 4 | Frontend (patient, clinician, admin) | Browser tests green on three browsers; Lighthouse > 90; 0 critical accessibility violations; 320–1536 px verified |
| 5 | Real-time events | Queue update < 1 s end to end; 50-concurrent load test with no dropped messages |
| 6 | Production infrastructure | Zero-downtime rolling deploy; health checks green; ML gate shown blocking a bad model |
| 7 | Research artefacts and release | Preprint; dataset and model published; model card complete; `make reproduce` works from a clean clone |

## §16 Master gate table

| Gate | Blocks |
|---|---|
| `mypy --strict`, `ruff`, `tsc --noEmit`, `eslint` clean | every commit |
| Full test suites green; coverage not decreased | every commit |
| Leakage check clean; split hash unchanged | every training run |
| All 15 metrics of §9.2 met, with intervals, per language | model deploy |
| **CRITICAL recall ≥ 0.91 in each pure language** | model deploy (hard) |
| **CRITICAL → ROUTINE rate < 1.0%** | model deploy (hard) |
| **Red-flag safety suite 100% pass** | model deploy (hard) |
| ECE ≤ 0.05 on validation | model deploy |
| 0 critical accessibility violations; Lighthouse ≥ 90 | frontend release |
| 0 high-severity CVEs; 0 secrets; web security scan clean | production release |
| Every published number traceable to a script run | paper, model card, README |

## §18 Glossary (cited entries)

| Term | Definition as specified |
|---|---|
| CRITICAL | Urgency class 0: life-threatening, needs immediate intervention (specified as "ESI 1–2"). CRITICAL recall is the primary safety metric. |
| URGENT | Urgency class 1: serious, needs same-day attention (specified as "ESI 3"). |
| ROUTINE | Urgency class 2: non-urgent, suitable for a scheduled appointment (specified as "ESI 4–5"). |
| ETAT | Emergency Triage Assessment and Treatment; specified as the WHO framework used in Rwandan health centres and the basis of the three-class taxonomy. **Contradicted by the ETAT manual itself on age scope and modality** (`reports/TAXONOMY_SCOPE.md` §2–§2b), and inconsistent with the ESI mapping above, which cites a different instrument. |
| ECE | Expected calibration error: whether stated confidence matches observed accuracy. |
| Red-flag layer | The deterministic, escalate-only rules layer that runs before the model (L2). |
| KinyaMed-Triage | The multilingual medical symptom dataset introduced by this project. |
| Matrix language | The grammatically dominant language in a code-switched utterance. |
