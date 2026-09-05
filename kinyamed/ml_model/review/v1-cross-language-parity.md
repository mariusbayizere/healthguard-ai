# v1 cross-language parity: all 46 positions checked

**Seven positions where English, French and Swahili agree with each other and
say something the Kinyarwanda does not.** Three were found by accident; this is
the full survey the reviewer asked for.

The corpus's claim is that one concept id, one urgency label and one position
mean the same presentation in every language. At these seven it does not, in the
**shipped v1 corpus**, so a model learns a different presentation depending on
which language the row came from.

## Method, and where it is weak

French and Swahili I read directly, English likewise; the three-way agreement is
firm. **The Kinyarwanda side is the weak link** — I am reading it from vocabulary
attested across this project, not as a speaker. Every row below needs the
speaker's confirmation before it is acted on. Where `attest.py` could settle a
word I ran it, and those results are given.

Direction matters and is stated per row: `KY < others` means the other three
claim more than the Kinyarwanda does.

## The seven

| id | kinyarwanda says | en / fr / sw say | direction | confidence |
|---|---|---|---|---|
| **EX15** | vomiting and severe **weakness** (`gucika intege`) | signs of **dehydration** | KY ≠ others | high |
| **EX35** | a twisted **mouth** (`umunwa wagoramye`) | a drooping / deformed **face** | KY ≠ others | high |
| **EX37** | mild tiredness | mild tiredness **during the day** | KY < others | high |
| **EX42** | a rash **on the body** | a rash **spreading** | KY < others | high |
| **EX43** | high fever and **does not eat** (`ntarya`) | high fever and **refuses** to eat | KY < others | high |
| **EX13** | repeated vomiting and **I do not eat** (`sindya`) | repeated vomiting and **cannot** eat | KY < others | medium |
| **EX04** | breathing badly, lips **changing colour** | lips turning **blue** | KY < others | high — **still open**, see below |

### Attestation behind three of them

- `yanga` / `kwanga` (to refuse): **not** in the speaker's phrases, **not** in
  approved v1 vocabulary, **not** in the review sheet. Only in the CHW corpus.
  So the Kinyarwanda at EX43 and EX13 does not say "refuse" — the word exists in
  Rwandan usage and was not the one used.
- `gukwirakwira` (to spread): same picture — RBC curriculum only, nothing in the
  speaker's or the approved sets. EX42's Kinyarwanda does not claim spread.
- `ubururu` (blue): attested in the speaker's own work, but **not in EX04 any
  more** — it survives in `CR03` (`Iminwa yanjye yahindutse ubururu`, blue lips)
  and in `EX41` (`uruhu rwe rwahindutse ubururu`, a child's skin). The word is
  available and the speaker chose not to use it here, which is the strongest
  form this evidence takes.

### EX04 — CORRECTED, and it went the other way

When this survey ran, EX04's Kinyarwanda first said `ibara` (colour) and its
third said `ubururu` (blue), and I read that as the speaker closing a parity gap
independently. **That reading is now wrong.** The Kinyarwanda has since been made
consistent in the opposite direction: both persons now say `ibara`. The gap
against English, French and Swahili is open in both persons, and the Kinyarwanda
side is settled.

So EX04 does not show the speaker converging on the other three languages. It
shows the corpus doing what this document argues it should — keeping the
patient's report and leaving the clinical term to the concept that owns it.
`CR03` is that concept: its speaker text is `Iminwa yanjye yahindutse ubururu`,
blue lips, central cyanosis. EX04 and CR03 were distinguishable only by that one
word, and dropping *blue* from EX04's English separates them.

English corrected accordingly: `I am struggling to breathe and my lips have
changed colour`. French and Swahili need the same.

## Five more that are mixed, not three-against-one

Listed so the survey is complete and so nobody re-finds them as new:

| id | the split |
|---|---|
| EX05 | en/fr "crushing", ki/sw "severe" — 2-2 |
| EX19 | en/fr "deep" wound, sw "big", ki "serious" — 2-1-1 |
| EX08 | en "readings", fr "taux/level", ki "exceeds the limit", sw just "a lot of sugar" |
| EX25 | ki puts the severity on **both** fever and cough; the other three on the cough only |
| EX21 | **English alone** adds "a *bad* fall"; ki/fr/sw say only "a fall" |

EX21 is the only place English is the outlier on its own, and it is the mildest
of the twelve.

## Why this is not a translation-quality complaint

The three non-Kinyarwanda languages agree with each other at every one of the
seven. That is not what independent translation error looks like. The pattern
says the four cells were drafted from a shared clinical idea, and the Kinyarwanda
was drafted more conservatively — it says what a patient reports, while the other
three say what the sign is called. `gucika intege` is what someone feels;
"dehydration" is what a clinician concludes. `umunwa wagoramye` is what a family
sees; "drooping face" is the stroke exam.

**On that reading the Kinyarwanda is the better corpus and the other three
languages are the ones that need correcting** — which is the opposite of how a
parity defect is usually resolved, and it is the reviewer's call, not mine.

## What has to happen before v2

1. Put all seven to the speaker; EX04 shows they will have views.
2. Decide the direction per row — pull en/fr/sw back to the patient's report, or
   push the Kinyarwanda up to the clinical term. **Do not split the difference
   per language.**
3. `EX43` additionally has a label question — see `review/ex-concept-drift.md`.
4. Whatever is decided, French and Swahili move with English. Swahili is blocked
   for authoring, but this is a correction to existing v1 text, not authoring,
   and leaving it would keep a defect in the corpus that the block was never
   about.
