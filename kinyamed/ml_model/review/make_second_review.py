#!/usr/bin/env python
"""Build a blind second-speaker review sheet from a completed first-pass brief.

Two mechanisms, because they answer different questions.

RATE: the second speaker rates every phrase the first speaker wrote. Catches
phrases that are wrong. Cheap, but it is a judgement about someone else's text and
people are reluctant to reject fluent-looking work.

AUTHOR-BLIND: for a random sample, the second speaker writes their own phrasing
from the English gloss WITHOUT seeing the first speaker's. Comparing the two
independent phrasings measures agreement rather than assent. This is the stronger
signal and the reason the script exists.

The sample is drawn with a fixed seed so it is reproducible and cannot be
gerrymandered after the fact.

Usage:
    python review/make_second_review.py review/speaker_brief_kinyarwanda_FILLED.csv \
        --language kinyarwanda --blind-fraction 0.2
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("filled_brief", type=Path)
    ap.add_argument("--language", required=True)
    ap.add_argument("--blind-fraction", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", type=Path, default=Path("review"))
    args = ap.parse_args()

    rows = list(csv.DictReader(args.filled_brief.open(encoding="utf-8")))
    filled = [r for r in rows if (r.get("your_phrasing") or "").strip()]
    if not filled:
        raise SystemExit("no completed 'your_phrasing' entries found")

    rng = random.Random(args.seed)
    indices = list(range(len(filled)))
    rng.shuffle(indices)
    n_blind = max(1, round(len(filled) * args.blind_fraction))
    blind = set(indices[:n_blind])

    rate_rows, blind_rows = [], []
    for i, r in enumerate(filled):
        common = {"concept_id": r.get("concept_id", ""), "domain": r["domain"],
                  "proposed_urgency": r["proposed_urgency"],
                  "english_gloss": r.get("english_gloss", "")}
        if i in blind:
            # Speaker 1's phrasing is deliberately absent from this file.
            blind_rows.append({**common, "your_independent_phrasing": "",
                               "second_phrasing_optional": "", "notes": ""})
        else:
            rate_rows.append({**common, "phrase_to_rate": r["your_phrasing"],
                              "rating_1_to_4": "", "your_better_phrasing": "",
                              "notes": ""})

    rate_path = args.out_dir / f"second_review_RATE_{args.language}.csv"
    blind_path = args.out_dir / f"second_review_BLIND_{args.language}.csv"
    with rate_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rate_rows[0])); w.writeheader(); w.writerows(rate_rows)
    with blind_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(blind_rows[0])); w.writeheader(); w.writerows(blind_rows)

    key_path = args.out_dir / f"second_review_KEY_{args.language}.csv"
    with key_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["concept_id", "speaker1_phrasing"])
        for i in sorted(blind):
            w.writerow([filled[i].get("concept_id", ""), filled[i]["your_phrasing"]])

    print(f"  {rate_path}  {len(rate_rows)} phrases to rate")
    print(f"  {blind_path}  {len(blind_rows)} to author blind ({args.blind_fraction:.0%})")
    print(f"  {key_path}  speaker 1's phrasings for the blind set — DO NOT SEND")
    print()
    print("  Rating scale to put in front of the second speaker:")
    print("    4  a patient would say this")
    print("    3  acceptable, though I would say it differently")
    print("    2  understandable but not natural")
    print("    1  wrong, misleading, or not Kinyarwanda a patient would use")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
