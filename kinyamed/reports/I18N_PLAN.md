# Multilingual patient receipt — proposal (not implemented)

**Status 2026-09-15: proposal only.** Blocked on translators (H11), a clinician check of the escalation wording
(H6), and the decisions in §6. Nothing here changes what patients receive today.

## 1. What exists today

- **One English sentence set for every patient**, in `backend/app/services/patient_message.py`: "Your report has
  been received. Your queue number is {n} and you are number {p} in the queue. If you feel worse or this is an
  emergency, go to the health centre immediately."
- **Sent two ways:** by SMS (`triage_service`) and as `patient_response` on `POST /triage` (shown to staff by
  `PatientMessage.tsx`, which says "English only").
- **The response names the language:** `patient_message_language = "english"`.
- **No patient language preference is stored.** `symptom_reports.language_detected` exists, but the detector
  measured 0.877 on Kinyarwanda and 0.33 on mixed text (MODEL_AUDIT §6.3).
- **Existing protection:** the receipt is identical for every urgency, and no authored urgency template reaches
  it (`tests/integration/test_patient_message.py`).

## 2. Where the strings live

**One catalogue, in the backend, versioned:** `backend/app/content/patient_receipt.v1.csv`.

- **In the backend, not the frontend.** The backend sends the SMS; the frontend only displays what the API
  returns. A second copy of the text in the frontend would be a second source of truth for what the patient
  was told.
- **One row per language.** Columns:

| Column | Meaning |
|---|---|
| `language` | `kinyarwanda`, `english`, `french`, `swahili` (+ `swahili_variant` if E-decision says TZ/KE differ) |
| `text` | the whole message, with slots `{queue_number}` and `{queue_position}` only |
| `source_sha256` | digest of the English text this translation was made from |
| `translated_by`, `reviewed_by` | T1 native-speaker codes (§10.2); reviewer ≠ translator |
| `escalation_checked_by` | clinician code confirming the escalation sentence means the same thing |
| `approved_at` | date |

**Rules:**
- **Whole-message templates only.** Sentences are never assembled from fragments, because word order and
  agreement differ across the four languages.
- **No machine translation, at build time or at runtime.**
- **No service names or phone numbers** until a document in `docs/clinical/` confirms them (H20: SAMU/912 is
  unconfirmed). The escalation line stays generic.
- **One language per receipt.** Code-switched speakers receive their chosen pure language.

## 3. Which language a patient gets

**Proposed order — a decision for you (§6):**
1. The patient's **stated preference**: a new optional `patients.preferred_language`, set by staff at
   registration. This needs a migration (L14: SQL shown first).
2. Otherwise the language **staff select** on the triage screen.
3. The **detected language may pre-fill** the selector, and **never decides alone**, given the accuracy above.

## 4. How a missing translation fails

**The rule:** a missing translation must never block a triage or an SMS, never show a patient an unfilled slot,
and never be silent.

| Case | Behaviour |
|---|---|
| Catalogue row invalid: missing reviewer or clinician code, slots not exactly `{queue_number}` and `{queue_position}`, empty text | **Rejected when the catalogue loads.** The app refuses to start if the **fallback** language is invalid. Any other invalid row is excluded, and a startup ERROR names it. |
| Row is stale: `source_sha256` ≠ the current English text | Treated as **missing**. A changed English source must be re-translated, not silently kept. |
| Requested language has no valid row | Send the **fallback language**. Response carries `patient_message_language` = the language actually sent, `patient_message_requested` = what was asked, and `patient_message_fallback: true`. Log event `receipt_language_fallback` with the language codes only (no PII). |
| Rendered text still contains `{` | Existing defence in `PatientMessage.tsx` withholds it on screen. Add the same check before SMS dispatch: send the fallback instead and log ERROR. |
| SMS would exceed 2 segments in that language (GSM-7 vs UCS-2 changes the segment length) | Checked when the catalogue loads, for the largest queue numbers. A row that fails is invalid. |

**Fallback language:**
- The catalogue names exactly one `fallback_language`, which must itself be valid, or the app does not start.
- **Today that can only be English**, the only text that exists. English is **not reviewed by anyone either**:
  it was written in this project.
- **For a Kinyarwanda health centre the right fallback is plausibly Kinyarwanda** once it is approved. That is
  a decision for you and the clinical lead (§6), not a default I should choose.

## 5. Tests to write first, when implemented

1. **Catalogue loader:** rejects each invalid-row case in §4, and refuses to start without a valid fallback.
2. **Slot parity (property):** every valid row renders with random queue numbers and positions, and leaves no
   `{`.
3. **Fallback:** a request for a language without a valid row returns the fallback text and the three response
   fields, and logs one fallback event.
4. **Stale source:** changing the English text marks every translation stale.
5. **Extend `test_patient_message.py` per language:** the receipt is identical across urgency classes in every
   catalogued language. No per-language "reassuring words" list is added without a speaker (L16).
6. **SMS segment ceiling** per language.
7. **Frontend:** `PatientMessage` shows the language sent, and says so when a fallback was used.

## 6. Decisions needed before implementation

| # | Decision | Owner |
|---|---|---|
| I1 | Language source: stored patient preference (migration) vs staff selection per triage | you |
| I2 | Fallback language (English now; Kinyarwanda once approved?) | you + clinical lead |
| I3 | Whether Swahili needs TZ and KE variants of the receipt | you + Swahili speakers |
| I4 | The escalation instruction itself: is "go to the health centre immediately" right for every setting, and when may a service or number be named? | clinical lead (H5, H6, H20) |
| I5 | Who is T1 translator and reviewer per language | you (H11) |

**Out of scope:** the staff interface language, which stays English; any urgency-specific patient text, which
stays forbidden (item 2).
