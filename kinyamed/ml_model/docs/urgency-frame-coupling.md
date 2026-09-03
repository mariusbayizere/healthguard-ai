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

**Onsets never escalate** — a time expression is orthogonal to urgency, and
`kuva hashize icyumweru` on a CRITICAL phrase is clinically interesting rather
than contradictory. So the whole question is contexts, closers and two openers.

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
