# Paediatric, surveyed before drafting

The neurological batch was surveyed before drafting and five of its eight new
concepts turned out to restate v1 concepts the speaker had already authored.
**Paediatric is worse.** Of its ten new concepts, **five restate a concept that
already exists in another domain**, and in every case the only thing that makes
the paediatric row different is its relation set.

That is rule 9's shape exactly — *where the child-ness lives only in `{REL}`,
mark `applies=no` rather than authoring a near-duplicate* — but rule 9 was
written about the FIRST person of a paediatric concept. These are duplicates in
the **third** person, across domains, which rule 9 does not cover.

## RULED: PA06 collapses into EX42

Asked for and ruled. They are one presentation:

| | EX42 | PA06 |
|---|---|---|
| domain / urgency | paediatric URGENT | paediatric URGENT |
| relations | CHILD_RELATIONS | CHILD_RELATIONS |
| Kinyarwanda | **authored** — `{REL} afite umuriro n'uduheri ku mubiri` | none |
| gloss / anchor | none (v1 concept, none recorded) | child with fever and rash / IMCI MEASLES |

Nothing distinguishes them. There is no `distinct from` note on either, and the
IF07/EX29 test says an axis that is not recorded may not be invented.

**EX42 survives**, on the same ground that kept EX29 over IF07: it carries the
speaker's authored wording, which is the scarce thing. **PA06 becomes
`applies=no` in both persons, and its gloss and anchor move to EX42** — the
anchor is the part PA06 contributes, and losing `IMCI: MEASLES` would leave EX42
with no clinical reference at all, which is the state every EX concept is
already in and should not be extended.

English side, done: EX42 third is drafted, PA06 third is not, and PA06 carries
the ruling in its note. **Execution is cross-language and belongs to the
Kinyarwanda session** — `applies=no` on both PA06 rows, `concept_anchors.csv`
re-keyed from PA06 to EX42, and the row target drops by one concept.

## Four more of the same shape — flagged, not ruled

Each needs the same ruling and I am not making four concept rulings unasked.

**The convulsion cluster — four concepts, one presentation.**

| id | domain | relations | Kinyarwanda third |
|---|---|---|---|
| EX40 | paediatric | CHILD | `{REL} ari guhinda umushyitsi kandi afite umuriro uri hejuru ya dogere 40` |
| PA01 | paediatric | CHILD | none |
| IF02 | infectious_fever | ALL | `{REL} afite umuriro mwinshi kandi yaragagaye.` |
| EX33 | neurological | ALL | `{REL} yagagaye kandi arimo guhinda umushyitsi.` |

EX40 and IF02 are both *fever plus convulsions*; they differ only in relation
set. PA01 is *convulsions*, EX33 is *convulsions plus shaking*, and they differ
only in relation set. Two pairs, or possibly one group of four. Note NE01 already
collapsed into EX33 on this exact reasoning, so the cluster has been through one
round of consolidation and did not close.

**PA03 against EX32.** `child unconscious or floppy` (IMCI: lethargic or
unconscious) against `{REL} yataye ubwenge kandi ntasubiza` — lost consciousness
and does not respond. PA03 adds *floppy*, which EX32 does not carry; that is a
candidate axis, and it is not recorded anywhere.

**PA04 against CR04.** `child breathing fast with chest indrawing` against
`fast breathing with lower chest wall indrawing`. The same sign, and CR04 is
**held** because `igituza kiramanuka` and `munsi y'igituza harinjira` are rival
descriptions nobody has chosen between. Drafting PA04 would either duplicate CR04
or quietly pick one of the two descriptions the hold exists to prevent picking.
**Not drafted.**

**PA05 against GI04, with a label conflict.** `child with diarrhoea and sunken
eyes` (URGENT, IMCI SOME/SEVERE DEHYDRATION) against `severe diarrhoea with
dehydration` (**CRITICAL**, IMCI SEVERE DEHYDRATION). If these are one concept
they cannot keep two urgency labels.

PA05 carries a second problem of its own. Section 7 records that the sunken-eye
sign is attested in **neither** of two Rwandan corpora, and that the question is
no longer "what is the word" but "is this sign reported in Rwanda at all" — and
that if not, the concept should lose the sign rather than gain a word. **The
speaker has since resolved GI04 without it**, writing `yagize umwuma` (has become
dry). PA05 is the only row still carrying sunken eyes. Drafting it in English
would reintroduce, in a second language, a sign the first language has just
dropped. **Not drafted.**

## What was drafted

Eleven rows, all of them either unentangled or v1 concepts that survive any
collapse:

```
EX04 first, third   parity correction — see below
EX40 third          v1 concept, authored Kinyarwanda; survives the cluster ruling
EX41 third          v1 concept, authored Kinyarwanda; SKIN not lips is its axis
EX42 third          already drafted; the ruling above confirms it
EX43 third          parity restored, Kinyarwanda reverted since
PA02 third          unentangled
PA07 third          unentangled
PA08 first, third   hold lifted — Kinyarwanda vocabulary blocker, not a concept one
PA09 first, third   unentangled, authored Kinyarwanda
```

Not drafted, pending rulings: **PA01, PA03, PA04, PA05, PA06**. Five of ten new
paediatric concepts.

### EX04 moved while this batch was being drafted

When the parity survey ran, EX04's Kinyarwanda first said `ibara` (colour) and
its third said `ubururu` (blue) — one concept, two claims. The Kinyarwanda has
since been made consistent and **both persons now say `ibara`**. So the earlier
note in `v1-cross-language-parity.md` calling EX04 "already closed" is wrong: the
gap against English, French and Swahili is now open in both persons and settled
on the Kinyarwanda side.

Under the ruling the English follows, so EX04's English drops *blue* for
*changed colour*. That has a second effect worth having: **it separates EX04 from
CR03**, whose speaker text is `Iminwa yanjye yahindutse ubururu`. The two were
distinguishable only by that word, and now the specific-colour concept is CR03's
alone.

### PA08's hold, and why lifting it is not a liberty

`PA08` first is `hold=yes` in Kinyarwanda for a reason that is purely lexical:
no ear term is attested anywhere in the approved vocabulary — `ugutwi` appears in
none of the speaker's phrases, none of `dataset/vocabulary.py`, none of
`phrase_review_sheet.csv`, and the only `amatwi` hits are `gutega amatwi`, to lend
an ear. The row cannot be written in Kinyarwanda until the speaker supplies a
word.

English has no such gap. This is the case the brief's carry-over rule was built
for: inherit every hold, then lift the ones whose reason is Kinyarwanda wording
rather than the concept. The lift is recorded on the row.
