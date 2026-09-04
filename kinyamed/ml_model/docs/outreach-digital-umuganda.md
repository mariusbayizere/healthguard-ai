# Outreach — Digital Umuganda / C4IR Rwanda

Drafted 2026-09-03 off the investigation in `language-resources.md` section 2a.
**Not sent.** The licence question that gated it is settled (`licensing.md` Q5:
target CC BY 4.0), so the draft is clear to send — but read notes 2 and 4 first,
which change what you should ask for.

**Send the seven questions first, and separately.** They cost a reply, not an
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

## The seven questions — answerable in five minutes

**This is the highest-value thing to send, and it is much smaller than the data
request.** Seven words and idioms that do not exist in any source available to the
project. Each has stalled a specific row for weeks; none needs a dataset, a licence
or an agreement — only someone who speaks Kinyarwanda and has worked in a Rwandan
health post.

Send it as its own short message, or as an appendix to the access request below. A
single reply resolves more than the full 5,609 questions would.

> **Seven Kinyarwanda questions from a clinical triage corpus**
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
