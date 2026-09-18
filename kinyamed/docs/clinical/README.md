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

## A caveat this file cannot fix

Removing the file from the working tree does **not** remove it from git history:
the blob remains reachable from earlier commits, so a clone still carries it.
Purging it needs a history rewrite (`git filter-repo`) and a force-push, which
is a destructive operation on a published branch and is **not** done without the
maintainer's explicit instruction. Until then, treat the exposure as open and
recorded rather than resolved.
