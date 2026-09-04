# EX concept drift — the merged record

**Two analyses, run independently and merged 2026-09-04.** The Kinyarwanda arm
worked backwards from the collapse rulings; the English arm read all 47 EX rows by
hand while attaching English text to concepts. Neither knew what the other was
doing. This document supersedes both — the English arm's copy at
`review/ex-concept-drift.md` and the earlier Kinyarwanda-only version at this path.

**An EX id names the *position* a v1 phrase occupied.** The speaker was asked
whether each v1 phrase was natural and to give their own phrasing; they were **not
asked to hold the concept fixed**, and several rewrites landed on a different
presentation. Nothing was done wrong — the brief never asked for concept stability.
But the ids now denote the rewritten concept, and **anything keyed on "EX*n* means
what v1 slot *n* meant" is wrong.**

---

## 1. Where the two analyses disagreed — read this first

They **contradict each other nowhere.** Every fact each asserts survives the other.
The disagreement is entirely in *coverage*, and the coverage gaps are structural,
which makes them worth stating rather than quietly unioning.

### The Kinyarwanda arm missed three, and the reason is a defect in its method

`EX11`, `EX27` and `EX43` were **not found** by the Kinyarwanda pass. It seeded its
candidate list from two filters — concepts that absorbed a collapse, and rows whose
v2 phrase differs from the speaker's first pass — and asked "did the *v2 rewrite*
move off the first pass?"

**The wrong question.** For all three of these the drift happened **at the first
pass** and was never touched again, so `v2 == first pass` and both filters passed
them through as unchanged. The English arm asked "does the phrase today mean what
the v1 phrase meant?", which is the question, and read every row rather than
filtering.

The same defect explains a second gap: **the Kinyarwanda arm cannot find a vacated
concept at all.** `EX27` and `EX17` left v1 concepts with no row anywhere (§4), and
a string comparison between v1 and v2 phrases has no way to notice that a *meaning*
is now unrepresented. Only reading finds that.

**Conclusion: prefer the hand-read.** The 47 rows are a morning's work and the
filter approach missed 3 of 7 real movements plus 2 vacancies.

### The English arm did not have three things

- **The rotation, and with it the evidence that nothing was lost.** The English doc
  records EX30 as moving "onto old EX29" but not that **`EX31` now carries the runny
  nose**, nor that **`CR07` already existed in `concepts.py` glossed "short mild
  cough, no fever"** — v1 EX29's concept exactly. Those two facts are what turn
  "EX30 drifted" into "EX30's rewrite landed on a concept that already existed, and
  the sign it vacated survives elsewhere". They strengthen its EX30 row rather than
  contradicting it. §2.
- **The six absorbed-axis concepts.** `EX18`, `EX22`, `EX33`, `EX34`, `EX35`, `EX36`
  each absorbed a collapsed concept whose distinguishing axis their phrase does not
  carry. That is a different question from drift and the English pass did not ask
  it. §5.
- **The two collapse re-openings**, which are the reason any of this was
  commissioned. §3.

### The English arm had one thing entirely outside the Kinyarwanda scope

**A v1 defect running the other way** — three positions where English, French and
Swahili say something the Kinyarwanda never said. §6. It is the most serious finding
in either document and neither arm was looking for it.

---

## 2. The three-way rotation — EX29, EX30, EX31

```
v1 EX29   inkorora yoroheje nta muriro        mild cough, NO fever
   |      rewritten to
   +----> mfite umuriro woroheje umaze        mild FEVER one day,
          umunsi umwe, ariko nta kindi        otherwise well
          kibazo mfite                        = IF07's concept

v1 EX30   amazuru atemba yoroheje             mild RUNNY NOSE
   |      rewritten to
   +----> nkorora gake ariko nta muriro       mild COUGH, no fever
          mfite                               = v1 EX29's concept, and CR07's

   EX31   amazuru arantemba gake              mild RUNNY NOSE
                                              = v1 EX30's concept
```

**No sign was lost here, and it is checkable rather than reassuring.** `CR07`
already existed independently in `concepts.py`, glossed **"short mild cough, no
fever"**, anchor **"IMCI: cough, no pneumonia (green)"** — v1 EX29's concept word
for word. EX30's rewrite produced a phrase for a concept that was already there.
`EX31` carries the runny nose.

**One loose end, stated rather than papered over:** `EX31`'s own v1 position could
not be linked by either arm. So *this* rotation loses nothing, but what EX31 itself
may have vacated is unresolved. Do not read "nothing was lost" more widely than the
three ids above.

## 3. The two collapses, re-opened at the speaker's instruction — both STAND

### `IF07 -> EX29`

```
the ruling said   IF07 (IMCI: fever, no danger sign; "a slight fever since
                  yesterday but otherwise well") and EX29 are one concept,
                  because EX29 "states exactly that"
against v1        FALSE. v1 EX29 is "mild cough, no fever" - IF07's presenting
                  sign is the one v1 EX29 explicitly EXCLUDES
against today     TRUE. The rewritten EX29 IS IF07, in substance
```

**Stands.** The corpus contains phrases, not v1 glosses, and keeping both would put
two phrases of one concept into the inventory — the near-duplicate leak
`near_duplicates.py` and `test_leakage.py` exist to catch. The argument was sound;
it was sound *about the rewrite*, and the ruling presented it as a fact about EX29.

### `EX30 -> CR07`

```
against v1        FALSE. v1 EX30 is "mild runny nose". Collapsing that into a
                  cough concept would have deleted a sign.
against today     TRUE. The rewritten EX30 is "mild cough, no fever" and CR07's
                  gloss is "short mild cough, no fever" - the same sentence
```

**Stands**, and is the tidier of the two: the rewrite landed on a pre-existing
concept, so the collapse removed a real duplicate. The runny nose survives on
`EX31` — nowhere in the ruling, and the only reason no sign was lost.

## 4. Everything that moved — the union of both passes

| id | v1 concept | after the rewrite | how far | found by |
|---|---|---|---|---|
| `EX27` | fever and aching all over | fever + chills + "I suspect malaria" | **onto EX26** | English |
| `EX29` | mild cough, no fever | mild fever one day, nothing else | cough → fever | both |
| `EX30` | mild runny nose | mild cough, no fever | onto old EX29 | both |
| `EX17` | slight abdominal pain, not severe | unwell in the belly after eating | onto EX16 | English |
| `EX47` | a question about healthy diet | advice on feeding a child | **very close to PR08** | both |
| `EX43` | high fever, **refusing** to eat | high fever, **not able** to eat | toward an IMCI danger sign | English |
| `EX11` | follow-up after previous treatment | wanting to keep coming for check-ups | broadened | English |

### Two v1 concepts are now vacant

- **`EX27` duplicates `EX26`**, which is the one row of the 47 the speaker left
  byte-identical: `ibimenyetso bya malariya, umuriro n'imbeho` against
  `mfite umuriro kandi numva mfite imbeho, nkeka ko ari malariya`. Fever, chills,
  malaria suspected — twice, one domain, one urgency. The EX16/EX17 shape, and the
  same remedy applies. **The concept EX27 vacated — fever with generalised body
  aches — has no row in any language.** IF04 is fever + chills + sweats, not aches.
- **`EX17` vacated "slight abdominal pain, not severe"** on its way onto EX16, and
  was then collapsed into EX16. Same shape: the collapse was right about the
  phrases and the v1 concept is unrepresented.

### `EX43` — RULED 2026-09-04, and applied

`ntarya` (*does not eat*) became `ntabwo arimo kubasha kurya` (*is not able to
eat*). Not able to eat is an IMCI general danger sign — the ground `IF03` and `PA02`
stand on — while the row is labelled URGENT.

**Speaker's ruling: revert the wording to not-eating, keep URGENT, flag
`needs_clinician`.** Their reasoning, recorded because it is the general principle
and not just this row: *the danger sign is drinking, not eating, and moving toward
it without landing on it is worse than either position.* A phrase that straddles two
urgency classes is worse than one that sits clearly in the wrong one, because the
wrong one is at least visible.

```
EX43 third   {REL} afite umuriro mwinshi kandi ntarya.
```

`ntarya` is v1 corpus vocabulary and sits in `attest.py`'s **approved** tier. Only
the second clause changed. The first person stays `applies=no` under rule 9. The
open clinician question — whether *high fever and not eating* is URGENT, or close
enough to the drinking danger sign to be CRITICAL, with `PA02` next door — is on
the row.

### `EX47` — already closed

Drifted child-specific, restored to generic nutrition, and the child-feeding wording
rehomed to `PR08`, which is the concept it actually described.

## 5. The six absorbed-axis concepts — checked, and NOT affected by drift

Each absorbed a collapsed concept whose distinguishing axis its phrase does not
carry. The question is whether those collapses also rest on rewrites. **They do
not.**

| | v1 → today | absorbed | the axis that is in neither |
|---|---|---|---|
| `EX18` | **byte-identical** | `HT01` | pressure was applied and failed |
| `EX22` | **byte-identical** | `HT06` | the wound is **swollen** |
| `EX33` | `arimo` added | `NE01` | **continuous** convulsion |
| `EX34` | drifted, then returned | `NE03` | **sudden** weakness |
| `EX35` | preserved | `NE04` | **sudden** difficulty speaking |
| `EX36` | preserved | `NE08` | **intermittent** headache |

`EX18` and `EX22` are byte-identical across v1, first pass and today, so `HT01` and
`HT06` were ruled on exactly the phrase in the corpus now.

**`EX33` drifted TOWARD its absorbed concept.** `arimo` — the progressive, *is in
the process of* — is in neither v1 nor the first pass, and NE01's axis was
*continuous*. Not a claim the axis is carried; only that the concern is smaller here
than for EX34, EX35 and EX36.

**`EX34` is the one place a rewrite made a concept worse, and the speaker caught it
themselves.** The first pass `rwaramugaye` — *became disabled* — is a
permanent-disability claim v1 never made and a sudden stroke does not support. The
authored form went back to v1's `ntirukora`.

**Still open, and not a drift:** `EX22`'s second-phrasing slot is empty, so HT06's
swollen-versus-infected axis is unrepresented anywhere. Blocked-list item 3.

## 6. A v1 defect in the other direction — the most serious thing in either document

Not about the rewrites. **At three v1 positions the English, French and Swahili
phrases say something the Kinyarwanda never said** — and the three agree with each
other, so the Kinyarwanda is the outlier, not the mistranslation:

| position | kinyarwanda | english / french / swahili |
|---|---|---|
| `EX15` | `kuruka no gucika intege bikabije` — vomiting and severe **weakness** | vomiting and signs of **dehydration** |
| `EX35` | `kutabasha kuvuga neza n'umunwa wagoramye` — a twisted **mouth** | a drooping **face** / `le visage deforme` / `uso umepinda` |
| `EX37` | `umunaniro woroheje` — mild tiredness | mild tiredness **during the day** |

Weakness is not dehydration; a twisted mouth is not a drooping face. **These are in
the shipped v1 corpus**, under one label and one concept id, so a model trained on
them learns a different presentation depending on which language the row is in.
That is a direct hit on the cross-lingual parity the corpus exists to demonstrate.

The pattern suggests all four languages were drafted from a shared clinical idea
rather than translated from the Kinyarwanda, with the Kinyarwanda drafted more
conservatively. **Three found while looking for something else — the other 43
positions have not been checked.** Detail in `review/v1-cross-language-parity.md`.

## 7. The detector, stated so nobody trusts it

`build_english_brief.py`'s stem-overlap check flagged 8 of 46. **4 real**
(EX11, EX17, EX30, EX47), 4 paraphrases (`EX14`, `EX23`, `EX36`, `EX37` — all keep
the sign and the severity and change only the words). It **missed 3** — EX27, EX29,
EX43 — each of which kept a shared word (`umuriro`, `umwana`) while changing what
the sentence claims.

Precision 4/8, recall 4/7. **A lead generator, never a verdict.** Zero stem overlap
is routine in Kinyarwanda, which can say the same thing from an entirely different
root.

## 8. What to carry forward

**A collapse compares two phrases — the right test. The *record* names concept ids,
and an id is stable while its phrase is not.** "IF07 and EX29 are one concept"
silently became a claim about whatever EX29 says next. The two rulings that needed
re-opening are exactly the two that named only ids and quoted no phrase. **Where a
ruling turns on a phrase, quote the phrase.**

**Two checks worth running before v2, neither implemented:**

1. For every EX position, does the phrase today mean what the v1 phrase meant? The
   rotation was found by accident; three ids moved and it went unnoticed.
2. For every v1 position, do the four languages agree? §6 is three of 46 checked.
