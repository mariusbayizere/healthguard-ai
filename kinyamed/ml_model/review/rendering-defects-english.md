# Two English rendering defects — for the Kinyarwanda session

Both found by the English review pass, 2026-09-05. Both now ruled.

| | where the fix goes | status |
|---|---|---|
| 1. pronoun `I` lowercased after a greeting | `dataset/` — **the Kinyarwanda session's** | ruled *site B only*, **not applied here** |
| 2. English utterances carry no terminal stop | the English brief — the English arm's | **applied**, 190 phrases |

The first is not a v2 risk. **It is already in the shipped v1 corpus, in 48,398
rows**, and the ruling leaves it there — see *What that concedes* below.

---

## 1. The pronoun "I" is lowercased after a greeting

### What ships today

```
Doctor, i have heavy bleeding that will not stop and I am worried. What should I do?
Good morning, i am experiencing crushing chest pain spreading to the arm for two days now
Excuse me, i am experiencing breathing trouble and lips turning blue for the past two hours
```

Lowercase `i` opening the clause, correct capital `I` later in the same sentence.
**36,724 rows contain both**, which is what makes it unmistakable rather than
arguable.

### Extent, measured on `dataset/raw/symptoms_large.csv`

```
48,398 of 1,000,000 rows          4.8% of the corpus
  26,673  language label "mixed"
  21,725  language label "english"
```

Mixed is the larger share because an English *frame* can carry a Kinyarwanda or
Swahili phrase, and the frame is where the defect lives.

### Cause

`dataset/generate_large_dataset.py`, `Family.render()`. Two sites, both correct
in principle:

```python
149        if subject:
150            if continues:
151                subject = subject[0].lower() + subject[1:]      # <-- site A, v1
...
157        if continues:
158            phrase = phrase[0].lower() + phrase[1:]             # <-- site B, v2
```

An opener ending in a comma continues the sentence, so what follows must not keep
its capital. That is right for `Mfite` -> `mfite`, for `J'ai` -> `j'ai`, for
`Nina` -> `nina`. It is wrong for exactly one word in one language: English `I`,
which is capitalised for its own sake and not because it starts a sentence.

**Site A is the one that ships in v1.** `SUBJECTS["english"]` has ten members and
two of them begin with the pronoun — `"I have"` and `"I am experiencing"` — and
five of the six English openers end in a comma.

**Site B is not reached in v1 at all.** `PHRASE_FORMS` is empty, so every v1
phrase takes `DEFAULT_FORM = noun_phrase` and the subject branch. Site B becomes
live the moment English phrases are utterances, which is what the person split
does: **72 of the 203 drafted English phrases begin with "I"**, and 5 of 6 frames
would lowercase each of them.

### The fix

Guard on the whole first word, at both sites:

```python
        if subject:
            if continues and subject.split(" ", 1)[0] != "I":
                subject = subject[0].lower() + subject[1:]
...
        if continues and phrase.split(" ", 1)[0] != "I":
            phrase = phrase[0].lower() + phrase[1:]
        else:
            phrase = phrase[0].upper() + phrase[1:]
```

**Guard on the word, not the character.** `I` must keep its capital; `In labour
since yesterday` must not. A `phrase[0] != "I"` test would break the second.

The `else` branch on site B still needs to run for a non-`I` phrase with no
opener, so the guard belongs on the `if` alone — do not restructure it into an
early return.

### RULED 2026-09-05: site B only

**Fixing site A changes the v1 corpus.** 48,398 rows change, every frozen digest
moves, and `make verify-full` fails until the manifests are re-frozen. That is not
a reason to leave it — it is a reason it cannot be slipped in with a v2 change.

Three ways to sequence it were on the table:

1. **Fix both sites as part of the v2 build.** v2 is refreezing anyway, so the
   cost is zero and the defect leaves the corpus at v2. v1 keeps it, permanently,
   as a historical artefact.
2. **Fix site B only.** v1 stays byte-identical and keeps the defect; v2's
   utterances are clean but v2's *noun-phrase* rows would still carry it — except
   there are none, since every v2 English row is an utterance. In practice this is
   equivalent to option 1 for v2 output, and cheaper.
3. **Fix both and re-freeze v1.** Only if v1 is going to be reissued for another
   reason. Not worth doing on its own.

**Option 2 is ruled.** Fix site B; leave site A alone.

## What that concedes, recorded so it cannot be forgotten

**The shipped v1 corpus keeps this defect permanently.** 48,398 of its 1,000,000
rows — 4.8% — open a sentence with a lowercased pronoun `i`, and 36,724 of them
contain a correct capital `I` later in the same sentence. v1 is frozen, its
digests are committed, and fixing site A would move all of them.

**No paper may quote a v1 row that carries it.** Any example of English or mixed
output drawn from `dataset/raw/symptoms_large.csv` or
`dataset/sample/symptoms_sample.csv` must be checked against:

```
grep -E "^\"?(Doctor|Hello|Please help|Good morning|Excuse me), i " <file>
```

An illustrative row quoted in a paper is chosen, not sampled, so this is entirely
avoidable — but only if someone remembers. That is what this section is for.

**It is a limitation of v1, not of the method**, and it is worth saying so
plainly if v1 output is discussed at all: the renderer was written for a
Kinyarwanda-first corpus, and no Kinyarwanda word is capitalised for its own sake.
The defect is what that assumption costs in English, and v2 does not carry it.

---

## 2. English utterances carry no terminal punctuation

### What it looks like

With the empty closer — one of five — a Kinyarwanda row ends punctuated and an
English row does not:

```
kinyarwanda   Muganga, iminwa ye yahindutse ubururu.
english       Doctor, my lips have turned blue
```

The Kinyarwanda speaker's authored utterances end in a full stop. The English
drafts do not.

### This one is NOT a `dataset/` fix, and should not be made into one

The renderer must not add terminal punctuation, because that would change v1's
output for every language and break the freeze for a cosmetic reason. The right
fix is in the **data**: add a full stop to the English drafted phrases, mirroring
what the Kinyarwanda rows already do.

That is a change to `review/speaker_brief_english_v2.csv`, which is the English
arm's file. **RULED AND APPLIED 2026-09-05: 190 drafted phrases gained a terminal
full stop.**

The 19 rows left alone are stale sheet or v1 text on held and `applies=no` rows —
not the English arm's wording, and not going to generate.

Safe on inspection:

- `lint_phrases.py` explicitly allows a trailing stop on an utterance and rejects
  only a trailing comma or colon.
- `_drop_terminal_stop()` removes it again whenever an onset or context follows,
  so no row gains a mid-sentence full stop.
- `_match_form()` strips terminal stops before comparing, so phrase grouping is
  unaffected — the `check_english_grouping.py` result would not move.

### Verified after applying

```
bare frame        My lips have turned blue.
onset follows     My lips have turned blue since yesterday
opener + closer   Doctor, my lips have turned blue. What should I do?
```

The stop is kept where the phrase ends the sentence and dropped before any
continuation, which is `_drop_terminal_stop` doing its job. Phrase grouping did
not move — 203 phrases, 0 containments, unchanged — confirming `_match_form`
strips terminal stops before comparing. Lint: 0 errors.
