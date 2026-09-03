# Language resources, code-switching, and the path to native-quality phrasing

## 1. What exists, and what is actually usable

Licence checked in each case; "usable" means usable for a public, non-commercial
research corpus with attribution.

| resource | licence | usable? | for what |
|---|---|---|---|
| **WHO IMCI chart booklets** | CC BY-NC-SA 3.0 IGO | **yes**, non-commercial, attribute WHO, share-alike | danger-sign *concepts* and clinical framing in EN and FR. The best source found. |
| **Swahili Corpus (Mendeley `d4yhn5b9n6`)** | **CC BY 4.0** | **yes** | has an AFYA (health) category; ~1.69M sentences across 12 domains. Register is news/publication, not patient speech. |
| **MasakhaNER 1.0 / 2.0** | CC-BY-4.0-**NC** | yes if the project stays non-commercial | Kinyarwanda and Swahili text; NER-annotated news. Monolingual source data carries per-site licences. |
| **KINNEWS / KIRNEWS** | not stated on the repo | **unclear — do not use until confirmed** | 3,449 Kinyarwanda news articles from igihe.com. News register, and the licence question is unresolved. |
| **MedlinePlus Kinyarwanda** | CDC items are US-government public domain; Immunization Action Coalition items have their own terms | partially | genuine *patient-facing* Kinyarwanda, but the collection is vaccine/immunisation only — it maps to `preventive` and nothing else. |
| **Emergency Severity Index (ESI)** | © Emergency Nurses Association. Royalty-free licence to *use the algorithm clinically*; reproduction requires written permission | **no** | cannot redistribute descriptors in a dataset |
| **Manchester Triage System** | proprietary, paid licence via ALSG/triagenet | **no** | cannot use |
| **Rwanda CHW benchmarking subset** (figshare `10.6084/m9.figshare.29213147`) | **CC BY 4.0**, read from the figshare record itself | **yes** — the best Kinyarwanda clinical source found | 524 real CHW questions **with Kinyarwanda originals**, plus clinician answers in Kinyarwanda. Substantiates vocabulary; see section 2a. |
| **Waxal / `google/WaxalNLP`** | **per provider**: CC-BY-4.0 for University of Ghana languages only; **CC-BY-SA-4.0** for all the rest | **not for Kinyarwanda — there is none** | 19 ASR / 17 TTS African languages. **Kinyarwanda is absent.** Swahili is present but share-alike; see section 2a. |
| **Mbaza RBC (AAAI 2025)** | not determinable — OpenReview is behind a bot challenge | **unknown, treat as closed** | no released data located; the contact route runs through C4IR/RBC, section 2a. |

**The two triage systems named in the brief are the two that cannot be used.** ESI's
royalty-free grant covers clinical use of the algorithm, not redistribution of its
descriptors as corpus content; MTS is licensed IP. Build the urgency taxonomy from
WHO IMCI instead, which is openly licensed and already the basis for Rwandan
practice.

## 2. Rwanda MoH and community health worker materials

**Not found in machine-readable form.** `moh.gov.rw/publications` exposes six
categories (Legal Frameworks, Guidelines & Protocols, Policies, Strategies, Health
Reports, Scientific Health Publications) but the index pages surface no
Kinyarwanda-language or patient-facing documents, and the one CHD document
retrieved (`CHD-Strategic_plan.pdf`) is an image-based PDF in English with no
extractable Kinyarwanda text.

References exist to a 2011 MoH *Trainer's Guide on Integrated Management of Child
Illness and Community Case Management* and to community-based family planning
materials, but no download was located.

**This is the highest-value unresolved lead.** Rwanda trains roughly 45,000 CHWs
using Kinyarwanda materials; those materials are patient-facing clinical language
of exactly the register needed, and they beat anything drafted. Getting them is a
matter of asking the Community Health Desk directly, not of searching harder — and
that request is better made by a Rwandan colleague than by a scraper.

**Partly answered as of 2026-09-03.** Not the training materials, but 524 real
CHW clinical questions *in Kinyarwanda*, openly licensed, are now in hand — and
the ask above now has a named route and a named contact. See section 2a.

## 2a. Digital Umuganda — the RBC lead, investigated 2026-09-03

Lead: `digitalumuganda.com/publications`. Three items were checked. **Every
licence below was read from the issuing record itself, not from an abstract** —
and in two of the three cases the abstract was wrong or incomplete.

### (1) Nature Health 2026 — 5,609 CHW clinical questions. **Partly released, CC BY 4.0.**

Paper: `nature.com/articles/s44360-025-00038-1`, open access via
`PMC12880909`, article licensed CC BY 4.0.

The headline number is *not* what is released. Quoting the data availability
statement in full:

> "The subset of 524 questions, answers and individual evaluation results that
> comprise this benchmarking study can be accessed via figshare at
> 10.6084/m9.figshare.29213147. The full dataset has been donated to the Rwanda
> Biomedical Centre (RBC) [...] It will be made available to researchers on
> request and based on an assessment of 'fair value exchange' by stakeholders, to
> ensure that the indigenous population that generated the information benefits
> from its exploitation."

**The 524-row subset was downloaded and inspected** (`Supplementary Material 2
(Rwanda).csv`, 18.9 MB, 43 columns, licence CC BY 4.0 per the figshare record).
It is far more useful than the paper implies:

```
524 rows, 524 unique questions, 86 distinct CHWs
question_kinyarwanda        524/524 non-empty   <- the ORIGINAL, not a back-translation
question_english            524/524             <- professional linguist translation
answer_human_kinyarwanda    524/524             <- Rwandan clinician answers
445,401 characters of Kinyarwanda
```

Provenance runs the right way: CHWs submitted **voice recordings in Kinyarwanda**,
transcribed by Digital Umuganda's STT model, screened by trained local nurses, and
only then translated into English. The Kinyarwanda is the source text.

**Register — read it before assuming it fits.** These are CHW-to-clinician case
reports, not patient speech:

```
416/524   third-person patient framing (afite, yaje, arwaye)
277/524   CHW first-person narration ("nakiriye", "nasuye" — I received, I visited)
239/524   reported speech ("ambwira ko" — they tell me that)
 45 words median question length
```

So it maps onto **third-person `{REL}` rows**, not first-person patient
utterances, and it carries a professional overlay (weights, MUAC, temperatures)
that a patient would not produce. It is a **substantiation source, like
`phrase_review_sheet.csv` — not a source of phrases to copy.** Standing rules 5
to 8 are unchanged by it: the speaker still authors.

**It resolves one of the two vocabulary blockers, and not the other.** Both were
checked against the full 445k characters:

| blocker | result |
|---|---|
| `GI03` — a word for stool | **partly unblocked.** `kwituma` (to defecate) is attested 13x in genuine clinical use: *"nyuma ya buri gihe cyo kwituma"*, *"inshuro yitumye"*, and a clinician's definition of diarrhoea — *"umwana afite impiswi iyo yitumye birebire cyangwa byoroshye inshuro zirenga eshatu ku munsi"*. But it is a **verb**, not the noun; `amabyi` = 0 and `umukara` (black) = 0, so **melaena still cannot be written** from this. It is a lead for the speaker, not an answer. |
| `PA08` — a word for ear | **still blocked.** `ugutwi` = 0. `amatwi` appears 4x and **every one is the idiom `gutega amatwi`, "to lend an ear"**, in counselling passages — not the anatomical ear. Do not mistake the hit count for a result. |

Also present and not otherwise attested in the project: `impiswi` 67x, `guhitwa`
23x, `amaraso` 208x. `umwanda` appears 12x but means dirt/filth in hygiene advice
(*"indwara ziterwa n'umwanda"*), **not** stool — a false friend for GI03.

**Caveats.** The Kinyarwanda is an ASR transcript cleaned by nurses, so expect
transcription artefacts. And the copy in `github.com/PATH-AI-Initiative/RwandaBenchmarking`
carries **no licence file at all** (`license: null` on the GitHub API) — the same
CSV is all-rights-reserved there and CC BY 4.0 on figshare. **Use the figshare
copy and cite that DOI.**

### (2) Mbaza RBC (AAAI 2025) — **not verifiable; no data located**

`openreview.net/forum?id=VGxhF4xlWx` and both OpenReview APIs return
`ChallengeRequiredError` — an interactive bot challenge. **The record could not be
read, so nothing about its licence or its "3,000 questions" is confirmed here**;
secondary summaries were not treated as a substitute. No released dataset was
found under that title.

The contact route is the useful outcome, and it is documented in the Nature paper:

> "The Centre for the Fourth Industrial Revolution, as the innovation lab for the
> Rwandan Government, serves as the primary point of contact for researchers
> seeking to access this data. Prospective users should contact 'info@c4ir.rw' to
> request access via GitHub."

Named people who connect the work: **Samuel Rutunda** (Digital Umuganda; first
author of the figshare dataset), **Emery Hezagira** and **Eric Remera** (RBC), and
**Dr Bilal Akhter Mateen** (`bmateen@path.org`), corresponding author on the
protocol paper (`PMC12519661`, CC BY 4.0).

### (3) Waxal — **no Kinyarwanda in it, and it is mostly not CC-BY-4.0**

The premise does not survive contact with the source. Verified three ways: the
HuggingFace card, the raw `README.md` frontmatter, and the provider tables.

**Kinyarwanda is absent.** The declared language list is `ach, aka, amh, bau, dag,
dga, ewe, fat, ful, hau, ibo, kik, kpo, lin, luo, lug, mas, mlg, nyn, orm, pcm,
sid, sna, sog, swa, tir, twi, wal, yor`. No `kin`, no `rw`. Digital Umuganda is a
provider, but its contribution is **Fula, Lingala, Shona, Malagasy, Amharic,
Oromo, Sidama, Tigrinya, Wolaytta** — not the language of the country it is based
in. **The question "do the Kinyarwanda transcripts contain usable health
language?" has no subject.**

**The licence is per provider, not CC-BY-4.0 across the board.** The arXiv
abstract's "released [...] under the permissive CC-BY-4.0 license" is true of one
provider only:

```
University of Ghana   Akan, Ewe, Dagbani, Dagaare, Ikposo      CC-BY-4.0
Makerere University   Acholi, Luganda, Masaaba, Nyankole, Soga CC-BY-SA-4.0
Digital Umuganda      Fula, Lingala, Shona, ... Wolaytta       CC-BY-SA-4.0
Media Trust / Loud and Clear / AIMS Senegal                    CC-BY-SA-4.0
```

The card says so itself: *"Please check the license for the specific languages you
are using, as they may differ between providers."*

**This matters for the Swahili arm, which is the only part Waxal could touch.**
`swa` is present, but under **CC-BY-SA-4.0** — and CC BY-SA 4.0 is **one-way
incompatible** with the CC BY-NC-SA 4.0 this dataset may have to carry (see
`docs/licensing.md` Q2): share-alike forbids adding the NC restriction downstream.
So if the WHO-derived material forces NC, **Waxal cannot be mixed in at all**.
It is also general ASR/TTS speech with no health domain, which was the other thing
the abstract did not say.

### What to do with this

1. **Use the figshare 524 as a substantiation corpus**, alongside
   `phrase_review_sheet.csv` — to confirm a word exists in real Rwandan clinical
   Kinyarwanda before the speaker authors with it. Never as phrases to lift.
2. **Take `kwituma` to the speaker for GI03**, framed as a lead with its attested
   contexts, along with the fact that the noun and the colour term are still
   missing. `PA08` stays blocked; nothing was found.
3. **Ask for the full 5,609** via `info@c4ir.rw` — this is the "fair value
   exchange" route, and it is the same Community Health Desk conversation section
   2 already identified as the highest-value lead. Draft in
   `docs/outreach-digital-umuganda.md`.
4. **Drop Waxal** from the Kinyarwanda plan entirely, and treat it as
   conditional-at-best for Swahili.

## 3. Drafting status

Obstetric is complete: 12 new concepts x 4 languages = 48 drafts, taking obstetric
from 2 to 14 phrases per language. Concepts are WHO maternal danger signs
(eclampsia, pre-eclampsia, cord prolapse, obstructed labour, puerperal sepsis,
reduced fetal movement, PPROM, preterm labour, fever in pregnancy, hyperemesis,
antenatal check, breastfeeding advice); the phrasings are drafted, not copied.

Confidence is recorded per row: **medium** for English and French, **low** for
Kinyarwanda and Swahili.

**On the remaining eight domains, a deliberate recommendation.** For English and
French I can draft the remaining ~180 phrases at the same quality. For Kinyarwanda
and Swahili I should not. A drafted phrase in a language I cannot evaluate is not
a head start for a native speaker — it is an anchor toward my errors, and it is
harder to reject a plausible-looking wrong sentence than to write a right one from
a clear brief. For those two languages the useful artefact is the **concept plus
English gloss** in the review sheet, with the speaker authoring directly.

## 4. Code-switching: how it is built now, and why it is not realistic

The mechanism, from `generate_large_dataset.py` and `vocabulary.py`:

- Six ordered pairs in `MIXED_PAIRS`: kinyarwanda↔english, kinyarwanda↔french,
  swahili↔english.
- Each mixed family has a `frame_language` and a `phrase_language`.
- `Family.render()` assembles `opener + subject + phrase + onset + context + closer`.
  Every slot except `phrase` comes from the frame language; `phrase` comes from the
  other.

So every "mixed" row is **one switch, always at the same syntactic boundary**, with
the symptom phrase wholesale in the other language and no morphological
integration.

Four ways that departs from real Kinyarwanda–English speech:

1. **Insertion, not alternation.** Real bilingual Rwandan speech is typically
   matrix-language framed: Kinyarwanda supplies the morphosyntax and single English
   content words are embedded — often a noun, sometimes a verb stem. The corpus does
   the opposite, swapping a whole multi-word clause at a fixed seam.
2. **No morphological integration.** Embedded nouns in Bantu languages take noun-class
   prefixes and trigger agreement. Corpus mixes drop an English string in unchanged.
3. **Borrowing is not code-switching.** Medical vocabulary — *malaria*, *pressure*,
   *diabetes*, *sugar* — is borrowed into everyday Kinyarwanda even in otherwise
   monolingual speech. Much of what looks "mixed" in real data is a monolingual
   utterance containing established loanwords, a category the corpus has no model of.
4. **The pair inventory is arbitrary.** French pairs only with Kinyarwanda, Swahili
   only with English; there is no kinyarwanda↔swahili or french↔english. Whether
   that reflects Rwandan usage is an empirical question nobody has answered.

**And a structural point that matters more than any of these:** mixed families draw
their `phrase` slot from the *same* 46 phrases per language. **The 48% of the corpus
labelled "mixed" contributes zero additional distinct clinical phrasings** — it
varies the frame, not the clinical content. Expanding the phrase inventory is
therefore worth roughly twice what the row counts suggest.

Making it realistic needs observed data: recordings or transcripts of Rwandan
patients describing symptoms. Failing that, a native speaker should author mixed
utterances directly rather than have them assembled, and the switch points should
come from what they write.

## 5. Review sheet

`review/phrase_review_sheet.csv` — 184 existing phrases plus 48 obstetric drafts.
Columns: `id, status, language, domain, proposed_urgency, phrase, english_gloss,
drafted_by, confidence, speaker_verdict, speaker_corrected_phrase, speaker_notes,
clinician_urgency, clinician_verdict, clinician_notes`.

Every existing phrase is included deliberately. The current 184 have never been
reviewed by a speaker or a clinician either; their labels are internally consistent
because a template assigned them, not because anyone qualified agreed.

## 6. A realistic path to native-quality output in four languages

Assuming access to one Kinyarwanda speaker, one Swahili speaker, and one clinician
familiar with Rwandan primary care.

**Step 1 — validate what exists before adding to it (1 session per language).**
Put the 46 existing phrases per language in front of a speaker. Expect a meaningful
fraction to be rejected or rewritten; the corpus was authored without review. This
also calibrates how much to trust drafted material.

**Step 2 — clinician sets the urgency taxonomy against WHO IMCI (1 session).**
Nine domains x three classes, with IMCI danger signs as the anchor. Output is a
concept list — "what a patient says when presenting with X" — independent of
language. This is the artefact everything else hangs off, and it is licensed.

**Step 3 — speakers author from concepts, not from my drafts (the bulk).**
For each concept, the speaker writes 2–3 natural phrasings. Roughly 120 concepts
x 2 languages is the real work; budget several sessions. English and French I draft
and the clinician reviews.

**Step 4 — code-switching authored, not assembled (1–2 sessions).**
The same speakers write mixed utterances directly. Compare against the current
generated mixes to decide whether the frame/phrase model survives at all.

**Step 5 — regenerate and re-freeze as v2.**
Mechanical and mine: regenerate, re-validate, re-freeze both manifests as v2,
update every count in the README and paper.

**Ordering note.** Steps 1 and 2 are worth doing *before* any large drafting effort,
because both change what gets drafted. And since any vocabulary change invalidates
the v1 manifests, results from a v1 training run will not be comparable to anything
produced after this work.
