# Urgency/frame coupling — should the frame set depend on the label?

**Design proposal, 2026-09-03. Nothing implemented.** Raised when HT08 was ruled:
a ROUTINE phrase — a small cut that has stopped bleeding — was rendering as

> *Muganga, mfite igikomere gito kandi amaraso yarahagaze kuva ijoro ryashize
> kandi **sinshobora gusinzira**. **Ndakeneye ubufasha vuba**.*
>
> "Doctor, I have a small cut and the bleeding has stopped since last night and
> **I cannot sleep**. **I need help quickly**."

labelled ROUTINE. The frame contradicts the label, and the label is the target.

---

## 1. The slot inventory, and which members escalate

```
OPENERS   6   ''  Muganga,  Muraho,  Nyabuneka,      | Mfasha,  Ndakeneye ubufasha,
ONSETS   10   '' + 9 time expressions                | (none escalate)
CONTEXTS  5   ''  kandi ndahangayitse                | kandi birushaho kuba bibi
              kandi nta miti mfite                   | kandi sinshobora gusinzira
CLOSERS   5   ''  . Nkora iki?   . Murakoze.         | . Ndakeneye ubufasha vuba.
                                                     | . Mfasha muganga.
                        neutral                      | escalating
```

`6 x 10 x 5 x 5 = 1,500` frame combinations per phrase instance.

~~**Onsets never escalate**~~ — **this was wrong, and section 7 corrects it.** A
time expression is orthogonal to *urgency*, which is what I checked. It is not
orthogonal to *coherence*: a service request has no onset at all, so every "since
X" onset is incoherent against it before any context or closer is added.

## 2. It runs both ways, and the two directions are not symmetric

**ROUTINE with escalating tail** — the case that prompted this. The phrase is the
*only* thing carrying low urgency, so an escalating context or closer can
overwhelm it. Affects every ROUTINE phrase, not just HT08: `CR07` and `EX29` have
identical exposure today.

**CRITICAL with a mild tail** — the mirror, and real:

> *Ndi kuva amaraso menshi kandi ntahagarara. **Murakoze.***
> "I am bleeding heavily and it will not stop. **Thank you.**"

> *Mfite ubushye bunini ku mubiri kandi **ndahangayitse**.*
> "I have a large burn on my body and **I am worried**." — understatement, not
> contradiction.

**The asymmetry that matters is not linguistic, it is capacity.** See §4.

## 3. How many rows this affects

> **The figures in sections 3 and 4 predate the eleven concept collapses.** They
> were computed at 120 concepts and a 1,728,000 target; the corpus is now 115 and
> 1,648,000, and ROUTINE has 117 instances rather than 123. The *conclusions* are
> unchanged — ROUTINE is thin, CRITICAL is not — and section 8 carries current
> numbers. Re-derive before acting on any single figure here.

Rows are not assigned per phrase. `allocate()` gives each family a quota from
`target x language_share x CLASS_SHARES[urgency]`, capped at
`family.combinations`, and `generate()` draws with `rng.sample(...)` — **without
replacement**. No row ever repeats; a family that runs out of combinations simply
under-fills, and the shortfall is redistributed to families with headroom.

So the question is never "how many rows are wrong" — it is **"does each class
still have the capacity to fill its bucket?"**

Projected at full v2 (120 concepts, all rows authored, relation rulings applied):

| class | phrases | instances after `{REL}` | relations/phrase |
|---|---|---|---|
| CRITICAL | 81 | 350 | 4.3 |
| URGENT | 87 | 371 | 4.3 |
| **ROUTINE** | **47** | **123** | **2.6** |

**ROUTINE is already structurally thin, and the relation rulings are why.** Ten
ROUTINE concepts are `NO_RELATIONS` (first person only) and eight more are
`CHILD_RELATIONS` (five relations, not eight). Those rulings are correct — nobody
presents on another's behalf for a medicine refill — but they concentrate almost
entirely on ROUTINE, so ROUTINE gets 2.6 instances per phrase where the other two
classes get 4.3.

Ten family groups draw on each phrase inventory: 4 pure languages + 6
`MIXED_PAIRS`.

| class | needs | capacity now | headroom |
|---|---|---|---|
| CRITICAL | 570,240 | 5,250,000 | **9.21x** |
| URGENT | 587,520 | 5,565,000 | **9.47x** |
| ROUTINE | 570,240 | 1,845,000 | **3.24x** |

## 4. What each option costs

**Option A — ROUTINE drops the 2 escalating contexts and 2 escalating closers.**
Frame falls `1,500 -> 540`.

**Option B — A, plus the 2 escalating openers (`Mfasha,`, `Ndakeneye ubufasha,`).**
Frame falls `1,500 -> 360`.

| | ROUTINE capacity | headroom | verdict |
|---|---|---|---|
| now | 1,845,000 | 3.24x | |
| **A** | 664,200 | **1.16x** | viable, but the margin is gone |
| **B** | 442,800 | **0.78x** | **fails** |

**Option B cannot work.** ROUTINE could not fill its bucket; the shortfall would
redistribute to CRITICAL and URGENT, ROUTINE's share would fall below the 28%
floor in `CLASS_TARGETS`, and `problems()` would fail the build. It would not fail
silently — but it would fail.

**Option A survives on 1.16x, which is too thin to be comfortable.** Any of the
following would push it under: a ROUTINE concept collapsing (four concepts have
collapsed this month), a `NO_RELATIONS` ruling on a concept that currently expands,
or raising the row target. A design whose margin is 16% is one ruling away from a
red build.

**The reverse direction is nearly free**, because CRITICAL has 9.21x:

| CRITICAL restricted | frame | capacity | headroom |
|---|---|---|---|
| drop `. Murakoze.` | 1,200 | 4,200,000 | 7.37x |
| drop `. Murakoze.` + `kandi ndahangayitse` | 960 | 3,360,000 | 5.89x |

## 5. Recommendation

**Do the CRITICAL side. Do not do the ROUTINE side as a frame restriction.**

1. **Restrict CRITICAL (and URGENT) away from trivialising tails** — drop
   `. Murakoze.` and optionally `kandi ndahangayitse` from CRITICAL. Costs 36% of
   a 9x margin and removes the more damaging error: a model that learns
   "*bleeding heavily ... Thank you.*" is CRITICAL has learned the phrase, but a
   model shown that pattern often enough may learn the closer is uninformative,
   which is the opposite of what a triage frame should teach.

2. **Fix ROUTINE by adding frame material, not by removing it.** The right shape
   is a small set of *de-escalating* contexts and closers that only ROUTINE draws
   on — "it is not bad", "I just wanted it checked", "there is no hurry". Three
   such contexts would take ROUTINE from 540 back to about 1,600 under option A's
   restriction, restoring roughly 2.8x. **These have to be authored by the
   speaker**, which is why this is a proposal and not a patch: inventing
   de-escalating Kinyarwanda is exactly what rules 5 to 8 forbid.

3. **If neither happens, leave the frames alone.** The contradiction is real but
   bounded — it affects the tail of ROUTINE renderings, not the phrase, and the
   phrase is what the holdout and the attribution sweep are built around. A
   capacity failure is a worse outcome than an occasionally odd ROUTINE row.

## 6. What would need writing, if this is taken up

Not implemented, but the shape is known:

- `vocabulary.py` gains urgency-keyed slot maps — `CONTEXTS_BY_URGENCY`,
  `CLOSERS_BY_URGENCY` — defaulting to the current sets so **v1 output stays
  bit-identical**. `build_families` already keys on urgency, so the change is
  local to the slot lookup.
- A test that every class still clears its bucket, computed rather than assumed,
  so the 1.16x class of problem fails at test time instead of at generation time.
- The `2,000 rows per phrase` note in `generate_large_dataset.py` and
  `docs/v2-sizing.md` would need revisiting: it reads as a per-phrase guarantee
  and is really a corpus-wide median, which is what made this analysis
  counterintuitive at the start.

## 7. One thing this surfaced that is worth knowing anyway

**A first-person phrase has only 1,500 combinations, and the stated invariant is
2,000 rows per phrase.** No phrase repeats, because sampling is without
replacement and quotas are capped — so a first-person-only concept can never
reach 2,000 rows on its own. The corpus hits its median because `{REL}` phrases
expand over 4 to 8 relations and carry the average up.

That is fine, but it means **"2,000 rows per phrase" is a corpus median, not a
per-phrase property**, and the ROUTINE class — which is where the `NO_RELATIONS`
rulings concentrate — sits furthest below it. Worth stating plainly in
`v2-sizing.md` before someone reads the invariant as a guarantee.

---

## 8. Correction: onsets are not neutral — added 2026-09-04

Section 1 said onsets never escalate and set them aside. That is true of urgency
and false of coherence, which CC09 exposed the moment it was rendered:

> *Muganga, ndashaka kujya kwa muganga kwisuzumisha diyabete **kuva ubu gitondo
> cya kare** kandi birushaho kuba bibi.*
> "Doctor, I want to go for a diabetes check-up **since early this morning** and
> it is getting worse."

**A scheduled review has no onset.** The incoherence is in the onset alone — it
does not need a context or a closer to appear. Nine of the ten onsets are "since
X" expressions and **all nine fail the same way** on a request; only the empty
onset works.

### Which concepts, and this is the part that decides it

The affected set is the **service concepts** — rule 12's category, plus the ten
ruled `NO_RELATIONS` (first person only, nobody presents on another's behalf).
22 concepts. Where they sit:

```
CRITICAL   314 instances,   0 service   ( 0%)
URGENT     371 instances,   0 service   ( 0%)
ROUTINE    117 instances,  75 service   (64%)
```

**Every service concept is ROUTINE**, and they are 64% of it. So the onset problem
lands entirely on the class with the least capacity headroom — the same class the
context/closer restriction was already going to squeeze. The two proposals collide.

### What each option costs

ROUTINE needs 543,840 rows.

| | capacity | headroom |
|---|---|---|
| today | 1,755,000 | 3.23x |
| service concepts: **empty onset only** | 742,500 | **1.37x** |
| that **plus** the section 5 context/closer cut | 339,300 | **0.62x — fails** |
| service: empty **+ 3 authored service onsets** | 1,080,000 | **1.99x** |
| **the full package** (see below) | 1,555,200 | **2.86x** |

**Restricting alone is viable but thin; restricting twice fails.** Empty-onset-only
takes a service phrase from 1,500 frame combinations to 150 — a tenfold cut on
two-thirds of the class. Add the context/closer cut on top and ROUTINE cannot fill
its bucket, the shortfall redistributes, and the 28% `CLASS_TARGETS` floor breaks.

### Recommendation: the additions have to land before the cuts

This is the same conclusion section 5 reached about contexts and closers, now with
a second instance and a sharper edge. **Fix ROUTINE by adding frame material, and
treat every cut as conditional on the additions existing first.**

Concretely, the package that holds at 2.86x:

1. **3 service-appropriate onsets**, authored by the speaker — the sense wanted is
   *scheduled* rather than *since*: "for my appointment", "this month", "as I was
   told to". These are what make a request coherent with a time expression at all.
2. **3 de-escalating contexts and 3 de-escalating closers** — already written into
   `frame_fragments_brief.csv` as English glosses awaiting Kinyarwanda.
3. **Then** apply the cuts: service concepts drop the nine "since X" onsets;
   ROUTINE drops the two escalating contexts and two escalating closers.

Order matters and is not negotiable: applying step 3 before steps 1 and 2 is the
0.62x row.

### What this does not settle

**Whether an onset is incoherent is a property of the concept, not the class.**
CC06 and CC07 — "ran out of ARV medicine", "ran out of TB medicine" — are service-
adjacent but URGENT, and a duration works perfectly on them ("I ran out a week
ago"). They are correctly outside the 22. But that means the restriction cannot be
keyed on urgency alone; it needs the service-concept list, which is
`service_speaker_audit.csv` plus the `NO_RELATIONS` rulings. **A
`ONSETS_BY_CONCEPT` map, not `ONSETS_BY_URGENCY`** — unlike contexts and closers,
which really are a class property.

That is a different mechanism from the one section 6 sketched, and it is the reason
this correction is worth its own section rather than a line in section 1.

## 9. A second onset problem: the phrase already carries the time — added 2026-09-05

Found from the English arm while drafting gastrointestinal, and it is **not** the
problem section 8 describes. Section 8 is about concepts that admit no onset at
all — a scheduled review has no *since*. This is about concepts that admit one
perfectly well and **already contain one**, so the slot duplicates rather than
contradicts:

> *I have had bad diarrhoea **for three days** **for three days**.*
> *Maze iminsi itatu ndwaye impiswi zikomeye **kuva hashize iminsi itatu**.*

Both languages, same phrase, same slot.

### It refines section 8's own counter-example

Section 8 sets `CC06`/`CC07` aside — "ran out of ARV medicine", "ran out of TB
medicine" — on the ground that they are service-adjacent but URGENT and **"a
duration works perfectly on them ('I ran out a week ago')"**. That is right about
the concept and insufficient as a test. `CC06`'s drafted English is *I finished my
HIV medicine **several days ago***. The concept tolerates a duration; the phrase
has already spent it.

So the restriction needs **two** questions, not one:

1. Does this concept admit a time expression at all? *(section 8's question)*
2. Does this concept's phrase already carry one? *(this one)*

A concept can fail either and needs the empty onset for either reason.

### Measured

Confirmed in **both** languages — the phrase carries its own duration in
Kinyarwanda and in English independently:

| concept | Kinyarwanda | English |
|---|---|---|
| `EX12` | `maze iminsi itatu ...` | for three days |
| `GI06` | `Maze ibyumweru birenga bibiri ...` | for more than two weeks |
| `CR06` | `Maze ibyumweru birenga bibiri ...` | for more than two weeks |
| `OB04` | `Maze umunsi wose ...` | the whole day |

`EX29` joins them as soon as its English is corrected: the Kinyarwanda says
`umaze umunsi umwe` (one day) while the English candidate is still the stale v1
`a mild cough with no fever`, which carries no time at all — one of the rows the
EX30 collapse left behind.

English-only so far: `PR05`, `CC06`, `IF04`, `NE06`. Of these only `PR05` is a
ruled wording; the rest are unreviewed 2026-08-31 drafts that may lose their time
expression when redrafted.

### The duration cannot be reworded away

It is the axis. `EX12` is three days and `GI06` is more than two weeks — that
difference is the whole distinction between them, and `CR06`'s two weeks is the TB
screening threshold. Dropping the duration to fit the slot would collapse EX12
into GI06 and strip CR06 of its reason to exist.

### `lint_phrases.py` does not catch it, and cannot as written

The onset check tests whether the phrase's **last word** begins an onset:

```python
last = phrase.split()[-1].lower().strip(",.")
if last in onset_heads:      # onset_heads = {"since", "for"}
```

`for three days` ends in `days`, which begins no onset. The check catches
`...and it has been going on since` + ` since yesterday`; it cannot catch a
duration sitting anywhere else in the phrase. Extending it means detecting time
expressions rather than matching a word list, which is worth doing in English and
is a research problem in Kinyarwanda — `kuva` is both *since* and *to bleed*, and
a naive scan flags `EX18`, `EX19` and `EX20` as durations when they are
haemorrhage phrases. **Prefer the declared list over the detector.**

### What it costs, and the good news

Same shape as section 8: restricting an affected phrase to the empty onset takes
it from 1,500 frame combinations to 150.

**But it lands almost entirely outside ROUTINE.** `EX12`, `GI06` and `CR06` are
URGENT and `OB04` is CRITICAL — the two classes section 8's table shows with
headroom, against ROUTINE's 117 instances. Only `PR05` is both service and
duration-carrying, and it is already inside section 8's 22.

So this **adds concepts to the same `ONSETS_BY_CONCEPT` map section 8 concludes is
needed, without deepening the ROUTINE capacity problem that makes section 8's
ordering non-negotiable.** It is a second reason to build that map, not a second
constraint on the same scarce class.

### One wording it makes newly relevant

`PR05`'s English — *This is my first check-up **since** I became pregnant* — was
chosen to keep PR05 out of OB11's phrase group, which it does. It also renders as
*...since I became pregnant since yesterday*. The alternative measured at the time,
*I am newly pregnant and I have not been checked yet*, avoids both: it carries no
time expression and it is not a subsequence of OB11 under the rule that replaced
`PREFIX_UNION_CHARS`. Flagged for the reviewer rather than changed, since the
current wording was a ruling.
