# Evaluation-set specification — Item 5 (design only)

**Status:** specification, tooling and evaluator built; **no items authored, no labels collected**. Clinical
definitions are **BLOCKED** on `docs/clinical/` (empty). Nothing here is clinical content.

**Single source of truth:** `kinyamed/ml_model/training/eval_spec.py`. Every number below is printed by
`python training/eval_spec.py --report` or recomputed by `--verify`. `training/evaluate.py` enforces these
minimums, and `annotation/` builds the set to them.

Companion documents:
- `ml_model/docs/protocols/d7-eval-set-annotation-protocol.md` — the annotator protocol
- `reports/CLINICIAN_BRIEF.md` — the one-page brief for clinicians

---

## 1. Why the current set cannot be used

| | Current held-out set (v2 phrase holdout, reporting subset) |
|---|---|
| Rows | 17,942 |
| Distinct sentences | **9** (4 CRITICAL) |
| Languages | Kinyarwanda only |
| 95% CI, CRITICAL recall (phrase-cluster bootstrap) | **[0.08, 1.00]** |
| Exact 95% CI if all 4 CRITICAL sentences were correct | [0.398, 1.000] |
| Gate metrics measurable | 11 of 15 in Kinyarwanda at all; **none** at a precision that supports a claim |

A training run evaluated on this set cannot be falsified. The set measures template variation around nine
sentences, not the model's behaviour on patients' speech.

## 2. The decision rule — a proposal you must approve

**Proposed:** a threshold "metric ≥ t" is **MET** only when the **lower end of the two-sided 95% interval** is
≥ t; "metric < t" only when the upper end is < t.

| Verdict | Meaning |
|---|---|
| MET | interval entirely on the passing side |
| NOT MET | interval entirely on the failing side |
| NOT DEMONSTRATED | interval contains the threshold |
| INSUFFICIENT DATA (n=X, need Y) | population below this spec's minimum; **no number is printed** |
| NOT MEASURED | required input absent (latency, memory, language detection) |

For proportions, the deciding bound is the more conservative of the exact Clopper–Pearson interval and the
scenario-cluster bootstrap.

**Why a point estimate is not enough.** With 400 CRITICAL items and an observed recall of exactly 0.91, the
exact 95% interval is [0.878, 0.936]. The data are consistent with a true recall as low as 0.878, below the safety floor. CLAUDE.md
§9.2 says "report each with a 95% bootstrap CI" but does not say which end decides. This rule makes the interval
decide, and it is stricter than a point-estimate gate. **It changes what "passing" means, so it needs your
approval (decision E1).**

## 3. The power calculation: CRITICAL recall ≥ 0.91 per pure language

**Question.** How many CRITICAL items per language are needed so that "recall ≥ 0.91" is a claim and not noise?

**Method.** Exact binomial throughout; standard library only (`eval_spec.py`).
1. For n items, find the smallest count x whose Clopper–Pearson 95% lower bound is ≥ 0.91.
2. Power = P(X ≥ x) when the model's true recall is p, with X ~ Binomial(n, p).
3. The minimum n is the smallest n where power ≥ 0.80 holds for that n **and the next 9**. Binomial power
   saw-tooths in n, so a single crossing can dip again (visible below: 0.85 at n=365, 0.85 at n=400).
4. The implementation is checked against published Clopper–Pearson values (5/10 → [0.1871, 0.8129];
   0/10 → [0, 0.3085]; 91/100 → [0.836, 0.958]) in `tests/test_eval_spec.py`.

**Interval width at an observed recall of exactly 0.91:**

| n CRITICAL | exact 95% CI | half-width |
|---|---|---|
| 4 | [0.398, 1.000] | 0.301 |
| 50 | [0.808, 0.978] | 0.085 |
| 100 | [0.836, 0.958] | 0.061 |
| 200 | [0.861, 0.946] | 0.042 |
| 300 | [0.872, 0.940] | 0.034 |
| **400** | **[0.878, 0.936]** | **0.029** |
| 500 | [0.881, 0.934] | 0.026 |
| 1000 | [0.891, 0.927] | 0.018 |

**Power to demonstrate recall ≥ 0.91** (probability the lower 95% bound clears 0.91):

| true recall | n=100 | n=200 | n=365 | n=400 | n=800 | n=1535 |
|---|---|---|---|---|---|---|
| 0.93 | 0.07 | 0.10 | 0.27 | 0.25 | 0.54 | 0.82 |
| **0.95** | 0.26 | 0.45 | **0.85** | **0.85** | 0.99 | 1.00 |
| 0.97 | 0.65 | 0.92 | 1.00 | 1.00 | 1.00 | 1.00 |

**Choice.**
- **Minimum 365 gold CRITICAL items per pure language; allocated 400** (9.6% margin for items adjudicated
  UNCLASSIFIABLE).
- **The design point is a true recall of 0.95.** That equals the repo's own G1 gate, and a model genuinely at
  0.95 has at least an 80% chance (0.85 at n=365 and at n=400) of showing ≥ 0.91.
- **At a true 0.93 the requirement is 1,535 per language.** A model only slightly above the floor cannot
  practically be shown to be above it; that is a property of the problem, not of this design.
- **No n makes a model at exactly 0.91 pass,** and none should.
- **v2d's measured recall of 0.8504 would be NOT MET** on a set this size if it held, because its interval would
  sit entirely below 0.91.

## 4. Every gate metric: population and minimum n

Thresholds are §9.2's. "Design true value" is the assumed true performance used for power. It is a design point,
not a measurement.

| Gate | Metric | Threshold | Population (what n counts) | Min n | Design true | Justification |
|---|---|---|---|---|---|---|
| 1 | overall accuracy | ≥ 0.82 | all gold items | 710 | 0.86 | exact power |
| 2 | weighted F1 | ≥ 0.83 | gold items of each class, pooled | 570 | — | no closed-form power; bounded by gates 5 and 8; bootstrap CI |
| 3 | macro F1 | ≥ 0.80 | gold items of each class, pooled | 570 | — | as 2 |
| 4 | CRITICAL precision | ≥ 0.88 | items **predicted** CRITICAL, pooled | 485 | 0.92 | exact power; checkable only after inference |
| 5 | CRITICAL recall, **each** pure language | ≥ 0.91 | gold CRITICAL in that language | **365** | 0.95 | §3 |
| 6 | CRITICAL F1 | ≥ 0.89 | gold CRITICAL, pooled | 365 | — | bounded by 4 and 5; bootstrap CI |
| 7 | CRITICAL → ROUTINE rate | < 0.01 | gold CRITICAL, pooled | 720 | 0.002 | exact power; with zero observed events 368 suffice; at a true 0.5% it is 2,470 |
| 8 | URGENT recall | ≥ 0.86 | gold URGENT, pooled | 570 | 0.90 | exact power |
| 9 | Kinyarwanda accuracy | ≥ 0.80 | gold Kinyarwanda items | 780 | 0.84 | exact power |
| 10 | English accuracy | ≥ 0.86 | gold English items | 570 | 0.90 | exact power |
| 11 | French accuracy | ≥ 0.84 | gold French items | 640 | 0.88 | exact power |
| 12 | Swahili accuracy | ≥ 0.80 | gold Swahili items | 780 | 0.84 | exact power |
| 13 | mixed-language accuracy | ≥ 0.82 | gold mixed items, pooled; **and ≥ 100 per pair** | 710 | 0.86 | exact power on pooled items; the per-pair floor stops one pair standing in for six |
| 14 | latency p50 / p95 | < 150 / < 200 ms | timed batch-1 requests | 1,000 | — | a nearest-rank p95 over 1,000 rests on 50 observations |
| 15 | memory @ 50 concurrent | < 2 GB | one load run on the target machine (D5) | 1 | — | a measurement, not a sample |
| X-ECE | calibration error, 15 bins | < 0.05 | gold items with confidences | 2,000 | — | §5 |
| X-LID-pure | language ID, pure | ≥ 0.92 | gold pure-language items | 590 | 0.95 | exact power |
| X-LID-mixed | language ID, mixed pairs | ≥ 0.85 | gold mixed items | 380 | 0.90 | exact power; the exact pair must be named, since a generic "mixed" is wrong |

`--verify` recomputed the 12 power-derived minimums from scratch (3 min). **It caught one error of mine:** I had
typed 880 for gate 4, and the derived value is 485. It is corrected, and `KINYAMED_SLOW=1 pytest
tests/test_eval_spec.py` pins stored = derived.

**Two deviations from §9.2, for your decision:**
- **E2 — Gate 13.** §9.2 says "mean of 6 combos". I score **pooled** mixed items with a 100-per-pair floor. With
  equal allocation per pair (150) the two are identical. Pooling avoids six under-powered per-pair intervals
  being averaged.
- **E3 — Gate 1.** §9.2 gives "n=100,000". The requirement is 710 **distinct** items. 100,000 rows of templated
  text would carry less information than 710 distinct scenarios.

## 5. Calibration: why ECE needs 2,000 items, and where to measure it

Sampling noise alone gives a **perfectly calibrated** model a non-zero ECE. Simulated in `eval_spec.py`
(confidences uniform on [1/3, 1], correctness drawn at exactly that confidence, 15 bins, 300 trials, seed 7):

| n | mean ECE (calibrated model) | 95th percentile |
|---|---|---|
| 300 | **0.061** | 0.086 |
| 500 | 0.048 | 0.069 |
| 1,000 | 0.033 | 0.047 |
| **2,000** | **0.024** | **0.033** |
| 4,000 | 0.017 | 0.024 |

A 0.05 gate on 300 items fails a perfectly calibrated model most of the time. At 1,000 the noise alone nearly
reaches the gate.

**Proposal (decision E4).** §9.2 says "ECE ≤ 0.05 on the validation split".
- A validation split large enough for that (≥ 2,000) would nearly double clinician effort.
- Instead: fit the single temperature parameter on a **calibration split of 1,500 items**, used for nothing
  else, and measure ECE on the **test set (4,900 items)** with the rule in §2.
- `evaluate.py` does that, draws the reliability diagram (SVG), and refuses both below 2,000 items.

## 6. Target size and allocation

| Split | Per pure language (C / U / R) | Per mixed pair (C / U / R) | Total |
|---|---|---|---|
| **Test** | 1,000 (400 / 300 / 300) | 150 (60 / 45 / 45) | **4,900** (4,000 pure + 900 mixed) |
| **Calibration** | 300 (100 / 100 / 100) | 50 (20 / 15 / 15) | **1,500** |
| **All** | | | **6,400 items, each labelled twice → 12,800 labels + adjudications** |

`check_allocation_meets_requirements()` confirms the test allocation meets every minimum fixed before inference
(it is tested). Gate 4's denominator depends on the model, so it is checked at evaluation time.

**Class balance within the test set** is a design choice for power, not a prevalence estimate: 40% CRITICAL
per pure language. **No metric here estimates real-world performance at clinic prevalence** (§10).

**Phasing (recommended, decision E5).** Kinyarwanda first: 1,000 test + 300 calibration = 1,300 items. That is
the deployment language, and it alone unblocks gates 5 (KW), 9, and the KW row of every pooled metric. Other
languages follow as speakers are found (D4).

## 7. The stratification grid

Four axes: **urgency × language × clinical domain × presentation type.** Only urgency × language is powered;
the other two are coverage axes, and `evaluate.py` never reports a metric per domain or presentation type.

| Axis | Levels | Status |
|---|---|---|
| Urgency | CRITICAL, URGENT, ROUTINE (gold); UNCLASSIFIABLE (excluded, counted) | category **names** fixed; **definitions BLOCKED** (protocol §3) |
| Language | 4 pure + 6 unordered pairs (§4.4); matrix language recorded per mixed item | fixed |
| Clinical domain | from the national triage protocol's own organisation | **BLOCKED**. The repo's 9 corpus domains (cardiac_respiratory … preventive) are a placeholder only; they come from an unratified taxonomy and must not define the grid |
| Presentation type | see below | linguistic types fixed; clinical types **BLOCKED** |

**Presentation types that need no clinical judgement** (definable from the text alone, recorded by the author):
- **Voice:** first person / reported by a relative or carer.
- **Length:** fragment (≤ 5 words) / sentence / narrative (≥ 40 words).
- **Negation:** contains a negated symptom ("no fever").
- **Multiple complaints:** ≥ 2 distinct complaints mentioned.
- **Register:** everyday / formal. Whether a phrasing is everyday speech is the **speaker's** call (D4).
- **Code-switched:** mixed items only; matrix language recorded.

**Presentation types that need a clinical source (BLOCKED on D2/D3):** atypical presentation of a
time-critical condition; paediatric; obstetric; near-boundary pairs (items a clinician judges close to the
CRITICAL/URGENT or URGENT/ROUTINE line). Their definitions must cite `docs/clinical/`.

**Minimum cell counts.**

| Cell | Minimum | Why |
|---|---|---|
| language × urgency (test) | as §6 (e.g. 400 CRITICAL per pure language) | powered (§3–4) |
| language × urgency × domain | ≥ 10 per non-empty cell | coverage only: no domain may be absent from the set; never reported as a metric |
| language × presentation type (each linguistic type) | ≥ 10% of that language's items | coverage only; prevents a set of only tidy first-person sentences (the current corpus's failure mode) |
| mixed pair | ≥ 100 (test) | gate 13 floor |

## 8. Independence of items

The power calculation assumes independent items. Items written as paraphrases of one scenario are correlated.
Effective n for 400 items grouped m to a scenario with intra-scenario correlation ρ is n / (1 + (m−1)ρ):

| items per scenario (m) | ρ = 0.1 | ρ = 0.3 | ρ = 0.5 |
|---|---|---|---|
| 1 | 400 | 400 | 400 |
| 2 | 364 | 308 | 267 |
| 3 | 333 | 250 | 200 |
| 5 | 286 | 182 | 133 |

**Rules.**
- **One item per scenario in the test set.** Paraphrase variants may exist only in the calibration split.
- Every item carries a `scenario_id`, and `evaluate.py` bootstraps by scenario. A test proves that clustered
  errors widen the interval by more than 2×.
- **No test item may share a scenario with the calibration split, or with any training data.** Leakage is
  checked before evaluation (L8), exactly as the phrase holdout is today.

## 9. Inter-annotator agreement (κ) per language

- **Target:** κ ≥ 0.80 (§9.1), per language, judged by the lower bound of a 95% bootstrap interval. It is
  computed on first labels, **before adjudication**.
- **Minimum:** 200 double-labelled items per language to report a κ at all (`KAPPA_MINIMUM_ITEMS_PER_LANGUAGE`).
  Below that, `kappa.py` prints INSUFFICIENT DATA.
- **Precision** (large-sample approximation; the tool itself uses the bootstrap): with observed agreement 0.90
  and chance agreement 0.34, the 95% half-width is ±0.089 at n=100, ±0.063 at n=200, ±0.040 at n=500 and
  ±0.028 at n=1,000. **At n=200 an observed κ of about 0.87 is needed to clear 0.80 (0.87 − 0.063 ≈ 0.81).**
- **Plan:** all 6,400 items are double-labelled, so every pure language has 1,300 κ items.

## 10. What this set cannot establish

- **Real patient speech.** Items are authored vignettes. Real presentations are longer, vaguer, and differ
  in distribution. A pass here is necessary, not sufficient; prospective validation on consented real data needs
  D7 approvals (L10).
- **Clinic prevalence.** The class balance is set for power. Metrics are not the performance a clinic would
  see at its own case mix.
- **Clinical correctness of the taxonomy.** Two clinicians agreeing does not make the category boundaries right;
  that is D2/D3.

## 11. BLOCKED — what I need, exactly

| # | Document or person | Used for |
|---|---|---|
| B1 | **The WHO ETAT document in the edition Rwandan facilities use**, full text, placed in `docs/clinical/`. I have not verified which edition that is and will not cite one from memory. One point to confirm with a clinician: to my understanding ETAT is written for paediatric emergency triage, so it may not cover adults. | label definitions (protocol §3); clinical presentation types |
| B2 | **The Rwanda MoH / RBC triage protocol or clinical guideline** in use at health centres and district hospitals (adult and paediatric), with the mapping of its categories to CRITICAL / URGENT / ROUTINE | the domain axis (§7); the category mapping |
| B3 | **The adult triage tool used in Rwandan facilities**, if it is not ETAT | adult label definitions |
| B4 | **RBC maternal / obstetric danger-sign guidance** | obstetric presentation type |
| B5 | **A lead clinician** (D3) to approve the category mapping and supply or approve worked examples | protocol §3–4 |
| B6 | **Native-speaker clinicians** per language (D4): authors plus two annotators and one adjudicator per language | items, labels, adjudication |
| B7 | **Institutional confirmation** (D7) of whether clinician authoring and labelling of synthetic vignettes needs ethics review at the clinicians' institutions | before engaging anyone |

## 12. Decisions requested

- **E1:** the interval decision rule (§2).
- **E2:** pooled mixed accuracy with a per-pair floor (§4).
- **E3:** distinct-item minimums instead of n = 100,000 (§4).
- **E4:** ECE measured on the test set, with temperature fitted on a separate calibration split (§5).
- **E5:** Kinyarwanda first (§6).

## 13. Reproduce

```bash
cd kinyamed/ml_model
python training/eval_spec.py --report        # every table above (~35 s)
python training/eval_spec.py --verify        # recompute the 12 power-derived minimums (~3 min)
python -m pytest tests/test_eval_spec.py tests/test_gate_evaluate.py tests/test_annotation.py
```
