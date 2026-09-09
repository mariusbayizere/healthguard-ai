# Project status — 2026-09-09

Every figure re-derived from disk today, not recalled. One page.

## Corpus

| item | built | measured | gap | what closes it |
|---|---|---|---|---|
| Kinyarwanda corpus | **yes** | 330,000 rows, 165 phrases, 96 concepts | half the phrases are not directly speaker-authored (82/165 = 49.7%) | more speaker authoring, or report the split as-is |
| Kinyarwanda phrases | 170 authored rows | — | 23 held, 25 flagged for a clinician | D2 clinician session |
| English arm | brief only, 256 rows | — | machine-drafted, unreviewed; no speaker has seen it | an English-speaking reviewer |
| French arm | brief only, 256 rows | — | same | a French-speaking reviewer |
| Swahili arm | brief issued, **relations authored (12)** | — | **0 phrases authored** | speaker returns the 194 rows |
| Frame fragments | Kinyarwanda only (12/10/10/11) | — | **absent for EN, FR, SW** | ~39 short utterances per language |
| Response + SMS templates | KW 6/6, SW 6/6 | segment lengths measured | EN 0/6, FR 0/6 | those two speakers |
| Code-switching | generator built, refuses | 15 terms ruled | **0 of 6 pairs generate** | KW-EN needs 10 more terms ruled; SW needs its own worksheet; EN/FR need frames |
| 1,000,000 rows | no — 330,000 | — | needs ~500 phrases, have 165 | ~335 more phrases across three languages |

## Model

| item | built | measured | gap | what closes it |
|---|---|---|---|---|
| Classifier (v2d) | yes | macro F1 0.7724, CRITICAL recall 0.8504 | **fails the gate** (G1 needs 0.95) | not closable by tuning — see below |
| Acceptance gate | 3 conditions | G1 fail, G2 pass, G3 pass | G1's 0.95 unsourced; G3's margin a clinical judgement | a clinician sets both |
| Evaluation base | phrase holdout | 17,942 rows / **9 sentences / 4 CRITICAL** | recall moves in quarter steps | more distinct phrases, nothing else |
| Baseline comparison | **no** | — | mBERT / AfriBERTa not trained | run A2 |
| Inference latency | yes | warm p95 103 ms, cold 1341 ms | cold exceeds the 200 ms claim 20x | warm start (done) or a resident worker |

## System

| item | built | measured | gap | what closes it |
|---|---|---|---|---|
| Triage endpoint | yes | endpoint latency untested end-to-end | — | measure through HTTP |
| Queue | yes, priority-ordered | — | — | — |
| SMS | yes, flagged off, dry-run | segment lengths | sends nothing in EN/FR | those templates |
| Dashboard | **no — frontend empty** | — | C4 not started | scaffold |
| Deployment | **no** | — | runbook's first precondition (gate) fails | the gate, then D6 |

## The six claims that need people

None has a value anywhere, and none may be written. Protocols are written and unexecuted.

| claim | instrument | what closes it |
|---|---|---|
| Inter-rater agreement (κ) | `d1-annotation-protocol.md` | a second annotator |
| Clinician approval of the taxonomy | `d2-clinician-review-pack.md` | one clinician session (25 rows, 5 questions) |
| Native-speaker authenticity ratings | `d3-speaker-rating-instrument.md` | a rating session |
| Human-nurse baseline | `d4-nurse-baseline-design.md` | a nurse study |
| CHW consultation | `d5-chw-consultation-guide.md` | three visits |
| Deployment | `d6-deployment-runbook.md` | all of the above first |

## Paper

19 pages, builds clean, every number a macro from one verified inference pass.
13 `\PENDING{}` markers at their points of use. Sections written: abstract,
introduction, related work, method, results, system, discussion, limitations,
future work. **No conclusion.**

## If you do one thing before Friday

**The clinician session (D2).** It unblocks 23 held rows and 25 flagged ones,
answers the two gate thresholds that are currently unsourced, and is the single
precondition that gates deployment. It is also the only item on this page where
one meeting closes a whole column.

**The thing that cannot be fixed by a meeting:** the evaluation base is four
CRITICAL sentences. No clinician, no tuning and no additional training run
changes that — only more authored phrases do, and that is speaker time.
