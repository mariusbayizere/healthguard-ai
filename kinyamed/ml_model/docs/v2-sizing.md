# v2 corpus sizing

## The arithmetic, computed from the generator

```
v1 as built
  families                160
  distinct phrase strings 184
  distinct combinations   6,900,000
  rows                    1,000,000   (14.5% of the space)
  mean rows per phrase     5,435

v2 projected (14 phrases per domain per language)
  (urgency,domain) cells  26   (+10; obstetric gains URGENT and ROUTINE, etc.)
  phrases per language    126
  distinct phrase strings 504
  distinct combinations   18,900,000   (2.74x v1)
```

The frame slots (opener x subject x onset x context x closer = 15,000 per language)
are unchanged by vocabulary work; the whole 2.74x comes from the phrase slot.

## What each row count buys

| rows | rows per phrase | share of combination space |
|---|---|---|
| 1,000,000 | **1,984** | 5.3% |
| **1,008,000** | **2,000** | 5.3% |
| 1,500,000 | 2,976 | 7.9% |
| 2,000,000 | 3,968 | 10.6% |
| 3,000,000 | 5,952 | 15.9% |

## The finding: above ~1M, more rows spend the quality the vocabulary bought

The brief asks for two things that pull in opposite directions — a bigger corpus,
and median rows-per-phrase around 2,000. At 504 phrase strings those meet at
**1,008,000 rows** and nowhere else.

Going to 2M does not make a better corpus. It makes each phrase repeat 3,968 times
instead of 1,984 — half the diversity per phrase, for a bigger number on the cover.
At 3M rows the corpus would be **less diverse per phrase than v1 is today** (5,952
against 5,435), which would mean the vocabulary expansion had bought nothing.

Repetition is not the binding constraint here — 2M rows uses only 10.6% of the
18.9M combination space, so nothing repeats. The constraint is that rows-per-phrase
is the honest measure of how much clinical variety a row count represents, and it
gets worse as rows go up and better only as phrases go up.

## If you want a genuinely larger corpus

The lever is phrases, not rows. Holding 2,000 rows per phrase:

| phrase strings | per language | per domain per language | supports |
|---|---|---|---|
| 504 | 126 | 14 | **1,008,000 rows** |
| 750 | 188 | ~21 | 1,500,000 rows |
| 1,000 | 250 | ~28 | 2,000,000 rows |

To say "2,000,000" and mean it at v2 quality needs roughly **1,000 phrase strings** —
double the current Phase 2 target, and double the speaker and clinician time.

## Recommendation

**Generate 1,008,000 rows.**

- Literally satisfies "1,000,000+" without inflating it.
- Hits 2,000 rows per phrase exactly.
- Uses 5.3% of the combination space, so uniqueness by construction still holds
  with wide margin.
- Every row is backed by 2.74x more distinct clinical material than v1.

The paper can then say **1,008,000 rows from 504 clinician-reviewed,
speaker-authored phrasings across 9 domains and 4 languages** — which is a stronger
sentence than "2,000,000 rows" from the same 504 phrases, and it is one nobody can
undercut by dividing.

If a bigger headline number is wanted later, fund more phrases. Do not raise the
row count.
