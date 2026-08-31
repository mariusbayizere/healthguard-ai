# Generative Kinyarwanda medical assistant — feasibility

**Verdict: a separate multi-year effort, not Phase 2 of this project.** The reason
is not ambition or compute. It is that the training data does not exist and the
evaluation problem is unsolved.

## The number that decides it

Kinyarwanda monolingual text available for pretraining, from published corpora:
roughly **426 million words / 16.1M sentences / 2.5 GB**, with a comparable crawl
reporting 1.2M documents / 18M sentences / 2.8 GB. Call it **~0.4–0.5 billion
tokens** in total, and much of it Wikipedia, news, legal and religious text.

For scale:

| | tokens |
|---|---|
| All available Kinyarwanda text | ~0.4 B |
| Chinchilla-optimal for an 8B model | ~160 B |
| Llama 3 pretraining | ~15,000 B |

**Kinyarwanda has about 0.25% of the data one 8B model wants, and 0.003% of what a
current frontier model saw.** No amount of compute closes that. This is the whole
answer; everything below is detail.

## Model class and scale

Three routes, none good:

1. **Fine-tune an open multilingual model** (Llama 3.1 8B, Gemma 2 9B, Qwen 2.5).
   Cheapest. But these models saw very little Kinyarwanda, and their tokenizers
   fragment it badly — a morphologically rich Bantu language costs far more tokens
   per word than English, which degrades quality and inflates inference cost.
   Expect fluent-sounding but unreliable Kinyarwanda.
2. **Continued pretraining then instruction tuning.** Better, and what you would
   actually do. Bounded by the 0.4B tokens above; you would be repeating the corpus
   for several epochs, which has diminishing and eventually negative returns.
3. **Frontier API model with retrieval.** Best Kinyarwanda quality today, but you
   do not control it, it changes under you, and sending patient descriptions to a
   third-party API is a data-governance question before it is a technical one.

Realistic scale for open-ended medical QA: **7–9B parameters minimum**. Smaller
models hallucinate too freely for medical content. Note that **InkubaLM (0.4B), the
flagship African-language small model, does not include Kinyarwanda** — its five
languages are Swahili, Yoruba, isiXhosa, Hausa and isiZulu.

## Training data required, and what it would cost to make

| stage | needed | exists? |
|---|---|---|
| Continued pretraining | 5–20 B Kinyarwanda tokens | **No.** ~0.4 B exists |
| Medical instruction tuning | 10k–50k clinician-verified Kinyarwanda medical Q&A pairs | **No.** Essentially zero exist |
| Preference/safety tuning | 5k–20k ranked Kinyarwanda response pairs | **No** |
| Evaluation set | 2k–5k clinician-graded held-out questions | **No** |

The instruction data is the item people underestimate. At an optimistic 5 minutes
per pair to author and clinically verify, **10,000 pairs is ~830 hours — about five
months of one clinician working full time on nothing else.** 50,000 pairs is over
two years. And that is before preference data or evaluation sets.

## Compute and cost — not the bottleneck

Continued pretraining an 8B model on ~1.6B tokens (0.4B x 4 epochs) is about
7.7e19 FLOPs. On 8xA100 at realistic utilisation that is **roughly a day of
wall clock and a few hundred dollars of rented GPU.** Instruction tuning is
cheaper still.

**Compute is genuinely affordable. That is precisely why it is not the constraint,
and why "we could train it on a grant" is the wrong frame.** The cost is in
clinician hours and speaker hours, and those do not scale with money the way GPUs do.

## What exists for Kinyarwanda that could be built on

- **KinyaBERT** — encoder, morphology-aware, strong for classification. Not generative.
- **AfroXLMR / AfriBERTa / SERENGETI** — multilingual encoders. Not generative.
- **KinyaColBERT** — a lexically grounded *retrieval* model built explicitly for
  low-resource retrieval-augmented generation in Kinyarwanda. **This is the most
  relevant existing asset, and it points at the realistic architecture.**
- **KinyaEmbed** — sentence embeddings.
- **NLLB-200** — covers Kinyarwanda for translation.
- **KINNEWS/KIRNEWS**, Masakhane sets — small, news-domain, licence questions.

Note the shape of that list: Kinyarwanda NLP has good **encoders and retrievers**
and essentially no **generators**. That is not an accident of effort; it reflects
what the available data supports.

## Timeline, honestly

With a funded team of 5–10 including at least two Kinyarwanda-speaking clinicians
working substantially on this: **3–5 years to something deployable.** With one
person and no dedicated clinical time: it does not converge. The limiting resource
is clinician-hours for data creation and evaluation, and that is a hiring and
funding problem, not an engineering one.

## Safety work required before anyone uses it

This is where I would push back hardest.

1. **You cannot evaluate what you cannot read at scale.** A generative medical
   system needs thousands of outputs graded by clinicians who speak the language,
   repeatedly, on every model version. This project currently cannot get 184
   phrases reviewed. The gap is not incremental.
2. **Hallucination in medical advice is the failure mode**, and it is worse in
   low-resource languages, where models are least grounded and most fluent-sounding.
   A confidently wrong dosage in Kinyarwanda is harder to catch than one in English,
   because fewer reviewers exist.
3. **Refusal behaviour has to work in Kinyarwanda**, including for questions the
   system should not answer at all. Safety training transfers poorly across
   languages; a model that refuses correctly in English may not in Kinyarwanda.
4. **Regulatory.** An open-ended medical Q&A system is a clinical decision support
   tool. Rwanda FDA and MoH approval, a liability framework, and an incident
   process are prerequisites, not follow-ups.
5. **A red-team set in Kinyarwanda** — adversarial and ambiguous cases, authored by
   clinicians. Does not exist and would have to be built.

## What is actually a plausible Phase 2

**Retrieval over a clinician-approved Kinyarwanda answer bank — not open
generation.**

The patient asks a question; the system retrieves the closest clinician-written
answer and shows it, verbatim, with a "this may not match your situation, see a
nurse" framing. It generates nothing.

- Every answer was written and approved by a clinician, so it cannot hallucinate.
- It is evaluable: retrieval accuracy is measurable without grading free text.
- **KinyaColBERT already exists for exactly this**, and the retrieval quality
  problem is far more tractable than the generation quality problem.
- It reuses the vocabulary and clinician work already underway rather than needing
  a different kind of data.
- A few hundred approved answers is a useful system. A few hundred instruction
  pairs is not.

That is a genuine Phase 2: months, not years, and it degrades safely. The generative
version is a different project with a different team, and it should be planned as
one rather than as an extension of this.
