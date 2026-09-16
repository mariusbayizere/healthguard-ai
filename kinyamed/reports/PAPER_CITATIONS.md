# Citation and class-C figure audit

**Checked 2026-09-17.** Rule applied: an entry is verified only if a source was **actually
fetched** in this session and its metadata read from it. Nothing here comes from memory, and
nothing comes from a search snippet alone unless the snippet is the catalogue record itself,
which is marked where it applies.

Verified entries live in `ml_model/paper/references.bib`. Everything below the line needs a
source I could not fetch, and is **not** in the bibliography.

---

## Verified (in `references.bib`)

| Entry | How it was verified |
|---|---|
| WHO ETAT, *Manual for participants*, 2005, ISBN 92-4-154687-5 | Read from the PDF we hold (`docs/clinical/participant_manual.pdf`), imprint page. Also recorded: facilitator ISBN 92-4-154688-3, NLM WS 205, and that the course was developed by Prof. Elizabeth Molyneux |
| Adelani et al., *MasakhaNER*, TACL 9:1116–1131, 2021, doi 10.1162/tacl_a_00416 | ACL Anthology page fetched; BibTeX reproduced verbatim (63 authors) |
| Adelani et al., *MasakhaNER 2.0*, EMNLP 2022, pp. 4488–4508, doi 10.18653/v1/2022.emnlp-main.298 | ACL Anthology page fetched; BibTeX reproduced verbatim (44 authors) |
| Niyongabo, Hong, Kreutzer, Huang, *KINNEWS and KIRNEWS*, COLING 2020, pp. 5507–5521, doi 10.18653/v1/2020.coling-main.480 | ACL Anthology page fetched; BibTeX reproduced verbatim |
| Rutunda et al., *Large language models for frontline healthcare support in low-resource settings*, Nature Health 1(2):191–197, 2026, doi 10.1038/s44360-025-00038-1 | Europe PMC REST record fetched. **Author names are initials only** — the Nature page redirects to authentication and PMC serves a CAPTCHA, so given names must be expanded from the article PDF before submission |
| WHO–ICRC *Basic Emergency Care*, 2018, ISBN 978-92-4-151308-1, CC BY-NC-SA 3.0 IGO | WHO publications item page fetched |
| WHO *Managing complications in pregnancy and childbirth*, 2nd ed., 2017, ISBN 978-92-4-156549-3 | WHO catalogue listing (ISBN carried in the item URL). **The item page returned 403 to an automated fetch**, so it was not read directly |

## UNVERIFIED — not in the bibliography, and what each needs

| Entry | Status | What it needs |
|---|---|---|
| **WHO IMCI Chart Booklet, 2014, ISBN 978-92-4-150682-3** | **AMBIGUOUS — possible mis-citation in our own paper.** WHO pages carrying that ISBN are titled both *IMCI chart booklet* and *IMCI set of distance learning modules*. Our paper attaches it to the chart booklet | The WHO item page for 9789241506823, or the booklet's own imprint page, read directly. If the ISBN belongs to the distance-learning set, the paper's citation is wrong and must be corrected |
| **ESI (Emergency Severity Index) handbook** | UNVERIFIED. The instrument changed hands: ENA acquired it in 2019 and issued a v4 handbook in 2020, while the widely cited v4 implementation handbook is an earlier AHRQ publication | A decision on which edition the paper means, then that edition's title page (publisher, year, editors) |
| **Manchester Triage System** | UNVERIFIED. Publisher and retailer listings give Mackway-Jones, Marsden and Windle, *Emergency Triage*, 3rd ed., Wiley/BMJ Books, 2014 | The publisher's own record or the book's title page, fetched |
| **CHW benchmarking dataset (figshare)** | PARTIAL. The DOI 10.6084/m9.figshare.29213147 resolves to a Springer Nature figshare item whose title slug reads *A Realistic Rwandan Communty Health Worker Generated Vingette-based I e Open-ended Questions Benchmarking Dataset with Associated Clinician and LLM Responses* (the typos are in the source). The item page returned 403 | Authors, licence, posted year and the item count, read from the figshare page. Our "524 questions" figure comes from `docs/language-resources.md`, not from the item |
| **MedlinePlus Kinyarwanda immunisation material** | UNVERIFIED — described in the paper but never named | The collection's own page; `docs/language-resources.md` records only that CDC items are US-government public domain and Immunization Action Coalition items carry their own terms |
| **Swahili health corpus** | UNVERIFIED — described and measured in `docs/swahili-corpus-assessment.md`, not named in the paper | The corpus's own record (name, licence, host) |
| **Masakhane** (as a research collective) | **Cut.** It was named decoratively; the paper no longer relies on it |

---

## Class-C figures: the document and page each would need

Class C = recorded in a repository document with no script behind it (`PAPER_NUMBERS.md`).

| Figure | Where it is used | Document and page needed | Status |
|---|---|---|---|
| ETAT is defined on examination signs; rules against history on convulsions; no remote or written triage; population is children; categories EMERGENCY / PRIORITY / NON-URGENT | Related work §"Why we make no comparison" | ETAT manual, printed pp. 3–5, 7, 26, 35–36, 44, 67–68; p. 1 for population; Chart 2 | **VERIFIED NOW.** The manual is in `docs/clinical/`, the page references were checked against the PDF in `TAXONOMY_SCOPE.md` §2, and the imprint page is confirmed above |
| Anchor table: 24 IMCI, 15 BEC, 11 MCPC, 20 clinician-defined | Method §"Concept taxonomy" | **Requires the three guidance documents, none of which we hold**: IMCI Chart Booklet 2014, WHO–ICRC BEC 2018, WHO MCPC 2017 (2nd ed.). Each concept's anchor must be checked against the cited page in the document it names | **BLOCKED on documents.** The paper marks the table as unverified anchor records |
| Concept total (68 / 80 / 126 / 127 / 128) | Method | No external document: an internal reconciliation of `docs/clinical-anchors.md`, `docs/triage-taxonomy.md`, `docs/licensing.md`, `docs/v2-sizing.md` and the review CSVs against the authoring record | **BLOCKED on internal work.** The paper asserts no total |
| Phrase provenance split (previously 82 of 165, 49.7%) | Method, Limitations | No external document: an aggregation script over the per-phrase provenance column | **Cut from the paper**; would take an hour to make class A |
| "60 of 61 concepts split across the holdout"; 42 shared characters | Discussion | `docs/phrase-group-closure.md`, §7, where the measurement was made during design | **Marked NOT REPRODUCIBLE in the paper.** Would become class A if a script recomputed it from the authored inventory |
| Keyword fallback: 5.7% caught, 94.3% to routine | System §"It fails closed" | Would need the Phase 0 script `scratchpad/ml_audit.py`, which was never committed and is gone | **Numbers cut**; direction stated, marked NOT REPRODUCIBLE |
| Mixed rows "nearly half of v1" | System §"Why the generator refuses" | `docs/language-resources.md` | Softened; document named |
| External corpus sizes: 3,449 news articles; 5,609 CHW questions; 26,390 / 42,576 / 28,621 lines | Related work, Method | The third-party sources themselves (see UNVERIFIED table above) | Attributed to our audits, not to the sources |
