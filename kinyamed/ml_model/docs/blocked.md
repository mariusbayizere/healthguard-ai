# Blocked — questions only a person can answer

Per `docs/ENGINEERING_SPEC.md` L16. Each entry names the question, the rows it gates, and what
was already checked. The maintainer answers in batches.

---

## 1. Cross-arm ruling disagreements — 25 rows over 18 concepts

**Re-derived from disk 2026-09-08**, not recalled. Reproduce with a hold-column
diff of the three briefs against the spine.

These are NOT six, and they are not one kind of thing. Splitting them by kind is
the point: two groups need no speaker at all, and only the third is a real
question.

### 1a. Both non-Kinyarwanda arms lifted the same spine hold — 11 rows, 7 concepts

`CR05` third, `GI03` third, `IF01` f/t, `IF03` f/t, `IF04` f/t, `IF06` f/t,
`OB12` third.

| | reading |
|---|---|
| **Kinyarwanda** | held — the block is a missing or unvalidated Kinyarwanda WORD (a term for wheeze, a noun for stool, one word for sweating, the register of a phrase for painful urination) |
| **English and French** | lifted, independently, on the same reasoning: a block on a Kinyarwanda word cannot bind a language that has the word |

**Not a question for anyone.** Two arms reached this separately, which is the
strongest evidence available that these are word blocks rather than concept
blocks. Recorded so the divergence is visible, not to be answered.

### 1b. Stale English holds that B1 has not yet cleared — 6 rows, 4 concepts

`CC04` first, `EX40` third, `GI04` third, `HT05` f/t.

| | reading |
|---|---|
| **Kinyarwanda** | authored and unheld; the vocabulary block that caused each hold closed on 2026-09-05 |
| **English** | still held, because `hold` is not a regenerated column and was seeded before those blocks closed |

**Engineering, not judgement.** These clear when the remaining staleness items
are applied. Listed so they are not mistaken for disagreements.

### 1c. Genuine concept-level disagreements — 8 rows, 7 concepts

**This is the group that goes to the English and French speakers with the
flagged rows.**

| concept | Kinyarwanda | English | French |
|---|---|---|---|
| `NE06` first | applies, unheld | **held** — can a patient who accurately reports their own new confusion be meaningfully confused? | **held**, same reasoning |
| `OB03` f/t | applies, unheld, flagged `needs_clinician` | **held** — cord presentation wording must be validated before anything generates | not held |
| `PA01` third | applies, unheld | **held** | not held |
| `PA03` third | applies, unheld | **held** | not held |
| `PA04` third | applies, unheld | **held** | not held |
| `PA05` third | applies, unheld | **held** | not held |
| `EX27` first/third | first authored and unheld; third held for a clinician | **held**, and the English pass separately recorded `EX27` collapsing into `EX26` | third lifted, both drafted and worded apart |

**Two of these are asymmetric in a way worth stating.** `NE06` is the only one
where English and French agree with each other against the spine, and it is a
claim about the concept rather than about any language — which is why the French
arm carried it across deliberately. The `PA` group and `OB03` are English-only
and have no French counterpart, so they are one arm's judgement, not two.

**`EX27` is a record conflict, not a ruling.** `english-review-pass.md` reports
`EX27` going `applies=no` as part of the `EX26` collapse; the spine has both
concepts `applies=yes` with `EX27` first authored. The French arm drafted both
and worded them apart rather than ruling it. Nobody has ruled the collapse, and
until someone does, the English row should not sit on text belonging to a third
concept.

### What we are NOT asking, and why the asymmetry matters

The Kinyarwanda rulings in 1c have corpus evidence behind them: an authored
phrase, a speaker's judgement, and in several cases a recorded reason. The
English and French holds do not — no English or French speaker has reviewed
either arm, and both are `machine_reviewed` throughout. So the arms probably
need to follow Kinyarwanda here.

**That is a speaker's call and not ours to make.** These go to the English and
French speakers alongside the flagged rows, with both readings as above, and
they answer.

---

## 2. Relation-set wording, English and French

**Ruled 2026-09-08: ship as `machine_reviewed`**, the same provenance as the
phrases they attach to, rather than dropping 97 English and 100 French
third-person rows that carry `{REL}`.

One distinction for the flag list, because it is not quite uniform:

- **Set MEMBERSHIP mirrors the speaker's Kinyarwanda rulings** one for one, in
  the same order. That half is speaker-derived.
- **The WORDS come from v1's `SUBJECTS` slot**, which was machine-drafted.

So the reviewers should be asked about the words, not the sets. `Umukecuru` is
rendered `My grandmother` because v1 chose that; whether a Rwandan English
speaker would say grandmother, old woman, or something else is open. The
gender-neutrality of `My neighbour` inside the obstetric set is a separate open
question already recorded against `PR05`.

---

## 3. Swahili — relation terms and frame fragments

`RELATIONS` in `vocabulary_v1.py` has a `kinyarwanda` key and nothing else, so
**no Swahili relation term exists anywhere in the project** and every
third-person `{REL}` in the Swahili brief has nothing to substitute. A
12-row sheet is with the speaker.

Frame fragments — openers, onsets, contexts, closers — are also unauthored for
Swahili, English and French. `OPENERS`, `CONTEXTS` and `CLOSERS` exist for
Kinyarwanda only; `ONSETS` and `SUBJECTS` survive from v1 as machine drafts and
`SUBJECTS` is unused under the utterance form.

**No language but Kinyarwanda can generate a row today**, whatever its phrase
count. This gates B5.

---

## 4. Code-switching — the model itself (gates B4)

`docs/code-switching-design.md` is design only. Five questions there have no
answer without speakers, and one has no answerable form without observed data:

1. Does whole-phrase alternation occur, or is insertion the dominant pattern?
2. Which medical terms are actually switched, and which are simply borrowed?
3. What noun class does each inserted English or French noun take, and what
   agreement does it trigger? **This is the one where a speaker's judgement
   cannot be substituted for.**
4. Are `kw↔sw` and `en↔fr` real in this setting? Neither is in the current six
   pairs and nobody established that the six reflect Rwandan usage.
5. Roughly what proportion of patient utterances contain any switching? The
   48% in v1 was a generation target, not a measurement, and **has no
   answerable form until someone transcribes Rwandan patients describing
   symptoms.** It should be described as a guess wherever it appears.

The worksheet that makes 2 and 3 resolvable in one exchange is
`review/code_switching_worksheet.csv`.

---

## 5. Kinyarwanda ROUTINE SMS can exceed one segment

**Not urgent, and not a correction to the speaker's wording.** Logged for the
next exchange rather than acted on.

Measured 2026-09-08 with the authored templates:

| language | urgency | 5-char name | 22-char name | 40-char name |
|---|---|---|---|---|
| Kinyarwanda | ROUTINE | 133 | 148 | **168 — two segments** |
| Kinyarwanda | CRITICAL | 116 | 131 | 149 |
| Swahili | ROUTINE | 98 | 115 | 147 |
| Swahili | CRITICAL | 110 | 127 | 147 |

The GSM-7 single-segment limit is 160 characters; beyond it a message bills as
two. **Swahili has headroom at every name length. Kinyarwanda ROUTINE is the
only template that spills**, and only for names around 40 characters, which are
uncommon but not impossible in Rwanda.

**The question for the speaker, when there is a next exchange:** is there a
shorter way to say the ROUTINE sentence that they would still use? About ten
characters would close it.

**What we will not do:** shorten their sentence ourselves. The failure mode is a
second SMS segment, which costs money and nothing else; a truncated or reworded
patient instruction costs meaning. If no shorter phrasing exists, the correct
answer is to accept two segments for long names and say so in the deployment
runbook.

Note the earlier framing of this as a *Swahili* boundary was wrong; Swahili is
the language with room to spare.
