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
