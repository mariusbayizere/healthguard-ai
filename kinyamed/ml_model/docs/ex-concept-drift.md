# EX concept drift — what the speaker's rewrites did to the v1 concepts

**Re-opened 2026-09-04 at the speaker's instruction.** Two collapses were ruled
against phrases that no longer mean what their v1 originals meant. Both were
re-examined from the v1 phrase forward. **Both stand — and both stand on the
rewrite, which is what the original rulings failed to say.**

## Method

The v2 brief's EX rows carry no v1 phrase. The link is
`review/speaker_brief_kinyarwanda.csv`, the v1 brief, whose `VALIDATE existing`
rows pair `original_corpus_phrase` with the speaker's first-pass `speaker_phrase`.
Joining on the normalised first pass links 35 of 47 EX ids directly; the rest were
resolved by domain and urgency against the same file. Every chain below is
`v1 corpus phrase -> speaker's first pass -> phrase today`, read off disk.

---

## 1. The three-way rotation — EX29, EX30, EX31

This is the finding, and it is bigger than either collapse. **The rewrites did not
lose concepts. They moved three concepts across three ids.**

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

**Nothing was lost, and that is checkable rather than reassuring.** `CR07` already
existed independently in `concepts.py` with the gloss **"short mild cough, no
fever"** and the anchor **"IMCI: cough, no pneumonia (green)"** — which is v1 EX29's
concept exactly. EX30's rewrite produced a phrase for it. `EX31` carries the runny
nose. `EX29`'s id carries what IF07 described.

### 1a. `IF07 -> EX29` — STANDS, on the rewrite

```
the ruling said   IF07 ("a slight fever since yesterday but otherwise well",
                  IMCI: fever, no danger sign) and EX29 are one concept,
                  because EX29 "states exactly that"
against v1        FALSE. v1 EX29 is "mild cough, no fever" - IF07's presenting
                  sign is the one v1 EX29 explicitly EXCLUDES
against today     TRUE. The rewritten EX29 is "mild fever one day, otherwise
                  well", which is IF07 word for word in substance
```

**Verdict: the collapse stands.** The corpus contains phrases, not v1 glosses, and
the phrase that exists says what IF07 said. Keeping both would put two phrases of
one concept into the inventory, which is the near-duplicate leak
`near_duplicates.py` and `test_leakage.py` exist to catch — the original argument,
still sound. **But it is sound about the rewrite, and the ruling presented it as a
fact about EX29 as such.**

### 1b. `EX30 -> CR07` — STANDS, on the rewrite

```
the ruling said   EX30 and CR07 are one concept; CR07 carries the anchor
                  "IMCI: cough, no pneumonia (green)"
against v1        FALSE. v1 EX30 is "mild runny nose". Collapsing a runny-nose
                  concept into a cough concept would have deleted a sign.
against today     TRUE. The rewritten EX30 is "mild cough, no fever", and CR07's
                  gloss is "short mild cough, no fever" - the same sentence
```

**Verdict: the collapse stands**, and it is the tidier of the two: the rewrite
landed EX30 on a concept that already existed with that exact gloss, so the collapse
removed a genuine duplicate. **The runny nose survives on `EX31`** — which is the
only reason no sign was lost, and it was nowhere in the ruling.

### 1c. What this actually costs

Not the concepts — those are all present. Two things:

- **An id no longer means what its v1 phrase meant**, so any reasoning that reaches
  for `phrase_review_sheet.csv` (`E098 amazuru atemba yoroheje`,
  `E099 inkorora yoroheje nta muriro`) or the v1 brief and assumes the id still
  carries it will be wrong. Those rows are history, not error, and they are the
  evidence this rotation happened at all.
- **Two rulings were recorded as facts about a concept when they were facts about a
  rewrite.** Had either v1 phrase been the live one, the same ruling would have
  deleted a sign.

---

## 2. The six tier-2 concepts — none rests on a rewrite

`EX18`, `EX22`, `EX33`, `EX34`, `EX35`, `EX36` each absorbed a concept whose
distinguishing axis their phrase does not carry. Checked the same way, and the
result is different from section 1: **their v1 meanings are intact, so those
collapses rest on the phrase the ruling actually examined.**

| | v1 | first pass | today | drift |
|---|---|---|---|---|
| `EX18` | `amaraso menshi adahagarara` | *unchanged* | *unchanged* | **none** |
| `EX22` | `igikomere cyanduye kitukura kandi kirimo amashyira` | *unchanged* | *unchanged* | **none** |
| `EX33` | `kugagara no guhinda umushyitsi` | `yagagaye kandi ahinda umushyitsi` | `{REL} yagagaye kandi **arimo** guhinda umushyitsi.` | toward the absorbed concept |
| `EX34` | `uruhande rumwe rw'umubiri rutagikora` | `rwaramugaye` (*became disabled*) | `ntirukora` (*does not work*) | drifted, then returned |
| `EX35` | `kutabasha kuvuga neza n'umunwa wagoramye` | *preserved* | *preserved* | none |
| `EX36` | `uburibwe buke mu mutwe budakabije` | `umutwe urandya ariko ntabwo cyane` | *same* | none |

**EX18 and EX22 did not change at all** — first pass and today are byte-identical to
each other, and mean what v1 meant. `HT01`'s collapse was ruled on exactly the
phrase that is in the corpus now, and its reasoning is untouched by any of this: the
attestation corpus could not settle whether a patient frames bleeding as
"pressure applied and failed", and the axis was never in `concepts.py`.

**`EX33` moved slightly TOWARD `NE01`, not away.** `arimo` — the progressive, "is in
the process of" — is in neither v1 nor the first pass. NE01's axis was *continuous*
convulsion. So the rewrite partially supplies the axis the collapse was accused of
dropping. **Not a claim that the axis is carried**, only that the drift runs the
helpful way and the concern is smaller here than for the other three.

**`EX34` is the one to watch, and it self-corrected.** The first pass
`rwaramugaye` — *became disabled/crippled* — is a permanent-disability claim that v1
did not make and that a sudden stroke presentation does not support. The authored
form went back to `ntirukora`, which is v1's *no longer works*. Worth recording
because it is the one place a rewrite made a concept **worse** and the speaker caught
it themselves.

### The open gap, which is not a drift

**`EX22` has no second phrasing and `HT06`'s axis is therefore unrepresented.** The
collapse ruled "keep the swollen wording as a second phrasing", the slot is empty
because the only candidate was an unaccepted machine draft, and
`second_phrasing_optional` feeds `PHRASE_VARIANTS` into the corpus. So *swollen*
versus *infected* currently exists nowhere. Already item 3 of section 7's blocked
list; repeated here because this is where someone will look for it.

---

## 3. What to carry forward

**The failure mode is general, and it is not about these two rulings.** A collapse
compares two phrases and asks whether they say the same thing. That is the right
test. But the *record* of the ruling names concepts, and a concept id is stable
while its phrase is not — so a ruling written as "IF07 and EX29 are one concept"
silently becomes a claim about whatever EX29 says next.

**Both collapses stand.** Section 1 changes their justification, not their outcome,
and the justification is now written down. **Where a ruling turns on a phrase, say
which phrase**, and quote it — the two rulings that needed re-opening are the two
that named only ids.

Worth a check, not implemented: for every EX concept, does the phrase in the corpus
still mean what `phrase_review_sheet.csv` says the original meant? The rotation in
section 1 was found by accident, while listing drift for the English arm. Three ids
moved and nobody noticed for a month.
