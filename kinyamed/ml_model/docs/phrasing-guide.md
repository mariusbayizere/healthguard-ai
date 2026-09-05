# Writing phrases: what to check as you go

Two different kinds of check. The first kind is mechanical, and
`review/lint_phrases.py` does it for you. The second kind is your judgement, and
nothing in this repository can do it — the guide below is structure for applying it
consistently, not instruction in Kinyarwanda.

---

## Part 1 — the composition constraints (mechanical)

Your phrase is **not a sentence**. It is one slot in six, and the generator wraps it:

```
opener + subject + " " + PHRASE + onset + context + closer
```

Rendered, with a real phrase from the corpus:

```
Muganga, umugore wanjye afite ububabare bukabije mu nda kuva hashize iminsi ibiri
kandi birushaho kuba bibi. Ndakeneye ubufasha vuba.
```

So the phrase must survive being embedded. Five rules follow:

**1. It is the complement of *afite* / *mfite*.** A noun phrase, not a clause with
its own subject. `ububabare bukabije mu nda` works. Something that reads as a full
sentence will not.

**2. It must work after all ten subjects**, not just first person:

```
Mfite            Ndumva mfite       Umwana wanjye afite   Umugore wanjye afite
Umugabo wanjye afite               Mama afite            Papa afite
Mushiki wanjye afite               Umuturanyi wanjye afite   Umukecuru afite
```

This is the rule the existing corpus breaks worst. One existing phrase embeds
*ndi utwite* ("I am pregnant"), which generates:

```
Umugabo wanjye afite ububabare bukabije mu nda ndi utwite kandi ndavuye amaraso
```

— "my husband has severe abdominal pain I am pregnant and I have bled". **Test every
phrase against `Umugabo wanjye afite …` before you accept it.** If it only works in
first person, it is wrong here.

**3. No time reference inside the phrase.** The onset slot adds one — *kuva ejo*,
*kuva mu gitondo*, *kuva hashize iminsi ibiri*. A phrase carrying its own produces
two.

**4. No *kandi* clause inside the phrase.** The context slot adds one. **Six of the
existing 46 break this**, e.g. *ububabare bukabije mu gituza kandi sinshobora
guhumeka* which renders as *"… kandi sinshobora guhumeka kandi ndahangayitse"*. The
linter flags all six.

**5. No leading capital, no trailing punctuation, no double space, straight
apostrophes, NFC-normalised.** The linter checks these. The apostrophe and
normalisation ones matter more than they look: mixed Unicode forms silently break
the substring-leakage detection that the whole evaluation rests on.

Run it as you go:

```bash
python review/lint_phrases.py review/speaker_brief_kinyarwanda.csv --language kinyarwanda
```

---

## Part 2 — what 80% is probably failing on

I drafted the existing Kinyarwanda from English concepts, and I can tell you how
that process fails even though I cannot tell you whether a given phrase is right.
Four predictable defects, worth checking each phrase against:

**Calqued syntax.** Written by mapping an English structure onto Kinyarwanda words.
Grammatical, comprehensible, and not how the sentence would be built by someone
thinking in Kinyarwanda first. This is the most likely single cause of "80%".

**Register drift upward.** A clinical or written word where speech uses an everyday
one. Patients do not use the term a nurse would write in a file. If a phrase sounds
like a case note, it is wrong even if every word is correct.

**Borrowing avoided.** I mostly wrote "pure" Kinyarwanda. Real speech borrows
freely — *malaria*, *pressure*, *sugar*, *test* — and a phrase that carefully avoids
the borrowed term a patient would actually use is less natural, not more.

**Too complete.** Generated text produces well-formed, fully specified descriptions.
Speech is elliptical, and a patient in a queue says less than a written summary
would.

## The speaker's standing rules

Set by the Kinyarwanda speaker and binding on all drafting, mine included:

**1. Clarity over sophistication.** If an older rural patient hears it and
understands immediately, that is the better training example. A more elegant or
more literary construction that takes a second to parse is the worse one. The
corpus is modelling what people say in a waiting room, not what reads well.

**2. Prefer `{REL}` as the grammatical subject** rather than reaching for an
object marker. `{REL} ahumeka bimugora cyane` puts the relation in subject
position, where it substitutes cleanly across all eight. A construction that
makes the relation an object, or leaves it out of the main clause, may not.

**3. Never mix first and third person inside one phrase.** A phrase is entirely
the speaker's own symptom or entirely someone else's. The original corpus violated
this — `ntabasha kuvuga neza kandi umunwa waramugoramye` opens first person and
closes with a third-person object marker — and it was rewritten as
`Ntashobora kuvuga neza kandi umunwa we waragoramye`, fully third.

**4. Never increase dataset size by generating linguistically or clinically
questionable combinations.** Validity and provenance matter more than row count.
The combination space is large enough that no relation set, no not-applicable row
and no narrowed concept threatens any row target — so when a combination is
doubtful, drop it. A row describing a patient who does not exist is worse than a
row that does not exist.

**5. Never accept machine Kinyarwanda because the grammar looks plausible.**
Every phrase is either speaker-approved or flagged. Plausible-looking output from
a non-speaker is exactly the failure this process exists to prevent, and the
provenance columns record which is which so the paper can state it.

**6. Where a relation combination is uncertain, restrict the relation set.** Do not
invent Kinyarwanda to make a combination work, and do not generate a clinically
questionable example to fill it. The combination space is large enough that
restriction costs nothing measurable.

**7. Never silently resolve low-confidence Kinyarwanda.** If a phrase cannot be
confidently validated from speaker knowledge, it is marked `needs_clinician` or
left unresolved. Producing a plausible-sounding fix and moving on is the failure
mode, not the fix.

**8. A draft is a suggestion, never an approval.** Nothing is `machine_approved`
unless the speaker says "accept". `speaker` and `needs_clinician` must stay
distinguishable in the record, because the paper reports them separately.

**9. Where a paediatric first-person row would duplicate an adult concept**, mark
it `applies=no` rather than authoring a near-duplicate. The child-ness of the
patient lives in `{REL}`, and first person has no slot for it — so a child saying
"I have a fever and a rash" is the adult concept, not a paediatric one. Ruled
against PA06/EX42 (vs IF05), EX40 (vs IF02), EX41 (vs CR03) and EX43 (vs IF03).

**10. Where a ruling conflicts with evidence, say so before recording it**, not
after. A ruling given on wording does not settle a question about the concept, and
recording it as though it did buries the question. Raise it, then record what the
speaker decides.

**11. Three-way test before writing any first-person row.** Not every concept has
one. Ask what kind of thing the concept is:

| the concept is | first person | because |
|---|---|---|
| **a symptom the patient can report** | potentially yes | they feel it and can say it |
| **a routine service the patient receives** | no — third person | someone brings them; the recipient does not present themselves |
| **an observer or measurement finding** | no — third person | the patient cannot perceive it about themselves |

The three limbs are about *who can know the thing*, not about severity.

- **Symptom.** Pain, fever, bleeding, breathlessness, a rash the patient can see.
  PA08's ear pain and discharge qualify; so does every obstetric first-person row,
  because the pregnant woman is the patient.
- **Service received.** Vaccination, deworming, growth monitoring — the child is
  the recipient and an adult brings them. Distinguish this from *advice*, which is
  received by the carer and is therefore theirs to ask for in first person: OB12
  (`Ndashaka kugirwa inama uko nakonsa umwana`) and EX47 are correct as first
  person, PR09 is not.
- **Observer or measurement finding.** Sunken eyes, a slow skin pinch, chest
  indrawing, unconsciousness, drowsiness, new confusion. The patient cannot see or
  judge these about themselves.

**The measurement limb means "has not been told", not "was measured".** The
speaker's own EX08 (`isukari yo mu maraso yanjye yazamutse cyane`) and EX09
(`umuvuduko w'amaraso wanjye wazamutse cyane`) report a blood sugar and a blood
pressure in first person, and they are right to: the patient has been given the
reading and can repeat it. A measurement becomes third-person only when nobody has
told the patient — a growth curve read off a chart, a skin pinch done during the
examination itself.

**A patient can report an observer sign when they can perceive it directly.**
"Observer sign" is a clinical category, not a linguistic one, and the two do not
line up. Cyanosis and chest indrawing are signs a health worker is trained to look
for — and a patient can still see their own lips and fingertips, and still feel
their chest pull in as they breathe. The speaker's `CR03`
(`Iminwa yanjye yahindutse ubururu`), `EX04` and `CR04`
(`Iyo mpumeka, igituza cyanjye kiramanuka cyane`) are all correct first person for
exactly that reason. What the limb excludes is what the patient has no access to:
a skin pinch performed during the examination, a growth curve, their own
unconsciousness, their own confusion.

**12. SERVICE_SPEAKER — for a service concept, first person is the person
presenting or requesting the service, not necessarily the patient.** Symptom
concepts and service concepts do not work the same way. In a symptom concept the
speaker is the patient, and rule 11's limbs apply. In a service concept the
speaker is whoever walks in and asks — and for a service delivered *to* someone
else, that is not the patient.

```
beneficiary == requester   ->  ordinary first person   (CC08 refill, PR07 screening,
                                                        OB11 antenatal, PR03 HIV test)
beneficiary != requester   ->  first person is the REQUESTER
                               (EX46 gukingiza umwana, PA09, PA10, PR08, EX47)
```

The speaker's own `EX46` — `gukingiza umwana`, "vaccinating a child" — is the
evidence this rule is built from. It sits in a first-person row, it is
speaker-authored, and the child is plainly not the one speaking. The row is
correct; what was missing was the rule saying why.

Two consequences worth stating:

- **A service concept's first-person row is not a child speaking**, so rule 9's
  duplication test does not apply to it. `PA09` and `PA10` keep their first-person
  rows on this ground.
- **It does not license mixing person inside a phrase** (rule 3). `gukingiza
  umwana` carries no person marking at all; it is a bare noun phrase in the
  requester's mouth. A service phrase that inflects for a third-person subject
  still breaks rule 3.

Rule 11's "routine service the patient receives -> third person" limb is
**narrowed by this**: it excludes the *patient's* first-person row, not the
carer's. Both persons can exist for a service concept, and they are different
speakers rather than the same speaker rephrased.

**Rule 11 flags; it does not overrule.** Where the test disagrees with a phrase
the speaker has already authored, the authored phrase stands and the test has
raised a question under rule 10 — nothing more. The test is a prompt to ask, and
its own limbs have twice been corrected by what the speaker had already written.

**13. Before collapsing one concept into another, check that the absorbing PHRASE
carries the whole sign — not that the domain or the gloss looks close.** Two
proposed collapses failed this on 2026-09-05, both plausible on domain and neither
on content, and the failure has one shape: **the absorbing phrase quietly adds a
requirement, or covers only half of one.**

```
PA01 -> EX40   EX40 is "convulsing AND fever above 40". Collapsing an IMCI
               general danger sign there makes it CONDITIONAL ON A TEMPERATURE.
               A child convulsing without fever is still a danger sign.
               Correct target: EX33, the plain-convulsion phrase.

PA03 -> EX32   IMCI's danger sign is "lethargic OR unconscious".
               EX32 is "yataye ubwenge KANDI ntasubiza" - lost consciousness
               AND unresponsive. It covers only the unconscious half, and the
               lethargic half is the one that presents EARLIER. Held, not
               collapsed.
```

**The `kandi`-versus-*or* test, which is the cheap mechanical form of this.**
Where the concept's anchor names two states with **or**, and the candidate phrase
joins two clauses with **`kandi`**, the phrase is narrower than the concept and the
collapse loses a presentation. A conjunction standing in for a disjunction is the
most reliable tell available, because it survives translation and needs no clinical
judgement to spot: compare the anchor's connective with the phrase's.

It runs the other way too. A phrase joining with `kandi` where the concept means
one thing said twice — v1's `kugagara no guhinda umushyitsi`, convulsing and
shaking — is *not* two requirements, and PA01 collapsed into it correctly. **So the
test flags; it does not decide.** What it reliably catches is the case where nobody
looked at the connective at all.

**And check the anchor before executing** — `concept_anchors.csv` holds no v1
concepts, so collapsing an anchored concept into an unanchored one deletes a
clinical reference silently. Carry it across or record it as dropped. See
`docs/session-state.md` section 8a.

## Part 3 — the consistency test

For each phrase, in this order:

1. **Read it aloud** inside a full rendering, with a third-person subject. Not on the
   page — aloud. Calqued syntax survives silent reading and does not survive speech.
2. **Would you say this, or would you say something else?** If something else comes
   to mind, that is the phrase. Write what came to mind, not a repair of mine.
3. **Would you say it unprompted**, or only if a nurse asked you directly? Both
   exist in real consultations, but the corpus is meant to be what a patient
   volunteers.
4. **Is a word here doing work no patient would do?** Precision a patient would not
   supply, a body part named formally, a duration stated exactly.
5. **Could a different patient say the same thing differently?** If yes, write that
   too in `second_phrasing_optional`. Two natural phrasings are worth much more than
   one polished one — variation is the thing the corpus is short of.

**Write your own, do not edit mine.** You said this already and it is right: editing
anchors you to my structure, which is the defect. The brief has the English gloss
precisely so you can work from the clinical meaning rather than from my sentence.

## A note on what "98%" can mean here

98% of phrases being natural is a reachable target. 98% *confidence* that they are is
not, from one speaker — which is why the second-reviewer process exists. What you
can do alone is make them consistently *yours*; what makes them defensible is a
second speaker agreeing independently.
