# English brief — eight things the spine has moved past

**For the English session. Nothing here is fixed; this is a list to apply.**

Found by the French arm on 2026-09-05, by building a brief off the same spine on
the same day and diffing the two. Every item is re-derived from
`speaker_brief_kinyarwanda_v2.csv` and `speaker_brief_english_v2.csv` as they
stand, not recalled. Re-run this before acting on any of it:

```
python - <<'PY'
import csv
ky={(r['concept_id'],r['person']):r for r in csv.DictReader(open('review/speaker_brief_kinyarwanda_v2.csv'))}
en={(r['concept_id'],r['person']):r for r in csv.DictReader(open('review/speaker_brief_english_v2.csv'))}
print('missing concepts:', sorted({c for c,_ in ky}-{c for c,_ in en}))
for k in sorted(en):
    s=ky.get(k)
    if s and s['hold']!=en[k]['hold']:
        print(k, 'spine_hold', s['hold'] or '-', 'en_hold', en[k]['hold'] or '-',
              'spine_authored', bool(s['your_phrasing'].strip()))
    if s and not k[0].startswith('EX') and s['english_gloss']!=en[k]['english_gloss']:
        print(k, 'GLOSS', s['english_gloss'], '!=', en[k]['english_gloss'])
PY
```

## Item 0 — none of this self-heals, because the builder cannot run

```
$ python review/build_english_brief.py --check
KeyError: 'ububabare bukabije mu gituza kandi sinshobora guhumeka'
```

`ex_to_v1_english()` maps v1 Kinyarwanda phrases to positions using the WORKING
TREE `SYMPTOMS["kinyarwanda"]`, which the in-flight v2 edits have rewritten. It
fails there, before it ever reaches the missing `english` key.

**Fix this first**, or items 1 and 2 cannot be refreshed even though they are in
`REGENERATED`. The French builder's approach is in `build_french_brief.v1_vocabulary()`:
read the frozen v1 from git rather than from a tree being edited for v2, because
a positional mapping into v1 is a fact about the frozen file.

```python
V1_REF, V1_PATH = "HEAD", "kinyamed/ml_model/dataset/vocabulary.py"
```

**Better source landing:** `dataset/vocabulary_v1.py` appeared untracked during
this pass. Its bytes differ from `HEAD:dataset/vocabulary.py` (comments only) but
`SYMPTOMS`, `OPENERS`, `SUBJECTS`, `ONSETS`, `CONTEXTS`, `CLOSERS` and `LANGUAGES`
are **identical** — checked by loading both and comparing the objects. Once it is
committed, import it instead of shelling out to git.

## What refreshes itself and what does not

`REGENERATED` in `build_english_brief.py` is `domain, proposed_urgency,
english_gloss, anchor, relation_set, applies, person_note`. **`hold` is not in
it** — it is seeded once and preserved forever. So:

- item 1 and item 2's gloss half fix themselves on the first successful rebuild;
- items 2–7's holds do **not**, and need `apply_english_drafts.py` or a hand edit;
- item 8 is a drafting error and no rebuild touches it.

---

## 1. `OB13` is missing entirely — the brief is 254/127, the spine is 256/128

`OB13` (*reduced fetal movement*) was added 2026-09-05 when `OB06` was re-ruled.
`build_english_brief.main()` hard-asserts the old shape:

```python
if len(rows) != 254:
    raise SystemExit(f"expected 254 rows on the 127-concept spine, built {len(rows)}")
```

**Apply:** change to 256 / 128, or derive it as the French builder does:

```python
concepts = len({r["concept_id"] for r in rows})
if (len(rows), concepts) != (256, 128):
    raise SystemExit(...)
```

`OB13` must **not** be drafted. It has no phrase in any language and is not
awaiting one — the speaker reports Kinyarwanda has no natural expression for it —
and it is out of generation, subtracted as a concept exactly as `PR02` is. Add it
to `OUT_OF_GENERATION`. The French rows are held and empty; do the same.

(French *can* say it — `le bebe bouge moins que d'habitude` — which is evidence on
the open question the ruling left, and is written up in `french-review-pass.md`.
It is not licence to draft it in English either.)

## 2. `OB06` — the gloss, the hold and the phrase are all on the old concept

The worst of the eight, because the English text is not stale wording but text
describing **a concept that no longer exists at this id**.

| | |
|---|---|
| spine gloss | `fetal demise - the baby has died in the womb` |
| brief gloss | `reduced fetal movement` |
| spine hold | `yes` (re-held for a clinician on the urgency change) |
| brief hold | not held |
| brief phrase, both persons | *"the baby is no longer moving in my/her stomach"* |

`OB06` was re-ruled on 2026-09-05: a Kinyarwanda speaker confirmed `ntagikina`
means the baby **has died**, and that no natural phrase says *reduced movement*.
It moved from URGENT to CRITICAL. The presentation the English text describes is
now `OB13`'s.

**Apply:** rebuild for the gloss; set `hold=yes` on both persons; **withdraw both
English phrases** — they are drafted to a concept that moved. Do not redraft to
fetal demise while the row is held for a clinician on whether fetal demise belongs
in a triage taxonomy at all. The French rows are held and empty for exactly this
reason.

## 3. `HT05` — held here, authored on the spine, and it is the leg

| | |
|---|---|
| spine | `Naguye, ukuguru kuragoramye ariko sinumva ko kuvunitse.` — authored, unheld |
| brief | held, both persons: *"I fell and my arm is bent out of shape."* |

The vocabulary block closed on 2026-09-05 and the speaker's sentence settles more
than the wording:

- **It is the LEG** (`ukuguru`). The gloss says *limb*, the English says *arm*,
  `concepts.py` says *arm*. The speaker chose the leg.
- **It disclaims the fracture inside the phrase** — `ariko sinumva ko kuvunitse`,
  *but I do not feel that it is broken*. That is rule 11's axis stated in
  Kinyarwanda: deformity is what a patient perceives, a fracture is the diagnosis.
  The English carries no such disclaimer.

The English hold's stated reason was that accepting it risked English saying
*deformed* while Kinyarwanda said *broken* under one id. **That risk is gone** —
the speaker resolved it in the opposite direction, keeping deformity and denying
the fracture.

**Apply:** lift both holds, redraft both persons to the leg with the disclaimer.
French is `J'ai fait une chute et ma jambe est tordue, mais je ne crois pas
qu'elle soit cassee.`

## 4. `CC04` first — held here, authored on the spine

| | |
|---|---|
| spine | `Nabyimbye ibirenge kandi sinshobora guhumeka neza iyo ndagaramye.` — authored, unheld |
| brief | held: *"my legs are swollen and I cannot breathe lying down"* (not an utterance) |

The hold turned on one word, `ngaramye` — lying flat — which is what makes the
phrase orthopnoea rather than ordinary breathlessness. The speaker's `iyo
ndagaramye` restores it.

**Apply:** lift the hold, redraft as an utterance with a terminal stop. The third
is already drafted and needs no change.

## 5. `EX40` third — held here, unheld on the spine after the `PA01` ruling

Held while `PA01`'s collapse target was open. **The ruling went against `EX40`**:
collapsing a plain-convulsion concept into a row that conditions it on a
temperature above 40 would have made an IMCI general danger sign depend on a
thermometer. `PA01` went to `EX33` instead, and this row stands as the
fever-plus-convulsion presentation it always was.

**Apply:** lift the hold. The drafted text (*"{REL} is convulsing and has a fever
above 40 degrees."*) is fine as it stands.

## 6. `GI04` third — held here, authored on the spine

| | |
|---|---|
| spine | `{REL} afite impiswi zikomeye kandi yagize umwuma.` — authored, unheld |
| brief | held: *"watery diarrhoea with sunken eyes and the skin stays pinched"* (not an utterance) |

**And the content is wrong as well as held.** Neither the gloss (*severe diarrhoea
with dehydration*) nor the speaker's phrase names sunken eyes or a skin pinch.
Those are IMCI assessment findings a clinician elicits, not what a carer walks in
saying — rule 11's observer limb is about what is directly perceived. The text
came from sheet draft D084 and was never redrafted.

**Apply:** lift the hold, redraft to the gloss. French is `{REL} a une diarrhee
severe et se deshydrate.`

## 7. `EX27` first — held here with stale v1 text; the spine has it authored

| | |
|---|---|
| spine | `mfite umuriro kandi numva mfite imbeho, nkeka ko ari malariya` — authored, unheld |
| brief | held: *"fever and aching all over"* — the v1 English at this position |

The speaker's rewrite moved this concept from aching to **fever, chills and a
suspicion of malaria**. The English candidate is still the v1 text and describes
neither.

**Carries a record conflict — flagged, not resolved by either arm.**
`english-review-pass.md` reports `EX27` going `applies=no` as part of the `EX26`
collapse (*"two more after it (EX27)"*). The spine has **both** concepts
`applies=yes`, with `EX27`'s first person authored. The spine is the record, so
the French arm drafted both and worded them apart. Whoever rules the collapse owns
this; until then the English row should not sit on text from a third concept.

**Apply:** either redraft to the speaker's rewrite and word it apart from `EX26`,
or rule the collapse. Not both languages guessing separately.

## 8. `PA08` first — a defect, not staleness

**This is the one that is wrong rather than out of date.**

The row's `person_note` reads *"usually third (the parent speaks); write first
only if an older child would say it"*. So the **first person is the child speaking
about their own ear**. The brief has:

```
PA08 first   "My child's ear is hurting and there is fluid coming out."
```

That is a carer's report — the **third** person's speaker — sitting in a
first-person slot. It is the error session-state records the Kinyarwanda arm
nearly making on this exact row:

> I proposed `Umwana wanjye afite umuhaha` for PA08 **first** and it was approved.
> The row's `person_note` says *"usually third (the parent speaks) …"* — so that
> sentence is the **third** person, and putting it in the first would have broken
> rule 3. First is `Mfite umuhaha.` **Read the person_note before writing a
> paediatric row**, including when a proposal has already been accepted.

**Apply:** redraft `PA08` first in the child's voice. French is `J'ai mal a
l'oreille et elle coule.`

**And sweep the rest of the domain while you are there.** Every paediatric row
carries that person note, and this arm only checked the ones it drafted. The
French first persons that exist are `PA08` (the child) and `PA09` (the carer,
under rule 12, because a growth-monitoring visit is a service whose requester and
beneficiary differ). Those two being different speakers on adjacent rows is
exactly how this error hides.

**Separately on `PA08`, and it is not staleness:** the speaker's phrase is now
`Mfite umuhaha.`, which **names a condition** and states neither the pain nor the
discharge the gloss claims. `NE05` and the old `OB06` have the same shape.
Session-state calls it a pattern rather than three coincidences: where the
Kinyarwanda is natural it names the illness or its cause, and an English gloss
written from IMCI enumerates signs. Both French rows follow the gloss and keep the
`needs_clinician` flag; English should do the same, consciously.

---

## Not on this list, deliberately

**Holds the English arm lifted that the spine still carries** — `CR05` third,
`GI03` third, `IF01`/`IF03`/`IF04`/`IF06` both persons, `OB12` third. These are
not staleness. Each is a Kinyarwanda *word* block that does not exist in English,
lifted with a stated reason, and **the French arm lifted every one of them on the
same reasoning**. Two independent arms reaching the same lifts is the strongest
evidence available that the lifts are right.

**Holds the English arm added that the spine does not carry** — `NE06` first
(clinical: can a patient who accurately reports new confusion be meaningfully
confused), `OB03` both, `PA01`/`PA03`/`PA04`/`PA05` thirds. Deliberate. The French
arm carried `NE06`'s across, because it is a claim about the concept rather than
about a language.

**`CR03`'s gloss.** The spine still says *blue lips or fingertips* while
`concept_anchors.csv` and `concepts.py` say *blue lips*, so both the English and
French briefs display the un-narrowed gloss next to a lips-only phrase. That is
one record for the Kinyarwanda session to fix, not an English item — see
`review/cr03-gloss-not-narrowed.md`.
