# Clinical lexicon (CLAUDE.md §10.6)

`red_flags.csv` is the source of truth for the red-flag rules layer (L2). **It ships empty on purpose**: a header
and no terms. With it empty, the layer is a no-op and triage behaves exactly as it did without it.

- Every row needs `source` and `validated_by`. A row missing either makes the backend refuse to start, with the
  line number.
- Terms come from a clinical lead and native-speaker validators (STATE.md H10). **No term is added from memory, a
  model, or a translation tool.**
- `rw_colloquial_variants` holds several variants separated by `|`.
- Only rows with `red_flag=true` are matched. Matching is on whole words, ignoring case, accents and spacing.
- The layer only escalates, to CRITICAL. It can never lower urgency, and PostgreSQL enforces that
  (`ck_triage_results_rules_escalate_only`).

When validated terms exist, adding them is a CSV edit.
