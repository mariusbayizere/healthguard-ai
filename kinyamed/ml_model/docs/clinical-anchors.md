# Clinical anchors for the concept taxonomy

Every licence below was verified by downloading the document and reading its own
copyright page, not from a search result.

## Sources checked

| source | licence — verified how | usable? |
|---|---|---|
| **WHO-ICRC *Basic Emergency Care: approach to the acutely ill and injured*, 2018.** ISBN 978-92-4-151308-1 | **CC BY-NC-SA 3.0 IGO** — read from the PDF's own licence page: *"Some rights reserved. This work is available under the Creative Commons Attribution-NonCommercial-ShareAlike 3.0 IGO licence"* | **yes** — copy, redistribute and adapt for non-commercial purposes with attribution and share-alike |
| **WHO *IMCI Chart Booklet*, 2014.** ISBN 978 92 4 150682 3 | **All rights reserved** — read from the PDF's own copyright page; zero Creative Commons mentions in the document | concepts only; no text may be reproduced or translated without WHO Press permission |
| **WHO IMAI District Clinician Manual, Vol 1** | **not verified** — `iris.who.int` and `apps.who.int` both return a JavaScript shell (755 bytes), not the PDF | unknown; not used |

BEC is the better source of the two available: it is genuinely open, it is
adult-inclusive, and it was written for exactly this setting — first-contact
providers managing acute illness and injury with limited resources.

## What BEC covers

Five modules, confirmed from the document: ABCDE and SAMPLE history; approach to
trauma; approach to difficulty in breathing; approach to shock; approach to altered
mental status. Presentation coverage confirmed by search within the text: shock
(312), trauma (325), burns (169), altered mental status (137), seizure (80),
hypoglycaemia (39), diabetic (26), weakness (22), snake bite (21), chest pain (18),
poisoning (17), stroke (13).

Hypoglycaemia appears with "Sweating (diaphoresis)" as a listed sign, which matches
concept CC02 directly.

## Result: the 40 unanchored concepts

Of the 68 general concepts:

```
WHO IMCI 2014 (All rights reserved)      28
WHO-ICRC BEC 2018 (CC BY-NC-SA 3.0 IGO)  18   <- newly anchored
clinician-defined, no WHO anchor         22   <- genuinely unanchored
```

**18 of the 40 now have an openly-licensed clinical anchor.** Full mapping in
`review/concept_anchors.csv`.

## The 22 that remain clinician-defined

They cluster where you would expect, and the pattern is the answer:

| domain | n | why no anchor exists |
|---|---|---|
| preventive | 8 | screening, family planning, HIV testing, bed nets. Not emergencies; no emergency-care document covers them |
| chronic_care | 7 | medication refills, adherence lapses, routine reviews. Chronic-disease management, not acute care |
| gastrointestinal | 2 | severe abdominal pain, minor indigestion |
| haemorrhage_trauma | 2 | infected wound, minor cut |
| cardiac_respiratory | 1 | chronic cough with weight loss (TB screening) |
| infectious_fever | 1 | fever with dysuria |
| neurological | 1 | intermittent mild headache |

**These are marked `clinician-defined (no WHO emergency-care anchor)` rather than
given a strained mapping.** Two-thirds are preventive or chronic-care presentations
that emergency triage literature does not address by design. A Rwandan clinician's
judgement is the appropriate anchor, and the taxonomy should record it as such —
naming the clinician and the date — rather than borrowing authority from a document
that does not cover the case.

## Obstetric

The 12 obstetric concepts were not re-checked here. WHO publishes *Managing
Complications in Pregnancy and Childbirth* and *Pregnancy, Childbirth, Postpartum
and Newborn Care*, either of which would be the right anchor, but neither has been
downloaded or licence-verified by this project. **Treat the obstetric concepts as
clinician-defined until that check is done.**

## Attribution to use if BEC-derived concepts are published

> Clinical concepts adapted from World Health Organization and International
> Committee of the Red Cross. *Basic Emergency Care: approach to the acutely ill and
> injured.* Geneva: WHO; 2018. Licence: CC BY-NC-SA 3.0 IGO.

Share-alike applies: derivative work must carry the same or an equivalent licence.
This constrains the dataset's licence and should be settled before release.
