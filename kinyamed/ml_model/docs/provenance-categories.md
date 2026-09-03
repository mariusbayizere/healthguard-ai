# Provenance categories — what "speaker rate" should mean

**Adopted and implemented 2026-09-03.** `review/provenance.py` derives the
categories, `--write` backfilled the brief, `walk.py` re-derives after every
decision, `progress.py` reports them, and `tests/test_provenance.py` pins the
properties.

**Correction against the first draft of this document.** It reported 27
speaker-derived and 11 machine-drafted. The implementation gives **24 and 14**:
the hand count called a row speaker-derived whenever its *counterpart* was
speaker-authored, but IF05, OB02 and OB07 have a speaker-authored **third** and a
machine-drafted **first**, and a first-person phrase is not a transform of a third.
Direction matters, and the looser test inflated the headline. 81% became 79%.

The figure this replaces was **60% speaker**, which understated the corpus in a
way a reviewer would not accept either — in both directions.

---

## 1. Why the old number was wrong

`source` has four values: `speaker`, `machine_approved`, `machine_edited`,
`not_applicable`. The headline divides `speaker` by `speaker + machine_approved`.

That treats these two as the same thing:

```
GI02 third   {REL} araruka amaraso.
             a person-transform of a phrase I drafted and the speaker accepted

EX18 third   {REL} ari kuva amaraso menshi kandi ntahagarara.
             ndi -> ari on a sentence the SPEAKER WROTE, nothing else moved
```

The second is not machine-authored in any sense a linguist would recognise. Every
content word is the speaker's; the only change is a subject-agreement morpheme
that Kinyarwanda grammar determines. Calling it `machine_approved` and then
reporting a falling speaker rate makes the corpus look like it is drifting away
from its speaker as more third-person work lands — **which is the opposite of what
is happening.**

The rate has fallen 74% -> 66% -> 61% across three batches, entirely because
third-person transforms accumulated. Nothing about the speaker's involvement
changed.

## 2. The categories

Five, replacing the old four. The test for each is stated so it can be applied
mechanically rather than by judgement.

| category | test | count | share |
|---|---|---|---|
| **speaker-authored** | the speaker wrote the words | 77 | 60.2% |
| **speaker-derived** | mechanical person-transform of the *same concept's* speaker-authored phrase, **third person only** | 24 | 18.8% |
| **machine-drafted, speaker-approved** | I composed new wording; the speaker accepted it unchanged | 14 | 10.9% |
| **machine-derived** | person-transform of a machine-drafted phrase | 11 | 8.6% |
| **unresolved** | wording settled, concept still open (CR04 both persons) | 2 | 1.6% |

**128 authored phrases.**

`machine_edited` keeps its meaning (I drafted, the speaker changed it) and is
still unused — no drafted phrase has been edited rather than accepted or
rewritten, which is itself worth reporting.

## 3. What the numbers become

```
the speaker's own words          101/128   79%     (authored + derived)
newly composed by me              25/128   20%     (drafted + derived-from-drafted)
open                               2/128    2%
```

**79%, not 60%.** And the number that matters for a reviewer asking "how much of
this is machine-generated Kinyarwanda" is the middle row: **20%, every row of
which carries an explicit accept.**

## 4. Why a reviewer should accept this

**The split is mechanical, not rhetorical.** `speaker-derived` is not "I think this
is basically the speaker's" — it is a defined test: the same concept's other
person is `source=speaker` and non-empty. It can be recomputed from the brief by
anyone, and it cannot be gamed by how a note is worded.

**It reports the unflattering number too.** `machine-derived` (11 rows, 8.6%) is
new and is *worse* than the current scheme admits: those are transforms of phrases
I composed, so neither person is speaker wording. The old scheme buried them
inside `machine_approved` alongside the EX18-type rows. Splitting the category
honestly means naming that group, not only the flattering one.

**It matches how the paper will have to describe the method anyway.** "The speaker
authored 77 phrases; a further 24 are grammatical person-transforms of those,
reviewed and accepted individually" is a defensible sentence. "60% speaker" invites
the question the split already answers.

## 5. The one judgement call, stated

A `speaker-derived` phrase is not *only* a person-transform in every case. Some
reuse the speaker's clauses from a **different** concept — GI06's
`Maze ibyumweru birenga bibiri` is CR06's verbatim, GI01's
`ndaruka ibyo ndya byose` is OB10's. Those land in
`machine-drafted, speaker-approved`, because the test looks only at the same
concept's other person.

That is deliberate and conservative: it **under**-counts speaker-derived. Widening
the test to "reuses an authored clause verbatim" would raise the 79% further, but
it needs a threshold for how much reuse counts, and a threshold is exactly the
kind of thing a reviewer should distrust. Better to leave the number lower and the
test crisp.

## 6. Implementation

- `source` gained `speaker_derived` and `machine_derived`; existing values keep
  their meaning. **Backfilled by script, not by hand** — 35 rows moved out of
  `machine_approved`, 24 to `speaker_derived` and 11 to `machine_derived`.
- `walk.py` re-derives after every decision, so the operator never classifies and
  the two derived categories — which depend on the *other* person's row and so
  cannot be set when one row is accepted — are never left to memory.
- `progress.py` prints all five and both roll-ups.
- `tests/test_provenance.py` pins seven properties, including that the stored
  column matches what the classifier derives (so the cache cannot drift from the
  function), that `speaker_derived` is only ever a third person, and that the
  roll-ups partition the authored rows.
