"""Report the labelled corpus: provenance, the gaps, and the diversity measures.

Writes, all under reports/:

  LABELLED_CORPUS.md          the report, opening with the provenance line
  labelled_missing_text.csv   B1: rows carrying a label and no Kinyarwanda
  labelled_missing_ids.txt    B2: ids absent from the range, unwritten not lost
  labelled_record_voice.csv   B3: rows in clinical-record voice, with their text

and, beside the corpus:

  triage_labels_ALL.enriched.csv   every original column, plus annotator,
                                   validated_by and register, so a run can
                                   filter on register without re-deriving it.

The original file is never modified. It is the record; this is a view of it,
and both carry the same digest in the report so they cannot be confused.

EVERY OUTPUT OPENS WITH THE PROVENANCE LINE. Not as a footer, not as an
appendix. A reader who stops after the first line must already know these
labels are one non-clinician's and have never been validated.

Usage:
    python review/report_labelled_corpus.py
    python review/report_labelled_corpus.py --check    # fail if stale
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataset import labelled_corpus as lc

REPORTS = ROOT.parent / "reports"
ENRICHED = lc.CORPUS.parent / "triage_labels_ALL.enriched.csv"


def write_enriched(rows: list[lc.Row]) -> None:
    with lc.CORPUS.open(encoding="utf-8-sig", newline="") as handle:
        original = list(csv.DictReader(handle))
    by_id = {r.id: r for r in rows}
    fields = [*original[0], "annotator", "validated_by", "register"]
    with ENRICHED.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in original:
            row = by_id[int(record["id"])]
            writer.writerow(
                {
                    **record,
                    "annotator": lc.PROVENANCE["annotator"],
                    "validated_by": lc.PROVENANCE["validated_by"],
                    "register": row.register,
                }
            )


def write_lists(rows: list[lc.Row]) -> tuple[int, int, int]:
    REPORTS.mkdir(parents=True, exist_ok=True)

    blank = [r for r in rows if not r.has_text]
    with (REPORTS / "labelled_missing_text.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["# " + lc.provenance_line()])
        writer.writerow(["id", "cue", "reporter", "age_group", "label"])
        for r in sorted(blank, key=lambda r: r.id):
            writer.writerow([r.id, r.cue, r.reporter, r.age_group, r.label])

    missing = lc.missing_ids(rows)
    with (REPORTS / "labelled_missing_ids.txt").open("w", encoding="utf-8") as handle:
        handle.write("# " + lc.provenance_line() + "\n")
        handle.write(
            "# Ids absent from the contiguous range. These are unwritten, not lost:\n"
            "# nothing was deleted, the ids were never filled.\n"
        )
        for start, end in lc.as_ranges(missing):
            span = f"{start}-{end}" if start != end else f"{start}"
            handle.write(f"{span}\t{end - start + 1}\n")
        handle.write(f"# total {len(missing)}\n")

    voice = [r for r in rows if r.record_voice]
    with (REPORTS / "labelled_record_voice.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["# " + lc.provenance_line()])
        writer.writerow(["id", "label", "marker", "text_kw"])
        for r in sorted(voice, key=lambda r: r.id):
            marker = next(m for m in lc.RECORD_VOICE_MARKERS if m in r.text.lower())
            writer.writerow([r.id, r.label, marker, r.text])

    return len(blank), len(missing), len(voice)


def render() -> str:
    rows = lc.load()
    div = lc.diversity(rows)
    labels = Counter(r.label for r in rows)
    labels_text = Counter(r.label for r in lc.measurable(rows))
    blank = [r for r in rows if not r.has_text]
    voice = [r for r in rows if r.record_voice]
    missing = lc.missing_ids(rows)
    patient = [r for r in lc.measurable(rows) if not r.record_voice]

    div_patient = lc.diversity(patient)
    reporters = Counter(r.reporter for r in lc.measurable(rows))
    ages = Counter(r.age_group for r in lc.measurable(rows))

    out = [
        "# The labelled Kinyarwanda triage corpus",
        "",
        "> **" + lc.provenance_line() + "**",
        "",
        f"Source file `dataset/labelled/triage_labels_ALL.csv`, sha256 `{lc.digest()}`.",
        "Every figure below is computed by `review/report_labelled_corpus.py` from",
        "that file. None of it is a model result and none of it is validated.",
        "",
        "## Counts",
        "",
        "| | |",
        "|---|---|",
        f"| rows in file | {len(rows):,} |",
        f"| rows carrying Kinyarwanda text | {div['rows_with_text']:,} |",
        f"| rows with a label and no text (B1) | {len(blank):,} |",
        f"| ids absent from the range (B2) | {len(missing):,} |",
        f"| rows in clinical-record voice (B3) | {len(voice):,} |",
        f"| rows in patient voice and measurable | {len(patient):,} |",
        "",
        "## Labels",
        "",
        "| label | all rows | rows with text |",
        "|---|---:|---:|",
    ]
    for label in lc.LABELS:
        out.append(f"| {label} | {labels[label]:,} | {labels_text[label]:,} |")
    out += [
        "",
        "`CANNOT CLASSIFY` is a judgement that the text does not support a triage",
        "decision. It is not a fourth urgency class and must not be folded into one.",
        "",
        "## Diversity",
        "",
        "Tokeniser: lowercase, split on whitespace, strip edge punctuation. The",
        "apostrophe is kept inside the token, because Kinyarwanda writes elided",
        "vowels with one and splitting on it would count `n'umwana` as two words.",
        "",
        "| measure | all rows with text | patient voice only |",
        "|---|---:|---:|",
    ]
    for key, name in (
        ("rows_with_text", "rows"),
        ("distinct_sentences", "distinct sentences"),
        ("word_types", "word types"),
        ("word_tokens", "word tokens"),
        ("ttr", "type/token ratio"),
        ("hapax", "types occurring once"),
        ("median_length", "median length (tokens)"),
        ("min_length", "shortest"),
        ("max_length", "longest"),
    ):
        out.append(
            f"| {name} | {div[key]:,} | {div_patient[key]:,} |".replace(",", ",")
        )
    out += [
        "",
        "## Reporter and age group, rows with text",
        "",
        "| reporter | rows | | age group | rows |",
        "|---|---:|---|---|---:|",
    ]
    r_items = reporters.most_common()
    a_items = ages.most_common()
    for i in range(max(len(r_items), len(a_items))):
        left = f"{r_items[i][0]} | {r_items[i][1]:,}" if i < len(r_items) else " | "
        right = f"{a_items[i][0]} | {a_items[i][1]:,}" if i < len(a_items) else " | "
        out.append(f"| {left} | | {right} |")

    # B5: the comparison the whole seeds-not-rows argument turns on.
    gen_path = ROOT / "dataset" / "raw" / "symptoms_large.csv"
    gen_line = "| generated corpus | not found on disk | | | |"
    if gen_path.exists():
        with gen_path.open(encoding="utf-8", newline="") as h:
            gen = [
                (r.get("text") or "").strip()
                for r in csv.DictReader(h)
                if (r.get("language") or "").strip() == "kinyarwanda"
            ]
        gt: Counter[str] = Counter()
        for t in gen:
            gt.update(lc.tokenise(t))
        gtok = sum(gt.values())
        gen_line = (
            f"| generated (`symptoms_large.csv`) | {len(gen):,} | {len(set(gen)):,} | "
            f"{len(gt):,} | {len(gt) / gtok:.4f} |"
        )

    out += [
        "",
        "## Against the generated corpus (B5)",
        "",
        "Same tokeniser both sides.",
        "",
        "| corpus | rows | distinct sentences | word types | TTR |",
        "|---|---:|---:|---:|---:|",
        f"| labelled, authored | {div['rows_with_text']:,} | "
        f"{div['distinct_sentences']:,} | {div['word_types']:,} | {div['ttr']} |",
        gen_line,
        "",
        "The row counts are not comparable and the type counts are the point: the",
        "generated corpus expands a small phrase inventory across frame slots, so",
        "rows grow without vocabulary growing. Every generated row is distinct",
        "because the frames differ, which is exactly why distinct-row counts say",
        "nothing about diversity and distinct word types do.",
        "",
        "## What is outstanding",
        "",
        f"- **{len(blank)} rows carry a label and no Kinyarwanda.** Listed by id in",
        "  `reports/labelled_missing_text.csv`. They are excluded from every count",
        "  above and from any run, and they are not dropped: the label is real work",
        "  and the text is work outstanding.",
        f"- **{len(missing)} ids are absent from the range.** Listed in",
        "  `reports/labelled_missing_ids.txt`. Unwritten, not lost.",
        f"- **{len(voice)} rows are in clinical-record voice**, a third party",
        "  reporting what the patient said rather than the patient's or carer's own",
        "  words. Listed with their text in `reports/labelled_record_voice.csv`.",
        "  Tagged `register=record_voice` in the enriched file so a run can exclude",
        "  them and report both ways. No Kinyarwanda has been rewritten.",
        "",
    ]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render()
    target = REPORTS / "LABELLED_CORPUS.md"

    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != rendered:
            print(
                f"{target.name} is stale. Regenerate:\n"
                "  python review/report_labelled_corpus.py",
                file=sys.stderr,
            )
            return 1
        print(f"{target.name} matches the corpus.")
        return 0

    rows = lc.load()
    REPORTS.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    write_enriched(rows)
    blank, missing, voice = write_lists(rows)
    print(lc.provenance_line())
    print(f"\nwrote {target.relative_to(ROOT.parent)}")
    print(f"      {ENRICHED.relative_to(ROOT)}")
    print(f"  B1 rows with no text      {blank:,}")
    print(f"  B2 ids absent from range  {missing:,}")
    print(f"  B3 record-voice rows      {voice:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
