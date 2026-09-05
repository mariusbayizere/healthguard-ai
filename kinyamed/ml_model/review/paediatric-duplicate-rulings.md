# Paediatric duplicate clusters — four rulings

**Rule each one individually.** Every cluster below is two or more concepts making
one clinical claim, with the phrases side by side so the question is what the
words say rather than what the glosses suggest.

I am not ruling any of these. Each needs either a `distinct from` axis recorded,
or a collapse — and the IF07/EX29 test says an axis that is not already recorded
may not be invented to save a concept.

---

## 1. The convulsion cluster — RESOLVED to two concepts

**`guhinda umushyitsi` means convulsions.** Ruled 2026-09-05. Everything
below the word question now follows, and the section is kept so the
reasoning survives the answer.

### What the ruling determines

```
EX40  paediatric      CRITICAL  CHILD_RELATIONS   no anchor recorded
      {REL} ari guhinda umushyitsi kandi afite umuriro uri hejuru ya dogere 40
      v1 english: convulsions with a fever above 40 degrees

IF02  infectious      CRITICAL  ALL_RELATIONS     IMCI general danger sign: convulsions
      {REL} afite umuriro mwinshi kandi yaragagaye.
      first person authored too: Mfite umuriro mwinshi kandi nagagaye.

PA01  paediatric      CRITICAL  CHILD_RELATIONS   IMCI general danger sign: convulsions
      (no Kinyarwanda authored)
      english draft: my child is having a fit

EX33  neurological    CRITICAL  ALL_RELATIONS     no anchor recorded
      {REL} yagagaye kandi arimo guhinda umushyitsi.
      v1 english: convulsions and shaking
```

**`IF02` and `PA01` cite a byte-identical anchor** — `IMCI general danger sign:
convulsions`. Same string, same urgency. The only difference between them is the
domain they were filed in and the relation set that follows from it, which is
rule 9's shape in the third person.

### The word the cluster turns on

`guhinda umushyitsi` appears in EX40 and EX33 and nowhere else in the speaker's
work. **v1 rendered it two different ways in English:**

| v1 Kinyarwanda | v1 English |
|---|---|
| `kugagara no guhinda umushyitsi` (EX33) | convulsions and **shaking** |
| `umwana ufite guhinda umushyitsi n'umuriro urenga dogere 40` (EX40) | **convulsions** with a fever above 40 degrees |

The same Kinyarwanda phrase, translated once as a danger sign and once as
something that is not one. Attestation says **both readings are real Rwandan
usage**:

- **Convulsions.** The RBC curriculum lists it five separate times inside the
  child danger-sign list, between losing consciousness and being unable to
  breastfeed: *"...kugaragaza intege nke cyane, kutagira icyo yitayeho,
  gutakaza ubwenge, **guhinda umushyitsi** o Kutabasha konka no kutarya."*
- **Shivering with fever.** A CHW conversation: *"...rimwe na rimwe yumva akonje
  kandi **agahinda umushyitsi**, hanyuma ako kanya akumva ashyushye cyane"* —
  sometimes feels cold and shivers, then straight away feels very hot. That is
  rigors, not a seizure.

**So the ruling question is not really "are these four concepts one".** It is:
*does `guhinda umushyitsi` mean convulsions or shivering in EX40?* Everything
follows from that.

- If **convulsions**: EX40 is fever + convulsions, which is IF02. Two pairs to
  collapse — {EX40, IF02} and {PA01, EX33} — or one group of four.
- If **shivering**: EX40 is rigors with a high fever, a *different presentation
  from all three others*, and arguably not CRITICAL. EX33 keeps both words and
  stays the convulsion concept. The cluster shrinks to {PA01, EX33} and
  {IF02 alone}.

**The word was ruled first.** With it settled, the four concepts are two pairs:

```
fever + convulsions      EX40  {REL} ari guhinda umushyitsi kandi afite umuriro uri hejuru ya dogere 40
                         IF02  {REL} afite umuriro mwinshi kandi yaragagaye.
                               (and first person: Mfite umuriro mwinshi kandi nagagaye.)

convulsions              EX33  {REL} yagagaye kandi arimo guhinda umushyitsi.
                         PA01  (no Kinyarwanda authored)
```

`EX33` says convulsions twice — `yagagaye` (past) and `arimo guhinda umushyitsi`
(progressive). That is not redundancy: NE01, *continuous convulsion*, collapsed
into EX33, so the not-stopping limb is what it absorbed.

**Recommended: IF02 and EX33 survive; EX40 and PA01 collapse into them.**

| | survives | collapses in | why |
|---|---|---|---|
| fever + convulsions | **IF02** | EX40 | IF02 has BOTH persons authored and an anchor; EX40 has one person and none. Keep EX40's `above 40 degrees` as a second phrasing — the EX16/EX17 pattern — so the threshold wording is not lost. |
| convulsions | **EX33** | PA01 | EX33 has the authored wording, PA01 has none. EX33 inherits PA01's anchor. Identical to the PA06 -> EX42 ruling you confirmed. |

### And the axis between the two pairs needs recording, because IF02's anchor is wrong

`IF02` and `PA01` collide on a byte-identical anchor only because IF02 cites the
generic danger sign. Its siblings do not:

```
IF01  fever with stiff neck        IMCI: stiff neck -> VERY SEVERE FEBRILE DISEASE
IF05  fever with generalised rash  IMCI: generalised rash -> MEASLES
IF02  fever with convulsions       IMCI general danger sign: convulsions      <-- odd one out
```

Every other `fever with X` concept anchors to what fever-plus-X classifies as.
IF02 should read **`IMCI: convulsions -> VERY SEVERE FEBRILE DISEASE`**.

Correcting it does three things at once: it makes IF02 consistent with IF01 and
IF05, it **records the fever axis** that separates the two pairs, and it dissolves
the IF02/PA01 anchor collision without either concept moving. After the collapse
PA01 is gone anyway, but the axis still has to be recorded or the next survey
finds EX33 and IF02 and asks the same question again.

---

## 2. PA03 against EX32 — unconscious, and "floppy"

```
EX32  neurological    CRITICAL  ALL_RELATIONS     no anchor recorded
      {REL} yataye ubwenge kandi ntasubiza.
      v1 english: lost consciousness and is not responding

PA03  paediatric      CRITICAL  CHILD_RELATIONS   IMCI general danger sign: lethargic or unconscious
      (no Kinyarwanda authored)
      english draft: my child is floppy and will not wake
```

Same presentation; the difference is the relation set. **PA03 carries one thing
EX32 does not: *floppy*** — hypotonia, which is a separate observation from being
unresponsive, and the one a carer actually notices first in an infant.

That is a candidate axis and it is **recorded nowhere** — not in `concepts.py`,
not in `concept_anchors.csv`. The anchor PA03 cites says *lethargic or
unconscious*, and EX32's phrase covers the unconscious limb only.

**My recommendation: collapse, unless you want the floppy limb.** If you do, the
axis has to be written into the gloss and the anchor before either row is
drafted, and EX32's phrase then needs the lethargy limb it currently lacks.
Note the RBC danger-sign list keeps them together — *`kugaragaza intege nke
cyane, kutagira icyo yitayeho, gutakaza ubwenge`*, very weak, unresponsive, loses
consciousness — as one item, not three.

---

## 3. PA04 against CR04 — identical anchor, different urgency

```
CR04  cardiac_resp    URGENT    ALL_RELATIONS     IMCI: chest indrawing -> SEVERE PNEUMONIA
      first : Iyo mpumeka, igituza cyanjye kiramanuka cyane.
      third : Iyo {REL} ahumeka, munsi y'igituza harinjira cyane.
      HELD — the two descriptions above are rivals; neither has been chosen

PA04  paediatric      CRITICAL  CHILD_RELATIONS   IMCI: chest indrawing -> SEVERE PNEUMONIA
      (no Kinyarwanda authored)
      english draft: my child breathes fast and the chest pulls in
```

**Byte-identical anchors, and the two rows carry different urgency labels.** One
of the labels is wrong, whatever else is decided — the anchor says SEVERE
PNEUMONIA for both.

This is also why PA04 was not drafted in English. CR04 is held precisely because
`igituza kiramanuka` and `munsi y'igituza harinjira` are two rival descriptions of
the same sign and nobody has chosen. Writing PA04's English would put a third
description of chest indrawing into the corpus while the first two are still
unresolved.

**My recommendation: settle CR04's hold first, then collapse PA04 into it** with
`CHILD_RELATIONS` if the concept should be child-only — which the anchor implies,
since chest indrawing is an IMCI sign and IMCI is under-fives. The urgency then
follows from one row rather than being reconciled between two.

---

## 4. PA05 against GI04 — and the sign the speaker has already dropped

```
GI04  gastrointestinal CRITICAL  ALL_RELATIONS    IMCI: SEVERE DEHYDRATION
      {REL} afite impiswi zikomeye kandi yagize umwuma.
      english candidate (stale): watery diarrhoea with sunken eyes and the skin stays pinched

PA05  paediatric       URGENT    CHILD_RELATIONS  IMCI: SOME/SEVERE DEHYDRATION
      (no Kinyarwanda authored)
      english draft: my child has diarrhoea and the eyes look sunken
```

Near-identical anchors, **different urgency labels**, and the same presentation.

The second problem is independent of the first. **The speaker has already
resolved GI04 without the sunken-eye sign**, writing `yagize umwuma` — has become
dry. Section 7 records why: `yinjiye` was not substantiable in the eye sense, and
524 CHW questions covering childhood diarrhoea describe dehydration as
`kubura amazi mu mubiri`, lacking water in the body, **never once by sunken
eyes**.

**PA05 is the last row in the corpus still carrying that sign**, and its English
draft is the only place it survives. Drafting it would reintroduce, in a second
language, a sign the first language has just dropped — and the English wording
would then be the only evidence that the concept ever had it.

**My recommendation: collapse PA05 into GI04 and let the sign go with it.** If
the SOME/SEVERE distinction is worth keeping as an axis, it is an axis about
severity, not about eyes, and it needs recording either way.

---

## Found while assembling this — and it caught two I had missed

`python review/shared_anchors.py`. Two concepts citing the same anchor are making
the same clinical claim; that is objective, unlike judging whether two glosses
feel alike. Five real groups, three of which disagree on urgency:

```
IMCI general danger sign: convulsions                 IF02 CRITICAL / PA01 CRITICAL
IMCI general danger sign: not able to drink or        IF03 CRITICAL / PA02 CRITICAL
  breastfeed
IMCI: chest indrawing -> SEVERE PNEUMONIA             CR04 URGENT   / PA04 CRITICAL   <-- conflict
BEC Module 2: approach to trauma                      HT02 CRITICAL / HT05 URGENT     <-- conflict
BEC Module 3: approach to difficulty in breathing     CR02 CRITICAL / CC04 URGENT     <-- conflict
```

**`HT02`/`HT05` and `CR02`/`CC04` are outside paediatric and were not on any
list.** The first two are same-domain; the third is cross-domain, chest pain
against heart failure, and those may be genuinely different presentations sharing
a coarse module-level anchor. They are flagged here, not ruled.

### A correction: I drafted PA02 as unentangled and it is not

`PA02` shares `IF03`'s anchor byte for byte — *not able to drink or breastfeed*.
I drafted PA02 third as unentangled in the paediatric batch and should not have
called it that.

**I still think it survives, and here is the argument rather than the assertion:**
the anchor names *two* signs and the two concepts take one limb each — IF03 is
*fever and unable to drink*, PA02 is *too weak to breastfeed*. That axis is
visible in both glosses, so it is recorded, which is exactly what PA01 and PA03
lack. The draft stands, but it stands on a stated axis now rather than on my not
having noticed.

---

## New evidence bearing on the EX43 ruling you already made

You ruled EX43 back to not-eating with the label kept at URGENT, on my argument
that IMCI's danger sign is *not able to **drink** or breastfeed*, so "not able to
eat" gestures at the sign without landing on it.

**The Rwandan curriculum renders that sign as `Kutabasha konka no kutarya`** —
not able to breastfeed **and not to eat**. Eating is inside the danger-sign list
as Rwanda teaches it, which is evidence in the direction I argued against.

The ruling is yours and it stands; the `needs_clinician` flag on the row is
carrying exactly this question. But the flag now has better evidence behind it
than when it was raised, and the clinician should see this line rather than only
the IMCI English.
