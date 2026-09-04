# Attestation corpus — provenance and licence

Two sources, licensed separately. `attest.py` reports them as separate tiers
(`chw` and `rbc`) so a hit always says which corpus it came from — they differ in
register, in provenance, and in how much a hit is worth.

---

## 1. `chw_questions_kinyarwanda.csv` — 524 CHW questions, CC BY 4.0

A **derived subset**, redistributed here under
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


---

## 2. `rbc_kinyarwanda_health.txt` — RBC health/CHW training text, CC BY 2.0

Retrieved 2026-09-04, unmodified.

| field | value |
|---|---|
| **Source** | `DigitalUmuganda/Monolingual_health_dataset` on HuggingFace, file `rbc_kinyarwanda_health_dataset.txt` |
| **URL** | https://huggingface.co/datasets/DigitalUmuganda/Monolingual_health_dataset |
| **Originating body** | Rwanda Biomedical Centre (RBC), per the dataset card: *"Rwanda Biomedical Center (RBC) (26,390 sentences)"* |
| **Licence** | **CC BY 2.0**, declared in the dataset card's `license` field — https://creativecommons.org/licenses/by/2.0/ |
| **Retrieved** | 2026-09-04, ungated, no authentication |
| **sha256** | `b02375186cbdb1e7180f8adc71619a7dcdc1550a5698277e457cd36b78f61100` |
| **Size** | 2,509,528 characters, 28,621 non-empty lines (28,539 unique), 330,232 words |

**Changes made to the source: none.** The file is byte-identical to the one
published. CC BY 2.0 requires attribution and that changes be indicated; there are
no changes to indicate.

### The companion file is deliberately NOT vendored

The same repository ships `gpt_generated_medical_data.txt` — **42,576 sentences of
GPT-4 output**, per the dataset card. It was never downloaded and must not be.
This directory exists to attest **human** Kinyarwanda; adding model-generated text
would make `attest.py` confirm the project's own machine drafting back to it, which
is the precise failure standing rules 5 to 8 exist to prevent. The card's own line
is the record: *"Rwanda Biomedical Center (RBC) (26,390 sentences) / GPT-4 prompting
(42,576 sentences)"*.

Verified after download: **0% of lines are English prose**, and no model-style
scaffolding appears.

### Licence caveat — read before relying on this

**The CC BY 2.0 grant is Digital Umuganda's, not RBC's.** Digital Umuganda deposited
the file and set the licence field; nothing in the record shows RBC granting those
terms on its own training material. This is the same shape as the
figshare-versus-GitHub split in section 1, where the identical CSV was CC BY 4.0 in
one place and all-rights-reserved in another — and that one was caught only by
reading both records.

**Treat the licence as provisional until RBC confirms it.** Using it as an internal
substantiation check is low risk; redistributing it or citing it as corpus
provenance is not, and this file is not part of the generated corpus.

### What it is, and what it is not

RBC health and community-health-worker **training curriculum**: lesson units
(*ICYIGWA 3.2*), learning outcomes, counselling-form instructions, service
descriptions. Written and edited Kinyarwanda, so unlike section 1 there is **no ASR
layer** and no transcription artefacts — a single clean hit is worth more here.

Measured register, on the same test used for every other source:

```
symptom-word lines                     1,229
first-person patient marker lines         12
BOTH first-person and a symptom            2
English prose lines                        0
```

**It is instructional, not clinical narrative and not patient speech.** It says what
a CHW should do and teach, in the second person and the infinitive. So it
substantiates **terminology and its noun-class behaviour** — which is what the
vocabulary blockers need — and it substantiates **nothing about how a patient
phrases a complaint**. Do not read a term's presence here as evidence of register.

Same standing as section 1 in every other respect: **a hit is a lead for the
speaker, never permission to write a phrase.**
