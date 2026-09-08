# D5 — Community health worker consultation guide

**STATUS: NOT EXECUTED.** These consultations did not occur. The project
document describes consultations at three health centres; none took place, and
nothing here may imply otherwise.

## Why this is worth doing before more corpus is written

Every phrase in the corpus was authored by a speaker imagining how a patient
speaks. That is the best available source and it is not the same as observation.
A CHW hears the real thing daily.

The one question the whole corpus is guessing at:

> **Roughly what proportion of patients describing symptoms switch languages
> mid-sentence?**

v1 set that at 48% as a generation target. It has never been measured, and
`docs/code-switching-design.md` records that it has no answerable form without
observed data. A CHW can answer it approximately, which is infinitely better
than a target chosen arithmetically.

## Session structure — 45 minutes

**1. How people actually present (15 min).** Open, not prompted. What do people
say first? Do they name a body part, a duration, a fear? Do they name the
illness they think they have?

**2. Language (15 min).** Which language do patients use? Does it change with
age, with the interviewer, with the topic? Do they mix within one sentence, and
if so what gets switched — a noun, a whole clause? Which medical words are
always the borrowed ones?

**3. Read them the corpus (15 min).** Rendered rows, no labels. Would a patient
say this? What would they say instead? **This is the highest-value fifteen
minutes** and should not be cut if the session runs over.

## What to bring back

- Recorded answers to the switching proportion, with the CHW's own hedging intact.
- Corrections to specific rows, attributed and dated.
- Any presentation the taxonomy has no concept for. **A missing concept is a
  finding**; the taxonomy was assembled from WHO guidance and one speaker, and
  neither sees a waiting room.

## What NOT to do

Do not ask a CHW to approve the urgency taxonomy — that is D2 and needs a
clinician. Do not treat corrections as authored corpus rows: they are leads for
the speaker, under the same rule as `attest.py` hits.
