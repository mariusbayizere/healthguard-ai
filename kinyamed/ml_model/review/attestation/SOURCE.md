# Attestation corpus — provenance and licence

`chw_questions_kinyarwanda.csv` is a **derived subset**, redistributed here under
the terms of its licence.

| field | value |
|---|---|
| **Source** | Rutunda, S.; Williams, G.; Kabanda, K.; Nkurunziz, F.; Uwiduhaye, S.; Rugegamanzi, E.; Nshimiyimana, C.; Menon, V.; Emmanuel-Fabula, M.; Denniston, A.; Liu, X.; Hezagira, E.; Mateen, B. A. — *A Realistic Rwandan Community Health Worker Generated Vignette-based Benchmarking Dataset (with Associated Clinician and LLM Responses)* |
| **DOI** | `10.6084/m9.figshare.29213147` |
| **Licence** | **CC BY 4.0** — https://creativecommons.org/licenses/by/4.0/ |
| **Retrieved** | 2026-09-03, from the figshare record |
| **Companion paper** | *Large language models for frontline healthcare support in low-resource settings*, Nature Health, 2026. `10.1038/s44360-025-00038-1` |

**Cite the figshare DOI, never the GitHub mirror.** The same CSV appears in
`github.com/PATH-AI-Initiative/RwandaBenchmarking`, which carries **no licence
file** (`license: null` on the GitHub API). That copy is all-rights-reserved by
default; only the figshare record grants CC BY 4.0.

## Changes made to the source

CC BY 4.0 requires that changes be indicated. This file is not the original:

- **Columns dropped.** The source has 43; six are kept — `question_id`, `chw_id`,
  `question_categories` (renamed `categories`), `question_kinyarwanda`,
  `answer_human_kinyarwanda` (renamed `answer_clinician_kinyarwanda`), and
  `question_english`. All LLM-generated answers and all evaluation and rater
  columns were removed: this corpus exists to attest **human** language, and
  model output would defeat that.
- **Rows unchanged.** All 524 are present; no text was edited, cleaned or
  reordered.

To re-derive it, download the source CSV from the DOI above and keep those six
columns.

## What it is, and what it is not

CHWs recorded questions as **voice in Kinyarwanda**; Digital Umuganda's
speech-to-text model transcribed them; trained Rwandan nurses screened them; only
then were they translated to English by professional linguists. **The Kinyarwanda
is source text, not back-translation.** The clinician answers are likewise
Kinyarwanda originals where `response_language` was Kinyarwanda.

**It is a substantiation source, exactly like `phrase_review_sheet.csv` — not
phrases to lift.** Standing rules 5 to 8 apply unchanged: a word appearing here
means it exists in real Rwandan clinical use, which is grounds for the speaker to
*consider* it. It is never grounds to write a phrase they have not authored.

Two properties limit it, and both matter when reading a hit:

- **Register.** These are CHW-to-clinician case reports, not patient speech.
  416/524 use third-person patient framing and 277/524 carry CHW first-person
  narration ("nakiriye", "nasuye"). They carry weights, MUAC and temperatures a
  patient would not produce. Useful for third-person `{REL}` phrasing; misleading
  if read as a model for first person.
- **ASR provenance.** The Kinyarwanda passed through a speech-to-text model before
  nurse screening, so transcription artefacts are possible. A single odd-looking
  hit is weak evidence; a term used consistently across several CHWs is strong.

`attest.py` reports the CHW count behind every hit for that reason.
