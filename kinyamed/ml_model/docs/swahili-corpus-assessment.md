# Swahili Corpus (Mendeley `d4yhn5b9n6`) — health subset assessment

**Verdict: not usable as a source of patient-facing Swahili. Usable for terminology
only.**

## Method

Retrieved the file list via the Mendeley public API, downloaded `AFYA_Cleaned.txt`
(the health category, 707,155 bytes), and measured register directly rather than
inferring it.

## Measurements

```
non-empty lines                                     5,775
words                                             110,075
mean words per line                                    19.1

lines with first-person patient markers                 7   (0.12%)
  (nina / nahisi / naumwa / nimeanza / nataka ...)
lines containing a symptom word                       155   (2.7%)
  (homa / maumivu / kutapika / kuharisha / kikohozi / damu / kifua)
lines with BOTH first-person and a symptom word         0
```

**Zero lines** combine a first-person marker with a symptom word. Not few — none.

## What the text actually is

The symptom-bearing lines are government communications. Two representative openings:

- `jamhuri ya muungano wa tanzania wizara ya afya taarifa kwa vyombo vya habari...`
  — United Republic of Tanzania, Ministry of Health, press release
- `mheshimiwa spika katika mwaka wizara yangu...` — "Honourable Speaker", a
  parliamentary budget speech

This is institutional Tanzanian Swahili: ministerial press releases, parliamentary
addresses, vaccination programme reporting. It describes health *policy*, not
symptoms, and never in a patient's voice.

## What it is good for

- **Medical and public-health terminology in Swahili**: disease names, vaccine
  names, programme vocabulary. Useful for checking that a drafted term is the one
  Tanzanian health communication uses.
- **Not** phrasings, register, or anything about how a patient describes an illness.

A further caveat: this is Tanzanian Swahili. Swahili in Rwanda is closer to the
Congolese/East African border varieties, and terminology may differ.

## Licence

CC BY 4.0 — usable with attribution, including commercially. The most permissive
resource found in this audit, and unfortunately the least relevant to the actual
gap.

## Conclusion

The gap this project has is patient-voice symptom description in Kinyarwanda and
Swahili. No corpus found in this audit contains it. That register exists in
transcripts of real consultations and in health-promotion material written to be
spoken — neither of which is in any dataset located here. It has to come from
speakers, or from the Rwanda MoH materials requested in `moh-request.md`.
