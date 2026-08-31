# Second-speaker review

One speaker is one opinion. This makes the phrasings defensible rather than
merely consistent.

## Design

Two mechanisms, because they answer different questions.

**RATE — every phrase, 1 to 4.** Catches phrases that are wrong.

```
4  a patient would say this
3  acceptable, though I would say it differently
2  understandable but not natural
1  wrong, misleading, or not Kinyarwanda a patient would use
```

**AUTHOR-BLIND — 20% sample, written independently.** The second speaker sees the
English gloss and writes their own phrasing **without seeing yours**. This is the
stronger signal: rating someone else's fluent text invites assent, whereas two
speakers independently reaching similar phrasings is evidence, and reaching
different ones is a finding.

The sample is drawn with a fixed seed, so it is reproducible and cannot be selected
after the fact.

```bash
python review/make_second_review.py review/speaker_brief_kinyarwanda_FILLED.csv \
    --language kinyarwanda --blind-fraction 0.2
```

Produces three files. **Send the first two. The KEY file holds your phrasings for
the blind set and must not be sent** — if the second speaker sees it, the blind arm
is worthless and cannot be redone with the same person.

## Reading the result

**From the RATE arm**, report the distribution, not the mean. `% rated 4` is the
headline; anything rated 1 or 2 goes back for rewriting. A useful target is ≥90%
rated 3-or-4 and ≥70% rated 4.

**From the BLIND arm**, the question is not string equality — two natural phrasings
will differ. Judge:

- *same clinical content, similar phrasing* — strong agreement
- *same content, different phrasing* — both may be natural; keep both as variants,
  which is a gain rather than a problem
- *different content* — the English gloss is ambiguous, and that is a defect in the
  brief rather than in either speaker

Report agreement as those three proportions. Do not compute a single accuracy number
from it; there is no ground truth, only two informed opinions.

## Adjudication

Where the two disagree and both hold their view, do not average and do not let the
first speaker decide because they wrote it first. Either take both phrasings into
the corpus as variants — usually the right answer, since real patients vary — or put
it to the clinician if the disagreement is about clinical meaning rather than
wording.

## What to record for the paper

- number of phrases reviewed, and by how many speakers
- the rating distribution
- the blind-agreement proportions
- how disagreements were resolved
- both speakers named, with consent

That paragraph is what turns "we wrote some phrases" into a methods section. It is
also honest about the sample size: two speakers is better than one and still small,
and the paper should say so rather than implying broader validation.

## Sequencing

1. You complete the first pass.
2. Run the linter; fix what it flags.
3. Generate the second-review files.
4. Send RATE and BLIND. Keep KEY.
5. Merge, adjudicate, record.
6. Only then does the clinician urgency review need to be final — wording changes do
   not affect urgency, so the two reviews can overlap.
