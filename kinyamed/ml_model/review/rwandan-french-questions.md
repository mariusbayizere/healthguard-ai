# French: what the model could not settle — 51 rows, 39 concepts, 21 questions

**NO FRENCH SPEAKER HAS SEEN ANY OF THIS.** The verdicts in
`speaker_brief_french_v2.csv` are a model's, reviewed by the same model that
drafted them. This document is the honest output of that: the places where a
model review cannot answer the question, and where a francophone reviewer — ideally
a Rwandan one working in a health facility — has to.

Read it as the counterpart of `review/rwandan-english-questions.md`. Three of the
groups below are the SAME question the Kinyarwanda and English arms are blocked
on, and should go to one person at one time.

Every question names the rows it governs. Re-derive the list rather than trusting
this count:

```
python -c "import csv; r=[x for x in csv.DictReader(open('review/speaker_brief_french_v2.csv')) if x['rw_french_check'].strip()]; print(len(r), len({x['concept_id'] for x in r}))"
```

---

## The three that are blocked in every language

These are not a coincidence. They are the concepts nobody has settled in any
language, and each one cost the Kinyarwanda arm a separate outreach question.

**1. Wheeze — `CR05` both persons.** The French says `un sifflement`. Kinyarwanda
is blocked on whether `ijwi ridasanzwe` is a definitive clinical term; English on
`a whistling sound`. Is `sifflement` what a francophone patient says, is the
clinical `sibilants` expected, or is it something else?

**2. Stool — `GI03` both, `GI05` both.** The French says `les selles`. The
Kinyarwanda took a speaker to settle after `umwanda`, `umusarane`, `amabyi`,
`ubwiherero`, `kwituma` and `amase` were all considered and attestation ranked
three of them wrongly. Is `les selles` the patient word in Rwandan French or the
clinician's? `GI05` additionally follows the GLOSS rather than the speaker's
phrase, which says blood in the *diarrhoea*.

**3. Ear discharge — `PA08` both.** The French says `J'ai mal a l'oreille et elle
coule`. Same question as the Kinyarwanda `ugutwi` block and the English flag.
Two extras on this concept: the first person is the CHILD speaking about their own
ear, not a carer (see the person note), and the speaker's Kinyarwanda now names a
condition — `umuhaha` — and states neither the pain nor the discharge.

---

## Vocabulary the corpus must choose deliberately

**4. `paludisme` or `malaria` — `EX26` first, `EX27` first.** Both are current in
Rwandan French. The corpus should pick one and use it in both rows.

**5. `VIH` or `SIDA` — `CC06` first, `CC10` first, `PR03` both.** This is a parity
question as much as a register one. French distinguishes the virus (VIH) from the
disease (SIDA); the speaker's Kinyarwanda uses `SIDA` for both — `imiti ya SIDA`
is literally *AIDS medicine*. The French drafts say `VIH`, which is medically
correct and is not what the speaker said.

**6. `la tension` — `CC03` first, `EX09` first, `CC08` first, `PR06` first.**
Standard French for blood pressure. Confirm it is the ordinary Rwandan patient
word rather than `la pression` or the clinical `la tension arterielle` (which is
what v1 used and which was down-registered here).

**7. Blood sugar, and the corpus contradicts itself — `EX08` both, `CC02` third.**
`EX08` says `mon taux de sucre dans le sang`; `CC02` says `mon sucre`. Both are
plausible and they should not both be in the corpus for the same substance.
`ma glycemie` is a third option and is probably too clinical.

**8. `teter` or `allaiter` — `PA02` third, `OB12` both.** `Teter` is what the baby
does and `allaiter` what the mother does, so the two rows are using them
correctly as drafted — but confirm both, because they are the same clinical
topic seen from two sides.

**9. `vermifuge` — `PR09` both.** Is it the patient word or is
`medicament contre les vers` more natural? Separately, on the third person: with
`Ma grand-mere` substituted, does `son enfant` read as her grandchild? The
Kinyarwanda `umwana we` carries the same ambiguity and the group-A ruling
accepted it.

**10. `en travail` for labour — `OB04` both.** Ordinary Rwandan French, or midwife
register?

**11. `se deshydrate` — `GI04` third.** Chosen because `est deshydrate` agrees
with the subject. Is it clinical register for a carer?

**12. Photophobia — `NE05` both.** Is `la lumiere me fait mal aux yeux` the
ordinary way to say it? This row is separately flagged for a clinician, because
the speaker's Kinyarwanda frames the light as the CAUSE of the headache and omits
the vomiting the gloss names.

**13. Mild indigestion — `EX16` both.** `mon ventre ne va pas bien`. Register.

**14. Cervical screening — `PR07` first.** `le depistage du cancer du col de
l'uterus` is long. The speaker deliberately chose a SHORT form for this concept;
is there a shorter ordinary French equivalent?

**15. Chest indrawing — `CR04` first (held), `PA04` third.** Which French
describes lower chest wall indrawing. `CR04` is held in Kinyarwanda because the
speaker has two rival descriptions and the standing ruling is not to choose
between them; `PA04` is a separate concept and is drafted, with
`le bas de sa poitrine rentre`. Sheet draft D056's `le bas du thorax qui se
creuse` is the alternative. **When CR04 is ruled, the two rows must be made to
agree.**

**16. Diagnosis placement — `CC05` first.** `J'ai une plaie au pied qui ne guerit
pas et je suis diabetique` puts the diagnosis last, following the speaker. Does
it read naturally?

---

## Gender agreement — the questions FR-1 created

Every row below was reworded to avoid an adjective or participle agreeing with a
subject whose gender the corpus does not know. **The claim is unchanged in every
case; what needs confirming is that the rewrite still sounds like a patient.** If
a francophone reviewer has a better neutral form, these rows want it.

**17. Participles avoided in the first person (7 rows).**

| row | avoided because it is masculine | drafted as |
|---|---|---|
| `CR02` both | `je suis essouffle` | `je n'arrive pas a finir une phrase sans m'arreter pour respirer` |
| `HT07` both | `un serpent m'a mordu`, `j'ai ete mordu` | `je me suis fait mordre par un serpent` |
| `NE07` first | `je me suis evanoui` | `j'ai eu plusieurs evanouissements` |
| `EX37` first | `je me sens fatigue` | `je ressens de la fatigue` |
| `PR01` first | `je veux etre depiste` | `je voudrais faire le test` |
| `EX23`, `HT05` first | `je suis tombe` | `j'ai fait une chute` |

`HT07` is the interesting one: the two obvious repairs both fail, because with
`avoir` the participle agrees with a preceding direct object and with `etre` it
agrees with the subject. `se faire + infinitif` leaves it invariable.

**18. Third persons that could not be transformed from their first (3 rows).**
These are the rows where French pays a real cost, and it is the same shape as the
Kinyarwanda object-marker problem holding `CR01` and `CR05`: the third person is
not obtainable from the first by substitution.

- `GI01` third — the faithful `vomit tout ce qu'il mange` forces a gender, so the
  relative clause was dropped for `toute la nourriture`. **Compare `OB10` third,
  where the identical clause SURVIVES** as `tout ce qu'elle mange`, because the
  obstetric relations are uniformly feminine. Same clause, two relation sets, two
  outcomes.
- `IF06` third — `quand il urine` forces a gender, so
  `se plaint de brulures en urinant` replaces the subordinate clause.
- `CC04` third — `quand il s'allonge` forces a gender, so `en position allongee`
  carries the orthopnoea limb. That limb is the concept, so a stiffer phrase was
  preferred to losing it.

**19. The `idees claires` idiom — `HT03`, `NE06`, `CC02` thirds.** `confus`
inflects and cannot sit in a `{REL}` phrase, so all three say
`n'a plus les idees claires`. Confirm it is right in all three and not too
colloquial for any of them. The alternative is the noun, `de la confusion`.

**20. `sans force` for floppy — `PA03` third.** Sheet draft D150 said
`mon enfant est mou`, and `mou` has the irregular feminine `molle` — wrong for
`Ma fille`, who is in `CHILD_RELATIONS`. Does `sans force` render the IMCI
floppy/lethargic sign?

---

## The one question that governs every obstetric third person

**21. `Ma voisine` — `EX38` third, and by extension the 13 obstetric thirds that carry a phrase, plus
`PR05` third.**

The speaker ruled `Umuturanyi wanjye` — gender-neutral — into the obstetric four.
English inherits that and resolves the gender downstream with `she`. French cannot
wait: the relation is a noun phrase, and `Mon voisin est enceinte` states that a
man is pregnant before any pronoun can fix it. So the French obstetric set uses
`Ma voisine`.

**Is that the right resolution of the speaker's ruling, or a narrowing of it?**
The English arm's position is that resolving the gender downstream is *"a drafting
choice inside the ruling, not a change to it"*, and `Ma voisine` claims the same
standing at a different point in the sentence. It is the one member of any French
relation set that is not a one-for-one carry of the Kinyarwanda wording, and
`french_relations.check_mirrors_kinyarwanda` allows it by name rather than by
accident.

It also buys something: with the neighbour resolved, `OBSTETRIC_RELATIONS` is
**uniformly feminine**, which is why `elle` is correct in every obstetric third
person and why FR-1 does not apply to them at all.

---

## Not a question for a French speaker, but do not lose it

**Accents.** Every French string in this corpus — v1's 46 phrases, all six frame
slots, `concepts.py`, the review sheet and all 205 candidates in this brief — is
unaccented ASCII. `mere`, `fievre`, `derniere`, `S'il vous plait`. Zero accented
characters in 609,975 shipped French and mixed rows. **No document declares this
and no ruling records it.** v2 follows v1 because v1 is frozen and a corpus that
is accented in half its rows would be worse than one that is accented in none.
It is a decision someone should make on purpose. See `french-review-pass.md`.
