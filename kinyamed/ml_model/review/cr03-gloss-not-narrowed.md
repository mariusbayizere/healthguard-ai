# CR03 — the gloss was narrowed in two records out of three

**For the Kinyarwanda session. One edit, in the one file neither language arm may
touch.**

On 2026-09-05 the reviewer ruled `CR03` to be **lips only** — fingertips would be
a new concept, not a gloss stretch. The English arm narrowed it byte-wise
everywhere it had standing to:

```
review/concept_anchors.csv    blue lips or fingertips -> blue lips   DONE
review/concepts.py  (gloss)   blue lips or fingertips -> blue lips   DONE
review/speaker_brief_kinyarwanda_v2.csv                              NOT DONE
```

**The spine was never narrowed, and the spine is what every language brief reads
its gloss from.** Re-derived just now, not recalled:

| record | says |
|---|---|
| `speaker_brief_kinyarwanda_v2.csv`, both persons | `central cyanosis - blue lips or fingertips` |
| `concept_anchors.csv` | `central cyanosis - blue lips` |
| `concepts.py` gloss | `central cyanosis - blue lips` |
| English brief, both persons | `central cyanosis - blue lips or fingertips` |
| French brief, both persons | `central cyanosis - blue lips or fingertips` |
| Swahili brief, both persons | `central cyanosis - blue lips or fingertips` |

So **every CR03 row in all three language briefs displays a gloss claiming
fingertips next to a phrase that says lips**, and each of those rows is a row a
reviewer is asked to judge for fidelity — against the wrong gloss.

```
KY    Iminwa yanjye yahindutse ubururu.        lips
EN    My lips have turned blue.                lips
FR    Mes levres sont devenues bleues.         lips
gloss central cyanosis - blue lips OR FINGERTIPS
```

## Why it did not fix itself

`english_gloss` is a `REGENERATED` column in `build_english_brief.py` and
`build_french_brief.py`, and its source is the spine. A rebuild copies the spine's
value in faithfully — which is the design working, not failing. **Narrowing the
spine is the whole fix**; both briefs pick it up on their next successful rebuild
and no per-language edit is needed. (The English builder cannot currently run at
all — see `english-brief-staleness.md` item 0.)

## Apply

Two cells, both persons of `CR03` in `speaker_brief_kinyarwanda_v2.csv`:

```
central cyanosis - blue lips or fingertips  ->  central cyanosis - blue lips
```

Then `python review/build_french_brief.py` and, once it runs, the English one.
Both will report the change as refreshed derived drift, which is the confirmation.

Verify with:

```
python -c "import csv; print({r['english_gloss'] for f in ['review/speaker_brief_kinyarwanda_v2.csv','review/speaker_brief_english_v2.csv','review/speaker_brief_french_v2.csv','review/speaker_brief_swahili_v2.csv','review/concept_anchors.csv'] for r in csv.DictReader(open(f)) if r['concept_id']=='CR03'})"
```

It should print exactly `{'central cyanosis - blue lips'}`.

**Checking that the four briefs merely AGREE is not the test** — they agree
today, on the un-narrowed value, because all four take it from the same spine.
`concept_anchors.csv` has to be in the set for the check to discriminate, and the
value has to be named.

## The French phrase in `concepts.py` is left alone, deliberately

`concepts.py`'s French column still reads:

```
"mes levres et le bout des doigts sont devenus bleus"
```

Asserting fingertips under a lips-only gloss, and sheet draft `D054` carries the
same text. The English pass recorded that its English twin was **dead** because
the brief superseded it, while *"the French one is live, because French has no
brief and `concepts.py` is the only place its phrasing exists"*.

**French now has a brief**, carrying `Mes levres sont devenues bleues.` and
`Les levres de {REL} sont devenues bleues.`, so the French column is dead in the
same way the English one is — the moment the brief is accepted as the source of
truth for French.

**Not edited, on purpose.** It is a shared file this project edits only on an
explicit ruling, and its phrase columns are already due to be dropped under the
source-of-truth ruling. If that ruling is not accepted, `concepts.py` still
asserts fingertips in French and someone has to decide which is right.

## And the ruling that started this is still worth re-reading

If the concept **is** meant to carry fingertips, then it is the gloss and all
four languages that need it — not one language quietly widening. That was the
English arm's flag and it stands. The narrowing is currently recorded in two files
and contradicted in one, which is the state that makes a ruling look like a
disagreement. `PR06` cost this project a day for the same reason: a prose line
outlived two later machine-readable rulings.

**The lesson there was about where a ruling gets recorded.** This one is the same
shape, one layer down: the ruling landed in the two files the arm could reach and
not in the file everything else derives from.
