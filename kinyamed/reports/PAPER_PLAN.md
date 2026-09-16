# Paper plan — what this project can claim, and on what evidence

**Created 2026-09-16.** This file plans what a paper may assert. It is not the paper
(`ml_model/paper/`). Nothing here is a claim yet: each entry names the evidence that
would license it, and says plainly when that evidence does not exist.

**The standing constraint.** No model quality claim is available. No evaluation set
meeting `EVAL_SET_SPEC.md` exists, the deployment gate refuses on the only held-out set
there is, and no model has been trained through the committed pipeline. A paper written
today is a **negative-results and methodology paper**, and that is the honest frame.

---

## Results section 1 (the headline): a row count is the wrong unit for a corpus requirement

**Claim.** Scaling synthetic generation cannot substitute for authored diversity, and a
corpus requirement expressed as a row count is satisfiable without delivering anything
the requirement was meant to stand for.

**The demonstration, end to end, all of it reproducible from the repository:**

1. The specification asks for **1,000,000 examples** (FR-04-07). Generation produced them
   in **130 seconds**, and the generator's own quality targets passed.
2. Run against the nine corpus gates in the *same* specification, that corpus **fails
   four as generated** (G5, G7, G8, G9) and, on the split where seeds can be counted,
   **six** (G1, G2, G5, G7, G8, G9).
3. The binding gate counts **distinct authored seed phrases**, not rows:

   | Seeds available | Rows allowed by G1 (50/seed) | Passes G2? | Largest passing corpus |
   |---|---|---|---|
   | **165 (today)** | 8,250 | **No** (needs 3,000) | **0 rows** |
   | 3,000 | 150,000 | Yes | 150,000 |
   | 20,000 | 1,000,000 | Yes | **1,000,000 — the target** |

4. **The shortfall to the target is 19,835 seed phrases, not 999,000 rows** — roughly
   660–990 clinician-hours of authoring. Rows are generated at ~7,700/s; seeds are
   written by native-speaking clinicians at 2–3 minutes each.
5. Even at 20,000 seeds, the generated corpus still fails G5, G7, G8 and G9: those
   constrain *how* a row is made (origin, provenance, authorship, surface variation),
   not how many there are.

**What each gate measures, and what failed** (`ml_model/dataset/corpus_gates.py`, 19 tests):

| Gate | What it measures | On the v2 corpus |
|---|---|---|
| G1 | rows per seed (≤ 50; no seed above 0.1%) | **FAIL** — worst seed 8,975 rows, 26.07% of the eval split |
| G2 | distinct seeds per language (≥ 3,000) | **FAIL** — 15 in the eval split, 150 in train, 165 in the whole inventory |
| G3 | lexical diversity against the pilot's own floor | NOT COMPUTABLE — the pilot that defines the floor does not exist |
| G4 | near-duplicate seeds (≤ 2% at Jaccard 0.85) | PASS — 0 of 15 |
| G5 | machine person-transformation banned | **FAIL** — no recorded origin per row |
| G6 | frame consistent with reporter and age group | NOT COMPUTABLE — neither is recorded |
| G7 | per-row provenance complete | **FAIL** — no seed, origin, author or validator columns |
| G8 | author concentration (≤ 20% per language × domain) | **FAIL** — the corpus has no authors |
| G9 | surface variation (case, punctuation, spacing, typos) | **FAIL** — 0 capitalised rows, 0 with stray spacing, no typos |

**Why the claim generalises beyond this project.** The failure is structural, not
local: any corpus requirement stated as a row count can be met by expansion, because
expansion is the cheap operation. The quantity that resists expansion — and that the
model actually needs — is the number of independently authored source items. A
specification that does not state a floor on *that* number has not constrained quality
at all. The same argument applies to any templated, augmented or LLM-expanded corpus,
and the remedy is a one-line change to how the requirement is written: constrain seeds,
and let the row count follow.

**Supporting result (same root cause, measured on the model).** A model trained on a
corpus with no surface variation changes its predicted class under surface variation
alone: **capitalisation 31.5%**, **a single realistic typo 21.0%**, punctuation 5.0%,
extra whitespace 0.0% (the one the tokenizer normalises). This is a corpus-health signal,
not a quality metric (MODEL_AUDIT §11).

## Results section 2: what an evaluation set of nine sentences cannot establish

**Claim.** Cluster structure, not row count, determines what a held-out set can show; a
set of 17,942 rows built from 9 source sentences supports no gate verdict at all.

Evidence: the gate's own refusal (38 of its cells, reproducible from a clean clone), the
seed-resampled intervals on record (accuracy [0.400, 0.914], CRITICAL recall
[0.08, 1.00]), the power derivations in `ml_model/training/eval_spec.py`, and the
majority-class floors (0.4995 on the n=9 set; 0.3418 on the v2 eval split).

## Results section 3: two silent deployment failure modes

1. **A model shipped without its tokenizer loads without error**, returns a five-token
   vocabulary, and answers its class prior on unreadable input, while probabilities,
   determinism and label order all look healthy. Encountered in our own harness and
   initially mistaken for single-class collapse (MODEL_AUDIT §11.1). Already drafted into
   `paper/sections/limitations.tex`.
2. **Surface fragility**, above.

Both are invisible to any metric computed from the model's own outputs.

## What the paper must not claim

- No accuracy, recall, calibration or latency figure for any model, until the gate passes
  on a set meeting EVAL_SET_SPEC. The existing 0.7065 is measured on 9 sentences with a
  floor of 0.4995 beneath it, and is not evidence of deployability.
- No clinical validity of the three-class taxonomy: no document in the repository
  authorises assigning urgency from an unexamined written report (`TAXONOMY_SCOPE.md`).
- v2d is **NOT A BASELINE**. It is an audit artefact.

## Sequence

1. Write sections 1–3 now: they rest entirely on committed, reproducible measurements.
2. The clinician pilot (STATE.md) produces the first authored seeds and the first gold
   labels. Only then does a quality section become possible, and it is reported against
   the gate, not against v2d.
