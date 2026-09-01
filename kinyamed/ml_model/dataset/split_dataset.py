#!/usr/bin/env python
"""Split the corpus into leakage-controlled train/eval halves.

Holds out whole groups — either a family (language-pair:label:domain) or a
substring-closed phrase group — so no eval row is a paraphrase of a training
row it shares a seed phrase with.

Crash safety
------------
This runs on a memory-constrained box where systemd-oomd kills the whole
terminal cgroup once the user slice passes its pressure limit, so a kill can
arrive at any instruction and leave no traceback:

  * the corpus is streamed; row bodies are never all resident at once
  * every output goes to a sibling temp file, is fsynced, and is renamed into
    place with os.replace — a reader sees the old file or the new one, never a
    half-written file that still passes a shallow check
  * each step records a checkpoint keyed to a fingerprint of its inputs, so a
    restart costs one step rather than the whole run, and an edited upstream
    file correctly invalidates everything downstream

Phrase attribution is the expensive part (184 seed phrases tested against a
million rows), so the scan resolves each row to a phrase id once and persists
the ids; the write pass replays them instead of re-matching.

Usage:
    python dataset/split_dataset.py --strategy phrase
    python dataset/split_dataset.py --strategy phrase --out-dir /tmp/repro
    python dataset/split_dataset.py --strategy family --restart
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from array import array
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.atomicio import (  # noqa: E402
    Checkpoint,
    atomic_write,
    atomic_write_json,
    peak_rss_mib_total,
    sweep_partials,
)
from dataset.validate_dataset import all_symptom_phrases  # noqa: E402

COLUMNS = ["text", "language", "label", "domain", "family", "phrase", "phrase_group"]
# Rows per unit of work handed to a worker. Large enough that pickling overhead
# stays negligible, small enough that the in-flight queue is bounded.
BATCH_ROWS = 20_000
MAX_WORKERS = 2


def phrase_components() -> dict[str, str]:
    """Map every seed phrase to the id of its substring-closed group.

    Some phrases contain others ("maumivu makali ya tumbo" inside "maumivu
    makali ya tumbo wakati wa ujauzito na damu"). Holding out only the inner one
    would still expose its exact characters in every training row built on the
    outer one — an exact-match check reports zero overlap while the model has
    plainly seen the string. Nested phrases therefore move as one unit.

    Matching is deliberately cross-language: leakage is textual, and a shared
    substring leaks regardless of which language list the phrases came from.
    """
    phrases = sorted({p for values in all_symptom_phrases().values() for p in values})
    parent = {phrase: phrase for phrase in phrases}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for outer in phrases:
        for inner in phrases:
            if inner != outer and inner in outer:
                union(inner, outer)

    return {phrase: find(phrase) for phrase in phrases}


def substring_violations(train_phrases: set[str], eval_phrases: set[str]) -> list[dict]:
    """Held-out phrases whose characters still appear in a training phrase."""
    violations: list[dict] = []
    for held in sorted(eval_phrases):
        for trained in sorted(train_phrases):
            if held and trained and (held in trained or trained in held):
                violations.append({"eval_phrase": held, "train_phrase": trained})
    return violations


def attribute_phrase(text: str, family: str, phrase_index: dict[str, list[str]]) -> str | None:
    """The seed phrase a row was built around; longest match wins.

    Matching is case-insensitive. An utterance-form phrase is capitalised when it
    starts the sentence and lowercased when it follows a greeting, so a
    case-sensitive match loses every row with an opener — which would drop those
    rows out of the phrase holdout and out of the leakage analysis without any
    error being raised.
    """
    phrase_language = family.split("->", 1)[1].split(":", 1)[0]
    lowered = text.lower()
    for phrase in phrase_index.get(phrase_language, ()):
        if phrase.lower() in lowered:
            return phrase
    return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --- parallel attribution -------------------------------------------------
# Workers are read-only: they resolve (text, family) pairs to a phrase and send
# back plain strings. Ordering is preserved by imap, so the result is identical
# whether one worker or two did the matching.

_INDEX: dict[str, list[str]] | None = None


def _init_worker() -> None:
    global _INDEX
    _INDEX = all_symptom_phrases()


def _attribute_batch(batch: list[tuple[str, str]]) -> list[str]:
    index = _INDEX if _INDEX is not None else all_symptom_phrases()
    return [attribute_phrase(text, family, index) or "" for text, family in batch]


def _batched(iterable, size: int):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def stream_rows(path: Path):
    """Yield source rows in file order, one dict at a time."""
    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


# --- step 1: scan ---------------------------------------------------------


def scan(path: Path, strategy: str, workers: int) -> tuple[array, list[str], dict]:
    """One streaming pass: resolve phrases and count group sizes.

    Returns the per-row phrase ids, the phrase vocabulary they index into, and
    the aggregates choose_holdout needs. Row bodies are discarded as they go.
    """
    components = phrase_components()
    vocab: list[str] = []
    vocab_ids: dict[str, int] = {}
    phrase_ids = array("i")

    sizes: Counter[str] = Counter()
    strata: dict[tuple[str, str], set[str]] = defaultdict(set)
    stratum_rows: Counter[tuple[str, str]] = Counter()
    total = 0

    def group_of(row: dict, phrase: str) -> str:
        if strategy == "family":
            return row["family"]
        return components.get(phrase, phrase)

    def absorb(row_batches: list[list[dict]], phrase_batches: list[list[str]]) -> None:
        nonlocal total
        for batch, phrases in zip(row_batches, phrase_batches):
            for row, phrase in zip(batch, phrases):
                pid = vocab_ids.get(phrase)
                if pid is None:
                    pid = len(vocab)
                    vocab_ids[phrase] = pid
                    vocab.append(phrase)
                phrase_ids.append(pid)
                group = group_of(row, phrase)
                sizes[group] += 1
                stratum = (row["language"], row["label"])
                strata[stratum].add(group)
                stratum_rows[stratum] += 1
                total += 1

    pool = Pool(workers, initializer=_init_worker) if workers > 1 else None
    pending_rows: list[list[dict]] = []
    pending_pairs: list[list[tuple[str, str]]] = []

    def flush() -> None:
        if not pending_pairs:
            return
        if pool is not None:
            results = pool.map(_attribute_batch, pending_pairs)
        else:
            results = [_attribute_batch(pairs) for pairs in pending_pairs]
        absorb(pending_rows, results)
        pending_rows.clear()
        pending_pairs.clear()

    try:
        for batch in _batched(stream_rows(path), BATCH_ROWS):
            pending_rows.append(batch)
            pending_pairs.append([(row["text"], row["family"]) for row in batch])
            if len(pending_pairs) >= max(workers, 1):
                flush()
        flush()
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    aggregates = {
        "total": total,
        "sizes": dict(sizes),
        "strata": [
            {"language": lang, "label": label, "groups": sorted(groups),
             "rows": stratum_rows[(lang, label)]}
            for (lang, label), groups in sorted(strata.items())
        ],
    }
    return phrase_ids, vocab, aggregates


def choose_holdout(aggregates: dict, eval_fraction: float, seed: int) -> set[str]:
    """Pick whole groups for the eval split, stratified by (language, label).

    Selecting within each stratum keeps the eval split's class and language
    balance close to the corpus, which a globally greedy choice would not.
    """
    rng = random.Random(seed)
    sizes = aggregates["sizes"]
    holdout: set[str] = set()
    for stratum in aggregates["strata"]:
        groups = set(stratum["groups"])
        target = stratum["rows"] * eval_fraction
        candidates = sorted(groups)
        rng.shuffle(candidates)
        # Best-fit rather than "add until we pass the target". Groups are large
        # and indivisible, so a naive greedy pass overshoots badly — a single
        # 14k family can be most of a stratum.
        candidates.sort(key=lambda group: -sizes[group])
        selected = 0
        for group in candidates:
            # Training must retain at least one group per (language, label).
            if len(holdout & groups) >= len(groups) - 1:
                break
            if selected + sizes[group] <= target * 1.05:
                holdout.add(group)
                selected += sizes[group]
        if selected == 0:
            # Nothing fitted; take the group closest to the target so the
            # stratum is still represented in eval.
            available = [g for g in candidates if g not in holdout]
            if len(available) > 1:
                best = min(available, key=lambda group: abs(sizes[group] - target))
                holdout.add(best)
    return holdout


# --- step 3: write --------------------------------------------------------


class SideStats:
    """Counters accumulated in file order, so summaries match a serial pass."""

    def __init__(self) -> None:
        self.rows = 0
        self.labels: Counter[str] = Counter()
        self.languages: Counter[str] = Counter()
        self.families: set[str] = set()
        self.phrases: set[str] = set()
        self.phrase_rows: Counter[str] = Counter()

    def add(self, row: dict) -> None:
        self.rows += 1
        self.labels[row["label"]] += 1
        self.languages[row["language"]] += 1
        self.families.add(row["family"])
        self.phrases.add(row["phrase"])
        self.phrase_rows[row["phrase"]] += 1

    def summary(self) -> dict:
        return {
            "rows": self.rows,
            "labels": dict(self.labels),
            "languages": dict(self.languages),
            "families": len(self.families),
            "phrases": len(self.phrases),
        }


def write_split(
    source: Path,
    strategy: str,
    holdout: set[str],
    phrase_ids: array,
    vocab: list[str],
    train_path: Path,
    eval_path: Path,
) -> tuple[SideStats, SideStats, set[str]]:
    """Stream the corpus once, routing each row to train or eval.

    Both handles are atomic: if this dies partway, neither destination is
    touched, so there is no output that looks complete but is short.
    """
    components = phrase_components()
    train_stats, eval_stats = SideStats(), SideStats()
    eval_texts: set[str] = set()

    with atomic_write(train_path, "w", newline="", encoding="utf-8") as train_handle, \
            atomic_write(eval_path, "w", newline="", encoding="utf-8") as eval_handle:
        train_writer = csv.DictWriter(train_handle, fieldnames=COLUMNS, extrasaction="ignore")
        eval_writer = csv.DictWriter(eval_handle, fieldnames=COLUMNS, extrasaction="ignore")
        train_writer.writeheader()
        eval_writer.writeheader()

        for position, row in enumerate(stream_rows(source)):
            phrase = vocab[phrase_ids[position]]
            row["phrase"] = phrase
            # The split groups by component, not by phrase, so nested phrases
            # cannot be separated.
            row["phrase_group"] = components.get(phrase, phrase)
            group = row["family"] if strategy == "family" else row["phrase_group"]
            if group in holdout:
                eval_writer.writerow(row)
                eval_stats.add(row)
                eval_texts.add(row["text"])
            else:
                train_writer.writerow(row)
                train_stats.add(row)
    return train_stats, eval_stats, eval_texts


# --- step 4: leakage ------------------------------------------------------


def leakage_report(
    train_path: Path, train_stats: SideStats, eval_stats: SideStats, eval_texts: set[str]
) -> dict:
    """What actually crosses the split boundary.

    Exact text overlap is measured by streaming the written train file against
    the eval texts, rather than holding both sides in memory at once.
    """
    shared_texts: set[str] = set()
    with train_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["text"] in eval_texts:
                shared_texts.add(row["text"])

    shared_phrases = sorted(train_stats.phrases & eval_stats.phrases)
    leaked_rows = sum(
        count for phrase, count in _eval_rows_by_phrase(eval_stats).items()
        if phrase in train_stats.phrases
    )
    violations = substring_violations(train_stats.phrases, eval_stats.phrases)

    return {
        "exact_text_overlap": len(shared_texts),
        "family_overlap": len(train_stats.families & eval_stats.families),
        "phrase_overlap": len(shared_phrases),
        "substring_violations": len(violations),
        "substring_violation_detail": violations[:10],
        "eval_rows_whose_phrase_appears_in_train": leaked_rows,
        "eval_rows_leaked_fraction": round(leaked_rows / max(eval_stats.rows, 1), 4),
        "shared_phrase_sample": shared_phrases[:5],
    }


def _eval_rows_by_phrase(eval_stats: SideStats) -> Counter:
    return eval_stats.phrase_rows


# --- checkpoint plumbing --------------------------------------------------


def scan_fingerprint(source_digest: str, strategy: str) -> str:
    return f"{source_digest}:{strategy}"


def choice_fingerprint(source_digest: str, strategy: str, seed: int, fraction: float) -> str:
    return f"{source_digest}:{strategy}:{seed}:{fraction}"


def save_scan(state_dir: Path, phrase_ids: array, vocab: list[str], aggregates: dict) -> None:
    with atomic_write(state_dir / "phrase_ids.bin", "wb") as handle:
        phrase_ids.tofile(handle)
    atomic_write_json(state_dir / "scan.json", {"vocab": vocab, "aggregates": aggregates})


def load_scan(state_dir: Path) -> tuple[array, list[str], dict]:
    payload = json.loads((state_dir / "scan.json").read_text())
    phrase_ids = array("i")
    blob = (state_dir / "phrase_ids.bin").read_bytes()
    phrase_ids.frombytes(blob)
    return phrase_ids, payload["vocab"], payload["aggregates"]


# --- reporting ------------------------------------------------------------


def print_report(
    strategy: str,
    total: int,
    train_summary: dict,
    eval_summary: dict,
    holdout: set[str],
    sizes: dict,
    leakage: dict,
) -> None:
    print(f"Strategy            : hold out whole {strategy} groups")
    print(f"Total rows          : {total:,}")
    print(
        f"Train               : {train_summary['rows']:,} "
        f"({train_summary['rows'] / total:.2%})  "
        f"{train_summary['families']} families, {train_summary['phrases']} phrases"
    )
    print(
        f"Eval                : {eval_summary['rows']:,} "
        f"({eval_summary['rows'] / total:.2%})  "
        f"{eval_summary['families']} families, {eval_summary['phrases']} phrases"
    )

    for name, summary in (("Train", train_summary), ("Eval", eval_summary)):
        print(f"\n{name} balance:")
        for label, count in sorted(summary["labels"].items()):
            print(f"  {label:<9} {count:>9,}  {count / summary['rows']:6.2%}")
        for language, count in sorted(summary["languages"].items()):
            print(f"  {language:<12} {count:>9,}  {count / summary['rows']:6.2%}")

    print(f"\nHeld-out {strategy} groups ({len(holdout)}):")
    for group in sorted(holdout, key=lambda g: -sizes[g]):
        print(f"  {group:<52} {sizes[group]:>7,}")

    print("\nCross-split leakage:")
    print(f"  identical texts in both splits          {leakage['exact_text_overlap']:,}")
    print(f"  families in both splits                 {leakage['family_overlap']:,}")
    print(f"  seed phrases in both splits             {leakage['phrase_overlap']:,}")
    print(f"  substring violations across the split   {leakage['substring_violations']:,}")
    for violation in leakage["substring_violation_detail"]:
        print(f"      {violation['eval_phrase']!r} <-> {violation['train_phrase']!r}")
    print(
        f"  eval rows whose phrase is in train      "
        f"{leakage['eval_rows_whose_phrase_appears_in_train']:,} "
        f"({leakage['eval_rows_leaked_fraction']:.2%})"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("dataset/raw/symptoms_large.csv"))
    parser.add_argument("--strategy", choices=("family", "phrase"), default="family")
    parser.add_argument("--eval-fraction", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("dataset/processed"))
    parser.add_argument(
        "--workers", type=int, default=MAX_WORKERS,
        help=f"Parallel attribution workers, capped at {MAX_WORKERS}.",
    )
    parser.add_argument("--restart", action="store_true", help="Ignore any existing checkpoint.")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing splits.")
    args = parser.parse_args()

    workers = max(1, min(args.workers, MAX_WORKERS))
    if args.workers > MAX_WORKERS:
        print(f"note: --workers {args.workers} capped to {MAX_WORKERS}\n")

    strategy = args.strategy
    out_dir = args.out_dir
    state_dir = out_dir / f".split_{strategy}_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = Checkpoint(state_dir / "checkpoint.json")
    if args.restart:
        for step in ("scan", "choose", "write", "leakage"):
            checkpoint.clear(step)

    peaks: dict[str, float] = {}

    def record(step: str) -> None:
        peaks[step] = peak_rss_mib_total()

    print(f"Source              : {args.input}")
    source_digest = sha256(args.input)
    print(f"Source sha256       : {source_digest[:16]}")
    scan_fp = scan_fingerprint(source_digest, strategy)
    choice_fp = choice_fingerprint(source_digest, strategy, args.seed, args.eval_fraction)

    # step 1 — scan
    if checkpoint.done("scan", scan_fp) and (state_dir / "scan.json").exists():
        phrase_ids, vocab, aggregates = load_scan(state_dir)
        print(f"[1/4] scan       resumed from checkpoint ({aggregates['total']:,} rows)")
    else:
        phrase_ids, vocab, aggregates = scan(args.input, strategy, workers)
        save_scan(state_dir, phrase_ids, vocab, aggregates)
        checkpoint.mark("scan", scan_fp, rows=aggregates["total"], workers=workers)
        print(f"[1/4] scan       {aggregates['total']:,} rows, {len(vocab)} phrases, "
              f"{len(aggregates['sizes'])} groups")
    record("scan")

    # step 2 — choose holdout
    if checkpoint.done("choose", choice_fp):
        holdout = set(checkpoint.state["steps"]["choose"]["holdout"])
        print(f"[2/4] choose     resumed from checkpoint ({len(holdout)} groups)")
    else:
        holdout = choose_holdout(aggregates, args.eval_fraction, args.seed)
        checkpoint.mark("choose", choice_fp, holdout=sorted(holdout))
        print(f"[2/4] choose     {len(holdout)} groups held out (seed {args.seed})")
    record("choose")

    train_path = out_dir / f"train_{strategy}_holdout.csv"
    eval_path = out_dir / f"eval_{strategy}_holdout.csv"

    if args.dry_run:
        print("\nDry run: no files written.")
        return 0

    # step 3 — write splits atomically
    orphans = sweep_partials(train_path, eval_path)
    for orphan in orphans:
        print(f"      swept stale partial from an earlier kill: {orphan}")
    train_stats, eval_stats, eval_texts = write_split(
        args.input, strategy, holdout, phrase_ids, vocab, train_path, eval_path
    )
    train_summary, eval_summary = train_stats.summary(), eval_stats.summary()
    checkpoint.mark(
        "write", choice_fp,
        train={"path": str(train_path), "sha256": sha256(train_path), "rows": train_summary["rows"]},
        eval={"path": str(eval_path), "sha256": sha256(eval_path), "rows": eval_summary["rows"]},
    )
    print(f"[3/4] write      train {train_summary['rows']:,} / eval {eval_summary['rows']:,}")
    record("write")

    # step 4 — leakage
    leakage = leakage_report(train_path, train_stats, eval_stats, eval_texts)
    checkpoint.mark("leakage", choice_fp, **{k: leakage[k] for k in
                                             ("exact_text_overlap", "substring_violations")})
    print(f"[4/4] leakage    {leakage['substring_violations']} substring violations\n")
    record("leakage")

    print_report(strategy, aggregates["total"], train_summary, eval_summary,
                 holdout, aggregates["sizes"], leakage)

    report = {
        "strategy": strategy,
        "eval_fraction_target": args.eval_fraction,
        "seed": args.seed,
        "train": train_summary,
        "eval": eval_summary,
        "holdout_groups": sorted(holdout),
        "leakage": leakage,
        "train_path": str(train_path),
        "eval_path": str(eval_path),
    }
    destination = out_dir / f"split_{strategy}_holdout.json"
    atomic_write_json(destination, report)
    print(f"\nWrote {train_path}")
    print(f"Wrote {eval_path}")
    print(f"Report written to {destination}")

    print("\nPeak RSS by step (process + workers):")
    for step, value in peaks.items():
        print(f"  {step:<10} {value:8.1f} MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
