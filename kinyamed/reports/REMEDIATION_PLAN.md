# Remediation plan — Phase 0

Ordered by **patient safety > correctness > performance > aesthetics > speed** (CLAUDE.md §1). Estimates are
focused engineer-days for one person who knows this codebase, excluding waiting on people; they are judgement,
not measurement. Every increment is test-first (L15), one concern per commit (L13), and ends by updating
`reports/STATE.md`.

Nothing below starts until you approve it. **Section 0 lists decisions only you can make.** Several later
items are blocked on them, and I have marked which.

---

## 0. Decisions and inputs needed from you (blocking)

| # | Decision / input | Why it blocks | Blocks |
|---|---|---|---|
| **D0** | **Commit or stash the current working tree.** At audit start: 19 modified, 1 deleted (`ml_model/CLAUDE.md`), 21 untracked files on `audit-p0-p1-and-frontend`, incl. a new migration `f1a2b3c4d5e6_add_password_reset_tokens.py` and CI changes. | I measured the working tree; remediation commits on top of uncommitted work would mix concerns (L13) and could lose it. I will not commit it for you without instruction. | everything |
| **D1** | **Which specification governs, and what happens to the old charter.** The repo was built to `ml_model/CLAUDE.md` (deleted, uncommitted), whose standing rules conflict with CLAUDE.md v2.0 in at least these places: (a) "patient-facing text is speaker-authored or absent" vs FR-01-08/FR-04-09 "all 4 responses non-null"; (b) "row count follows content, ~2,000 rows/phrase" vs FR-04-07 "≥ 1,000,000 rows"; (c) gate CRITICAL recall 0.95 vs 0.91; (d) `patients.phone` deliberately non-unique (shared handsets) vs `UNIQUE(phone)`; (e) authenticated-only triage vs FR-05-07 anonymous; (f) OAuth deferred over Law 058/2021 residency vs FR-01-03 Must; (g) length-only password policy (min 12) vs character classes (min 8); (h) SMS reset token 30 min vs 6-digit email OTP 10 min; (i) hand-built accessible Tailwind UI vs MUI/Framer/Zustand/RHF stack. | Each choice changes schema, API and tests. My recommendation: keep (a), (b), (c-as-stricter), (d), (g) from the old charter — they are safer or better-evidenced — and amend CLAUDE.md; decide (e), (f), (i) explicitly. | R1.3, R3, R5, R6, R7 |
| **D2** | **Clinical source documents in `docs/clinical/`** (Rwanda MoH / RBC triage protocol, WHO ETAT, emergency numbers, referral pathways). | L5: the red-flag rules content, escalation instructions and taxonomy may not come from model memory. | R1.3 content, R4, all patient-facing text |
| **D3** | **Named clinician** for taxonomy sign-off (`ml_model/docs/protocols/d2-clinician-review-pack.md`, already generated) and to confirm/replace the unsourced gate thresholds. | Gate thresholds (0.95 / 0.91, 1%) and every CRITICAL label are unratified. | R4, R5 gate |
| **D4** | **Native-speaker reviewers**: Kinyarwanda (≥ 2), Swahili (TZ + KE), English (Rwandan), French; bilingual raters per code-switch pair. | §10.2 hard rule; 3 of 4 languages have zero authored eval rows. | R4 |
| **D5** | **Target deployment CPU spec** (cores, RAM, whether shared with other services). | FR-04-05 / NFR latency and the 2 GB memory gate are only meaningful against a named machine. | R5.5 sign-off |
| **D6** | **Where v2d weights live**: publish (HF, pinned revision, SafeTensors SHA-256 recorded) or keep private and document. They currently exist only in `~/kinyamed-runs/`. | `make reproduce` from a clean clone is impossible without them. | R5 |
| **D7** | **`docs/compliance/`**: Rwanda NHRC/IRB status and the data-protection instrument (verify current law; the repo cites Law 058/2021 — not verified by me). | L10. No real-patient work may begin. | any real data |

---

## R1. Safety shell around whatever model is served — **do first** (≈ 7 days + D2 content)

Goal: no input can reach ROUTINE without passing an escalate-only check, and every uncertain case goes to a
human. Independent of model quality; valuable even with today's weak model.

| # | Increment | Test written first | Est. | Depends |
|---|---|---|---|---|
| R1.1 | Migration: `triage_results` + `model_version`, `probabilities` JSONB (CHECK keys + sum within 1e-6 via trigger or CHECK on extracted floats), `requires_human_review`, `rules_layer_triggered`, `rules_layer_reason`, `model_urgency_raw`; tested downgrade. Show you the SQL before applying (L14). | upgrade/downgrade test; constraint rejects probs summing to 0.9 | 1 | D0 |
| R1.2 | `InferenceResult` with all 7 fields; `ModelClassifier` returns probabilities, model version (SHA-256 of weights), duration; thread-safe singleton with an explicit lock (replace bare `lru_cache`) | 100-thread barrier test asserts builder called once; field-completeness test | 1 | R1.1 |
| R1.3 | **Escalate-only rules layer before the model** — the mechanism: normalisation (accent/case fold), lexicon-driven matcher, `max(rule, model)` combination that can only raise urgency, reason recorded. **Content loaded from `data/lexicon/`, empty until D2/D4 supply it; no terms hardcoded.** The existing `CRITICAL_TERMS` list is *not* promoted (it misses 94% of held-out CRITICAL rows). | property test: rules never lower urgency for any (rule, model) pair; fixture lexicon test | 2 | R1.2, D1 |
| R1.4 | **Fail-safe routing (L4)**: `requires_human_review=True` when language is `unknown`/unsupported, input shorter than a configured floor, model not ready, inference raises, or confidence below threshold. Such cases are **never** ROUTINE: queue at URGENT pending review (clinical choice for you/clinician — default proposed: URGENT) and surfaced on the board. Wire the currently dead `MODEL_CONFIDENCE_THRESHOLD`. | unit tests per trigger; integration: model raises → 201 + review flag, not 500 | 1.5 | R1.2 |
| R1.5 | Remove silent keyword fallback in **all** environments that serve users (staging too); dev keeps it only behind an explicit `ALLOW_BASELINE=true`. Keyword baseline stops emitting diagnosis-like `possible_conditions` strings (L1). | config tests | 0.5 | R1.4 |
| R1.6 | Fix `/ready`: report the actual selected classifier, 503 when the configured model is not loaded. | probe test with model stub | 0.5 | R1.2 |
| R1.7 | Clinical safety regression suite scaffold (`tests/safety/red_flags.csv`, append-only, CI-blocking). Seed it with the 20 audit probe inputs **as candidates marked `validated_by=NONE`**, excluded from the gate until D3/D4 validate them. | the file's append-only property test | 0.5 | R1.3 |

**Exit gate R1:** all probe inputs that the model sends to ROUTINE are flagged for review in an integration
test; no triage can be persisted without `model_version`.

## R2. Privacy, accountability and security (≈ 8 days)

| # | Increment | Test first | Est. | Depends |
|---|---|---|---|---|
| R2.1 | **PII scrub**: remove `to=` phone from `sms_stubbed` log; structlog processor that masks E.164 and known name fields in every event; mask phone in `QueueItemResponse` (full number only on explicit, audited reveal). | PII leak test scanning captured logs + API error bodies for `+\d{9,15}` (fails today) | 1 | D0 |
| R2.2 | **`audit_logs`** table (11th spec table), written in the same transaction as every state change via a service-layer helper; PII-scrubbed before/after JSONB. | audit-completeness test enumerating every non-GET route in OpenAPI and asserting exactly one audit row each; atomic rollback test | 2.5 | R2.1 |
| R2.3 | Rate limiting: trust `X-Forwarded-For` only from configured proxy CIDRs; separate auth bucket 10 / 15 min; write bucket 100 / min; Redis-backed when configured. | XFF-spoof test (fails today: 30/30 bypass); 11th login → 429 + Retry-After | 1 | — |
| R2.4 | Security headers middleware (CSP, HSTS in prod, nosniff, frame-ancestors, referrer-policy). | header test | 0.5 | — |
| R2.5 | `mypy --strict` to zero (20 errors in 11 files) and add to CI; one real bug among them is `health.py` importing a non-existent module (fixed in R1.6). | CI job | 1 | R1.6 |
| R2.6 | CI security stage: `pip-audit`, `npm audit --audit-level=high`, gitleaks (full history). Upgrade runtime packages flagged by `pip-audit` first — **PyJWT 2.10.1, python-multipart 0.0.20, pydantic-settings 2.14.1** (25 advisories, on the auth path) — then `transformers`/`setuptools` in ML, then `vitest` (critical, dev-only) and `postcss` (high). | CI job red on a planted fake secret in a throwaway branch | 1 | — |
| R2.7 | JWT: decide RS256 + key id/rotation (spec) vs documented HS256; refresh cookie SameSite=strict (path-scoped already); refresh-token record stores hash + `family_id`. | claim/alg tests | 1 | D1 |

## R3. Close the clinical feedback loop (≈ 5 days)

Without this, CRITICAL→ROUTINE in the field (L3) is unobservable forever.

| # | Increment | Est. | Depends |
|---|---|---|---|
| R3.1 | Consultations API (provisional/final diagnosis, outcome enum, follow-up) — the table exists, no route does | 2 | R2.2, D1 |
| R3.2 | "Mark AI incorrect" correction with original/corrected urgency, doctor, model_version; counter + alert on every CRITICAL→ROUTINE correction; per-model-version rate query | 1.5 | R1.1, R3.1 |
| R3.3 | `model_evaluations` table with partial unique index on `is_active`, plus `dataset_hash, code_commit, seed, calibration_ece, critical_to_routine_fnr`; `evaluate.py` writes it | 1.5 | R1.1 |

## R4. Lexicon, evaluation set and corpus (Phase 2) — **mostly people time** (engineering ≈ 6 days)

| # | Increment | Est. | Depends |
|---|---|---|---|
| R4.1 | `data/lexicon/` schema + validator (§10.6), seeded from `ml_model/review/concepts.py` + `concept_anchors.csv`; every row `validated_by` required before use | 2 | D2 |
| R4.2 | **Evaluation set first, corpus second**: target ≥ 150 distinct clinician-labelled CRITICAL sentences per pure language (so a cluster-bootstrap CI on recall is narrower than ±0.05), natively authored; κ per language | 1 (tooling) + people | D3, D4 |
| R4.3 | Dataset audit tooling committed (`make audit-data`): MD5 + MinHash 0.85 dedup, template/phrase collapse metrics, per-row provenance columns (`source, generation_method, validated_by, licence, variant, matrix_language`) | 2 | R4.1 |
| R4.4 | Datasheet (Gebru et al.) for v2; README/STATUS de-staled so no unmeasured or superseded figure remains (L6: README today contradicts itself) | 1 | — |

**Size.** I recommend reporting the largest *defensible* corpus (§10.7) rather than 1,000,000 rows; the repo's
own rule (~2,000 rows per distinct phrase) is the right discipline. Needs D1(b).

## R5. Model (Phase 3) — only after R4.2 exists (≈ 8 days compute-bound)

| # | Increment | Est. | Depends |
|---|---|---|---|
| R5.1 | Pin base revision (`bc04038b…`), record weights SHA-256 in run record, env lockfile | 0.5 | D6 |
| R5.2 | Baselines per §10.8 (XLM-R, AfriBERTa, Serengeti, AfroXLMR-base) on the R4.2 set: accuracy vs latency vs memory | 3 | R4.2 |
| R5.3 | Retrain: unfreeze more layers (v2d underfits its own training rows: 0.743), explicit cost matrix for CRITICAL→ROUTINE, OOD/"unsure" handling, threshold tuned to safety metric | 2 | R5.2 |
| R5.4 | Temperature scaling on a many-sentence validation split; ECE + reliability diagram emitted by `evaluate.py` | 1 | R5.3 |
| R5.5 | 15-metric gate in `evaluate.py` with phrase-cluster bootstrap CIs; CI job that runs it on a model manifest change (weights are git-ignored, so the trigger must be a committed manifest file, not `saved_model/`); **demonstrate it blocking a deliberately bad model** (v2c is a ready-made one) | 1.5 | R5.4, D5 |

## R6. Product scope from v2.0 not yet built (sized only; order after D1)

| Area | Est. | Notes |
|---|---|---|
| Google OAuth (JWKS verification, linking, revocation) | 4 | after D1(f) residency answer |
| Anonymous triage by phone | 1.5 | after D1(e); needs abuse controls |
| Multilingual responses (4 languages) | 1 engineering | content blocked on D2/D4; template-based only |
| Language detection eval set + model (≥ 92% / 85%) | 3 | measured today: KW 87.7%, SW 88.3%, mixed 33% |
| Kafka + WebSocket real-time | 5 | replaces 5 s polling |
| SMS: Africa's Talking client, DELIVERED webhook, retry, SMS-only flow | 5 | |
| Frontend v2.0 (patient portal, detail drawer, filters, undo, animations) | 15–25 | decide D1(i): extend current accessible Tailwind app (recommended) vs MUI rewrite |
| Infra: Dockerfiles, K8s manifests with probes, Prometheus/Grafana, staging | 8 | `infrastructure/` is empty |

## R7. Things I recommend *not* doing, or changing in the spec

1. **Do not fill the 4 response slots with machine-drafted text** to satisfy FR-01-08. It conflicts with §10.2
   and L1 and would put an unreviewed "go to hospital now / you can wait" sentence in a patient's hand.
2. **Do not lower any threshold** — and do not quote "CRITICAL→ROUTINE 0%" from the current set: 4 sentences.
3. **Do not generate 1M rows from 165 phrases** to hit FR-04-07; effective diversity is what a reviewer measures.
4. Amend the spec's internal contradictions: 87% vs 82% accuracy; 13/12 px type steps vs "no text below 14 px";
   "DB CHECK password_hash nullable only when oauth_provider set" is fine but the `users`/`patients` split in
   this repo (login ≠ chart, walk-ins without accounts) is better than the spec's merge — keep it.
5. `analytics_daily` "API never writes": the current admin snapshot endpoint is harmless; fine either way.

---

## Dependency summary

```
D0 ─┬─ R1.1 ─ R1.2 ─┬─ R1.3 (mechanism) ── R1.7        [content: D2, D4]
    │               ├─ R1.4 ─ R1.5
    │               └─ R1.6 ─ R2.5
    ├─ R2.1 ─ R2.2 ─ R3.1 ─ R3.2
    ├─ R2.3, R2.4, R2.6 (parallel)
    └─ R1.1 ─ R3.3
D2 ─ R4.1 ─ R4.3
D3 + D4 ─ R4.2 ─ R5.2 ─ R5.3 ─ R5.4 ─ R5.5 [D5, D6]
D1 ─ R2.7, R3.1, R6
```

**Proposed first increment after approval:** R1.1 — the `triage_results` migration adding `model_version`,
`probabilities`, `requires_human_review` and rules-layer fields, with its downgrade test, SQL shown to you first.
Rough total for R1–R3 (engineering only): **≈ 20 days**.
