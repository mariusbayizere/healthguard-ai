# Five Kinyarwanda phrase groups hold more than one concept

Found from the English side while drafting cardiac_respiratory, where `EX02` and
`CR02` had to be worded apart on purpose. **The Kinyarwanda pair they were worded
apart from is already joined, and it is not the only one.**

Written up for the Kinyarwanda session. Nothing here is fixable from the English
arm — the phrases are the speaker's and the remedy is a rewording only they can
make.

## What was measured

The project's own rule, imported from `split_dataset.py`, run over the 163
authored `applies=yes` Kinyarwanda phrases: substring containment, then ordered
subsequence, then the declared first/third join. Reproduce it with the same two
helpers (`_match_form`, `_is_subsequence`) so it cannot drift from the splitter.

```
163 phrases -> 87 phrase groups
  5 groups contain more than one CONCEPT
```

| group | concepts | phrases |
|---|---|---|
| **CR02, EX02, EX04** | 3 | 6 |
| **EX14, EX38, GI07** | 3 | 6 |
| CC03, EX09 | 2 | 4 |
| EX18, EX20 | 2 | 4 |
| EX42, IF05 | 2 | 3 |

## The joins, phrase by phrase

**Containment — one phrase is literally inside another.**

```
EX02  guhumeka birangora cyane
CR02  Guhumeka birangora cyane ku buryo ntabasha no kuvuga neza.
EX04  guhumeka birangora cyane kandi iminwa yanjye yahindutse ibara

EX09  umuvuduko w'amaraso wanjye wazamutse cyane
CC03  Umuvuduko w'amaraso wanjye wazamutse cyane kandi umutwe urandya cyane.

EX14  inda irandya cyane
GI07  Inda irandya cyane kandi ububabare ntibuhagarara.

EX42  {REL} afite umuriro n'uduheri ku mubiri
IF05  {REL} afite umuriro n'uduheri ku mubiri wose.
```

Each holds in **both persons** except EX42/IF05, which is third-person only.

**Ordered subsequence — every word of one appears in the other, in order.**

```
EX14  {REL} arababara cyane mu nda.
EX38  {REL} aratwite, arababara cyane mu nda kandi arava amaraso.

EX18  ndi kuva amaraso menshi kandi ntahagarara
EX20  ndi kuva amaraso menshi mu mazuru kandi ntahagarara
```

`EX18`/`EX20` is the pair `PREFIX_UNION_CHARS` was written for and only ever
caught in the third person. **The subsequence rule catches both persons**, which
is the improvement claimed for it, now confirmed independently.

## What this costs, stated precisely

**It is not a leak past the guard.** The union is the *correct* response to
containment — without it, holding out `EX02` while training on `CR02` would show
zero phrase overlap while the model had seen every character of EX02. The closure
is doing its job.

The cost is upstream of the guard, and it is real:

1. **Two concepts can never be evaluated separately.** `EX02` and `CR02` are
   different presentations — *serious difficulty breathing* against *too
   breathless to complete a sentence*, one CRITICAL for a different reason than
   the other. The phrase holdout can only ever hold out both or neither.
2. **The holdout is coarser than its headline count suggests.** 87 groups over
   163 phrases already; five of those groups are doing the work of eleven
   concepts. Any per-concept claim about generalisation to unseen wording is
   really a per-group claim.
3. **It will get worse as the corpus grows**, because the joins come from the
   speaker writing a fuller version of an existing phrase — which is exactly what
   authoring a more specific concept looks like.

## Two of the five may not be collisions at all

**`EX42` / `IF05` is probably one concept.** `{REL} afite umuriro n'uduheri ku
mubiri` against the same sentence plus `wose` (all over). Their anchors agree
after the paediatric ruling: EX42 inherits PA06's `IMCI: MEASLES`, and IF05 is
`IMCI: generalised rash -> MEASLES`. Two concepts, one sign, one anchor, one
sentence differing by one word. **This is a collapse candidate, not a rewording
problem** — and it is the third measles-shaped concept after PA06.

**`EX14` / `GI07`** — *belly pain* inside *belly pain that does not stop*. The
axis is whether it stops, which is recorded in neither gloss. Worth checking
before rewording, because if there is no axis it is a collapse too.

The other three are genuine distinct concepts that happen to nest:
`EX02`/`CR02`/`EX04`, `CC03`/`EX09`, `EX18`/`EX20`.

## What would fix them, and what would not

**Rewording, by the speaker.** `CR02` does not have to open with `Guhumeka
birangora cyane`; a phrase that says *too breathless to finish a sentence*
without restating *breathing is very hard* breaks the containment without losing
the concept. Same shape for CC03 against EX09 and GI07 against EX14.

**Not fixable by tuning the closure.** Loosening it to keep the pairs apart would
re-open the actual leak, which is worse. The closure is right; the phrases are
what collide.

**Not fixable from English.** The English drafts for `EX02`/`CR02` were worded
apart deliberately — `I am having a lot of trouble breathing` against `I cannot
finish a sentence without stopping for breath`, neither containing the other — so
the English arm does not inherit the collision. That is a divergence in group
structure between the two languages, which is allowed (groups are per-phrase, not
per-concept) but worth knowing about: **the same two concepts are separable in
the English holdout and not in the Kinyarwanda one.**
