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
