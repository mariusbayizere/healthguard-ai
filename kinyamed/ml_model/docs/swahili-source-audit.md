# Swahili source audit — 2026-09-04

> **STATUS: Swahili is BLOCKED and OUT OF SCOPE for this phase.** Ruled 2026-09-04
> by the project owner, on grounds this audit does not cover and cannot answer:
> **there is no Swahili speaker.** The owner authors Kinyarwanda and does not speak
> Kiswahili, so even a corpus would leave the language without the one role the
> whole method depends on — someone to author and rule. Swahili needs a corpus
> *and* a speaker; it has neither.
>
> The corpus finding below stands on its own and is the second reason, not the
> first. **Do not re-open this by finding a better corpus.** A corpus would remove
> one of two blocks. The outreach in section 5 is deliberately NOT sent.
>
> `speaker_brief_swahili_v2.csv` stays generated and at 0/254. Nothing generates
> from it, and it is not evidence of intent to fill it.

**Verdict: Swahili would rest on less evidence than Kinyarwanda did, and the gap is
in the one artefact that mattered most.** There is no Swahili equivalent of the 524
CHW questions: no openly licensed corpus of real clinical language produced by
health workers or patients. Everything found is institutional, instructional or
speech-domain text — terminology, not clinical utterance.

Extends `swahili-corpus-assessment.md` (the Mendeley AFYA subset), which stands
unchanged. Every licence below was read from the issuing record or the document's
own copyright page, never from an abstract or a search summary — and in three cases
the summary was wrong.

---

## 1. Does Digital Umuganda hold Swahili clinical text? **No.**

Enumerated all 22 datasets under the `DigitalUmuganda` HuggingFace org via the API.
The split is clean and it runs against Swahili:

| | health **text** | speech |
|---|---|---|
| **Kinyarwanda** | `Monolingual_health_dataset` (CC BY 2.0), `NMT_Health_parallel_data_en_kin` (no licence declared) | `Afrivoice_Kinyarwanda` |
| **Swahili** | **none** | `Afrivoice_Swahili`, `Afrivoice_Swahili_0.0`, `Afrivoice_Swahili-Voice_Instruct_Format`, `anv_test_data_nt_swahili` |

**Their only health *text* is Kinyarwanda/English. Every Swahili holding is ASR
speech.** That is the direct answer: the asymmetry noted for Waxal repeats across
their whole catalogue.

`Afrivoice_Swahili` is not Waxal, so it was checked on its own terms. From the
dataset record itself: `license: cc-by-4.0`, `language: sw`,
`task_categories: automatic-speech-recognition`, `gated: auto`, and the card's own
first line — *"This is an image prompt ASR dataset for Swahili. The dataset was
collected on 5 domains: Agriculture, Education, Finance, Government and Health."*

Two findings about it:

- **The register is image description, not clinical speech.** Speakers describe a
  photograph. A "Health" clip is someone narrating a picture of a clinic, not
  someone reporting a symptom. **This is inferred from the card, not measured** —
  the dataset is gated, and `datasets-server` refuses it without authentication, so
  the transcripts were not read. Treat the register claim as unverified.
- **It is not a Swahili advantage.** Deriving the Health row by subtraction from
  the published totals: Swahili Health ≈ **618 transcribed hours / 120,584 clips**;
  `Afrivoice_Kinyarwanda` publishes Health directly at **992.87 transcribed hours /
  179,219 clips**. Digital Umuganda's Kinyarwanda health speech is *larger* than
  its Swahili. If this is a usable source it was always usable for Kinyarwanda too.

**Side finding, and it is the most valuable thing in this audit — for Kinyarwanda,
not Swahili.** `DigitalUmuganda/Monolingual_health_dataset` is ungated and holds
`rbc_kinyarwanda_health_dataset.txt`: **28,621 lines, 2,480,884 characters of
Rwanda Biomedical Centre Kinyarwanda health text** — 5.6× the 524-question corpus.
The sample lines are CHW training material (*"Gukoresha neza Porogaramu ... y'abajyanama
b'ubuzima"*, *"Kuzuza ifishi y'ubujyanama n'igitabo cy'umujyanama"*, *"ICYIGWA 3.2"*).
This is the artefact `language-resources.md` §2 calls "the highest-value unresolved
lead" and reports as **not found in machine-readable form**. It is on HuggingFace.

Caveats before using it: the card declares **CC BY 2.0**, but the grant is Digital
Umuganda's, not RBC's — the same shape as the figshare/GitHub licence split the
project already caught, and it needs confirming with RBC. The repo also ships
`gpt_generated_medical_data.txt` (42,576 sentences of GPT-4 output) alongside the
RBC file; **only the RBC file is human text**, and mixing them would put machine
Kinyarwanda into an attestation corpus, which is what rules 5–8 exist to prevent.

## 2. Is there a Swahili equivalent of the 524 CHW questions? **No.**

### The structural analogue exists, and it is English-only

Same research programme, same authors (Menon, Denniston, Liu, Emmanuel-Fabula,
Williams, Mateen), same funder: *Benchmarking Large Language Models and Clinicians
Using Locally Generated Primary Healthcare Vignettes in Kenya*, medRxiv
`10.1101/2025.10.25.25338798`, now published as `10.1136/bmjdh-2026-000081`.
**7,606 clinical scenarios co-designed by 145 nurses across Kiambu, Kakamega and
Uasin Gishu**; 507 benchmarked.

Its released data was downloaded and measured rather than inferred from the paper:

```
github.com/pmwaniki/vignette @ v1.0.1   MIT licence   (Zenodo 10.5281/zenodo.17340120)
  Combined review data.csv    33,352 rows — RATINGS ONLY, no vignette text
  Prompt responses.xlsx          507 rows — vignette, clinician answer, 5 LLM answers

507 nurse-authored vignettes, 348,726 characters
  containing any Swahili symptom word ....... 0
  containing any Swahili FUNCTION word ...... 0      (na, ya, wa, kwa, ni, katika ...)
  clinician responses containing Swahili .... 0
```

**Zero. Not few — none**, on a test that cannot miss Swahili, since none of those
function words is an English word. The paper says so itself in its limitations:
*"the language of evaluation was restricted to English. Although our rubric assessed
contextual sensitivity, we did not benchmark performance in Swahili or other local
languages widely used in Kenyan healthcare."*

The Rwandan study released Kinyarwanda source text. Its Kenyan sibling released
English. **The thing that made the 524 valuable is exactly the thing the Kenyan
dataset does not have** — and the larger 7,606 pool is not released at all.

### Jacaranda Health PROMPTS — the best candidate, and it is not released

PROMPTS is a Kenyan maternal-health SMS service; Jacaranda states it trained
UlizaLlama on **over 1 million health questions** in Swahili and Sheng written by
actual mothers. That is patient-voice Swahili of precisely the register this
project needs.

**The HuggingFace org publishes 7 models and 0 datasets.** `Jacaranda/UlizaLlama`,
`UlizaLlama3`, `kiswallama-pretrained` and four others are there; the corpus is not.
The questions are patient data from a live service, so this is unlikely to change
by asking casually — but it is the only Swahili source located whose register is
right, and it is a named organisation with a public research presence.

### Everything else, measured the same way as the AFYA subset

`first-person patient marker` + `symptom word` on the same line, which is what a
first-person phrase needs:

| source | lines | symptom lines | **both** |
|---|---|---|---|
| Mendeley AFYA (prior audit) | 5,775 | 155 | **0** |
| Tanzania NTLP community TB handbook (Swahili) | 3,823 | 152 | **0** |
| Hesperian/COBIHESA environmental health, module 1 | 1,519 | 11 | **1** |
| Hesperian Swahili *Mahali Pasipo na Daktari*, `Kuhara` | 111 | 65 | **0** |

The one hit is a testimonial box: *"nilianza kukohoa kila nilipojaribu kupumua"* —
"I started coughing every time I tried to breathe." It is the right register and it
is one line.

**The Swahili HealthWiki is real and substantial** — `sw.hesperian.org` carries the
full *New Where There Is No Doctor* translation, ~12k characters on diarrhoea alone,
lay vocabulary throughout. It is the best Swahili *terminology* source found, better
than the Mendeley corpus for this purpose. It is instructional second-person
throughout ("if the child has…", "give…"), so it substantiates words and not
utterances — the same limit as every Kinyarwanda MoH document.

### Not ruled out, only unverified

- **Tanzania MoH** (`moh.go.tz`) reset the connection on every attempt. Tanzanian
  MoH patient materials are **not** excluded by this audit; they were unreachable.
  IMCI training materials *were* translated into Kiswahili in 1996 for the Mpwapwa
  and Magu districts, per the DFID implementation report — no machine-readable copy
  was located.
- **Kencorpus** (Kenyan Swahili/Dholuo/Luhya, 7,537 Swahili QA pairs) — no health
  subset documented; licence not confirmed from the record.

## 3. Licences, each read from its own source

| source | licence, verified | usable against the CC BY 4.0 target |
|---|---|---|
| Mendeley Swahili Corpus `d4yhn5b9n6` | **CC BY 4.0**, from the record's structured data | yes — **but the record itself adds** *"further permission may be required for any content within the dataset that is identified as belonging to a third party"*, and it is scraped news and government text. New caveat; not in the prior assessment. |
| `DigitalUmuganda/Afrivoice_Swahili` | **CC BY 4.0**, in `cardData` and tags | yes, but `gated: auto` — terms must be accepted, and the transcripts could not be read without it |
| `DigitalUmuganda/Monolingual_health_dataset` | **CC BY 2.0** (Kinyarwanda/English) | yes, subject to confirming DU may grant it on RBC's material |
| `DigitalUmuganda/NMT_Health_parallel_data_en_kin` | **none declared** — no licence field, no tag | **no** — all rights reserved by default, same trap as the RwandaBenchmarking GitHub mirror |
| Kenyan vignettes (`pmwaniki/vignette`) | **MIT**; preprint CC BY 4.0 | yes — and irrelevant, the data is English |
| AfriMed-QA (`intronhealth/afrimedqa_v2`) | **CC BY-SA 4.0**, `language: ["en"]` | **no, twice over**: English-only, and BY-SA forces BY-SA on the result |
| Hesperian / COBIHESA Swahili print edition | **"Haki zote zimehifadhiwa"** — *all rights reserved*, from the book's own copyright page. Non-commercial copying permitted for public education; *publishing for any purpose requires prior written permission from COBIHESA Trust Fund* | **no**, not without written permission |
| `sw.hesperian.org` HealthWiki | footer reads only `© Copyright — Hesperian Health Guides`. No CC licence declared; their permissions page 404s | **no**, pending a direct answer from Hesperian |
| MedlinePlus Swahili — CDC items | US federal government work, public domain | yes |
| MedlinePlus Swahili — Health Information Translations | from the PDF footer: *"Available for use as a public service without copyright restrictions at www.healthinfotranslations.org"* | probably — but it is a bare unilateral grant, not a licence with defined terms |
| Ped-PRO-CTCAE Swahili (PMC10260717) | article **CC BY 4.0**; the instrument is NCI's and the paper states no terms for it | article yes, **items unclear** |

Search summaries called the Hesperian material "freely available" and AfriMed-QA a
Swahili resource. Both are wrong at the source. That is the third and fourth time
this project has caught an abstract or summary misstating a licence.

## 4. The one genuine patient-voice find, and how small it is

**Ped-PRO-CTCAE Swahili** — *Swahili translation and cultural adaptation of the
pediatric patient-reported outcomes version of the CTCAE*, validated at Bugando
Medical Centre, Mwanza, through three rounds of cognitive interviews with **12
patients aged 8–17 and 5 caregivers**. **15 symptom terms**, wordings published in
the supplementary files: `Maumivu ya tumbo` (stomach pain), `Wasiwasi` (worried),
`Kuhisi ganzi (kama mkono au mguu kulala)` (numbness).

This is the only Swahili source found where symptom wording was tested against real
patients for how they actually say it. It is 15 terms in paediatric oncology, and
the instrument belongs to NCI.

## 5. The honest comparison

Kinyarwanda did not start from patient speech either — the 524 are CHW case reports,
416 of them third-person. The difference is not register. It is that Kinyarwanda had
**one human-authored, openly licensed, clinical-register artefact of real size**
(445,401 characters, CC BY 4.0, cited by DOI) against which a word could be checked,
plus 184 existing project phrases and a review sheet.

Swahili has no such artefact. It has:

- more *institutional* health text than Kinyarwanda (AFYA, 110k words) — measured at
  zero patient-voice lines;
- a better lay-terminology source than Kinyarwanda (Hesperian's Swahili WTND) —
  which is not openly licensed;
- comparable ASR speech — gated, image-prompted, and smaller than the Kinyarwanda
  equivalent;
- 15 cognitively validated symptom terms;
- no CHW corpus, no clinical questions, no consultation transcripts.

**So `attest.py` would run with a materially weaker corpus behind it.** The check
that resolved `kwituma` for GI03 and correctly refused `ugutwi` for PA08 — "does
this word appear in real clinical use, and in how many independent records" —
has no equivalent evidence base in Swahili. Every vocabulary flag would come back
"attested in a ministry press release" or "not attested", and neither answer helps
a speaker decide.

**Recommendation.** Do not open Swahili as a second authored language yet. Three
things would change the assessment, in order of value:

1. **Ask Jacaranda Health.** Named organisation, public research programme, the only
   located source whose register is right. Even a small released sample would be
   worth more than everything else in this audit combined.
2. **Ask Hesperian for terms on the Swahili HealthWiki.** A CC grant would give the
   Swahili arm its terminology base in one email. Their English materials have
   carried open licences before; the Swahili site simply does not say.
3. **Reach Tanzania MoH by a route that is not their website**, which is what the
   Rwanda MoH conversation already established as the working method.

Until at least one lands, Swahili phrases would be authored against a speaker's
judgement alone, with no attestation check behind them — which is the position
Kinyarwanda was in before 2026-09-03, and the reason `attest.py` was built.

## 6. What this audit did not establish

- `Afrivoice_Swahili` transcripts were **not read** (gated). Its register is inferred
  from the card's own description.
- `moh.go.tz` was **unreachable**, not empty. Tanzanian MoH materials remain open.
- Kencorpus was not retrieved; no health subset is documented, but none was ruled out.
- Jacaranda's absence from HuggingFace does not prove no release exists elsewhere.
- The 7,606-scenario Kenyan pool is unreleased; only the 507 rated subsample is public.
