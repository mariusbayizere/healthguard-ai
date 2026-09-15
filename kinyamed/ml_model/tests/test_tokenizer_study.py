"""training/tokenizer_study.py: label-independent tokenizer measurements.

A fake tokenizer pins the arithmetic, so no model or tokenizer is downloaded here.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

np = pytest.importorskip("numpy", reason="the cluster bootstrap needs numpy")

from training import tokenizer_study as ts  # noqa: E402


class FakeTokenizer:
    """Words split into 3-character pieces; 'zz' is unknown; 2 special tokens per text."""

    unk_token_id = 0
    all_special_ids: ClassVar[list[int]] = [1, 2, 0]

    def __call__(self, texts, add_special_tokens=True, truncation=False):
        ids = []
        for text in texts:
            pieces = []
            for word in text.split():
                for k in range(0, len(word), 3):
                    chunk = word[k : k + 3]
                    pieces.append(0 if chunk == "zz" else 10 + len(chunk))
            ids.append([1, *pieces, 2] if add_special_tokens else pieces)
        return {"input_ids": ids}

    def tokenize(self, word):
        return [word[k : k + 3] for k in range(0, len(word), 3)]


def test_per_text_counts_include_special_tokens_in_length_only():
    counts = ts.count_tokens(FakeTokenizer(), ["abcdef gh", "zz"])
    # "abcdef gh" -> abc, def, gh = 3 content tokens + 2 special
    assert counts.length.tolist() == [5, 3]
    assert counts.content.tolist() == [3, 1]
    assert counts.words.tolist() == [2, 1]
    assert counts.unknown.tolist() == [0, 1]
    assert counts.single_token_words.tolist() == [1, 1]


def test_truncation_rate_is_the_share_longer_than_max_length():
    counts = ts.TokenCounts.from_lists(
        length=[10, 128, 129, 300], content=[1] * 4, words=[1] * 4
    )
    summary = ts.summarise(counts, clusters=["a", "b", "c", "d"], bootstrap=200, seed=1)
    assert summary["truncated_128"].point == pytest.approx(0.5)
    assert summary["truncated_256"].point == pytest.approx(0.25)
    assert summary["truncated_192"].point == pytest.approx(0.25)


def test_fertility_and_unknown_rate_are_ratios_over_all_text():
    counts = ts.TokenCounts.from_lists(
        length=[5, 5], content=[3, 6], words=[3, 2], unknown=[0, 3]
    )
    summary = ts.summarise(counts, clusters=["a", "b"], bootstrap=200, seed=1)
    assert summary["fertility"].point == pytest.approx(9 / 5)
    assert summary["unknown_rate"].point == pytest.approx(3 / 9)


def test_every_statistic_carries_an_interval_resampled_by_cluster():
    """Two clusters of 1,000 identical texts each are two observations, not 2,000:
    the interval must reflect that the clusters disagree."""
    lengths = [100] * 1000 + [300] * 1000
    counts = ts.TokenCounts.from_lists(
        length=lengths, content=[1] * 2000, words=[1] * 2000
    )
    clustered = ts.summarise(
        counts, clusters=["a"] * 1000 + ["b"] * 1000, bootstrap=400, seed=2
    )
    independent = ts.summarise(
        counts, clusters=[str(k) for k in range(2000)], bootstrap=400, seed=2
    )
    wide = clustered["truncated_256"]
    narrow = independent["truncated_256"]
    assert wide.low == pytest.approx(0.0) and wide.high == pytest.approx(1.0)
    assert (narrow.high - narrow.low) < 0.1
    for stat in clustered.values():
        assert stat.low is not None and stat.high is not None


def test_length_percentiles_come_from_the_cluster_bootstrap():
    counts = ts.TokenCounts.from_lists(
        length=list(range(1, 101)), content=[1] * 100, words=[1] * 100
    )
    summary = ts.summarise(
        counts, clusters=[str(k) for k in range(100)], bootstrap=300, seed=3
    )
    assert summary["p95_length"].point == 95
    assert summary["p95_length"].low <= 95 <= summary["p95_length"].high
    assert summary["max_length_observed"].point == 100


def test_too_few_clusters_is_reported_not_summarised():
    counts = ts.TokenCounts.from_lists(
        length=[10] * 50, content=[1] * 50, words=[1] * 50
    )
    summary = ts.summarise(counts, clusters=["only"] * 50, bootstrap=50, seed=1)
    assert summary is ts.INSUFFICIENT_CLUSTERS


def test_identical_vocabularies_share_one_identity():
    class A:
        def get_vocab(self):
            return {"a": 0, "b": 1}

    class B:
        def get_vocab(self):
            return {"b": 1, "a": 0}

    class C:
        def get_vocab(self):
            return {"a": 0, "c": 1}

    assert ts.vocabulary_identity(A()) == ts.vocabulary_identity(B())
    assert ts.vocabulary_identity(A()) != ts.vocabulary_identity(C())


def test_segmentation_sheet_leaves_the_judgement_blank():
    sheet = ts.segmentation_sheet(["abcdef", "gh"], {"fake": FakeTokenizer()})
    assert sheet[0] == {
        "word": "abcdef",
        "fake": "abc | def",
        "coherent_per_native_linguist": "",
    }
    assert all(row["coherent_per_native_linguist"] == "" for row in sheet)


def test_a_checkpoint_that_cannot_load_is_recorded_not_measured(tmp_path, monkeypatch):
    """AfriBERTa-large ships only a SentencePiece model; without `sentencepiece` the
    load fails. The study must record that, not crash and lose the rest."""
    import transformers

    def refuse(*args, **kwargs):
        raise ValueError("`tiktoken` is required to read a `tiktoken` file.")

    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", refuse)
    monkeypatch.setattr(
        ts, "load_sources", lambda: [("s", "kinyarwanda", "x", ["a b"], ["c"])]
    )
    monkeypatch.setattr(ts, "kinyarwanda_words", lambda limit=60: ["abc"])
    assert ts.run(tmp_path, "castorini/afriberta_large", bootstrap=10) == 0
    import json

    entry = json.loads((tmp_path / "results.json").read_text())[
        "castorini/afriberta_large"
    ]
    assert entry["status"].startswith("NOT MEASURED")
    assert "tiktoken" in entry["status"]


def test_the_report_table_prints_every_number_with_its_interval():
    results = {
        "repo/a": {
            "status": "MEASURED",
            "vocabulary_sha256": "f" * 64,
            "vocabulary_size": 10,
            "sources": {
                "rows [kinyarwanda]": {
                    "status": "s",
                    "texts": 5,
                    "clusters": 2,
                    "summary": {
                        name: {"point": 1.5, "low": 1.0, "high": 2.0}
                        for name in (
                            "p95_length",
                            "p99_length",
                            "max_length_observed",
                            "truncated_128",
                            "truncated_192",
                            "truncated_256",
                            "fertility",
                            "unknown_rate",
                            "single_token_word_rate",
                        )
                    },
                }
            },
        },
        "repo/b": {"status": "NOT MEASURED (tokenizer failed to load: x)"},
    }
    table = ts.render_markdown(results)
    assert "| repo/a | rows [kinyarwanda] |" in table
    assert "1.50 [1.00, 2.00]" in table  # tokens per word
    assert "150.0% [100.0%, 200.0%]" in table  # a rate column keeps its interval
    assert "NOT MEASURED (tokenizer failed to load: x)" in table
