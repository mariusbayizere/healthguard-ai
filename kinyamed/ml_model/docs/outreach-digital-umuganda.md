# Outreach — Digital Umuganda / C4IR Rwanda

Drafted 2026-09-03 off the investigation in `language-resources.md` section 2a.
**Not sent.** The licence question that gated it is settled (`licensing.md` Q5:
target CC BY 4.0), so the draft is clear to send — but read notes 2 and 4 first,
which change what you should ask for.

**Send the eight questions first, and separately.** They cost a reply, not an
agreement, and they unblock more rows today than the full dataset would.

---

## Who to write to

| route | address | why |
|---|---|---|
| **Primary** | `info@c4ir.rw` | The access route the Nature paper names for the full 5,609-question dataset. Requests are assessed on "fair value exchange". |
| Named at Digital Umuganda | Samuel Rutunda | First author on the released figshare dataset; DU built the collection app and the Kinyarwanda STT model. |
| Named at RBC | Emery Hezagira, Eric Remera | RBC co-authors; RBC holds the full dataset. |
| Academic co-lead | Dr Bilal Akhter Mateen, `bmateen@path.org` | Corresponding author on the protocol paper. Useful if the C4IR route stalls. |

Send to C4IR first. Copy the others only if you have an existing introduction —
the RBC contact who gave you this lead is the better opener.

---

## Draft

> **Subject:** Access request — CHW clinical question dataset, for an open
> Kinyarwanda triage corpus
>
> Dear Centre for the Fourth Industrial Revolution,
>
> I am building an openly licensed Kinyarwanda dataset for clinical triage — the
> task of sorting a described complaint into an urgency level — and I am writing
> to ask about access to the full set of community health worker questions
> described in "Large language models for frontline healthcare support in
> low-resource settings" (Nature Health, 2026), which the paper names you as the
> point of contact for.
>
> I have already worked with the 524-question subset released on figshare
> (10.6084/m9.figshare.29213147) and it is the most useful Kinyarwanda clinical
> language I have found anywhere. I would like to explain what I am doing with
> it, because it bears on the "fair value exchange" assessment.
>
> The corpus I am building is authored, not scraped. A Kinyarwanda-speaking
> project owner writes every phrase; my role is to draft suggestions they accept,
> rewrite or reject, and roughly three quarters of the accepted phrases are their
> own wording rather than mine. Where a phrase cannot be substantiated against
> language a Rwandan has actually written, it is left blank rather than filled in
> with a plausible guess — there are rows in the current brief that have been
> open for weeks for exactly that reason. Two of them are open because the
> vocabulary does not exist in any source I have: one needs a word for stool, one
> needs a word for ear.
>
> Your released subset resolved part of the first of those. That is the specific
> value I am asking for more of: not training data in bulk, but attested clinical
> Kinyarwanda that lets a native speaker author with confidence.
>
> What I would ask for, in order of preference:
>
> 1. Access to the full 5,609 questions under whatever terms you set, including
>    terms that keep them non-redistributable — I can use them to substantiate
>    vocabulary without republishing them.
> 2. If the full set is not available, a pointer to any Kinyarwanda CHW training
>    or patient-facing material that RBC or the Community Health Desk can share.
>    The 2011 IMCI/community case management trainer's guide would be
>    particularly valuable.
> 3. A conversation, if you would find it useful, about what would count as fair
>    value exchange here. The obvious offer is that the resulting corpus and the
>    triage taxonomy behind it are openly licensed and returned to Rwandan use,
>    with Digital Umuganda's and RBC's contribution credited; I am open to being
>    told that is not enough, or not the right thing.
>
> I am happy to send the project's licensing analysis and the current speaker
> brief so you can see exactly what would be built and under what terms.
>
> With thanks for the work and for making the subset open,
>
> Bayizere Marius
> mariusbayizere119@gmail.com

---

## The eight questions — answerable in five minutes

**This is the highest-value thing to send, and it is much smaller than the data
request.** Eight words and idioms that do not exist in any source available to the
project. Each has stalled a specific row for weeks; none needs a dataset, a licence
or an agreement — only someone who speaks Kinyarwanda and has worked in a Rwandan
health post.

Send it as its own short message, or as an appendix to the access request below. A
single reply resolves more than the full 5,609 questions would.

> **Eight Kinyarwanda questions from a clinical triage corpus**
>
> Each of these is a word or idiom we could not confirm from any written source, so
> we have left the row blank rather than guess. Short answers are perfect — a word
> or a phrase, however a patient would actually say it.
>
> 1. **Stool.** The everyday word a patient would use — specifically for **black,
>    tarry stool**. We have `impiswi` for diarrhoea and `kwituma` as the verb, but
>    no ordinary noun.
> 2. **Sunken eyes.** How a Rwandan describes **a child's eyes having sunken** in
>    dehydration. We have `amaso` for eyes but no verb we can confirm.
> 3. **Ear.** The ordinary word, and how **a child says their ear hurts and is
>    running**. We could not confirm any ear term at all.
> 4. **A limb bent out of shape after a fall** — the visible deformity, not the
>    diagnosis "fracture". We have the fracture vocabulary and not the deformity.
> 5. **Light hurting the eyes** (photophobia), as a patient with a severe headache
>    would say it. We have no word for light we can confirm.
> 6. **Breathless when lying flat.** We need the **positional** sense — flat versus
>    propped up — rather than "when I go to bed" as a time of day. Does
>    `iyo nryamye` carry that, or is there a better way to say it?
> 7. **Medicine having run out**, as distinct from simply not having any. A patient
>    who finished a course and one who never collected it are different cases for
>    us, and we could not find a verb that separates them.
> 8. **The cervix**, as distinct from the womb — the everyday word a woman would use
>    asking for a cervical screening appointment. The only term we found,
>    `nyababyeyi`, is used for the womb in both the examples we have.
>
> If any question is malformed — if a distinction we are drawing does not exist in
> Kinyarwanda, or is not one a patient would make — that is just as useful an
> answer, and we would rather hear it than build the distinction into the data.

**That last paragraph matters.** Two of the seven may be false distinctions
imported from English clinical writing rather than real Rwandan usage — the
positional/temporal split in 6 and the ran-out/never-had split in 7. Being told so
is a result, not a failure, and it stops the corpus encoding a category that only
exists in the source language.

Which rows each question unblocks, for your reference rather than theirs:

| question | rows |
|---|---|
| 1 stool | `GI03` both persons — melaena, blocked since the first gastrointestinal batch |
| 2 sunken eyes | `GI04` third — `yinjiye` has one corpus hit and it means oxygen entering the lungs |
| 3 ear | `PA08` first — the oldest block in the project |
| 4 deformed limb | `HT05` first — the draft says "broken", the concept says "deformed" |
| 5 light | `NE05` first — drafted carrying two of its three signs |
| 6 lying flat | `CC04` first — orthopnoea is the entire clinical signal in that concept |
| 7 ran out | `CC06`, `CC07` — both accepted saying "I have no X medicine" instead |
| 8 cervix | `PR07` first — the draft says "examine my womb", a different request |

---

## Re-checked against the RBC corpus — 2026-09-04, AFTER the questions were sent

`review/attestation/rbc_kinyarwanda_health.txt` was added as the `rbc` tier of
`attest.py` on 2026-09-04: 2,509,528 characters of Rwanda Biomedical Centre health
and CHW training curriculum, CC BY 2.0, provenance in that directory's `SOURCE.md`.
All eight questions were re-run against it.

**The questions were already sent, so nothing here is withdrawn.** Read this as how
to interpret the replies: for the three marked ANSWERED, a reply that disagrees with
the corpus is more interesting than one that confirms it, and should win — the
corpus is written curriculum, the contacts are speakers.

| # | question | after the RBC corpus |
|---|---|---|
| 1 | stool | **ANSWERED** |
| 2 | sunken eyes | still open — and the evidence against the sign got stronger |
| 3 | ear | **partly** — the noun exists; the rest of the row does not |
| 4 | deformed limb | still open, unchanged |
| 5 | light | **partly** — the noun exists; photophobia does not |
| 6 | lying flat | **ANSWERED**, including the distinction the question asked about |
| 7 | ran out | **ANSWERED** |
| 8 | cervix | **ANSWERED**, and the ambiguity that caused it is resolved |

### 1. Stool — answered, and more fully than asked

`amabyi` is attested as a **gloss of `umwanda`**, twice: *"Utwo dukoko dukwirakwizwa
mu mwanda (amabyi)"*. `umukara` is attested 9 lines, and once **on stool directly**:
*"atuma uruhinja rwituma ya mabyi ya mbere y'umukara"* — the newborn's first black
stool. Noun, colour, and a precedent for combining them.

Blood-in-stool is attested repeatedly and **inside RBC's own danger-sign list**,
which appears three times in the curriculum: *"Kwituma umusarane uvanze n'amaraso"*.
Also *"Kwituma ibivanze n'amaraso"*, *"Kwituma umusarani uvanzemo amaraso"*,
*"kwituma umwanda uvanzemo amaraso"*, *"Kuva amaraso umaze kwituma"*.

**A noun nobody had considered: `umusarane` / `umusarani`.** It is used as the head
noun in those danger-sign lines. Elsewhere in the corpus the same string means
latrine, so this is a lead for the speaker and not a reading I can make.

### 6. Lying flat — answered, and the positional/temporal question is settled

*"Kunanirwa guhumeka igihe umurwayi **aryamye agaramye** kandi **adaseguye**"* —
inability to breathe when the patient is lying supine and not propped up. **That is
orthopnoea, defined in the national CHW curriculum**, and `aryamye agaramye` is
explicitly positional, with `adaseguye` carrying the propped-up contrast the question
asked for. Corroborated by *"Iyo umwana aryamye agaramye"*.

So question 6's distinction is **real in Kinyarwanda and already lexicalised**. What
remains for `CC04` is only the first-person inflection — `nryamye` is still attested
nowhere — but the construction to inflect is now known, which it was not.

### 7. Ran out — answered

`gushira` in the medicines sense: *"ku miti igiye **gushira**"* (medicines about to
run out) and *"Inombe (RUTF) y'icyumweru yatahanye imaze **gushira**"* (the week's
RUTF has run out). `yarangiye` too: *"gusaba imiti no gusubiza imiti **yarangiye**"*.

The earlier flag was that `yarangiye`'s only two hits meant "when all that is
finished", a different sense. Both verbs now appear in the supply sense. `CC06`/`CC07`
can be rewritten from "I have no X medicine" to the running-out sense.

### 8. Cervix — answered, and the ambiguity is resolved rather than tolerated

**`inkondo y'umura`** is the cervix: 41 RBC lines and 3 CHW records, and it appears in
`PR07`'s exact concept — *"isuzuma ry'ibimenyetso bibanziriza kanseri y'inkondo
y'umura ku badamu bafite hagati ya (30-65)"*, cervical screening for women 30–65.

And `nyababyeyi`, the term the question worried about, is settled as the **womb**:
*"Agapira gashyirwa muri nyababyeyi"* (an IUD placed in the uterus), *"kanseri yo muri
nyababyeyi"*. **They are two organs with two words.** The draft that said "examine my
womb" was wrong for the reason suspected, and the right word now exists.

### 3. Ear — the block moves rather than clears

**`ugutwi` is attested**, which it was not anywhere before: *"indwara zitandura
zifata ibice bitandukanye by'ugutwi"* and *"Gukomereka ingoma y'ugutwi"* (eardrum
injury). `indwara z'amatwi` is a standing curriculum topic with its own lesson unit.
The old finding — *"no ear term exists in the approved vocabulary at all"* — no
longer holds.

Two of the row's three elements are still unsubstantiated, so `PA08` stays held:

- **The possessive agreement.** `kwanjye` appears **0 times** in the corpus, so the
  class-15 agreement the draft depends on is still a guess.
- **Ear discharge.** No line pairs an ear term with `amashyira`, `hasohoka` or any
  discharge word. The `amazi` problem from the original analysis is unchanged.

Note the CHW-corpus warning still applies to `amatwi`: 182 RBC hits, and the ones
sampled are `gutega amatwi`, "to lend an ear". The anatomical sense lives in
`ugutwi`, not in the hit count.

### 5. Light — the noun exists, the sign does not

`urumuri` is attested 15 lines. **Every one is physical light** — sunlight
degrading condoms, torches in an equipment list. `umucyo` appears twice and both are
lightning in a storm-safety passage. **No line connects light to the eyes, to pain,
or to headache.** So `NE05` gains its noun and keeps its block: photophobia as a
symptom is not attested, and question 5 is still worth a speaker's answer.

### 2. Sunken eyes — still blocked, and the negative is now much stronger

`amaso` is richly attested (137 RBC lines, 30 CHW). **Not one is a sunken-eye
dehydration sign.** Searched directly for the sign and for the sign-lists it would
appear in; the curriculum's dehydration language is `kubura amazi mu mubiri` and
`umwuma`, never the eyes. `yinjiye` remains wrong-sense — in RBC it is a head
submerged in water (the drowning definition) and a dose of medicine entering.

**This changes the standing of the question.** The earlier note said a 524-row
sample could not tell whether the sign is simply not how Rwandans report
dehydration, or whether the sample was too small. It is now **two independent
corpora**, one of them a 28,621-line *national CHW curriculum that teaches childhood
diarrhoea in detail*, and neither uses it. That is no longer a sampling artefact.

**Question 2 may be malformed**, in exactly the way the covering note invited — the
distinction may be imported from IMCI's English rather than used in Rwandan
practice. If a contact says so, `GI04` should lose the sign rather than gain a word,
and the concept keeps the two signs it can substantiate.

### 4. Deformed limb — unchanged

`kwavunitse` is **still attested nowhere**, in any of the five tiers. `ukuguru` is
attested (leg), and the CHW hits are all fracture framing — *"umwana aguye hasi
akaba avunitse ukuguru"* — which is the diagnosis, and is what pulled the draft off
its own concept in the first place.

One lead, and it is only a lead: **the deformity stem is attested, on a different
body part.** `-goramye` is speaker-approved in `EX35` and v1 — *"umunwa wagoramye"*,
a twisted mouth after stroke. Whether it extends to a limb, and with what class
agreement, is a speaker question and not one the corpus answers.

---

## Notes before sending

**1. The licence question is settled — the email is clear to send.**
`docs/licensing.md` Q5 (2026-09-03) determines that **WHO material does not force
CC BY-NC-SA**: no WHO-derived expression reaches the corpus (verified — the output
has five columns, none WHO-derived; nothing in the generator reads the anchor
file; 0 of 67 anchor glosses appear among the 46 English corpus phrases). The
target is **CC BY 4.0**, conditional on running the clinician session
concepts-first and a lawyer's sign-off before release.

So "openly licensed and returned to Rwandan use" in the draft is accurate. If
asked to be specific, say **CC BY 4.0, pending clinical re-derivation and legal
review** — and do not offer CC0, which the WHO question is not settled enough to
support.

**2. The figshare subset needs no permission.** It is CC BY 4.0 and can be used
today with attribution. **Nothing in this request blocks that work** — do not
wait on a reply to take `kwituma` to the speaker. Note the GitHub mirror of the
same CSV carries no licence; cite the figshare DOI.

**3. Do not ask for Waxal.** It contains no Kinyarwanda at all, and asking would
signal the abstract was read rather than the dataset.

**4. The ask is deliberately modest on redistribution.** Point 1 accepts
non-redistributable terms on purpose: substantiation only needs read access, and
asking for redistribution rights invites a harder assessment for something the
project does not actually need.
