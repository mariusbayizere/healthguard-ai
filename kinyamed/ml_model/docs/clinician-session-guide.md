# Clinician session guide

**Two sessions, not one.** Roughly 2 hours then 1.5 hours. The reason is in
"Why two" below, and it is a safety argument rather than a scheduling one.

## The one rule that must not be broken

**The clinician states the concept list before seeing any WHO document, our
existing phrases, or the BEC mapping.**

This is not ceremony. If they generate the list independently, its provenance is
their professional judgement on a date, and the dataset can carry CC BY 4.0. If they
are shown WHO material first and asked to react, the list is arguably derived from
that material, which drags a non-commercial share-alike licence across the whole
dataset. The order of two conversations decides the licence of the artefact.

Do not have `concept_anchors.csv`, the BEC PDF, or the existing phrase list on the
table during Session 1 Phase A.

---

# Session 1 — approximately 2 hours

## Opening (10 min)

Explain, in this order:

1. What the tool does: reads a patient's own description, sorts urgency into
   critical / urgent / routine, to help a nurse decide who is seen first.
2. What is wrong with it now: the clinical content was assembled without a
   clinician. Nobody qualified has agreed the urgency labels.
3. What you are asking: for them to say what patients actually present with, in
   their own practice, and how urgent each is.
4. That they will be named as a contributor unless they decline, and that their
   list will be published as theirs.
5. **Why you are not showing them the existing list yet** — say this plainly. "I
   want your list first, independently, and then we compare. If I show you mine
   first I have anchored you to it." Clinicians understand bias in study design;
   this reads as rigour, not evasion.

## Phase A — elicitation (60-75 min) — NOTHING SHOWN

Go domain by domain. For each of the nine, ask in this order:

> **"In your health centre, what do patients come in saying, for [domain]?"**
>
> Then: **"Which of those cannot wait?"**
>
> Then: **"Which are routine — someone who could come back tomorrow?"**

The nine domains, in this order — start with the ones they see most, so the method
is established before the harder ones:

1. infectious_fever
2. gastrointestinal
3. cardiac_respiratory
4. paediatric
5. obstetric
6. neurological
7. haemorrhage_trauma
8. chronic_care
9. preventive

Record **in their words**. Write "the mother says the baby has stopped moving",
not "reduced fetal movement". The clinical register is yours to normalise later;
their phrasing is the evidence that the list is theirs.

Do not steer. If a domain comes back thin, ask once — *"anything else in that
group?"* — and move on. A thin domain is a finding, not a failure: it may mean that
presentation is rare in their setting, which is information you want.

## Phase A close — the provenance record (5 min)

Before anything else is shown, read the list back, let them correct it, then record
at the top of the file:

```
Concept list stated by [full name], [role], [facility], on [date].
Generated from the clinician's own practice before any external
guidance, WHO document, or existing project material was shown.
Recorded by [your name].
```

Ask them to confirm that statement is accurate. If you have their agreement in
writing or on the recording, better. **This paragraph is the licence argument.**

Save it as `review/clinician_concepts_[date].md` and commit before Phase B. The
commit timestamp is corroboration.

## Phase B — comparison (40 min) — NOW show things

Only now bring out the existing material. Three passes:

1. **What they named that we don't have.** New concepts. These are the most
   valuable output of the session — a presentation common in Rwandan primary care
   that global guidance and our drafting both missed.
2. **What we have that they didn't name.** Ask about each: is this real but
   uncommon, or is it wrong for this setting? Both answers are useful. Do not
   delete anything unilaterally.
3. **Then, and only then, the BEC/IMCI/MCPC comparison.** Frame it as a check, not
   a correction: "these are the ones international guidance also lists — does
   anything here change your view?" Record any concept they add at this stage
   **separately**, flagged as guidance-prompted, so the independent set stays clean.

---

# Session 2 — approximately 1.5 hours

## Urgency review — all 126 concepts

**You are reviewing 46 existing clinical items, not 184 phrases.** Verified: the
four language sets are structurally parallel — identical counts in all 16
(urgency, domain) cells — and spot-checked position by position. The English column
is sufficient for clinical review; the other three languages are the same clinical
content and belong to the speaker sessions, not this one.

So: 46 existing + 80 new = **126 urgency decisions**.

For each, one question:

> **"If a patient presented like this and was put in the routine queue, could that
> harm them?"**

That framing puts under-triage in front, which is the failure that matters. Record
CRITICAL / URGENT / ROUTINE, and where they hesitate, record the hesitation — a
concept the clinician found genuinely borderline is one the model will find
borderline too, and that belongs in the paper.

## Closing questions (15 min)

1. Is three classes the right granularity, or should it map to the IMCI pink /
   yellow / green bands?
2. Any concept where the urgency depends on something the text cannot convey — age,
   pregnancy status, how long it has been going on? Those are a known limit of this
   design and worth writing down.
3. Anything about this approach they think will not work in practice?

## Why two sessions

Phase A is generative and Session 2 is evaluative, and they use different attention.
More to the point, 126 urgency decisions at the end of a three-hour session is how
you get rubber-stamping — and every one of those decisions is a judgement about
whether someone can safely wait. A tired clinician agreeing with your defaults is
worse than no review, because it looks like validation. If it must be one session,
put a real break between the phases and expect to lose quality in the last half hour.

## What to bring

Session 1: blank paper, the nine domain names, nothing else.
Session 2: the merged concept list with proposed urgencies, and
`speaker_brief_*.csv` printed if they also speak Kinyarwanda — but treat that as a
bonus, not the plan.
