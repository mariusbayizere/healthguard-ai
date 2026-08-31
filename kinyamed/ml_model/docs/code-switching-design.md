# Code-switching design — proposal for speaker validation

**Status: design only.** Nothing here is built. A Kinyarwanda speaker and a Swahili
speaker validate or reject this before any code is written. The current generator
is unchanged.

## What is built today

From `generate_large_dataset.py` and `vocabulary.py`, verified by reading the code:

- `MIXED_PAIRS` has six ordered pairs: kinyarwanda↔english, kinyarwanda↔french,
  swahili↔english.
- Each mixed family carries a `frame_language` and a `phrase_language`.
- `Family.render()` composes `opener + subject + phrase + onset + context + closer`.
  Every slot except `phrase` comes from the frame language; `phrase` comes from the
  other language, whole and unmodified.

So every mixed row is **one switch, at the same syntactic seam, every time**.

**And the mixed families draw from the same 46 phrases per language.** The 48% of the
corpus labelled "mixed" adds no distinct clinical content — only frame variation.

## Four defects, and what would fix each

### 1. Alternation where insertion belongs

Real Kinyarwanda–English speech is typically **matrix-language framed**: Kinyarwanda
supplies morphosyntax and word order, and English contributes single content
morphemes — most often a noun, sometimes a verb stem. The generator does the
opposite: it swaps a whole multi-word clause.

*Proposal.* Add an insertion mode. Keep the frame entirely in the matrix language
and substitute **one** content word from the embedded language, chosen from a
speaker-approved list of terms that are actually switched. Retain the current
alternation mode only if speakers confirm whole-phrase switching occurs.

### 2. No morphological integration

Bantu nouns carry class prefixes and trigger agreement on verbs, adjectives and
possessives. An English noun dropped into a Kinyarwanda frame is normally
integrated — assigned a class and taking the agreement that follows. The generator
inserts the bare English string.

*Proposal.* For each approved insertable noun, the speaker records the noun class it
takes and the agreement it triggers, and the generator applies the concord. This is
the item most likely to expose the design as wrong, and the one where a speaker's
judgement cannot be substituted for.

### 3. Borrowing is not code-switching

Medical vocabulary — *malaria*, *pressure*, *sugar*, *diabetes* — is borrowed into
everyday Kinyarwanda and Swahili and appears in otherwise **monolingual** speech.
Much of what looks "mixed" in real transcripts is a monolingual utterance containing
established loanwords. The corpus has no representation of this at all: a row is
either pure or switched.

*Proposal.* A speaker-approved loanword list per language, with those terms usable
inside rows labelled **monolingual**. This likely matters more than the switching
model, because it affects the 52% of the corpus that is not labelled mixed.

### 4. Missing and arbitrary pairs

French pairs only with Kinyarwanda; Swahili only with English. There is no
kinyarwanda↔swahili and no english↔french. Nobody has established that this
reflects Rwandan usage.

*Proposal — to be answered by speakers, not by us:*

- **kinyarwanda↔swahili**: plausible in cross-border and trading contexts; is it
  plausible in a Rwandan health centre?
- **english↔french**: both are official languages of Rwanda and both are used in
  clinical settings; educated speakers may switch between them without Kinyarwanda.
- Is the current 48% mixed share anywhere near the real rate? It was chosen as a
  generation target, not measured.

## Validation questions

1. Does whole-phrase alternation occur, or is insertion the dominant pattern?
2. Which medical terms are actually switched, and which are simply borrowed?
3. What noun class does each inserted English/French noun take?
4. Are kw↔sw and en↔fr real in this setting?
5. Roughly what proportion of patient utterances contain any switching?

Question 5 has no answerable form without observed data. Until someone records or
transcribes Rwandan patients describing symptoms, the mixed proportion is a
guess, and should be described as one.
