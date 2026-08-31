# v2 freeze checklist

From filled-in briefs to a frozen v2 manifest. **In order.** The "if skipped" column
is the point of the document — every one of these has a way of failing silently.

Nothing here starts until speaker briefs and clinician sign-off are both back.

| # | step | command / action | if skipped |
|---|---|---|---|
| 1 | **Collect and archive the returned briefs** verbatim, before any editing | commit `review/returned/` as received | the raw evidence of what the speaker actually wrote is lost, and corrections become unattributable |
| 2 | **Record clinician provenance** | `review/clinician_concepts_[date].md` with the named statement | the CC BY 4.0 argument collapses; the dataset inherits NC share-alike from BEC |
| 3 | **Reconcile corrections vs new phrases** | speaker's `your_phrasing` replaces `current_phrase`; blanks stay blank | rejected phrases silently survive into v2 — the exact failure the review existed to catch |
| 4 | **Check for empties, duplicates, encoding** | script over the merged set; assert no blank, no duplicate within a language, NFC normalised, no curly apostrophes | a blank phrase makes an unmatched row; duplicates inflate a family; mixed Unicode forms break substring leakage detection |
| 5 | **Verify per-cell balance** | 14 per domain per language, all four languages parallel | `allocate()` distributes by family; an unbalanced cell skews class and language shares away from targets |
| 6 | **Update `vocabulary.py`** | add phrases in the same tuple structure | — |
| 7 | **Re-run slot distinctness** | `assert_slots_are_distinct()` (called by the generator) | duplicate slot values silently reduce the combination count, so uniqueness-by-construction stops holding |
| 8 | **Regenerate the corpus at 1,000,000, seed 42** | `python dataset/generate_large_dataset.py --target 1000000 --seed 42` | — |
| 9 | **Validate** | `python dataset/validate_dataset.py --report dataset/raw/symptoms_large.validation.json` | duplicate or malformed rows reach the splits undetected |
| 10 | **Near-duplicate scan** | `python dataset/near_duplicates.py` | the rows-per-phrase figure quoted in Limitations goes stale; with ~504 phrases it should fall from 5,674 toward ~2,000 and that number needs re-measuring, not estimating |
| 11 | **Rebuild both splits** | `split_dataset.py --strategy phrase` then `--strategy family` | — |
| 12 | **Check the leakage report** | `split_phrase_holdout.json` must show `substring_violations: 0`, `phrase_overlap: 0`, `eval_rows_leaked_fraction: 0.0` | **the headline claim of the whole project.** New phrases can be nested inside existing ones; the substring closure must still hold |
| 13 | **Bump `MANIFEST_VERSION` to 2** | `dataset/freeze_eval.py` line 31 | `freeze_eval` overwrites `eval_manifest_*_v1.json`, destroying the v1 record and any chance of comparing v1 results |
| 14 | **Keep the v1 manifests** | do not delete `*_v1.json` | v1 training results become uncheckable; keep them so old numbers stay traceable even though they describe a different corpus |
| 15 | **Freeze both** | `freeze_eval.py --strategy phrase` then `--strategy family` | — |
| 16 | **Regenerate the committed sample** | `--target 1000 --seed 42 --output dataset/sample/symptoms_sample.csv` | — |
| 17 | **Rebuild `sample_manifest.json`** | sha256 + rows + both split digests | `test_determinism` and `make verify` fail on the old digests — and this is the *good* failure; the bad one is step 18 |
| 18 | **Repoint `tests/test_leakage.py` from `_v1` to `_v2`** | lines 79 and 95 | **the silent one.** Those tests `pytest.skip` when the manifest is absent and validate the old file when present. Left alone they either skip quietly or green-light v1 while you believe they checked v2 |
| 19 | **Update every count in docs and README** | 184 -> ~504, 46 -> 126 per language, rows-per-phrase, held-out phrase count, eval matrix | the README's honesty section becomes false — the specific defect this project has been correcting all along |
| 20 | **Update the Limitations paragraph** | phrase count, distinct-items claim, holdout size | the paper concedes a limitation that no longer matches the artefact |
| 21 | **Set the dataset licence** | `LICENSE-data` CC BY 4.0, `LICENSE` MIT, attribution file for any WHO citation | released without a licence, nobody may reuse it — which defeats the stated purpose |
| 22 | **`make test-clean`** | must pass in a fresh clone | ambient-state failures ship; this is why the target exists |
| 23 | **`make verify` and `make verify-full`** | 6/6 and 8/8 | the digests in the manifest are unverified assertions |
| 24 | **Commit, push, confirm CI green** | all four jobs | — |
| 25 | **Re-run the family-overlap measurement** | recompute the phrase-train / family-eval overlap | the 89.2% figure is v1-specific; with a different phrase inventory it will change, and quoting the old number would be exactly the sin this project keeps correcting |

## Points where it is easy to get this wrong

**Step 12 is the one to slow down on.** Adding ~320 phrases multiplies the chances
that a new phrase contains an existing one as a substring. The union-find closure
handles it automatically, but the *consequence* is that phrase groups merge, so the
holdout may hold out more or fewer rows than intended. Read the split report, do not
just check that the number is zero.

**Steps 13–14 together.** Bump the version *and* keep v1. Doing one without the
other either destroys the old record or produces a v2 that overwrites it.

**Step 18 is the only step whose failure is invisible.** Everything else fails loudly.

## What does not need doing

- No retraining is implied by any of this. v2 is a dataset, not a model.
- Any v1 training result stays valid *as a v1 result*. It is not comparable to a v2
  number and must not be reported as one.
- `concept_anchors.csv` stays internal and is not part of the release.
