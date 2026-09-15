# Sources — verification log (docs/ENGINEERING_SPEC.md §10.1)

Every external model, tokenizer or corpus is recorded here **before** it is used. The checks:
- the repository resolves, and the revision is pinned;
- the licence is read from the repository's own metadata or files, not from memory;
- how it is used, and a verdict.

A resource that fails a check is listed as **UNVERIFIED** and is not used. Provenance of each model's own
training data (§10.1 step 3) is **not yet checked** for any row below; it is required before a model is adopted
or cited, but not for measuring a tokenizer.

The Hugging Face Hub API was queried on 2026-09-15.

## Verified — used in the tokenizer study (item 5a)

Tokenizer files only: no weights downloaded, nothing trained.

| Repository | Revision | Licence (from the repo) | Languages the card lists | Use | Verdict |
|---|---|---|---|---|---|
| `Davlan/afro-xlmr-mini` | `bc04038b969667884bd83cdd37bed9559c2c3d9c` | MIT (`license:mit`) | **none listed** | tokenizer study; current v2d base | verified for tokenizer measurement; the card does not state Kinyarwanda |
| `Davlan/afro-xlmr-base` | `25f27299c247a6b73a767bd82d12444138b19337` | MIT | 19, including Kinyarwanda and Swahili | tokenizer study | verified for tokenizer measurement |
| `Davlan/afro-xlmr-large` | `7036fa1ed38d3418a122d3c7e00d5c748ed29f08` | MIT | includes Kinyarwanda and Swahili | tokenizer study | verified for tokenizer measurement |
| `castorini/afriberta_large` | `231d92411ab8a99add67eda412ee948c74a4b179` | MIT | 12, including Kinyarwanda and Swahili | tokenizer study | verified for tokenizer measurement |
| `FacebookAI/xlm-roberta-base` | `e73636d4f797dec63c3081bb6ed5c7b0bb3f2089` | MIT | 94, including Swahili; **Kinyarwanda not listed** | tokenizer study | verified for tokenizer measurement |
| `FacebookAI/xlm-roberta-large` | `c23d21b0620b635a76227c604d44e43a9f0ee389` | MIT | as base | tokenizer study | verified for tokenizer measurement |
| `sentence-transformers/LaBSE` | `836121a0533e5664b21c7aacc5d22951f2b8b25b` | Apache-2.0 | 110, including Kinyarwanda and Swahili | tokenizer study | verified for tokenizer measurement |

## UNVERIFIED — not used

No licence was found in the model card, the `license:` tags, or any file in the repository.

| Repository | Revision seen | Why unverified | What would verify it |
|---|---|---|---|
| `UBC-NLP/serengeti` | `9d3a0853a0e8…` | no licence metadata or file. The README mentions native-speaker curation including Kinyarwanda; that is not a licence. The card's language list does not include Kinyarwanda. | a licence stated by the authors (repository or paper) |
| `castorini/afriberta_small`, `castorini/afriberta_base` | `51667384e9f1…`, `95b703f498c9…` | no licence metadata or file. `afriberta_large` is MIT, but that does not transfer. | a licence on each repository |
| `Davlan/xlm-roberta-base-finetuned-kinyarwanda`, `Davlan/xlm-roberta-large-finetuned-kinyarwanda`, `Davlan/bert-base-multilingual-cased-finetuned-kinyarwanda` | `eb8a4a357304…`, `3799e7a382b6…`, `0e7e407ca461…` | no licence | a licence on each repository |
| `RogerB/*` Kinyarwanda checkpoints (e.g. `KinyaBERT-small-pretrained-kinyarwanda`) | `cf1aa9f1009a…` | no licence, and no paper or provenance for an individual upload. The name is not evidence of the published KinyaBERT. | the authors' licence and a citable description of training data |

## Local text used (no external source)

- **Kinyarwanda:** v2 corpus rows (`dataset/processed/*_phrase_holdout.csv`, 330,000 rows from 165 phrases).
- **English and French:** v2 phrase drafts (`review/speaker_brief_{english,french}_v2.csv`), machine-drafted and
  not speaker-reviewed.
- **English, French, Swahili, mixed, Kinyarwanda:** v1 generator output
  (`generate_large_dataset.py --corpus-version 1 --target 100000`), machine-drafted.
- None of it is natural patient speech (DATASET_AUDIT §5–§7).
