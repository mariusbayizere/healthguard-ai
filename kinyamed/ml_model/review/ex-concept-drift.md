# The EX rewrites: which ones changed concept, and how far

Found while attaching English text to concepts, but this is a **Kinyarwanda-side
record**. An EX id names the *position* a v1 phrase occupied. The speaker was
asked whether each v1 phrase was natural and to give their own phrasing; they
were not asked to hold the concept fixed, and several rewrites landed on a
different presentation. Nothing was done wrong — the brief did not ask for
concept stability — but the ids now denote the rewritten concept, and anything
keyed on "EX*n* means what v1 slot *n* meant" is wrong.

All 47 rows read by hand. The stem-overlap detector in `build_english_brief.py`
is reported against that reading below; **it is about as often wrong as right**
and must not be used as a verdict.

## Genuinely moved — 7, of which one has since been closed

| id | v1 concept | after the rewrite | how far | already recorded? |
|---|---|---|---|---|
| **EX27** | fever and aching all over | fever + chills + "I suspect malaria" | **onto EX26** | **RULED 2026-09-05 — collapsed into EX26** |
| **EX29** | mild cough, no fever | mild fever one day, nothing else | cough → fever | via the IF07 collapse |
| **EX30** | mild runny nose | mild cough, no fever | onto old EX29 | yes — collapsed into CR07 |
| **EX17** | slight stomach pain, not severe | unwell in the belly after eating | onto EX16 | yes — collapsed into EX16 |
| ~~EX47~~ | a question about healthy diet | advice on food for feeding a child | **CLOSED 2026-09-05 — reverted** | see below |
| **EX43** | high fever and *refusing* to eat | high fever and *not able* to eat | **weaker → IMCI danger sign** | **no** |
| **EX11** | follow-up after previous treatment | wanting to keep coming for check-ups | broadened | **no** |

### The three that are not yet in the record

(EX47 was a fourth; it is closed — see below.)

**RULED 2026-09-05: EX27 collapses into EX26.** "I suspect malaria" is not a
different concept, it is the same patient saying it differently. EX26's wording
survives, EX27 goes `applies=no`, and EX27's wording is kept as EX26's second
phrasing. Execution is cross-language. **The v1 concept EX27 vacated — fever with
generalised body aches — still has no row in any language**, and that is the part
the collapse does not answer.

The original finding follows.

**EX27 now duplicates EX26, which was left unchanged.**

```
EX26  ibimenyetso bya malariya, umuriro n'imbeho          (untouched)
EX27  mfite umuriro kandi numva mfite imbeho, nkeka ko ari malariya
```

Fever, chills, malaria suspected — twice, in one domain, at one urgency. EX26 is
the only one of the 47 the speaker left byte-identical, which is itself worth
noticing: it suggests they read EX26, approved it, and then wrote EX27 as
another way of saying the same thing rather than as a different concept. If so
this is the EX16/EX17 shape exactly, and the same remedy applies — one concept,
both phrasings kept, one as `second_phrasing_optional`. **The v1 concept that
EX27 vacated (fever with generalised body aches) then has no row in any
language.** IF04 is fever+chills+sweats, not aches.

**EX43 moved onto a danger sign, and that raises its urgency question.**
`ntarya` ("does not eat") became `ntabwo arimo kubasha kurya` ("is not able to
eat"). *Refusing* to eat and *not able* to eat are different: the second is an
IMCI general danger sign, the same one IF03 and PA02 are built on. The row is
labelled URGENT. If the rewrite is what the concept now is, the label is
arguably wrong, and PA02 ("child too weak to breastfeed") is nearby. The row is
`applies=no` in the first person, so nothing generates from the first person
today — but the third person does.

**EX11 broadened into the shared check-up frame.** "Follow-up after previous
treatment" became "I want to keep going to the clinic for check-ups", which is
the `Ndashaka ... kujya kwa muganga kwisuzumisha` frame that section 7 already
flags as shared with CC09, CC10 and PR07 over `PREFIX_UNION_CHARS`. So this is
not only a concept question, it feeds the phrase-group merge that is already
being tracked.

### EX47 — closed, by the Kinyarwanda moving back

When this survey ran, EX47's rewrite was `kugirwa inama ku biryo byo kugaburira
umwana` — advice on food for feeding a child, which is PR08's concept. It has
since been returned to `Ndashaka inama ku mirire myiza.`, general nutrition. The
two are distinct again and the duplicate flag is discharged. Six of the seven
movements below still stand.

## Read as paraphrase, not movement — 4 the detector flagged wrongly

`EX14` (severe abdominal pain → the belly hurts a lot), `EX23` (severe pain
after a fall → I fell and now I hurt a lot), `EX36` (mild headache, not severe →
head hurts but not much), `EX37` (mild tiredness → I feel tired but not very).
All four keep the sign and the severity and change only the words. Zero stem
overlap, because Kinyarwanda can say the same thing with an entirely different
root — which is the detector's whole problem.

## Detector accuracy, stated so nobody trusts it

Flagged 8 of 46. Of those, **4 were real** (EX11, EX17, EX30, EX47) and 4 were
paraphrases. It **missed 3** (EX27, EX29, EX43), each of which kept a shared word
— `umuriro`, `umwana` — while changing what the sentence claims.

Precision 4/8, recall 4/7 — measured when the survey ran, and left as measured.
EX47 has since been reverted, which does not make the flag wrong: it was a real
movement at the time and being caught is part of why it was looked at.

It is a lead generator. The reading above is what found EX27 and EX43, and a
reading is what should settle any of these.

## A separate defect, in v1, in the other direction

Not about the rewrites at all. **At three v1 positions the English, French and
Swahili phrases say something the Kinyarwanda never said** — and the three agree
with each other, so Kinyarwanda is the outlier, not the mistranslation:

| position | kinyarwanda | english / french / swahili |
|---|---|---|
| EX15 | `kuruka no gucika intege bikabije` — vomiting and severe **weakness** | vomiting and signs of **dehydration** |
| EX35 | `kutabasha kuvuga neza n'umunwa wagoramye` — a twisted **mouth** | a drooping **face** / `le visage deforme` / `uso umepinda` |
| EX37 | `umunaniro woroheje` — mild tiredness | mild tiredness **during the day** |

Weakness is not dehydration; a twisted mouth is not a drooping face. These are
in the **shipped v1 corpus**, under one label and one concept id, and a model
trained on them learns different presentations depending on which language the
row is in. That is a direct hit on the cross-lingual parity the corpus exists to
demonstrate.

The pattern says all four languages were drafted from a shared clinical idea
rather than translated from the Kinyarwanda, and the Kinyarwanda was drafted
more conservatively. Worth checking the other 43 positions the same way before
v2 — this was three found while looking for something else, not a survey.
