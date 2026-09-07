# Writing the Swahili phrases — how to use the sheet

Everything you need is in the two spreadsheets. This page explains the columns
and states the rules the phrases have to satisfy. You do not need anything else
from the project.

**The sheets**

| file | rows | what it is |
|---|---|---|
| `speaker_brief_swahili_v2.csv` | 256 | the concepts — 128 of them, each with a first-person and a third-person row |
| `speaker_brief_swahili_v2_relations.csv` | 12 | the relation words (*my child*, *my wife* …). Nobody has written these in Swahili yet, and every third-person phrase needs them. |

---

## What we are asking for

For each row marked **WRITE**, put in `your_phrasing` the sentence a patient
would actually say in Kiswahili for the meaning in `english_gloss`.

**We are not asking for a translation.** The English gloss is a clinical
description — *"fever with generalised rash"* — deliberately not written as a
sentence, so that there is nothing to translate and nothing to edit. Read the
meaning, then write what someone would say in a health-centre queue.

**There is no Swahili anywhere in this brief, and that is on purpose.** An
earlier machine-translated Swahili corpus exists in this project and it is
deliberately not shown to you. When a speaker is given a draft to correct, the
corrections stay close to the draft and the draft's mistakes survive. That
happened to the first Kinyarwanda pass, and it is why the Kinyarwanda arm was
re-authored from scratch instead. You are the first person to write these.

Where a second natural phrasing exists, put it in `second_phrasing_optional`.
Two ordinary phrasings are worth much more to us than one polished one —
variation is the thing the dataset is short of.

---

## The columns

**Read these**

| column | what it is |
|---|---|
| `action` | **WRITE**, **SKIP — does not apply**, or **SKIP — held**. Start here. |
| `english_gloss` | the clinical meaning. Write from this. |
| `proposed_urgency` | CRITICAL / URGENT / ROUTINE. Not yours to set — but if one looks unsafe to you, say so; that is exactly the kind of thing we would rather hear. |
| `person` | `first` = the patient's own words. `third` = someone else speaking about them. |
| `person_note` | who is speaking on this row, where it is not obvious. |
| `relation_set_members` | for third-person rows: every relation this one sentence has to work for. |
| `keep_distinct_from` | concepts close enough to this one that a single sentence could accidentally serve both. Keep them apart — see below. |
| `brief_notes` | anything specific to this row, including the three open questions. |
| `needs_clinician` | `yes` means a doctor still has to rule on something here. It does not stop you writing the row unless `action` says SKIP. |

**Write in these — the rest of the sheet is ours**

| column | what to put in it |
|---|---|
| `your_phrasing` | the sentence. |
| `second_phrasing_optional` | another way the *same* patient might say it. |
| `regional_variant` | where usage differs by area: what changes, and where. Say which variety you wrote in `your_phrasing`, and what a speaker somewhere else would say instead. |
| `your_notes` | anything you want to tell us. Doubts, refusals, "there is no word for this", answers to the three questions. |

`regional_variant` and `second_phrasing_optional` are different things. A second
phrasing is two ways *one* person might say it; a regional variant is the same
thing said differently in a different place. If you are not sure which a given
alternative is, put it in `your_notes` and say so.

---

## The five rules a phrase has to satisfy

Your sentence is not used on its own. The generator wraps it:

```
opener  +  YOUR SENTENCE  +  onset  +  context  +  closer
```

which comes out as, in Kinyarwanda:

> *Muganga,* **umugore wanjye afite ububabare bukabije mu nda** *kuva hashize
> iminsi ibiri kandi birushaho kuba bibi. Ndakeneye ubufasha vuba.*
>
> Doctor, **my wife has severe abdominal pain** since two days ago and it is
> getting worse. I need help quickly.

So:

**1. Write a complete sentence, in the patient's voice.** Capital letter at the
start, full stop at the end. (The earlier corpus used bare fragments after "I
have…", and the Kinyarwanda speaker said that was a large part of why it read as
non-native. Full sentences now.)

**2. No time reference inside your sentence.** The wrapper adds one — *since
yesterday*, *since two days ago*. A sentence carrying its own produces two. The
exception is where the duration IS the concept: *"a cough for more than two
weeks"* has to say two weeks, because that is what makes it TB screening rather
than a cough.

**3. Do not end with an added clause.** The wrapper adds one of those too
(*…and it is getting worse*). A clause inside the phrase and a clause after it
read as a run-on.

**4. Third-person rows: write `{REL}` where the relation word goes** — those
five characters exactly, braces included. Make `{REL}` the grammatical subject,
and check the sentence still reads naturally for **every** member listed in
`relation_set_members`. This is the rule the old corpus broke worst: one phrase
had "I am pregnant" embedded in it, and the generator produced *"my husband has
severe abdominal pain I am pregnant"*.

**5. Never mix first and third person inside one sentence.** A sentence is
entirely the speaker's own symptom, or entirely someone else's.

Also: straight apostrophes, no double spaces.

---

## What we are actually short of

The first Kinyarwanda pass was written by a machine from English, and the
speaker who replaced it named four predictable faults. They apply to any
language written that way, so they are worth checking your own sentences
against:

- **Calqued syntax** — English structure with Swahili words. Grammatical,
  comprehensible, and not how someone thinking in Kiswahili would build the
  sentence. Read it aloud; this one survives silent reading.
- **Register too high** — a clinical word where speech uses an everyday one. If
  it sounds like a case note, it is wrong even if every word is correct.
- **Borrowing avoided** — real speech borrows freely: *malaria*, *pressure*,
  *sugar*, *test*. A phrase that carefully avoids the borrowed word a patient
  would really use is less natural, not more. Borrow where people borrow.
- **Too complete** — generated text is fully specified. A patient in a queue
  says less than a written summary would.

And the test to apply to each sentence, in this order:

1. Read it aloud, inside a full rendering, with a third-person subject.
2. Would you say this, or would you say something else? If something else came
   to mind, **that** is the phrase.
3. Would a patient volunteer it, or only say it if a nurse asked directly?
4. Is a word here doing work no patient would do — a body part named formally,
   a duration stated too exactly?
5. Could a different patient say it differently? If yes, write that too.

---

## `keep_distinct_from`, and why it is there

We measured this on the Kinyarwanda phrases after they were written: five groups
of phrases had become inseparable, holding eleven different concepts between
them. The cause was almost always the same — a short sentence turned out to be
the opening of a longer one written weeks later, so the two concepts could no
longer be told apart, and four phrases had to be rewritten.

Nothing about that is specific to Kinyarwanda. `keep_distinct_from` names the
concepts near enough to this one for it to happen again, so you can see it while
you write rather than afterwards. If two of them genuinely *are* the same thing
in Kiswahili, that is worth telling us in `your_notes` — it may be that they are
one concept and we have not noticed.

---

## The three open questions

Three concepts are stuck in **both** other languages, on the same three
vocabulary problems. They are marked in the sheet with the full question in
`brief_notes`:

| rows | the question |
|---|---|
| **CR05** | how a patient describes the sound of **wheeze** |
| **GI03, GI05** | what a patient calls **stool** |
| **PA08** | how a parent says a child's **ear is discharging** |

Answer in `your_notes` on the row, or separately — whichever is easier.

Two things worth saying about these. First, **"there is no ordinary word for
this" is a real answer** and a useful one; it is what the Kinyarwanda speaker
told us about two of the three, and it changed what we build rather than
stopping us. Second, **your answer is evidence for the other two languages, not
a ruling on them** — Kiswahili having a word does not settle what Kinyarwanda
does. We are asking three speakers the same question on purpose.

---

## What is not in the sheet, and will be asked for later

- **The wrapper fragments** — the greetings, time expressions and closing lines
  that go around your sentences. Tracked separately, in
  `review/frame_fragments_brief.csv`.
- **Which variety of Kiswahili this should be.** The one Swahili health corpus
  we found is Tanzanian institutional text, and Kiswahili in Rwanda is closer to
  the border varieties. `regional_variant` is where that starts getting
  recorded; a general view from you would help.
- **Code-switching.** Roughly half the dataset mixes languages within a
  sentence, and how Kiswahili mixes with Kinyarwanda or English in a Rwandan
  health centre is not something we can decide without asking.

---

## What happens to your work

Your phrases go into the dataset as speaker-authored, recorded separately from
anything a machine produced, and the paper reports the two separately. You will
be named as a contributor unless you would rather not be. The dataset is
published openly. If you want your contribution removed at any point, say so and
it comes out.

Nothing here is in use with any real patient, and will not be until clinicians
say it is safe.
