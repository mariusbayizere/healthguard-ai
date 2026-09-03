# Provenance categories — what "speaker rate" should mean

**Design proposal, 2026-09-03. Nothing implemented; the brief's `source` column is
unchanged.** The headline figure is currently **60% speaker**, and it understates
the corpus in a way a reviewer would not accept either — in both directions.

---

## 1. Why the current number is wrong

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

## 2. Proposed categories

Five, replacing the current four. The test for each is stated so it can be applied
mechanically rather than by judgement.

| category | test | count | share |
|---|---|---|---|
| **speaker-authored** | the speaker wrote the words | 77 | 60.2% |
| **speaker-derived** | mechanical person-transform of the *same concept's* speaker-authored phrase | 27 | 21.1% |
| **machine-drafted, speaker-approved** | I composed new wording; the speaker accepted it unchanged | 11 | 8.6% |
| **machine-derived** | person-transform of a machine-drafted phrase | 11 | 8.6% |
| **unresolved** | wording settled, concept still open (CR04 both persons) | 2 | 1.6% |

**128 authored phrases.**

`machine_edited` keeps its meaning (I drafted, the speaker changed it) and is
currently unused — no drafted phrase has been edited rather than accepted or
rewritten, which is itself worth reporting.

## 3. What the numbers become

```
the speaker's own words          104/128   81%     (authored + derived)
newly composed by me              22/128   17%     (drafted + derived-from-drafted)
open                               2/128    2%
```

**81%, not 60%.** And the number that matters for a reviewer asking "how much of
this is machine-generated Kinyarwanda" is the middle row: **17%, every row of
which carries an explicit accept.**

## 4. Why a reviewer should accept this

**The split is mechanical, not rhetorical.** `speaker-derived` is not "I think this
is basically the speaker's" — it is a defined test: the same concept's other
person is `source=speaker` and non-empty. It can be recomputed from the brief by
anyone, and it cannot be gamed by how a note is worded.

**It reports the unflattering number too.** `machine-derived` (11 rows, 8.6%) is
new and is *worse* than the current scheme admits: those are transforms of phrases
I composed, so neither person is speaker wording. The current scheme buries them
inside `machine_approved` alongside the EX18-type rows. Splitting the category
honestly means naming that group, not only the flattering one.

**It matches how the paper will have to describe the method anyway.** "The speaker
authored 77 phrases; a further 27 are grammatical person-transforms of those,
reviewed and accepted individually" is a defensible sentence. "61% speaker" invites
the question the split already answers.

## 5. The one judgement call, stated

A `speaker-derived` phrase is not *only* a person-transform in every case. Some
reuse the speaker's clauses from a **different** concept — GI06's
`Maze ibyumweru birenga bibiri` is CR06's verbatim, GI01's
`ndaruka ibyo ndya byose` is OB10's. Those currently land in
`machine-drafted, speaker-approved`, because the test looks only at the same
concept's other person.

That is deliberate and conservative: it **under**-counts speaker-derived. Widening
the test to "reuses an authored clause verbatim" would raise the 81% further, but
it needs a threshold for how much reuse counts, and a threshold is exactly the
kind of thing a reviewer should distrust. Better to leave the number lower and the
test crisp.

## 6. Implementation, if taken up

Not written. The shape:

- `source` gains `speaker_derived` and `machine_derived`; existing values keep
  their meaning, so nothing in the brief is rewritten by hand.
- `walk.py` sets `speaker_derived` automatically when accepting a third-person row
  whose first person is `speaker` — the operator should not have to classify.
- `progress.py` reports all five and the two roll-ups (81% / 17%).
- A test that the five are exhaustive and that the roll-ups match the sum, so the
  headline cannot drift from the rows the way the current one did.

**Do not backfill by hand.** Every one of the 128 rows can be classified by the
tests above from data already in the brief; a script should do it, and the result
should be checked against these counts.
