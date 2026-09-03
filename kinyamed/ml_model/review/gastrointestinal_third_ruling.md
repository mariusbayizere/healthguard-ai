# Gastrointestinal third person — nine drafts awaiting your ruling

Nine of the fourteen third-person rows. Two are already accepted (GI01, GI02),
two are held (GI03 on the stool word, EX17 pending the EX16/EX17 collapse), one
went `applies=no` with GI08.

**Rule each one individually.** Every draft renders across all eight relations in
`gastrointestinal_third_render.csv`, 88 rows — read a phrase there before
accepting it here, because a phrase can be fine with `Umwana wanjye` and wrong
with `Umukecuru`.

New since these were drafted: `review/attest.py` and the 524 CC BY 4.0 CHW
questions. **Every uncertain word below was re-checked against real Rwandan
clinical Kinyarwanda.** That is new evidence, and on one draft it points the
opposite way from the draft.

---

## The one that changed: GI04

```
draft   {REL} afite impiswi zikomeye kandi amaso ye yinjiye.
gloss   watery diarrhoea with sunken eyes and very slow skin pinch
```

The old note carried two flags. **The first clears, the second stands, and a
third has appeared.**

| element | attestation | verdict |
|---|---|---|
| `impiswi zikomeye` | your own EX12 first, verbatim | fine |
| `amaso` | **now attested — 20 distinct CHW/clinician records.** The old flag said it appeared only in unapproved draft D005 | **flag cleared** |
| `amaso ye` (possessive) | attested 5x in the CHW corpus, and matches your CR03/OB07 pattern | fine |
| `yinjiye` | **1 hit in 445k characters, and it is about oxygen entering the lungs** — *"iyo yinjiye ibasha kwica utwo dukoko"*. Not the eye sense at all | **not substantiated** |

So the head noun is now solid and **the verb is not**. Worth knowing: 524 CHW
questions covering ICCM and childhood diarrhoea describe dehydration as
**`kubura amazi (menshi) mu mubiri`** — lacking water in the body — and never
once by sunken eyes. That may be how the sign is actually reported in Rwanda, or
it may be an artefact of a 524-row sample; I cannot tell which from this.

The second original flag is unchanged: **the very slow skin pinch is an
examination manoeuvre a caregiver cannot perform or report**, so the draft
carries two of the concept's three signs regardless of wording.

**My recommendation: do not accept this one.** `needs_clinician`, or held, with
the draft left in `suggested_kinyarwanda` as the record. Substituting a different
verb for `yinjiye` would be me inventing Kinyarwanda, which is what rules 5 to 8
exist to stop — and I have no attested candidate to offer. If you know the
ordinary way to say a child's eyes have sunken, that is the missing piece and it
has to come from you.

---

## The seven that substantiate

All uncertain elements checked; nothing came back unattested. Still yours to
rule — attestation says a form is real, not that it is the right thing to say.

| id | draft | basis, and what to check |
|---|---|---|
| **GI05** | `{REL} afite impiswi zirimo amaraso.` | Direct transform of your accepted first person. `zirimo` is in your own GI05 first and in 7 CHW records. **The `zirimo` concord flag you accepted on the first person rides along unchanged** — it is recorded, not resolved. |
| **GI06** | `{REL} amaze ibyumweru birenga bibiri arwaye impiswi.` | `{REL} amaze ibyumweru birenga bibiri` is your CR06 third verbatim. `ndwaye`->`arwaye` is regular and `arwaye` is the single most common clinical verb in the CHW corpus (122 hits, 50 records). |
| **GI07** | `{REL} arababara cyane mu nda kandi ububabare ntibuhagarara.` | `arababara cyane mu nda` is your EX38 third verbatim. **Carries the class-14 `ntibuhagarara` flag from your first person** — attested only in your own phrase, 0 in the CHW corpus, so that uncertainty is untouched by the new evidence. Alternative following OB02: `inda iramubabaza cyane`. **This phrase properly contains EX14**, so `phrase_components` unions them into one phrase group — intended behaviour. |
| **EX12** | `{REL} amaze iminsi itatu arwaye impiswi zikomeye.` | The `{REL} amaze <duration>` frame is yours from CR06 and OB04 third. |
| **EX13** | `{REL} arakomeza kuruka kandi ntashobora kurya.` | `sinshobora`->`ntashobora` is your EX01 third and appears in your own phrases 4x. `arakomeza` is regular; note it is thin in the CHW corpus (1 record), so it rests on your EX01 pattern rather than on external attestation. |
| **EX14** | `{REL} arababara cyane mu nda.` | Your EX38 third verbatim; same construction as your EX05 third `arababara cyane mu gituza`. Contained by GI07 above. |
| **EX15** | `{REL} araruka cyane kandi yumva afite intege nke.` | `araruka` from OB10 third, `numva`->`yumva` from EX03 third. `yumva` 52 hits / 28 records and `intege nke` 7 hits / 6 records in the CHW corpus, both alongside your own use. |
| **EX16** | `Iyo {REL} amaze kurya, yumva inda itameze neza.` | The `Iyo {REL} a-..., ...` frame is your EX07 third in shape. **`{REL}` sits mid-phrase** — the shape that silently broke attribution twice; the sweep covers it now and passes. **Do not rule this one before the EX16/EX17 collapse**: if EX17 becomes a second phrasing of EX16, this concept has one third-person row and not two. |

That is eight rows in the table — EX16 is listed among them but is the one to
hold, so seven are genuinely rulable today.

---

## Order I would take them in

1. **EX14, then GI07.** EX14 is the shortest and GI07 contains it; ruling the
   contained phrase first makes the union concrete rather than theoretical.
2. **GI05, GI06, EX12, EX13, EX15** — direct transforms of phrases you have
   already accepted, so the only question is the transform.
3. **EX16 — hold** until the EX16/EX17 collapse is executed.
4. **GI04 — rule, but not accept.** `needs_clinician` or held; see above.

## Two things this sheet does not do

**It does not accept anything.** Every row above still has `your_phrasing` empty
and `source` blank. Rule 8 stands: a draft is a suggestion, never an approval.

**Attestation is not endorsement.** A word appearing in the CHW corpus means a
Rwandan health worker used it in a real clinical context. It does not mean a
*patient* would say it, and that corpus is CHW-to-clinician register throughout —
professional, with weights and temperatures in it. For a third-person `{REL}` row
the register gap is small, which is why the check is worth running here. It would
be worth much less on a first-person row.
