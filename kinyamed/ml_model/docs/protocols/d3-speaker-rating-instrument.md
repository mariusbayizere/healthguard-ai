# D3 — Native-speaker authenticity rating

**STATUS: NOT EXECUTED.** No rating session has run. The project document's
"1,200 examples rated 1–5 by native speakers" has no source.

## What is being measured

Whether a generated row reads as something a patient would actually say. Not
whether it is grammatical, and not whether the urgency is right — those are D1
and D2.

## The scale

| | |
|---|---|
| **5** | I have heard someone say this, or I would say it |
| **4** | Natural. Nothing in it is wrong |
| **3** | Understandable, but not how I would put it |
| **2** | Odd. A word or the word order is wrong |
| **1** | I would not know what this person means |

**3 is the important boundary.** 4–5 is usable corpus; 1–2 is broken; **3 is the
band this project exists to detect** — grammatical, comprehensible, and not what
a person would say. That is what the v1 corpus was, and an instrument that
collapses it into "fine" would have passed v1.

## Sampling

- **Sample rows, not phrases.** A phrase is rated through its renderings; the
  frame is part of what is judged, and the frame was never speaker-authored.
- **Stratify by urgency and by person.** Third-person rows carry a substituted
  relation and are where the frame is most likely to break.
- **Include the frame slots deliberately.** Some rows should carry an opener,
  onset, context and closer; some should carry none.
- Seeded, and the seed recorded with the ratings.

## Procedure

1. Rater sees the rendered row and the scale. No label, no gloss, no concept id.
2. Ratings are independent; no discussion during the session.
3. A rating of 1–3 may carry a free-text correction. **The correction is worth
   more than the rating** — it is authored language, and it is why this
   instrument exists at all rather than just a score.

## Analysis

`scripts/score_ratings.py` reports the distribution, the mean by urgency and by
person, and **the proportion at 3** separately from 1–2. It refuses to report a
single headline mean without the distribution beside it.

## What executing this does NOT establish

A high mean does not make the corpus large enough. The evaluation base is nine
distinct sentences; authenticity and sufficiency are different properties.
