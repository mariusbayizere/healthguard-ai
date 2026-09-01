# Splitting the work between two authors

## The problem a naive split creates

Halving the concepts between two people leaves nothing to compare. The blind
agreement measure needs both authors to phrase **the same** concepts
independently; with a clean split there is no overlap, and agreement cannot be
computed at all. A second author would double throughput and produce zero evidence
that either author's phrasings are good.

## The division

`review/split_authoring.py` carves out a stratified overlap set both authors write,
then splits the remainder:

```
127 concepts
  27 overlap    both authors write these, independently   (~20%, stratified by domain)
  50 author A only
  50 author B only

Author A: 77 concepts, 154 rows
Author B: 77 concepts, 154 rows
Coverage: 127 of 127, no gaps
```

Stratified by domain so agreement is not concentrated in one clinical area, and
seeded so the sample is reproducible and demonstrably not chosen after seeing
results.

## What each author must do for the measure to work

1. **Write independently.** Neither sees the other's file, for the overlap concepts
   above all. Author B's file is generated with the first-pass text stripped, so
   nothing leaks through the overlap rows.
2. **Declare `person` and `form` on every row.** Agreement is measured per (concept,
   person); a row with no person cannot be paired with its counterpart.
3. **Fill `second_phrasing_optional` where a second natural phrasing exists.** Two
   authors offering the same alternative is strong evidence; it also feeds corpus
   variety directly.
4. **Do not compare notes until both files are back.** One conversation about a hard
   concept invalidates that concept as evidence.

## The overlap rows are not marked

Neither author's file identifies which concepts are shared. Knowing which items are
scored changes how people write them.

Both authors **should** be told at the outset that about a fifth of the work overlaps
and is used to measure agreement. That is transparent about the design while staying
silent about which rows — the standard arrangement for annotation work, and honest in
the way that matters. `..._OVERLAP_KEY.csv` records the shared concepts and must not
be sent to either author.

## Reading the result

For each of the 27 overlap concepts x 2 persons = 54 paired phrasings, classify:

- **same content, similar phrasing** — strong agreement
- **same content, different phrasing** — both plausible; keep both as corpus
  variants, which is a gain rather than a disagreement
- **different content** — the English gloss is ambiguous. That is a defect in the
  brief, not in either author, and the gloss should be fixed before more work is
  built on it

Report the three proportions. Do not compute a single accuracy figure: there is no
ground truth here, only two informed opinions, and a percentage would imply one of
them is the answer.

## Adjudication

Where the two differ and both hold their view, prefer taking both into the corpus as
variants — real patients vary, and that variation is what the corpus is short of.
Escalate to the clinician only when the disagreement is about clinical meaning rather
than wording.

## For the paper

Record: number of concepts, number of authors, overlap fraction, how the overlap was
selected and seeded, the three agreement proportions, and how disagreements were
resolved. Name both authors with consent.

Two authors is better than one and still small. The paper should say so rather than
implying broader validation.
