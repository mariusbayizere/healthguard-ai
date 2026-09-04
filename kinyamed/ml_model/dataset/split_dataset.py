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
import re
from itertools import combinations
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
from dataset.vocabulary import (PHRASE_CONCEPTS, PHRASE_VARIANTS,  # noqa: E402
                                REL_PLACEHOLDER, SENTENCE_END)

COLUMNS = ["text", "language", "label", "domain", "family", "phrase", "phrase_group"]
# Two phrases sharing this many leading characters join one phrase group even
# when neither contains the other. Measured, not chosen: 25 and above leaves v1's
# partition byte-identical so the frozen splits survive, 22 and below changes it.
# 30 sits above the domain grammar and catches all eight near-duplicate pairs
# found at 128 authored phrases - six of which a reviewer missed by hand.
PREFIX_UNION_CHARS = 30
# Rows per unit of work handed to a worker. Large enough that pickling overhead
# stays negligible, small enough that the in-flight queue is bounded.
BATCH_ROWS = 20_000
MAX_WORKERS = 2



def _words(comparable: str) -> list[str]:
    """Word list of an already `_match_form`ed phrase, placeholder removed."""
    return re.findall(r"[a-z0-9']+", comparable.replace(REL_PLACEHOLDER.lower(), " "))


def _is_subsequence(small: list[str], big: list[str]) -> bool:
    """Every word of `small` appears in `big`, in the same order."""
    it = iter(big)
    return all(word in it for word in small)


def phrase_components() -> dict[str, str]:
    """Map every seed phrase to the id of its substring-closed group.

    Some phrases contain others ("maumivu makali ya tumbo" inside "maumivu
    makali ya tumbo wakati wa ujauzito na damu"). Holding out only the inner one
    would still expose its exact characters in every training row built on the
    outer one — an exact-match check reports zero overlap while the model has
    plainly seen the string. Nested phrases therefore move as one unit.

    Matching is deliberately cross-language: leakage is textual, and a shared
    substring leaks regardless of which language list the phrases came from.

    Comparison goes through `_match_form`, not the raw string. Every v2 phrase is
    an utterance ending in a full stop and often capitalised, and both defeat a
    raw `in`:

        "{REL} arababara cyane mu nda."   is NOT a substring of
        "{REL} arababara cyane mu nda kandi ububabare ntibuhagarara."

    yet `_drop_terminal_stop` removes exactly that period at render time, so the
    rendered rows DO contain one another. Comparing raw strings missed five
    authored pairs. This is the fourth time a terminal stop has defeated a string
    match here; `attribute_phrase` failed the same way three times.

    Beyond containment, two phrases are also unioned when they share
    PREFIX_UNION_CHARS leading characters. Containment catches a nested phrase and
    misses a divergent one with a long shared head - "{REL} ari kuva amaraso
    menshi kandi ntahagarara." against "... mu mazuru kandi ntahagarara." - which
    can then split across the phrase holdout. See docs/phrase-group-closure.md for
    why the threshold is where it is.
    """
    phrases = sorted({p for values in all_symptom_phrases().values() for p in values})
    parent = {phrase: phrase for phrase in phrases}
    comparable = {phrase: _match_form(phrase) for phrase in phrases}

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
            if inner != outer and comparable[inner] in comparable[outer]:
                union(inner, outer)

    # A long shared head is not containment, so the closure above misses it, but
    # it leaks the same way: a model that has trained on one has seen most of the
    # characters of the other. The threshold sits above the domain grammar -
    # "{REL} afite umuriro", "{REL} aratwite kandi" - and below every real
    # near-duplicate measured. Not a principle, a measurement; re-derive it when
    # the corpus is complete.
    for left, right in combinations(phrases, 2):
        if find(left) == find(right):
            continue
        a, b = comparable[left], comparable[right]
        shared = 0
        for x, y in zip(a, b):
            if x != y:
                break
            shared += 1
        if shared >= PREFIX_UNION_CHARS:
            union(left, right)

    # 7b(a): one phrase's words all appear in the other, IN ORDER. Reordering and
    # insertion defeat both rules above - "{REL} arababara cyane mu nda." is not a
    # substring of "{REL} aratwite, arababara cyane mu nda kandi arava amaraso."
    # and shares only 6 leading characters with it, yet every word of the first is
    # in the second and a model trained on the second has seen all of the first.
    #
    # SUBSEQUENCE, NOT SET SUBSET, and the difference is not cosmetic. The set
    # form breaks the v1 freeze on a real pair:
    #
    #     "maumivu makali ya tumbo"                 severe stomach pain
    #     "maumivu kidogo ya tumbo yasiyo makali"   slight stomach pain, NOT severe
    #
    # Every word of the first is in the second, so a set test unions two phrases
    # that mean opposite things - negation puts the negated word in the phrase,
    # and a set cannot see the "yasiyo". Requiring the order to hold refuses that
    # pair (ya precedes makali in one and follows it in the other) while still
    # catching EX18/EX20, which is the pair PREFIX_UNION_CHARS exists for.
    # Measured: the set form takes v1 from 180 groups to 179, the ordered form
    # leaves it byte-identical. See docs/phrase-group-closure.md section 10.
    for left, right in combinations(phrases, 2):
        if find(left) == find(right):
            continue
        a, b = _words(comparable[left]), _words(comparable[right])
        if a and b and (_is_subsequence(a, b) or _is_subsequence(b, a)):
            union(left, right)

    # A concept's second phrasing joins its primary, whether or not one contains
    # the other. Substring closure alone would leave two divergent phrasings of
    # one concept in separate groups and let the holdout split them.
    known = set(phrases)
    for variant, primary in PHRASE_VARIANTS.items():
        missing = [p for p in (variant, primary) if p not in known]
        if missing:
            # Silence here would put the pair in separate groups, which is the
            # exact failure the declaration exists to prevent. Refuse instead.
            raise SystemExit(
                f"PHRASE_VARIANTS declares {variant!r} -> {primary!r} but "
                f"{missing!r} is not in the symptom inventory. A declared pairing "
                "that names an absent phrase is a misconfiguration, not a no-op."
            )
        union(variant, primary)

    # Everything said about one concept joins one group: its first person, its
    # third person, any second phrasing. A similarity rule cannot do this - a
    # third-person phrase starts with {REL} and a first-person one with a letter,
    # so their shared prefix is 0 however low the threshold goes, and containment
    # fails on the verb morphology. The brief knows the answer, so it declares it.
    by_concept: dict[str, list[str]] = {}
    for phrase, concept in PHRASE_CONCEPTS.items():
        if phrase not in known:
            raise SystemExit(
                f"PHRASE_CONCEPTS assigns {phrase!r} to concept {concept!r} but that "
                "phrase is not in the symptom inventory. A declaration naming an "
                "absent phrase is a misconfiguration, not a no-op - it would leave "
                "the concept's other phrases unjoined and silently reopen the leak."
            )
        by_concept.setdefault(concept, []).append(phrase)
    for members in by_concept.values():
        for other in members[1:]:
            union(members[0], other)

    return {phrase: find(phrase) for phrase in phrases}


def substring_violations(train_phrases: set[str], eval_phrases: set[str]) -> list[dict]:
    """Held-out phrases whose characters still appear in a training phrase."""
    violations: list[dict] = []
    for held in sorted(eval_phrases):
        for trained in sorted(train_phrases):
            if held and trained and (held in trained or trained in held):
                violations.append({"eval_phrase": held, "train_phrase": trained})
    return violations


def _match_form(part: str) -> str:
    """The comparable form of a phrase or phrase segment.

    Lowercased, because an utterance is capitalised at a sentence start and
    lowercased after a greeting. Stripped of a terminal stop, because the
    generator drops one before a continuation - see _drop_terminal_stop. Both
    transformations happen at render time, so attribution has to see through
    them. Matching the authored form with its stop still attached misses every
    continued row, and worse than missing: the row falls through to a SHORTER
    phrase that happens to be a prefix, so "Guhumeka birangora cyane ku buryo
    ntabasha no kuvuga neza." loses its rows to "guhumeka birangora cyane".
    """
    part = part.strip()
    if part[-1:] in SENTENCE_END:
        part = part[:-1]
    return part.strip().lower()


def _is_word_char(character: str) -> bool:
    """Letters and digits join a word; punctuation, spaces and quotes do not.

    An apostrophe is deliberately NOT a word character: Kinyarwanda writes
    "n'uduheri" and "w'umuturanyi", and a segment beginning after one starts a
    real word.
    """
    return character.isalnum()


def _find_at_word_boundary(haystack: str, needle: str, start: int = 0) -> int:
    """First occurrence of `needle` that begins and ends on a word boundary.

    Plain `str.find` matches inside a word, and that is not a theoretical worry:
    "Ndashaka" ENDS WITH "ashaka", so the third-person phrase
    "{REL} ashaka inama ku mirire myiza." matched inside the first-person
    "Ndashaka inama ku mirire myiza." and, being the longer entry, captured its
    rows. Four authored pairs collided that way and six commits reached main red.

    This is the fourth silent failure in this function - after case sensitivity,
    the welded {REL} halves, and the terminal stop - so it is a rule about where
    a match may begin, not another special case.
    """
    if not needle:
        return -1
    position = start
    while True:
        found = haystack.find(needle, position)
        if found < 0:
            return -1
        before_ok = found == 0 or not _is_word_char(haystack[found - 1])
        after = found + len(needle)
        after_ok = after >= len(haystack) or not _is_word_char(haystack[after])
        if before_ok and after_ok:
            return found
        position = found + 1


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
        if REL_PLACEHOLDER in phrase:
            # The rendered row carries a concrete relation, so match on the
            # invariant parts around it. The canonical {REL} form is returned,
            # which keeps all eight relations in one phrase group and therefore
            # on the same side of the holdout.
            #
            # Match each segment in order rather than the concatenation. Deleting
            # the placeholder from a phrase where it sits mid-sentence leaves the
            # two halves welded together with a double space -- "Iyo  ahumeka" --
            # which never matches "Iyo Mama ahumeka". Those rows attributed to
            # None and dropped out of the phrase holdout with no error raised,
            # the same silent failure the case-sensitivity bug above caused.
            segments = [s for s in (_match_form(part)
                                    for part in phrase.split(REL_PLACEHOLDER)) if s]
            position = 0
            for segment in segments:
                found = _find_at_word_boundary(lowered, segment, position)
                if found < 0:
                    break
                position = found + len(segment)
            else:
                if segments:
                    return phrase
        elif _find_at_word_boundary(lowered, _match_form(phrase)) >= 0:
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
