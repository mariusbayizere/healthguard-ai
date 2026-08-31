# Triage concept taxonomy — for clinician sign-off

**Purpose.** One language-independent list of what a patient presents with, its
proposed urgency, and its clinical anchor. A clinician signs off this document in
one session; everything else — phrasings in four languages, the corpus, the eval
splits — is generated from it.

**126 concept slots per language**: 9 domains x 14. Of these, 46 per language are
existing phrases with no recorded concept (they need validation), and 80 are new
concepts defined here.

## Attribution and licence — corrected

Clinical structure follows **WHO, *Integrated Management of Childhood Illness:
Chart Booklet*, Geneva: World Health Organization, March 2014, ISBN 978 92 4 150682 3.**

That document is **"All rights reserved"** — it carries no Creative Commons licence.
Verified by extracting its own copyright page:

> © World Health Organization 2014. All rights reserved. ... Requests for permission
> to reproduce or translate WHO publications ... should be addressed to WHO Press

An earlier draft of this project's notes described WHO IMCI chart booklets as
CC BY-NC-SA 3.0 IGO. **That was wrong**, generalised from a search result about a
different 2019 IMCI title whose licence this project has not been able to verify
directly.

**What follows from that.** Clinical facts are not copyrightable — that an
unrousable child is a danger sign is a fact about medicine, not protected
expression. This taxonomy therefore cites IMCI as its clinical basis and uses its
classification vocabulary as terms of art, but **reproduces no WHO text and
translates no WHO text**. Every phrasing in this project is drafted here. If verbatim
IMCI wording is ever wanted, that needs written permission from WHO Press.

## Honest mapping

Of the 80 new concepts, **28 map to a real IMCI sign or classification** and **40 are
marked outside IMCI scope** (the obstetric 12 are counted separately below). IMCI
covers children under five; adult cardiac, stroke, trauma, and chronic-disease
presentations have no IMCI equivalent and are marked `not IMCI` rather than given a
spurious mapping.

## The concepts

Full machine-readable list: `review/concepts.py` (68 general) and the obstetric 12
in `review/speaker_brief_*.csv`. Structure per concept:

    domain | proposed_urgency | concept_id | english_gloss | who_imci_reference

Concepts anchored in a genuine IMCI general danger sign:

| concept | IMCI sign |
|---|---|
| child convulsing / fever with convulsions / convulsion in pregnancy | convulsions |
| child too weak to breastfeed / fever and unable to drink | not able to drink or breastfeed |
| child unconscious or floppy / unrousable | lethargic or unconscious |
| vomiting everything, cannot keep fluids down | vomits everything |

Concepts anchored in an IMCI main-symptom classification: chest indrawing ->
SEVERE PNEUMONIA; stiff neck -> VERY SEVERE FEBRILE DISEASE; sunken eyes with very
slow skin pinch -> SEVERE DEHYDRATION; blood in stool -> DYSENTERY; diarrhoea >14
days -> PERSISTENT DIARRHOEA; generalised rash -> MEASLES; ear pain with discharge
-> ACUTE EAR INFECTION; MUAC/oedema -> ACUTE MALNUTRITION.

## What the clinician is being asked to decide

1. **Is the proposed urgency right?** Especially every CRITICAL: is this a
   presentation where delay causes harm? And every ROUTINE: is there a presentation
   here that could be a critical case in disguise?
2. **Is any concept missing** from a domain that a Rwandan health centre sees often?
3. **Are the 46 existing phrases per language clinically sensible**, and is their
   assigned urgency right? They were never reviewed.
4. **Is the three-class scheme (CRITICAL / URGENT / ROUTINE) the right granularity**
   for the setting, or should it map onto the IMCI pink/yellow/green bands directly?

Under-triage is the failure that matters. Where the clinician is unsure, the safer
class is the more urgent one, and that asymmetry should be recorded rather than
silently applied.
