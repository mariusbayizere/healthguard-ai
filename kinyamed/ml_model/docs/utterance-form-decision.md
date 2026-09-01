# Phrase form: the generator must change, not the phrasings

The Kinyarwanda speaker rewrote the 46 existing phrases as **full patient
utterances** — *ndakorora cyane*, *maze iminsi itatu ndwaye impiswi*, *ndatwite
ndababara* — and reports the noun-phrase form as a large part of why the originals
read as non-native. That is a language judgement from the only person on the project
qualified to make it, so the generator is what changes.

## What breaks

`Family.render()` composes `opener + subject + PHRASE + onset + context + closer`,
where the subject supplies *Mfite* / *Umwana wanjye afite* / *Umugabo wanjye afite*.
A full utterance after a subject produces `Umugabo wanjye afite ndakorora cyane`.

## The cost, measured

Per-language frame products, from the actual slot sizes
(opener 6, subject 10, onset 10, context 5, closer 5):

```
with subject     15,000     current
without subject   1,500     utterance form   -> a 10x loss
```

Total space = 10 frame contexts (4 pure + 6 mixed) x frame product x phrases.

| option | phrases/lang | combination space | 1,008,000 rows uses | verdict |
|---|---|---|---|---|
| **A1** utterances, 126 phrases | 126 | 1,890,000 | **53.3%** | reachable but tight |
| **A2** utterances, 1st + 3rd person authored | 252 | 3,780,000 | 26.7% | tight |
| **A3** A2 + double the opener/closer slots | 252 | 15,120,000 | 6.7% | comfortable |
| **B** 80% utterance / 20% noun phrase | 252 | 10,665,000 | 9.5% | comfortable |
| **B** 50/50 | 252 | 20,790,000 | 4.8% | very comfortable |
| **C** per-phrase metadata | 252 | same as B for a given mix | — | comfortable |
| *v1 for reference* | *184* | *6,900,000* | *14.5%* | *near-dup 4.7%* |

**1,008,000 remains reachable in every option.** The constraint is not whether rows
can be generated — it is how much of the space they consume. v1 used 14.5% and
measured a 4.7% near-duplicate rate; A1 at 53.3% would push that well up, because
sentences drawn from a smaller space resemble each other more. A1 is the option to
avoid.

## The third-person point, which decides it

*ndakorora* and *umwana wanjye arakorora* are different shapes, not one phrase with
two subjects. Under the utterance form, **person moves out of the frame and into the
phrase**. That is not a loss — it is more honest, because the frame was previously
generating third-person sentences by mechanical substitution, and one existing phrase
already produced *"Umugabo wanjye afite ... ndi utwite"* ("my husband has ... I am
pregnant") that way.

It does mean the phrase inventory carries person: roughly 126 clinical concepts x
{first person, third person} = 252 phrases per language. The dataset needs both, and
under the old model it never really had them.

## Recommendation: option C, per-phrase metadata

Each phrase declares its own form rather than the corpus taking a global policy:

```python
Phrase("ndakorora cyane",                    form="utterance", person="first")
Phrase("umwana wanjye arakorora cyane",      form="utterance", person="third")
Phrase("umuriro mwinshi wa dogere 39",       form="noun_phrase")
```

- The generator picks frames per phrase: utterances get opener + onset + context +
  closer; noun phrases additionally get a subject.
- **It reflects the language rather than overriding it.** Some clinical items come
  out naturally as utterances; others (*umuriro mwinshi wa dogere 39*) sit fine after
  *afite*. A global rule throws that information away; the speaker decides per phrase,
  which takes them seconds because they know the answer as they write.
- Person becomes a recorded field, so class and language balance can be extended to
  person balance, and a split could hold out by person if that ever matters.
- Space stays comfortable at any realistic mix.

## What it costs to build

- `vocabulary.py`: phrase tuples become records carrying `form` and `person`. This
  is the largest edit and it is mechanical.
- `build_families()`: partition by form, choose the slot set accordingly.
- `attribute_phrase()` in `split_dataset.py`: unchanged in logic, but the phrase
  inventory it matches against grows.
- `assert_slots_are_distinct()`: extend to the new structure.
- Two new columns in the speaker brief: `form` and `person`.
- v2 manifests regenerate anyway, so no additional migration cost.

I would also raise the frame slots — openers 6 and closers 5 are thin, and under the
utterance form they carry proportionally more of the variation. Those are patient
speech fragments the speaker can author quickly.

## One consequence that needs the speaker, not a decision here

**The utterance form changes what "mixed" means.** Today a mixed row is a frame in
one language wrapping a phrase in another. With full utterances the phrase is a
complete sentence, so a mixed row becomes a Kinyarwanda greeting and time expression
wrapped around an English sentence — which may be more realistic than the current
alternation, or may be worse. That is 48% of the corpus and it should not be decided
by arithmetic. It belongs with the questions already listed in
`docs/code-switching-design.md`.
