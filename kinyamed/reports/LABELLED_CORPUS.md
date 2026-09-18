# The labelled Kinyarwanda triage corpus

> **PROVENANCE: annotator single, non-clinician, the paper's author; validated_by NONE; none computed; there is no second annotator. These labels are NOT clinical ground truth.**

Source file `dataset/labelled/triage_labels_ALL.csv`, sha256 `d7e1b3147af46e473589d719c6b3404377674dcd3b5777bfeb9c8ce88ce2264f`.
Every figure below is computed by `review/report_labelled_corpus.py` from
that file. None of it is a model result and none of it is validated.

## Counts

| | |
|---|---|
| rows in file | 2,483 |
| rows carrying Kinyarwanda text | 2,282 |
| rows with a label and no text (B1) | 201 |
| ids absent from the range (B2) | 317 |
| rows in clinical-record voice (B3) | 336 |
| rows in patient voice and measurable | 1,946 |

## Labels

| label | all rows | rows with text |
|---|---:|---:|
| ROUTINE | 1,363 | 1,240 |
| URGENT | 876 | 822 |
| CRITICAL | 194 | 174 |
| CANNOT CLASSIFY | 50 | 46 |

`CANNOT CLASSIFY` is a judgement that the text does not support a triage
decision. It is not a fourth urgency class and must not be folded into one.

## Diversity

Tokeniser: lowercase, split on whitespace, strip edge punctuation. The
apostrophe is kept inside the token, because Kinyarwanda writes elided
vowels with one and splitting on it would count `n'umwana` as two words.

| measure | all rows with text | patient voice only |
|---|---:|---:|
| rows | 2,282 | 1,946 |
| distinct sentences | 2,281 | 1,945 |
| word types | 3,930 | 3,575 |
| word tokens | 18,755 | 15,371 |
| type/token ratio | 0.2095 | 0.2326 |
| types occurring once | 2,305 | 2,170 |
| median length (tokens) | 8 | 8 |
| shortest | 2 | 2 |
| longest | 18 | 16 |

## Reporter and age group, rows with text

| reporter | rows | | age group | rows |
|---|---:|---|---|---:|
| Self | 1,502 | | Umuntu mukuru | 1,059 |
| Carer | 780 | | Umwana | 499 |
|  |  | | Umusaza/Umukecuru | 386 |
|  |  | | Impinja | 201 |
|  |  | | Ingimbi/Umwangavu | 137 |

## Against the generated corpus (B5)

Same tokeniser both sides.

| corpus | rows | distinct sentences | word types | TTR |
|---|---:|---:|---:|---:|
| labelled, authored | 2,282 | 2,281 | 3,930 | 0.2095 |
| generated (`symptoms_large.csv`) | 330,000 | 330,000 | 363 | 0.0001 |

The row counts are not comparable and the type counts are the point: the
generated corpus expands a small phrase inventory across frame slots, so
rows grow without vocabulary growing. Every generated row is distinct
because the frames differ, which is exactly why distinct-row counts say
nothing about diversity and distinct word types do.

## What is outstanding

- **201 rows carry a label and no Kinyarwanda.** Listed by id in
  `reports/labelled_missing_text.csv`. They are excluded from every count
  above and from any run, and they are not dropped: the label is real work
  and the text is work outstanding.
- **317 ids are absent from the range.** Listed in
  `reports/labelled_missing_ids.txt`. Unwritten, not lost.
- **336 rows are in clinical-record voice**, a third party
  reporting what the patient said rather than the patient's or carer's own
  words. Listed with their text in `reports/labelled_record_voice.csv`.
  Tagged `register=record_voice` in the enriched file so a run can exclude
  them and report both ways. No Kinyarwanda has been rewritten.

