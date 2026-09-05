# Paper-ready text

Paste-ready prose. I cannot edit the paper itself — it is not in this repository.

## For the dataset section

> The corpus comprises 1,008,000 examples generated from 504 seed phrasings — 14 per
> clinical domain per language — across nine domains, four languages and three
> urgency classes. The row count was chosen deliberately rather than maximised. At
> 504 phrasings the template families admit 18,900,000 distinct combinations, so
> repetition does not constrain the corpus at any size we considered; 2,000,000 rows
> would occupy only 10.6% of that space. The constraint we optimised instead is
> rows-per-phrase, which we take to be the honest measure of how much clinical
> variety a given row count represents. A corpus of one million rows built from 184
> phrasings carries approximately 184 phrasings' worth of linguistic variety, not one
> million, and inflating the row count without expanding the vocabulary increases
> repetition rather than diversity. At 1,008,000 rows the median phrase accounts for
> 2,000 examples; at 3,000,000 rows it would account for 5,952, which is less diverse
> per phrase than our earlier 184-phrase corpus. We therefore report 1,008,000 as the
> point at which corpus size matches the clinical content that supports it, and note
> that scaling further is a matter of authoring more phrasings rather than generating
> more rows.

## For the limitations section, replacing the v1 paragraph

> The evaluation corpus is generated rather than collected. All 1,008,000 rows are
> template expansions of 504 seed phrasings, so the corpus contains on the order of
> 504 clinically distinct items, with the median phrasing accounting for
> approximately 2,000 rows. Scores obtained on it should be read as an upper bound
> established under favourable, highly regular conditions.

(Retain the rest of the v1 Limitations paragraph on clinician review, native-speaker
validation, the phrase-versus-family holdout gap, and non-deployment. Update the
phrase and holdout counts once v2 is frozen and the numbers are measured rather than
projected.)

## For future work

> The natural extension is answering patient questions rather than classifying
> urgency alone. We deliberately scope this as retrieval over a clinician-approved
> answer bank rather than open-ended generation. Retrieved answers are authored and
> approved by clinicians and presented verbatim, so the system cannot fabricate
> clinical content; retrieval accuracy is measurable against a labelled set without
> requiring clinicians to grade free-text output for every model revision, which is
> the constraint that makes generative medical systems difficult to validate in
> low-resource languages. Existing Kinyarwanda retrieval models support this design
> directly.
>
> A generative assistant remains out of scope for this work. Published Kinyarwanda
> monolingual text amounts to approximately 0.4-0.5 billion tokens, against the
> roughly 160 billion a compute-optimal 8B-parameter model requires. The limiting
> resource is not compute, which is modest at this scale, but clinician time for
> creating and evaluating instruction data, and the absence of a scalable evaluation
> method for generated medical text in a language with few qualified reviewers.

## Numbers to update once v2 is measured

Do not paste these until they have been produced by a run:

- phrase strings (projected 504)
- rows (projected 1,008,000)
- median rows per phrase (projected ~2,000 — the near-duplicate scan measures it)
- held-out phrases in the phrase split (projected ~50)
- eval matrix counts, both splits
- phrase-train / family-eval overlap. **v1 measured 89.2%; v2 measures 0.0%** and
  the two holdouts have converged - v2 is monolingual, so each phrase belongs to
  exactly one family and holding one out removes its phrases entirely. Do not
  describe v2 as two difficulty levels; it is one strictness at two ratios
  (10.43% and 7.55%). See docs/v2-sizing.md.
