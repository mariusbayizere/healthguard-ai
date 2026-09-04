# Closing the phrase holdout over near-duplicates

**Sections 1-5 IMPLEMENTED 2026-09-03** (containment fixed, `PREFIX_UNION_CHARS =
30`). **Sections 6-7 are open design**, and section 7 is the larger of the two —
it found that a concept's own two persons split across the holdout in 60 of 61
cases, which no similarity rule catches and no similarity rule should.

Prompted by four pairs of concepts noticed by hand during rulings. Measuring it
changed the proposal three times.

---

## 1. There is a live bug underneath the design question

`phrase_components` unions on **raw substring containment**:

```python
if inner != outer and inner in outer:
    union(inner, outer)
```

Every v2 phrase is an utterance ending in a full stop, and many are capitalised.
Both defeat a raw `in`. So:

```
EX14 third   {REL} arababara cyane mu nda.
GI07 third   {REL} arababara cyane mu nda kandi ububabare ntibuhagarara.
```

**is not a containment today, because of the period** — even though at render time
`_drop_terminal_stop` removes exactly that period whenever a continuation follows,
so the *rendered rows* do contain one another. Five authored pairs are affected:

```
CR02 f / EX02 f    differs by CAPITALISATION
CR02 t / EX02 t    terminal stop
EX02 t / EX04 t    terminal stop
EX14 f / GI07 f    capitalisation
EX14 t / GI07 t    terminal stop      <- I asserted this pair WAS unioned. It is not.
```

**This is the fourth time a terminal stop has defeated a string match in this
codebase.** `attribute_phrase` failed the same way three times (section 9 of the
handover). The fix there was `_match_form` — lowercase, drop a terminal stop —
which already exists **in this very file** and is simply not used by
`phrase_components`.

**v1 cannot be affected.** Of v1's 184 phrases, **0 end in sentence punctuation
and 0 begin capitalised** — they are noun-phrase fragments. Normalising the
containment check leaves v1's partition provably identical, so the frozen phrase
split survives. Verified by comparing the full partition, not just the group count.

**Fix this first, whatever else is decided.** It is not a new policy; it is making
an existing safeguard work on the phrase form the corpus now uses.

## 2. The scale of the actual near-duplicate problem

128 authored phrases. Non-containment pairs sharing a prefix:

| shared prefix | pairs |
|---|---|
| >= 15 chars | 85 |
| >= 20 chars | 55 |
| >= 25 chars | 18 |
| >= 30 chars | 8 |

85 pairs at 15 characters is not a defect list — it is **the domain's grammar**.
Every obstetric third person opens `{REL} aratwite kandi`; every fever one opens
`{REL} afite umuriro`; every wound one opens `{REL} afite igikomere`. Those heads
are shared because that is how the language expresses the category.

So the question is not "which pairs share a prefix" but "at what point does a
shared prefix stop being grammar and start being a leak".

## 3. Option A — a shared-prefix threshold

Union any two phrases sharing at least N leading characters.

**Cost, measured on the 128 authored phrases:**

| threshold | phrase groups | largest group | v1 partition |
|---|---|---|---|
| containment only | 126 | 2 | — (today) |
| 40 | 126 | 2 | identical |
| 35 | 124 | 2 | identical |
| **30** | **118** | **2** | **identical** |
| 25 | 112 | 4 | identical |
| 22 | — | — | **CHANGED — breaks frozen digests** |
| 20 | 97 | 6 | **CHANGED** |

**A threshold of 25 or higher is v1-safe** — v1's fragments share no long heads, so
its partition is byte-identical and `verify-full` keeps passing. Below 22 it
breaks.

**What threshold 30 catches — and this is the argument for it:**

```
38  EX01 t / EX05 t          <- NOT noticed by hand
38  CR06 t / GI06 t          <- NOT noticed
34  IF02 t / EX25 t          <- NOT noticed
32  EX19 t / HT02 t          hand-flagged
31  EX01 f / EX05 f          <- NOT noticed
31  CR06 f / GI06 f          <- NOT noticed
30  EX18 t / EX20 t          hand-flagged
30  CR02 t / EX04 t          <- NOT noticed
```

**Eight pairs, of which six were missed by a reviewer who was actively looking
for this exact pattern across four separate rulings.** That is the case against
relying on human noticing, and it is a strong one.

Costs: it is a blunt instrument that will occasionally union two concepts that
genuinely differ early (none in the current set, but the corpus is 40% authored);
and the threshold is a magic number with no principle behind it beyond "v1-safe
and catches what we found".

## 4. Option B — a manual pairing declaration

A `NEAR_DUPLICATES` map alongside `PHRASE_VARIANTS`, declaring pairs of *distinct*
concepts that must share a phrase group.

**This is what `PHRASE_VARIANTS` does, and the difference matters.**
`PHRASE_VARIANTS` maps a second phrasing to its concept's primary — one concept,
two wordings. Here the concepts are genuinely different and both keep their own
label; only the grouping is shared.

Cost: **it does not scale and it fails in the direction that hurts.** Six of eight
pairs at threshold 30 went unnoticed by deliberate inspection. A declaration
mechanism catches only what someone thinks to declare, and a missed pair is
silent — the same failure shape as the empty `CONCEPT_RELATIONS`, which sat unread
for weeks.

It has one real virtue: it records *why* a pair is grouped, which a threshold
cannot.

## 5. Option C — normalised containment plus a threshold, with the pairs recorded

Recommended.

1. **Fix the containment check** to use `_match_form` (section 1). Not optional
   and not a policy choice.
2. **Add a prefix threshold of 30**, which is v1-safe and catches all eight known
   pairs including the six nobody spotted.
3. **Emit the unioned pairs as a report**, not silently — `phrase_components`
   should be able to print what it merged and why, so a reviewer sees "EX01/EX05
   unioned on a 38-char shared prefix" rather than discovering it from a group
   count. This is what Option B was really for, obtained without relying on
   anyone to notice first.
4. **Keep `PHRASE_VARIANTS` for what it is** — same concept, two wordings — and do
   not overload it with distinct-concept pairs.

Why 30 rather than 25: at 25 the largest group reaches 4 and the union starts
pulling in pairs like `EX01 t / EX14 t` that share only `{REL} arababara cyane`,
which is domain grammar. 30 sits above the grammar and below every real
near-duplicate found so far. **It should be re-measured when the corpus is
complete**, not treated as settled — the right number at 128 phrases may not be
the right number at 864.

## 6. What this does not solve

**A shared prefix is not the only way two phrases leak into each other.**
`EX18`/`EX20` share a 24-char head *and* a 19-char tail; a prefix rule catches it
by the head, but a pair sharing only a long tail would pass. If the complete
corpus shows tail-sharing pairs, the measure should become longest common
substring normalised by the shorter phrase, not prefix length. Not proposed now
because there is no evidence of it yet, and an unmeasured generalisation is how
the 85-pair number gets mistaken for a defect list.

---

## 7. Two more blind spots, found 2026-09-04 — and the larger one is not about similarity

Section 6 guessed that a shared *tail* would be the next gap. It is not. Two
different blind spots turned up, and the big one has a cleaner fix than any
threshold.

### 7a. A concept's own two persons are in different phrase groups — 60 of 61

```
concepts with BOTH persons authored          61
  their two phrases land in one group         1
  their two phrases SPLIT                    60
```

```
CR03 first   Iminwa yanjye yahindutse ubururu.
CR03 third   {REL} iminwa ye yahindutse ubururu.
             containment: no      shared prefix: 0
```

**The prefix rule can never catch a first/third pair**, because a third-person
phrase begins with `{REL}` and a first-person one begins with a letter — the shared
prefix is 0 by construction. Containment fails on the verb morphology. So the two
persons of the same concept can land on opposite sides of the phrase holdout, with
the model having seen three of the four content words of the held-out phrase.

That is precisely the leak the substring closure was written for: *"an exact-match
check reports zero overlap while the model has plainly seen the string."*

**Fix: union by concept id, not by similarity. IMPLEMENTED 2026-09-04.**
`vocabulary.PHRASE_CONCEPTS` maps phrase -> concept id; `phrase_components` unions
every phrase sharing a concept and **raises** if a declaration names a phrase not
in the inventory — silence there would leave the concept's other phrases unjoined
and reopen the leak, the same failure shape as the empty `CONCEPT_RELATIONS`.
`review/second_phrasings.py` emits it from the brief.

**It needs no threshold and cannot be tuned wrong**, which is the point.

Measured on the 150 authored phrases:

```
phrase groups WITHOUT the concept union   131   largest 3
phrase groups WITH it                      77   largest 6
reduction                                  54   (41%)
```

**v1 is untouched**: `PHRASE_CONCEPTS` is empty for v1, whose 184 phrases have no
concept ids and are one phrase per concept anyway.

Cost: the phrase holdout's unit becomes the concept rather than the phrase, which
is what it should have been — holding out a concept means holding out everything
said about it. It roughly halves the number of independent holdout units, and that
is a real reduction in eval granularity, paid to remove a leak affecting 60 of 61
concepts.

### 7b. Reordering defeats both rules — the token-overlap check

```
OB11  Ndatwite kandi ndashaka kujya kwa muganga kwisuzumisha.
PR05  Ndatwite kandi ndashaka kwisuzumisha kwa muganga.

shared prefix   25   (threshold 30)   -> no union
containment     no
token overlap   86%,  ZERO words unique to PR05
```

PR05 was a strict subset of OB11's vocabulary, reordered. **A character measure
cannot see that; a token measure sees it immediately.** (That pair was resolved by
rewriting PR05 rather than unioning, but the blind spot is general.)

Measured over the corpus, excluding same-concept pairs (7a covers those):

| token overlap | cross-concept pairs unioned | of which zero unique words |
|---|---|---|
| >= 75% | 1 | 1 |
| >= 70% | 3 | 1 |
| >= 65% | 5 | 2 |
| >= 60% | 11 | 3 |
| >= 55% | 18 | 5 |

**Recommend two rules, not one threshold:**

1. **Zero unique words on either side unions, at any overlap.** If every word of
   one phrase appears in the other, the shorter is a vocabulary subset of the
   longer and there is nothing for a model to learn from the held-out one that it
   has not seen. This catches EX18/EX20, EX02/EX06 both persons, EX14/EX38 and
   CR03/EX04 — five pairs — and it needs no tuned number.
2. **Token overlap >= 70% unions.** Three pairs today, and it degrades gracefully:
   65% would add two and 60% would add six, so the rule is not perched on a cliff
   the way `PREFIX_UNION_CHARS` is at 25.

**Do not lower `PREFIX_UNION_CHARS` to reach these.** 25 is the v1-safe floor, and
the pairs above are missed by *shape*, not by a few characters — a shorter prefix
would union unrelated domain-grammar pairs without catching a single one of these.

### 7c. What this says about the design

Four blind spots have now been found, in this order: terminal stops and capitals
(fixed), long shared heads (fixed by the prefix rule), a concept's own two persons,
and reordering. Each was invisible to the safeguard in place at the time.

The pattern is that **every rule so far measures the wrong thing slightly** —
characters when the leak is in words, position when the leak is in content. The
concept-level union in 7a is the first proposed rule that is not a similarity
measure at all, and it covers the largest class. **Prefer a declaration over a
measurement wherever the brief already knows the answer.**

---

## 8. Measured 2026-09-04: the PR05/OB11 pair clears the threshold by one character

```
PR05 third   {REL} aratwite kandi ashaka kwisuzumisha kwa muganga bwa mbere.
OB11 third   {REL} aratwite kandi ashaka kujya kwa muganga kwisuzumisha.
             ^-------- shared prefix, 29 chars --------^
             PREFIX_UNION_CHARS = 30   ->  independent, by ONE character
             containment: neither contains the other
```

Section 7b already names this pair as the worst cross-concept residual — 86% token
overlap with zero words unique to PR05 — and recommends a token-overlap rule that is
**not implemented**. What is new is the margin: the only thing keeping the two in
separate phrase groups today is a single character.

**Consequences worth stating plainly.** Any edit that lengthens the shared head by
one character silently unions a first antenatal booking with a routine antenatal
check, and the holdout stops being able to test whether the model separates them. It
would not raise; union is the safe-looking direction. **Re-measure both phrases
after any edit to either.**

**Do not reach for the threshold.** 25 is the v1-safe floor (section 3) and 30 was
measured, not chosen. Lowering it to catch this pair would union a great deal else
and put the frozen v1 partition at risk; raising it to separate them by more would
give back the EX18/EX20 union it was introduced for. The fix, if one is wanted, is
7b's token-overlap rule — which unions this pair on content rather than on position
and needs no tuned number.
