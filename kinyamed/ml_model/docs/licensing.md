# Dataset licensing

**I am not a lawyer and this is not legal advice.** Sections marked **CITED** quote
text I read in the source document. Sections marked **REASONING** are my analysis
and should be checked by someone qualified before release — particularly the
share-alike question and anything touching clinical deployment.

## Source licences — all verified from the document's own copyright page

| document | ISBN | licence |
|---|---|---|
| WHO-ICRC *Basic Emergency Care*, 2018 | 978-92-4-151308-1 | **CC BY-NC-SA 3.0 IGO** |
| WHO *Managing Complications in Pregnancy and Childbirth*, 2nd ed., 2017 | 978-92-4-156549-3 | **CC BY-NC-SA 3.0 IGO** |
| WHO *IMCI Chart Booklet*, 2014 | 978 92 4 150682 3 | **All rights reserved** |
| WHO *PCPNC*, 3rd ed., 2015 | 978 92 4 154935 6 | **All rights reserved** |
| Swahili Corpus, Mendeley `d4yhn5b9n6` | — | CC BY 4.0 |
| MasakhaNER 1.0/2.0 | — | CC-BY-4.0-**NC** (per repo README; not verified in-document) |

**REASONING — an observed pattern, not a rule.** The two documents from 2017–2018
carry CC licences; the two from 2014–2015 do not. That is consistent with WHO
adopting Creative Commons around 2016–17. Do not assume it for any other WHO
document — check each one.

## Where the 80 concepts now stand

```
WHO IMCI 2014 (All rights reserved)         29
clinician-defined (no WHO anchor)           23
WHO-ICRC BEC 2018 (CC BY-NC-SA 3.0 IGO)     18
WHO MCPC 2017 (CC BY-NC-SA 3.0 IGO)         10
```

**28 concepts have an openly-licensed anchor. That is the set the share-alike
question is about.**

## Q1: Does a concept taxonomy trigger share-alike?

**CITED**, from BEC's licence page: *"If you adapt the work, then you must license
your work under the same or equivalent Creative Commons licence."*

**REASONING.** Two separate questions hide in this one.

*Is a clinical fact copyrightable?* Generally no. Copyright protects expression, not
facts or ideas. "A patient who cannot be roused is a danger sign" is a fact about
medicine; it can be stated in many ways and no one owns the proposition. On that
basis, our concepts — none of which reproduces WHO wording — are not adaptations.

*Is the selection and arrangement copyrightable?* This is the sharper question, and
you were right to separate it. A compilation of facts can attract protection where
the selection or arrangement is itself original. (In US law the reference point is
*Feist v. Rural Telephone* (1991): facts are not protectable, compilations are only
where selection/arrangement shows originality. Other jurisdictions differ, and the
EU additionally has a *sui generis* database right with no US equivalent. Rwanda's
position I have not checked.)

Applying that here, the argument that share-alike does **not** attach:

- Our arrangement is **9 clinical domains × 3 urgency classes**, which we invented.
  BEC's arrangement is **5 modules** — ABCDE/SAMPLE, trauma, difficulty breathing,
  shock, altered mental status. The structures are unrelated, and our BEC-anchored
  concepts are scattered across our domains rather than following BEC's order.
- Our selection was driven by gaps in *our* domain grid — we needed N more concepts
  in `neurological` — not by working through BEC and taking its list.
- BEC was consulted **after** the concepts existed, to check clinical validity. It
  functioned as a citation, not a source.

The argument that it **might** attach: 18 concepts were chosen *because* BEC
supports them, and someone could characterise that as deriving from BEC's clinical
selection. I think that is the weaker reading, but it is not frivolous, and I would
not want a released dataset to rest on my reading of it.

**Citing BEC in the paper raises no licensing question at all.** Citation is not
licensing. The question is only whether BEC-derived material sits *inside* the
dataset.

## Q2: What licence can the dataset carry?

**REASONING**, conditional on Q1.

| if | dataset can be |
|---|---|
| BEC/MCPC-derived concepts are adaptations | **CC BY-NC-SA 4.0** — the only safe option; NC and SA both inherited |
| they are not adaptations (facts, independent arrangement) | **CC BY 4.0** or **CC0** available |
| MasakhaNER text is used | NC attaches regardless of the above |
| only the Swahili Corpus (CC BY 4.0) is used | attribution only, no NC |

Two further points. Code and data should be licensed separately — the pipeline can
be MIT or Apache-2.0 whatever the data carries. And CC BY-NC-SA **4.0** is generally
treated as an acceptable "equivalent" licence for adapting 3.0 IGO material, but
that is a judgement about equivalence, not something the 3.0 IGO text spells out.

## Q3: Does NC conflict with the project's goals?

**REASONING**, and I think the answer is yes, in a way that matters.

The README describes an open research dataset and an eventual triage system for
Rwandan health centres. NC does not obstruct the research use, and public-sector
deployment by a health ministry is unlikely to count as "primarily intended for
commercial advantage" — though that phrase is genuinely fuzzy and has no settled
test.

Where NC bites:

- **A commercial partner cannot build on it.** If deployment ever runs through a
  private hospital group, a telecom's health service, or a vendor implementing for
  MoH, NC is a blocker or at least a negotiation.
- **Adoption drops.** Many research groups and nearly all companies avoid NC data
  by policy. For a dataset whose stated value is being *the* multilingual African
  medical triage resource, NC materially reduces how many people can use it.
- **NC is viral through share-alike.** Anyone building on it inherits both terms.

If the goal is a resource the field actually adopts, NC works against it. If the
goal is a paper plus a non-commercial reference dataset, NC is fine.

## Q4: Re-derive the 18 (28) from clinician input?

**REASONING — and this is my recommendation.**

Have the Rwandan clinician who is already reviewing the taxonomy state the concept
list independently, working from their own practice rather than from BEC. Where
they name a concept BEC also covers, the anchor becomes *their professional
judgement on date D*, and BEC becomes a citation in the paper rather than a source
in the dataset.

Why I would do this:

1. **The session is already planned.** Step 2 of the path to native quality is
   exactly this. The marginal cost is close to zero — it is a change in how the
   session is run and minuted, not extra work.
2. **It removes the question rather than answering it.** No BEC-derived content
   means no share-alike analysis to get wrong, and no need to pay someone to opine
   on Q1.
3. **The artefact gets better.** A concept list validated against Rwandan primary
   care is more defensible for this system than one assembled from global guidance.
   The 23 already clinician-defined concepts are arguably the strongest in the set
   for the same reason.
4. **It keeps the permissive option open.** CC BY 4.0 or CC0 becomes available,
   which serves the adoption goal.

**How to run it so the provenance is clean:** ask the clinician for the concepts
*before* showing them the BEC mapping. If the list is generated and then compared,
the independence is real and demonstrable. If BEC is shown first, it is not, and the
argument for independent derivation weakens considerably.

Keep `review/concept_anchors.csv` as an internal cross-check — useful for showing
that clinician-derived concepts align with international guidance, which is a
strength in a paper — but do not ship it as the dataset's provenance.

## Recommendation

1. **Re-derive in the clinician session, concepts first, BEC comparison second.**
2. **Target CC BY 4.0 for the dataset**, MIT or Apache-2.0 for the code.
3. **Keep the IMCI/BEC/MCPC citations in the paper.** Citation is free.
4. **Get an actual opinion before release** if any BEC or MCPC material remains in
   the dataset, or if commercial deployment is on the roadmap. The NC question in
   particular is worth twenty minutes of a lawyer's time and could otherwise
   surface after publication, when it is expensive.
