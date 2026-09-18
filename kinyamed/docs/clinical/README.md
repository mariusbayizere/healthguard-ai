# Clinical source documents — not redistributed here

`docs/clinical/` holds the clinical references L5 requires: the triage taxonomy,
emergency numbers and referral pathways must come from these documents and never
from model memory.

**The documents themselves are not in this repository, and must not be added.**
This directory is gitignored apart from this file.

## Why

`participant_manual.pdf` (WHO ETAT participant manual, ISBN 92 4 154687 5) was
tracked in this repository until 2026-09-18. Its own rights page reads:

> © World Health Organization 2005. All rights reserved. … Requests for
> permission to reproduce or translate WHO publications — whether for sale or
> for **noncommercial distribution** — should be addressed to WHO Press.

This repository is public. Redistributing an all-rights-reserved WHO publication
from it is not permitted, and "it is for research" is not one of the exceptions:
the rights page names noncommercial distribution explicitly. It was removed and
is cited by URL instead.

## How to obtain them

| Document | Where |
|---|---|
| WHO ETAT participant manual (2005) | WHO: <https://www.who.int/publications/i/item/9241546875> |
| WHO ETAT facilitator / course materials | WHO Department of Child and Adolescent Health |
| Rwanda MoH / RBC clinical protocols | Rwanda Biomedical Centre |

Place them in this directory locally. They will not be committed.

## The blob is still in history, and that is a decision, not an oversight

Removing the file from HEAD does **not** remove it from git history. The blob
remains reachable from commits up to and including `0444c7c` (2026-09-17, where
it was added) and a fresh clone still downloads it. What changed on 2026-09-18
is the working tree and the ignore rule, nothing else.

**Ruled on 2026-09-18: leave it in history and record it here.** Purging would
need `git filter-repo` and a force-push over a published branch, rewriting every
commit hash since the file was added and breaking every existing clone and any
reference to a commit id. That cost was judged higher than the exposure, which
is one publicly available WHO document that anyone can download from WHO
directly. No history rewrite has been performed and none is planned.

So the accurate statement, and the one the paper's data statement makes, is:
the document is absent from HEAD, the directory is ignored, and the blob is
still reachable from earlier commits. Not "the repository does not contain
clinical documents".

Anyone re-examining this should know the two facts that make it tolerable: the
document is freely downloadable from WHO, and nothing in this repository
reproduces its text. What is forbidden is redistribution, and a git object
nobody is pointed at is a weaker form of that than a tracked file in HEAD, but
it is not nothing, which is why it is written down.
