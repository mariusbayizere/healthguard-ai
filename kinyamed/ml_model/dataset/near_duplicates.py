#!/usr/bin/env python
"""Near-duplicate analysis.

Two complementary measures, because each answers a different question:

*Structural* — exact, over the whole dataset. Every example is built around one
seed symptom phrase, so rows sharing a phrase are near-duplicates of each other
by construction. This is computed exactly, not estimated.

*Jaccard* — MinHash + LSH over a random sample, reporting the fraction of
documents having at least one neighbour above a similarity threshold. This is
the conventional number a reviewer will ask for; it is a sample estimate and is
labelled as one.

Usage:
    python dataset/near_duplicates.py --sample 60000 --threshold 0.8
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MERSENNE_PRIME = (1 << 61) - 1
MAX_HASH = (1 << 32) - 1


def word_shingles(text: str, size: int = 3) -> set[int]:
    """Hashed word n-grams. Word-level, because these texts are short."""
    words = text.lower().split()
    if len(words) < size:
        return {hash(" ".join(words)) & MAX_HASH}
    return {
        hash(" ".join(words[i : i + size])) & MAX_HASH for i in range(len(words) - size + 1)
    }


def minhash_signatures(
    documents: list[set[int]], permutations: int, seed: int
) -> np.ndarray:
    """MinHash signature matrix, shape (len(documents), permutations)."""
    rng = np.random.default_rng(seed)
    a = rng.integers(1, MERSENNE_PRIME, size=permutations, dtype=np.uint64)
    b = rng.integers(0, MERSENNE_PRIME, size=permutations, dtype=np.uint64)

    signatures = np.empty((len(documents), permutations), dtype=np.uint64)
    for index, shingles in enumerate(documents):
        values = np.fromiter(shingles, dtype=np.uint64, count=len(shingles))
        # (a * h + b) mod prime, minimised over the document's shingles.
        hashed = (np.outer(values, a) + b) % MERSENNE_PRIME
        signatures[index] = hashed.min(axis=0)
    return signatures


def lsh_candidates(signatures: np.ndarray, bands: int) -> set[tuple[int, int]]:
    """Candidate pairs: documents colliding in at least one band."""
    documents, permutations = signatures.shape
    rows = permutations // bands
    candidates: set[tuple[int, int]] = set()

    for band in range(bands):
        buckets: dict[bytes, list[int]] = defaultdict(list)
        block = signatures[:, band * rows : (band + 1) * rows]
        for index in range(documents):
            buckets[block[index].tobytes()].append(index)
        for members in buckets.values():
            if len(members) < 2:
                continue
            # A very large bucket means a degenerate band; cap the pairs drawn
            # from it so one bucket cannot dominate the estimate.
            if len(members) > 200:
                members = random.sample(members, 200)
            for i, left in enumerate(members):
                for right in members[i + 1 :]:
                    candidates.add((left, right) if left < right else (right, left))
    return candidates


def jaccard(left: set[int], right: set[int]) -> float:
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def structural_analysis(path: Path) -> dict:
    """Exact near-duplicate structure over the whole dataset."""
    from dataset.validate_dataset import all_symptom_phrases
    from dataset.split_dataset import attribute_phrase

    phrase_index = all_symptom_phrases()
    phrase_counts: Counter[str] = Counter()
    unmatched = 0
    total = 0

    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            total += 1
            # Route through the SPLITTER'S matcher, not a raw `in`. A raw
            # substring match cannot see a {REL} phrase at all - the placeholder
            # is not in the rendered text - and also misses the terminal stop the
            # renderer drops and the capital it lowercases after an opener. Those
            # are the same three defects attribute_phrase was fixed for, three
            # times, and this tool never got the fix: at the v2 freeze it reported
            # 87 of 165 phrases and 95.7% of rows unmatched, which is exactly the
            # 86 first-person phrases plus the one second phrasing.
            #
            # Reusing the function rather than reimplementing it is the point:
            # the rows-per-phrase figure the paper quotes now cannot drift from
            # the attribution the splits are built on.
            phrase = attribute_phrase(row["text"], row["family"], phrase_index)
            if phrase is None:
                unmatched += 1
            else:
                phrase_counts[phrase] += 1

    sizes = sorted(phrase_counts.values())
    return {
        "total": total,
        "distinct_phrases": len(phrase_counts),
        "unmatched_rows": unmatched,
        "rows_per_phrase_min": sizes[0] if sizes else 0,
        "rows_per_phrase_median": sizes[len(sizes) // 2] if sizes else 0,
        "rows_per_phrase_max": sizes[-1] if sizes else 0,
        "rows_per_phrase_mean": round(total / max(len(phrase_counts), 1), 1),
    }


def jaccard_analysis(
    path: Path, sample_size: int, threshold: float, permutations: int, bands: int, seed: int
) -> dict:
    """Sampled MinHash/LSH estimate of the near-duplicate rate."""
    rng = random.Random(seed)
    reservoir: list[str] = []
    seen = 0

    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            seen += 1
            if len(reservoir) < sample_size:
                reservoir.append(row["text"])
            else:
                position = rng.randrange(seen)
                if position < sample_size:
                    reservoir[position] = row["text"]

    started = time.monotonic()
    documents = [word_shingles(text) for text in reservoir]
    signatures = minhash_signatures(documents, permutations, seed)
    candidates = lsh_candidates(signatures, bands)

    near_pairs = 0
    involved: set[int] = set()
    for left, right in candidates:
        if jaccard(documents[left], documents[right]) >= threshold:
            near_pairs += 1
            involved.add(left)
            involved.add(right)

    return {
        "population": seen,
        "sample_size": len(reservoir),
        "threshold": threshold,
        "permutations": permutations,
        "bands": bands,
        "candidate_pairs": len(candidates),
        "near_duplicate_pairs": near_pairs,
        "documents_with_a_near_duplicate": len(involved),
        "near_duplicate_document_rate": round(len(involved) / max(len(reservoir), 1), 5),
        "seconds": round(time.monotonic() - started, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("dataset/raw/symptoms_large.csv"))
    parser.add_argument("--sample", type=int, default=60_000)
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--permutations", type=int, default=64)
    parser.add_argument("--bands", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    structural = structural_analysis(args.input)
    print("Structural near-duplicates (exact, whole dataset)")
    print(f"  rows                       {structural['total']:,}")
    print(f"  distinct seed phrases      {structural['distinct_phrases']}")
    print(f"  rows sharing a phrase      min {structural['rows_per_phrase_min']:,} / "
          f"median {structural['rows_per_phrase_median']:,} / "
          f"max {structural['rows_per_phrase_max']:,} "
          f"(mean {structural['rows_per_phrase_mean']:,})")
    print(f"  rows matching no phrase    {structural['unmatched_rows']:,}")

    sampled = jaccard_analysis(
        args.input, args.sample, args.threshold, args.permutations, args.bands, args.seed
    )
    print(f"\nJaccard near-duplicates (MinHash/LSH estimate, sample of {sampled['sample_size']:,})")
    print(f"  word 3-gram shingles, {sampled['permutations']} permutations, {sampled['bands']} bands")
    print(f"  candidate pairs            {sampled['candidate_pairs']:,}")
    print(f"  pairs at J >= {sampled['threshold']}          {sampled['near_duplicate_pairs']:,}")
    print(
        f"  documents with a neighbour {sampled['documents_with_a_near_duplicate']:,} "
        f"({sampled['near_duplicate_document_rate']:.2%} of sample)"
    )
    print(f"  computed in {sampled['seconds']}s")

    report = {"structural": structural, "jaccard_sample": sampled}
    destination = args.input.with_suffix(".neardup.json")
    destination.write_text(json.dumps(report, indent=2))
    print(f"\nReport written to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
