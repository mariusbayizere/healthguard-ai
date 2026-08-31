# Roadmap and future scope

Written to be usable as the basis of a paper's future-work section. Every figure
here traces to a measurement recorded elsewhere in `docs/`.

---

## Phase 1 (current) — a leakage-controlled triage classifier

Where the project is. A 1,000,000-row corpus from 184 seed phrases, two frozen
evaluation splits, a reproducibility chain verified in CI on every push. No model
has been trained on the leakage-controlled splits, so no accuracy is claimed.

The known limitation is stated plainly rather than deferred: 184 clinically distinct
items, no clinician review, no native-speaker validation.

## Phase 1b — vocabulary expansion to v2

Expand to 504 phrasings (14 per domain per language), authored by native Kinyarwanda
and Swahili speakers and reviewed by a Rwandan clinician, then regenerate at
**1,008,000 rows** and re-freeze both manifests as v2.

### Why 1,008,000 and not more

This is a deliberate choice against a larger number, and the reasoning belongs in
the paper rather than in a footnote.

At 504 phrase strings the corpus admits **18,900,000 distinct template combinations**
— 2.74x v1 — so repetition is not the binding constraint. 2,000,000 rows would use
only 10.6% of that space and nothing would repeat. The constraint is different:

| rows | rows per phrase |
|---|---|
| 1,008,000 | **2,000** |
| 1,500,000 | 2,976 |
| 2,000,000 | 3,968 |
| 3,000,000 | 5,952 |

**Rows-per-phrase is the honest measure of how much clinical variety a row count
represents.** A million rows resting on 184 phrases carries roughly 184 phrasings'
worth of variety, not a million; that is why v1's Limitations section has to concede
the point. Raising the row count without adding phrases does not add variety — it
adds repetition, and makes the concession worse. At 3,000,000 rows the v2 corpus
would be *less* diverse per phrase than v1 is today (5,952 against 5,435), which
would mean the vocabulary work had bought nothing.

So 1,008,000 = 504 x 2,000 is the point where the corpus is as large as its clinical
content honestly supports. If a larger corpus is wanted later, the lever is phrases:
1,000 phrase strings would support 2,000,000 rows at the same quality. Fund
phrasings, not rows.

## Phase 2 — retrieval over a clinician-approved answer bank

The natural next capability is answering patient questions, not only classifying
urgency. The right form for that is **retrieval, not generation**.

The system retrieves the closest clinician-written answer from a curated bank and
presents it verbatim, framed as guidance rather than diagnosis, with an explicit
instruction to see a health worker. It generates no free text.

Why this design:

- **It cannot hallucinate.** Every answer was written and approved by a clinician
  before it entered the bank. The failure mode becomes retrieving a less relevant
  answer, which is recoverable, rather than fabricating a dosage, which is not.
- **It is evaluable.** Retrieval accuracy is measurable against a labelled set
  without a clinician grading free text for every model version — the constraint
  that makes generative medical systems hard to validate in low-resource languages.
- **The retrieval component already exists.** KinyaColBERT is a lexically grounded
  retrieval model built specifically for low-resource retrieval-augmented generation
  in Kinyarwanda; Kinyarwanda NLP has strong encoders and retrievers.
- **It reuses the work already under way.** The clinician sessions and speaker
  sessions that produce v2 produce answers as a by-product; a few hundred approved
  answers is already a useful system, where a few hundred instruction-tuning pairs
  is not.
- **It degrades safely.** A poor retrieval shows a less relevant but still
  clinician-written answer.

Realistic scope: months, with the same team as Phase 1b.

## Future scope — generative assistant, and why it is not Phase 3

A model that answers open medical questions in Kinyarwanda is a separate,
multi-year effort with a different team. It is documented here as considered and
deferred, not overlooked.

**The deciding constraint is data, and it is not close.** Published Kinyarwanda
monolingual text amounts to roughly **0.4–0.5 billion tokens**. A Chinchilla-optimal
8B model wants ~160 billion; Llama 3 saw ~15 trillion. Kinyarwanda has about **0.25%
of what a single 8B model wants**. That gap does not close with funding or hardware.

**Compute is affordable, which is precisely why it is not the bottleneck.**
Continued pretraining an 8B model over the available corpus is roughly 7.7e19 FLOPs
— about a day on 8xA100 and a few hundred dollars. The real cost is clinician time:
10,000 clinically verified Kinyarwanda medical question-answer pairs, at an
optimistic five minutes each, is around 830 hours — five months of one clinician
doing nothing else. Fifty thousand pairs is over two years. Clinician-hours do not
scale with money the way GPUs do.

**The shape of existing Kinyarwanda NLP tells the same story.** There are good
encoders (KinyaBERT, AfroXLMR, SERENGETI), retrievers (KinyaColBERT) and embeddings
(KinyaEmbed), and essentially no generators. InkubaLM, the flagship African-language
small model, covers Swahili, Yoruba, isiXhosa, Hausa and isiZulu — not Kinyarwanda.
That is not an accident of effort; it reflects what the available data supports.

**Evaluation is the harder half.** A generative medical system requires thousands of
outputs graded by clinicians who speak the language, repeated on every model
version. Hallucination is worst in low-resource languages, where models are least
grounded and most fluent-sounding, and where fewest reviewers exist to catch a
confidently wrong answer. Safety behaviour transfers poorly across languages: a
model that refuses appropriately in English may not in Kinyarwanda. And an
open-ended medical assistant is a clinical decision support tool, which brings
Rwanda FDA and Ministry of Health approval, a liability framework and an incident
process as prerequisites rather than follow-ups.

Estimated: **3–5 years with a funded team of five to ten, including at least two
Kinyarwanda-speaking clinicians working substantially on data creation and
evaluation.** With one researcher and no dedicated clinical time it does not
converge.

Stating that plainly is more useful than a roadmap that implies otherwise.
