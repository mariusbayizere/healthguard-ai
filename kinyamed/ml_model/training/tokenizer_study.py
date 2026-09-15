#!/usr/bin/env python
"""Tokenizer study: label-independent measurements that may change the base model.

For each verified checkpoint (docs/SOURCES.md), on the text this repository has:

  * token-length distribution per language (special tokens included, as the model sees it)
  * share of texts truncated at 128, 192 and 256 tokens
  * subword fertility (content tokens per whitespace word) and unknown-token rate
  * a Kinyarwanda segmentation sheet for a native linguist; coherence is NOT judged here

Rows built from one seed phrase are not independent (DATASET_AUDIT §5, §10), so
every statistic is resampled by cluster: the source phrase where the corpus
records it, the v1 family otherwise. Every number carries a 95% interval.

Nothing here uses a label, loads model weights, or trains. Each tokenizer is loaded
alone and released before the next, and results are written after each one.

    cd kinyamed/ml_model
    python dataset/generate_large_dataset.py --corpus-version 1 --target 100000 \\
        --output dataset/raw/tokenizer_study_v1.csv
    python training/tokenizer_study.py --out ../reports/measurements/tokenizer_study
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_LENGTHS = (128, 192, 256)
MIN_CLUSTERS = 2
DEFAULT_BOOTSTRAP = 1000

# Verified 2026-09-15 (docs/SOURCES.md): repository exists, revision pinned, licence
# read from the repository's own metadata. Unverified candidates are not listed.
CHECKPOINTS: tuple[tuple[str, str], ...] = (
    ("Davlan/afro-xlmr-mini", "bc04038b969667884bd83cdd37bed9559c2c3d9c"),
    ("Davlan/afro-xlmr-base", "25f27299c247a6b73a767bd82d12444138b19337"),
    ("Davlan/afro-xlmr-large", "7036fa1ed38d3418a122d3c7e00d5c748ed29f08"),
    ("castorini/afriberta_large", "231d92411ab8a99add67eda412ee948c74a4b179"),
    ("FacebookAI/xlm-roberta-base", "e73636d4f797dec63c3081bb6ed5c7b0bb3f2089"),
    ("FacebookAI/xlm-roberta-large", "c23d21b0620b635a76227c604d44e43a9f0ee389"),
    ("sentence-transformers/LaBSE", "836121a0533e5664b21c7aacc5d22951f2b8b25b"),
)


# ── Counting ──────────────────────────────────────────────────────────────────
@dataclass
class TokenCounts:
    length: object  # np.ndarray of int: tokens including special tokens
    content: object  # tokens excluding special tokens
    words: object  # whitespace words
    unknown: object  # unknown-token count
    single_token_words: object  # words that tokenize to exactly one piece

    @classmethod
    def from_lists(cls, length, content, words, unknown=None, single_token_words=None):
        import numpy as np

        n = len(length)
        return cls(
            np.asarray(length, dtype=np.int64),
            np.asarray(content, dtype=np.int64),
            np.asarray(words, dtype=np.int64),
            np.asarray(unknown if unknown is not None else [0] * n, dtype=np.int64),
            np.asarray(
                single_token_words if single_token_words is not None else [0] * n,
                dtype=np.int64,
            ),
        )


def count_tokens(tokenizer, texts: list[str], batch_size: int = 512) -> TokenCounts:
    special = set(getattr(tokenizer, "all_special_ids", []) or [])
    unk = getattr(tokenizer, "unk_token_id", None)
    length, content, words, unknown, single = [], [], [], [], []
    piece_cache: dict[str, int] = {}
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        ids = tokenizer(batch, add_special_tokens=True, truncation=False)["input_ids"]
        for text, row in zip(batch, ids, strict=True):
            n_special = sum(1 for t in row if t in special and t != unk)
            length.append(len(row))
            content.append(len(row) - n_special)
            unknown.append(sum(1 for t in row if unk is not None and t == unk))
            text_words = text.split()
            words.append(len(text_words))
            ones = 0
            for word in text_words:
                if word not in piece_cache:
                    piece_cache[word] = len(tokenizer.tokenize(word))
                ones += piece_cache[word] == 1
            single.append(ones)
    return TokenCounts.from_lists(length, content, words, unknown, single)


# ── Summaries with cluster-bootstrap intervals ────────────────────────────────
@dataclass(frozen=True)
class Stat:
    point: float
    low: float | None
    high: float | None


INSUFFICIENT_CLUSTERS = "INSUFFICIENT CLUSTERS"


def summarise(
    counts: TokenCounts,
    clusters: list[str],
    *,
    bootstrap: int = DEFAULT_BOOTSTRAP,
    seed: int = 20260915,
):
    """Point estimates and 95% intervals, resampling clusters (never rows)."""
    import numpy as np

    keys = sorted(set(clusters))
    if len(keys) < MIN_CLUSTERS:
        return INSUFFICIENT_CLUSTERS
    index = {k: i for i, k in enumerate(keys)}
    cid = np.fromiter((index[c] for c in clusters), dtype=np.int64, count=len(clusters))
    n_clusters = len(keys)
    top = int(counts.length.max()) + 1

    # Per-cluster length histogram and per-cluster sums.
    hist = np.zeros((n_clusters, top), dtype=np.int64)
    np.add.at(hist, (cid, counts.length), 1)
    sums = np.zeros((n_clusters, 4), dtype=np.int64)
    for j, arr in enumerate(
        (counts.content, counts.words, counts.unknown, counts.single_token_words)
    ):
        np.add.at(sums[:, j], cid, arr)

    rng = np.random.default_rng(seed)
    weights = rng.multinomial(
        n_clusters, np.full(n_clusters, 1.0 / n_clusters), size=bootstrap
    )
    boot_hist = weights @ hist  # (B, top)
    boot_sums = weights @ sums  # (B, 4)
    point_hist = hist.sum(axis=0)
    point_sums = sums.sum(axis=0)

    def ci(values):
        return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))

    def quantile(h, q):
        cum = np.cumsum(h, axis=-1)
        total = cum[..., -1:]
        return np.argmax(cum >= np.ceil(q * total), axis=-1)

    out: dict[str, Stat] = {}
    for q, name in ((0.50, "p50_length"), (0.95, "p95_length"), (0.99, "p99_length")):
        out[name] = Stat(float(quantile(point_hist, q)), *ci(quantile(boot_hist, q)))
    for limit in MAX_LENGTHS:
        above_point = point_hist[limit + 1 :].sum() / point_hist.sum()
        above_boot = boot_hist[:, limit + 1 :].sum(axis=1) / boot_hist.sum(axis=1)
        out[f"truncated_{limit}"] = Stat(float(above_point), *ci(above_boot))
    content, words, unknown, single = point_sums
    bc, bw, bu, bs = boot_sums.T
    out["fertility"] = Stat(float(content / words), *ci(bc / bw))
    out["unknown_rate"] = Stat(float(unknown / content), *ci(bu / bc))
    out["single_token_word_rate"] = Stat(float(single / words), *ci(bs / bw))
    observed_max = int(np.nonzero(point_hist)[0].max())
    out["max_length_observed"] = Stat(
        float(observed_max), float(observed_max), float(observed_max)
    )
    return out


def vocabulary_identity(tokenizer) -> str:
    """SHA-256 of the sorted (token, id) vocabulary: equal hashes tokenize identically
    for the same normaliser, so a shared vocabulary is measured once."""
    items = sorted(tokenizer.get_vocab().items())
    return hashlib.sha256(json.dumps(items, ensure_ascii=False).encode()).hexdigest()


def segmentation_sheet(words: list[str], tokenizers: dict) -> list[dict[str, str]]:
    """How each tokenizer splits each word, for a native Kinyarwanda linguist to judge.
    The judgement column is left blank on purpose (CLAUDE.md L16, §10.2)."""
    rows = []
    for word in words:
        row = {"word": word}
        for name, tok in tokenizers.items():
            row[name] = " | ".join(tok.tokenize(word))
        row["coherent_per_native_linguist"] = ""
        rows.append(row)
    return rows


# ── Text sources ──────────────────────────────────────────────────────────────
def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_sources() -> list[tuple[str, str, str, list[str], list[str]]]:
    """(source, language, status, texts, clusters) for every text the repo has."""
    sources = []
    kw_texts, kw_clusters = [], []
    for name in ("train_phrase_holdout.csv", "eval_phrase_holdout.csv"):
        for row in _read(ROOT / "dataset/processed" / name):
            kw_texts.append(row["text"])
            kw_clusters.append(row["phrase"])
    sources.append(
        (
            "v2 corpus rows",
            "kinyarwanda",
            "generated from 165 phrases, partly speaker-authored (DATASET_AUDIT §6)",
            kw_texts,
            kw_clusters,
        )
    )
    for language, column in (
        ("english", "suggested_english"),
        ("french", "suggested_french"),
    ):
        rows = _read(ROOT / f"review/speaker_brief_{language}_v2.csv")
        texts = [r[column].strip() for r in rows if r[column].strip()]
        sources.append(
            (
                "v2 phrase drafts",
                language,
                "machine-drafted, not reviewed by a speaker",
                texts,
                texts,
            )
        )
    v1 = ROOT / "dataset/raw/tokenizer_study_v1.csv"
    if v1.exists():
        by_language: dict[str, tuple[list[str], list[str]]] = {}
        for row in _read(v1):
            texts, clusters = by_language.setdefault(row["language"], ([], []))
            texts.append(row["text"])
            clusters.append(row["family"])
        for language, (texts, clusters) in sorted(by_language.items()):
            sources.append(
                (
                    "v1 generated rows",
                    language,
                    "machine-drafted v1 corpus (seed 42, 100,000 rows); clustered by family",
                    texts,
                    clusters,
                )
            )
    return sources


def kinyarwanda_words(limit: int = 60) -> list[str]:
    """The words appearing in the most distinct v2 phrases."""
    phrases = {
        row["phrase"]
        for row in _read(ROOT / "dataset/processed/eval_phrase_holdout.csv")
    }
    phrases |= {
        row["phrase"]
        for row in _read(ROOT / "dataset/processed/train_phrase_holdout.csv")
    }
    counts: Counter[str] = Counter()
    for phrase in phrases:
        for word in {w.strip(".,?!;:").lower() for w in phrase.split()}:
            if word and "{" not in word:
                counts[word] += 1
    return [w for w, _ in counts.most_common(limit)]


# ── Study ─────────────────────────────────────────────────────────────────────
def run(out: Path, only: str | None, bootstrap: int) -> int:
    from transformers import AutoTokenizer

    out.mkdir(parents=True, exist_ok=True)
    results_path = out / "results.json"
    results = json.loads(results_path.read_text()) if results_path.exists() else {}
    sources = load_sources()
    words = kinyarwanda_words()
    for repo, revision in CHECKPOINTS:
        if only and repo != only:
            continue
        print(f"== {repo} @ {revision[:12]}", flush=True)
        try:
            tokenizer = AutoTokenizer.from_pretrained(repo, revision=revision)
        except (ValueError, OSError, ImportError) as error:  # recorded, not swallowed
            reason = str(error).splitlines()[0] if str(error) else type(error).__name__
            results[repo] = {
                "revision": revision,
                "status": f"NOT MEASURED (tokenizer failed to load: {reason})",
            }
            results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
            print(f"   NOT MEASURED: {reason}", flush=True)
            continue
        identity = vocabulary_identity(tokenizer)
        entry = {
            "status": "MEASURED",
            "revision": revision,
            "vocabulary_sha256": identity,
            "vocabulary_size": len(tokenizer.get_vocab()),
            "tokenizer_class": type(tokenizer).__name__,
            "sources": {},
        }
        for source, language, status, texts, clusters in sources:
            counts = count_tokens(tokenizer, texts)
            summary = summarise(counts, clusters, bootstrap=bootstrap)
            key = f"{source} [{language}]"
            entry["sources"][key] = {
                "status": status,
                "texts": len(texts),
                "clusters": len(set(clusters)),
                "summary": summary
                if summary == INSUFFICIENT_CLUSTERS
                else {k: asdict(v) for k, v in summary.items()},
            }
            print(
                f"   {key}: {len(texts):,} texts, {len(set(clusters)):,} clusters",
                flush=True,
            )
        entry["kinyarwanda_segmentation"] = {
            row["word"]: row[repo]
            for row in segmentation_sheet(words, {repo: tokenizer})
        }
        results[repo] = entry
        results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        del tokenizer
        gc.collect()
    write_segmentation_sheet(results, words, out / "kinyarwanda_segmentation_sheet.csv")
    return 0


def write_segmentation_sheet(results: dict, words: list[str], path: Path) -> None:
    """One column per measured checkpoint, built from saved results so no tokenizer
    has to stay in memory."""
    repos = [r for r, _ in CHECKPOINTS if r in results]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, ["word", *repos, "coherent_per_native_linguist"]
        )
        writer.writeheader()
        for word in words:
            row = {"word": word, "coherent_per_native_linguist": ""}
            for repo in repos:
                row[repo] = (
                    results[repo].get("kinyarwanda_segmentation", {}).get(word, "")
                )
            writer.writerow(row)


COLUMNS = (
    ("p95_length", "p95 tokens", "{:.0f}"),
    ("p99_length", "p99 tokens", "{:.0f}"),
    ("truncated_128", "> 128", "{:.1%}"),
    ("truncated_192", "> 192", "{:.1%}"),
    ("truncated_256", "> 256", "{:.1%}"),
    ("fertility", "tokens / word", "{:.2f}"),
    ("unknown_rate", "unknown", "{:.2%}"),
    ("single_token_word_rate", "one-token words", "{:.1%}"),
)


def _cell(stat: dict, fmt: str) -> str:
    """Point and interval in the same format, e.g. `66 [65, 68]` or `2.52 [2.50, 2.55]`."""
    return f"{fmt.format(stat['point'])} [{fmt.format(stat['low'])}, {fmt.format(stat['high'])}]"


def render_markdown(results: dict) -> str:
    """The report tables, generated from results.json so no figure is retyped."""
    header = ["Checkpoint", "Text", "Texts", "Clusters", "Max tokens"] + [
        c[1] for c in COLUMNS
    ]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for repo, entry in results.items():
        if not entry.get("status", "MEASURED").startswith("MEASURED"):
            lines.append(f"| {repo} | {entry['status']} |" + " |" * (len(header) - 2))
            continue
        for source, data in entry["sources"].items():
            summary = data["summary"]
            if isinstance(summary, str):
                lines.append(
                    f"| {repo} | {source} | {data['texts']:,} | {data['clusters']:,} | {summary} |"
                )
                continue
            cells = [_cell(summary[key], fmt) for key, _, fmt in COLUMNS]
            lines.append(
                f"| {repo} | {source} | {data['texts']:,} | {data['clusters']:,} | "
                f"{summary['max_length_observed']['point']:.0f} | "
                + " | ".join(cells)
                + " |"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--only", help="measure one repository (one at a time on a small machine)"
    )
    parser.add_argument("--bootstrap", type=int, default=DEFAULT_BOOTSTRAP)
    parser.add_argument(
        "--render",
        action="store_true",
        help="print the report tables from results.json",
    )
    args = parser.parse_args(argv)
    if args.render:
        print(render_markdown(json.loads((args.out / "results.json").read_text())))
        return 0
    return run(args.out, args.only, args.bootstrap)


if __name__ == "__main__":
    sys.exit(main())
