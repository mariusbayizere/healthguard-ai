"""training/pipeline.py: the training pipeline, ready to run, refusing below the eval-set
minimum (CLAUDE.md FR-04-12, FR-04-13, L6, L8).

Order, each step gating the next:
  1. eval sets meet EVAL_SET_SPEC (test: every pre-inference gate cell SUFFICIENT;
     calibration: its allocation), or REFUSE before reading the corpus
  2. leakage check across train, calibration and test (exact, scenario, near-dup),
     or REFUSE before training
  3. train with the cost-sensitive loss
  4. fit the temperature on the calibration split only
  5. tune thresholds to CRITICAL safety on the calibration split only
  6. write the model metadata, test-split predictions for the gate, and the manifest

No metric is printed: the gate (training/evaluate.py) reports. Every fixture here is
synthetic; the trainer and predictor are fakes except in the smoke test.
"""

from __future__ import annotations

import csv
import json
import zlib
from pathlib import Path

import numpy as np
import pytest
from training import eval_spec as spec
from training import pipeline as pl

ML_ROOT = Path(__file__).resolve().parent.parent
N9_GOLD = ML_ROOT / "dataset/processed/gate_n9_gold.csv"
HEADER = ["item_id", "text", "language", "gold_label", "scenario_id", "split"]


# ── Fixtures ──────────────────────────────────────────────────────────────────
def _write_gold(path: Path, allocation, split: str, rows_per_scenario: int = 1):
    """One scenario per allocated item. Each text is three unique tokens plus the
    class name, so no two texts share a word 3-gram across splits."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        k = 0
        for a in allocation:
            for cls, count in zip(
                spec.CLASSES, (a.critical, a.urgent, a.routine), strict=True
            ):
                for _ in range(count):
                    for r in range(rows_per_scenario):
                        writer.writerow(
                            [
                                f"{split}-{k}-{r}",
                                f"{split}{k}r{r} {cls.lower()} {split}x{k}r{r}",
                                a.language,
                                cls,
                                f"{split}-scenario-{k}",
                                split,
                            ]
                        )
                    k += 1
    return path


def _write_train(path: Path, extra: list[dict] | None = None):
    rows = [
        {
            "text": f"train{k} {cls.lower()} trainx{k}",
            "label": cls,
            "language": "kinyarwanda",
            "scenario_id": f"train-scenario-{k}",
        }
        for k, cls in enumerate(spec.CLASSES * 40)
    ] + (extra or [])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["text", "label", "language", "scenario_id"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


class FakeTrainer:
    def __init__(self):
        self.calls = []

    def train(self, train_rows, config, seed, out_dir: Path) -> Path:
        self.calls.append((len(train_rows), dict(config), seed))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "weights.bin").write_bytes(b"fake")
        return out_dir


class FakePredictor:
    """Overconfident logits that follow the class word in the text, with seeded noise.
    `test_shift` perturbs only test-split texts, to prove calibration never sees them."""

    def __init__(self, test_shift: float = 0.0):
        self.test_shift = test_shift
        self.seen: list[str] = []

    def logits(self, model_dir, texts, max_length, batch_size):
        self.seen.extend(texts)
        out = np.zeros((len(texts), 3))
        for k, text in enumerate(texts):
            rng = np.random.default_rng(zlib.crc32(text.encode()))
            cls = next(
                i for i, c in enumerate(spec.CLASSES) if c.lower() in text.split()
            )
            out[k] = rng.normal(0.0, 1.5, 3)
            out[k, cls] += 1.2
            out[k] *= 3.0
            if text.startswith("test"):
                out[k] += self.test_shift * rng.normal(0.0, 1.0, 3)
        return out


@pytest.fixture
def full(tmp_path):
    return {
        "gold_test": _write_gold(
            tmp_path / "gold_test.csv", spec.TEST_ALLOCATION, "test"
        ),
        "gold_calibration": _write_gold(
            tmp_path / "gold_calibration.csv",
            spec.CALIBRATION_ALLOCATION,
            "calibration",
        ),
        "train": _write_train(tmp_path / "train.csv"),
        "out": tmp_path / "run",
    }


def _run(paths, trainer=None, predictor=None, config=None, capsys=None):
    trainer = trainer or FakeTrainer()
    predictor = predictor or FakePredictor()
    config_path = paths["out"].parent / "config.json"
    config_path.write_text(json.dumps(config or pl.DEFAULT_CONFIG))
    code = pl.main(
        [
            "--train",
            str(paths["train"]),
            "--gold-test",
            str(paths["gold_test"]),
            "--gold-calibration",
            str(paths["gold_calibration"]),
            "--config",
            str(config_path),
            "--seed",
            "42",
            "--out",
            str(paths["out"]),
        ],
        trainer=trainer,
        predictor=predictor,
        repo=paths["out"].parent,
    )
    return code, trainer, predictor


def _manifest(paths):
    return json.loads((paths["out"] / pl.MANIFEST_NAME).read_text())


# ── 1. Refusal below the eval-set minimum ─────────────────────────────────────
def test_the_n9_shape_is_refused_before_the_corpus_is_read(tmp_path, capsys):
    """Nine source sentences, each repeated 200 times: 1,800 rows, 9 scenarios."""
    small = [spec.Allocation("kinyarwanda", 4, 2, 3)]
    paths = {
        "gold_test": _write_gold(
            tmp_path / "gold_test.csv", small, "test", rows_per_scenario=200
        ),
        "gold_calibration": tmp_path / "absent_calibration.csv",
        "train": tmp_path / "absent_train.csv",
        "out": tmp_path / "run",
    }
    code, trainer, predictor = _run(paths)
    out = capsys.readouterr()
    assert code == 2
    assert trainer.calls == [] and predictor.seen == []
    text = out.out + out.err
    assert "REFUSED" in text
    assert "1,800 rows from 9 distinct source sentences" in text
    assert "INSUFFICIENT DATA" in text
    assert "calibration split" in text
    assert "leakage check: NOT RUN" in text
    manifest = _manifest(paths)
    assert manifest["status"] == "refused"
    assert "train" not in manifest["inputs"]
    assert not (paths["out"] / "model").exists()


def test_a_calibration_split_below_its_allocation_is_refused(full, capsys):
    short = tuple(a for a in spec.CALIBRATION_ALLOCATION if a.language != "french")
    _write_gold(full["gold_calibration"], short, "calibration")
    code, trainer, _ = _run(full)
    assert code == 2 and trainer.calls == []
    assert "french CRITICAL: 0 distinct scenarios, need 100" in capsys.readouterr().err


def test_a_test_split_one_cell_short_is_refused(full, capsys):
    """Every pre-inference cell must be SUFFICIENT, not just one."""
    short = tuple(
        spec.Allocation(a.language, 300, a.urgent, a.routine)
        if a.language == "swahili"
        else a
        for a in spec.TEST_ALLOCATION
    )
    _write_gold(full["gold_test"], short, "test")
    code, trainer, _ = _run(full)
    err = capsys.readouterr().err
    assert code == 2 and trainer.calls == []
    assert "swahili" in err and "INSUFFICIENT DATA" in err


def test_the_real_n9_gold_set_is_refused_without_training(tmp_path, capsys):
    if not N9_GOLD.exists():
        pytest.skip(
            "gate_n9_gold.csv is corpus-derived and git-ignored; make reproduce builds it"
        )
    paths = {
        "gold_test": N9_GOLD,
        "gold_calibration": tmp_path / "none.csv",
        "train": tmp_path / "none_train.csv",
        "out": tmp_path / "run",
    }
    code, trainer, _ = _run(paths)
    assert code == 2 and trainer.calls == []
    assert "17,942 rows from 9 distinct source sentences" in capsys.readouterr().err


# ── 2. Leakage ────────────────────────────────────────────────────────────────
def test_an_exact_text_shared_with_the_test_split_is_refused(full, capsys):
    _write_train(
        full["train"],
        extra=[
            {
                "text": "  TEST5R0 critical testx5r0 ",
                "label": "CRITICAL",
                "language": "kinyarwanda",
                "scenario_id": "t-extra",
            }
        ],
    )
    code, trainer, _ = _run(full)
    err = capsys.readouterr().err
    assert code == 2 and trainer.calls == []
    assert "exact" in err and "test" in err


def test_a_scenario_shared_with_the_calibration_split_is_refused(full, capsys):
    _write_train(
        full["train"],
        extra=[
            {
                "text": "unrelated words entirely here",
                "label": "URGENT",
                "language": "english",
                "scenario_id": "calibration-scenario-3",
            }
        ],
    )
    code, trainer, _ = _run(full)
    assert code == 2 and trainer.calls == []
    assert "scenario" in capsys.readouterr().err


def test_a_near_duplicate_of_a_test_item_is_refused():
    """20 words, the last one different: 17 of 19 word 3-grams shared (J = 0.89)."""
    stem = (
        "the patient has had severe chest pain since early this morning and now "
        "cannot breathe properly when lying down at"
    )
    train, test = f"{stem} home", f"{stem} work"
    shared = pl._shingles(train) & pl._shingles(test)
    union = pl._shingles(train) | pl._shingles(test)
    assert (
        len(shared) / len(union) >= pl.NEAR_DUPLICATE_JACCARD
    )  # the fixture is a near-dup
    checked = pl.leakage_check(train=[(train, "a")], held_out={"test": [(test, "b")]})
    assert checked.near_duplicate == 1 and checked.exact == 0 and not checked.clean


def test_a_pair_just_below_the_jaccard_threshold_is_not_flagged():
    """14 words, the last one different: 11 of 13 shared (J = 0.846 < 0.85)."""
    stem = "the patient has severe chest pain and cannot breathe since this morning at"
    checked = pl.leakage_check(
        train=[(f"{stem} home", "a")], held_out={"test": [(f"{stem} work", "b")]}
    )
    assert checked.clean


def test_a_clean_split_passes_the_leakage_check():
    checked = pl.leakage_check(
        train=[("mfite umuriro mwinshi cyane", "a")],
        held_out={
            "test": [("ndashaka inama ku mirire", "b")],
            "calibration": [("amaguru arababara", "c")],
        },
    )
    assert checked.clean
    assert checked.as_record()["jaccard_threshold"] == pl.NEAR_DUPLICATE_JACCARD


def test_the_near_duplicate_threshold_is_the_contract_value():
    assert pl.NEAR_DUPLICATE_JACCARD == 0.85  # CLAUDE.md §3.6


# ── 3-6. A run that passes every check ────────────────────────────────────────
def test_a_passing_run_trains_once_and_writes_everything_the_gate_and_service_need(
    full, capsys
):
    code, trainer, _ = _run(full)
    out = capsys.readouterr().out
    assert code == 0, out
    assert len(trainer.calls) == 1
    model_dir = full["out"] / "model"
    metadata = json.loads((model_dir / pl.TRAINING_METADATA).read_text())
    assert metadata["max_length"] == pl.DEFAULT_CONFIG["max_length"]
    assert metadata["temperature"] > 0
    assert {"critical", "urgent", "rule"} <= metadata["thresholds"].keys()
    assert metadata["cost_matrix"] == [
        list(r) for r in pl.DEFAULT_CONFIG["cost_matrix"]
    ]

    manifest = _manifest(full)
    assert manifest["status"] == "completed"
    assert {"gold_test", "gold_calibration", "train"} <= manifest["inputs"].keys()
    assert {
        "training_metadata",
        "test_predictions",
        "thresholds",
        "reliability_calibration",
    } <= manifest["outputs"].keys()
    assert manifest["results"]["leakage"]["clean"] is True
    assert "leakage check: clean" in out
    assert "training/evaluate.py" in out
    for word in ("accuracy", "recall", "precision", "F1"):
        assert word not in out, f"the pipeline printed a metric word: {word}"


def test_the_test_predictions_carry_the_thresholded_decision_and_load_in_the_gate(full):
    from training import calibration as cal
    from training import evaluate as gate
    from training import thresholds as th

    assert _run(full)[0] == 0
    metadata = json.loads((full["out"] / "model" / pl.TRAINING_METADATA).read_text())
    predictions_path = full["out"] / pl.TEST_PREDICTIONS
    items, _ = gate.load_items(
        full["gold_test"], gate.load_predictions(predictions_path)
    )
    assert len(items) == sum(a.total for a in spec.TEST_ALLOCATION)
    probs = np.array([i.probs for i in items])
    decided = th.decide(
        probs, metadata["thresholds"]["critical"], metadata["thresholds"]["urgent"]
    )
    assert [i.pred for i in items] == decided.tolist()
    texts = {r["item_id"]: r["text"] for r in csv.DictReader(full["gold_test"].open())}
    raw = FakePredictor().logits(None, [texts[i.item_id] for i in items], 96, 8)
    assert np.allclose(probs, cal.softmax(raw / metadata["temperature"]), atol=1e-6)


def test_temperature_and_thresholds_never_depend_on_the_test_split(full, tmp_path):
    assert _run(full, predictor=FakePredictor(test_shift=0.0))[0] == 0
    first = json.loads((full["out"] / "model" / pl.TRAINING_METADATA).read_text())
    full["out"] = tmp_path / "run2"
    assert _run(full, predictor=FakePredictor(test_shift=5.0))[0] == 0
    second = json.loads((full["out"] / "model" / pl.TRAINING_METADATA).read_text())
    assert first["temperature"] == second["temperature"]
    assert first["thresholds"] == second["thresholds"]


def test_an_unsafe_cost_matrix_is_refused_before_training(full, capsys):
    config = dict(pl.DEFAULT_CONFIG, cost_matrix=[[0, 5, 5], [1, 0, 1], [1, 1, 0]])
    code, trainer, _ = _run(full, config=config)
    assert code == 2 and trainer.calls == []
    assert "CRITICAL -> ROUTINE" in capsys.readouterr().err


def test_a_config_without_a_max_length_is_refused(full, capsys):
    config = {k: v for k, v in pl.DEFAULT_CONFIG.items() if k != "max_length"}
    code, trainer, _ = _run(full, config=config)
    assert code == 2 and trainer.calls == []
    assert "max_length" in capsys.readouterr().err


def test_a_trainer_crash_is_recorded_as_a_failed_run(full, capsys):
    class Crashing(FakeTrainer):
        def train(self, *args, **kwargs):
            raise RuntimeError("out of memory")

    code, _, _ = _run(full, trainer=Crashing())
    assert code == 1
    manifest = _manifest(full)
    assert manifest["status"] == "failed" and "out of memory" in manifest["error"]
    assert not (full["out"] / "model" / pl.TRAINING_METADATA).exists()


def test_the_metadata_file_is_the_one_the_backend_reads():
    backend = ML_ROOT.parent / "backend/app/services/model_classifier.py"
    assert f'TRAINING_METADATA = "{pl.TRAINING_METADATA}"' in backend.read_text()


# ── The real trainer, on a tiny randomly initialised model ────────────────────
def _tiny_base_model(directory: Path, texts: list[str]) -> Path:
    tokenizers = pytest.importorskip("tokenizers")
    transformers = pytest.importorskip("transformers")
    vocab = {"[PAD]": 0, "[UNK]": 1, "[CLS]": 2, "[SEP]": 3}
    for text in texts:
        for word in text.lower().split():
            vocab.setdefault(word, len(vocab))
    tok = tokenizers.Tokenizer(tokenizers.models.WordLevel(vocab, unk_token="[UNK]"))
    tok.pre_tokenizer = tokenizers.pre_tokenizers.Whitespace()
    fast = transformers.PreTrainedTokenizerFast(
        tokenizer_object=tok,
        pad_token="[PAD]",
        unk_token="[UNK]",
        cls_token="[CLS]",
        sep_token="[SEP]",
    )
    config = transformers.BertConfig(
        vocab_size=len(vocab),
        hidden_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=32,
        max_position_embeddings=64,
        num_labels=3,
    )
    transformers.set_seed(0)
    transformers.BertForSequenceClassification(config).save_pretrained(directory)
    fast.save_pretrained(directory)
    return directory


def test_the_real_trainer_uses_the_cost_sensitive_loss_and_is_seed_deterministic(
    tmp_path, monkeypatch
):
    pytest.importorskip("torch")
    from training import cost_loss

    rows = [
        {
            "text": f"word{k % 7} {cls.lower()} filler{k}",
            "label": cls,
            "language": "english",
        }
        for k, cls in enumerate(spec.CLASSES * 20)
    ]
    base = _tiny_base_model(tmp_path / "base", [r["text"] for r in rows])
    config = dict(
        pl.DEFAULT_CONFIG, base_model=str(base), epochs=2, batch_size=8, max_length=16
    )

    used = []
    original = cost_loss.CostSensitiveLoss.forward

    def spy(self, logits, labels):
        used.append(self.cost_weight)
        return original(self, logits, labels)

    monkeypatch.setattr(cost_loss.CostSensitiveLoss, "forward", spy)
    trainer, predictor = pl.TransformersTrainer(), pl.TransformersPredictor()
    first = trainer.train(rows, config, 7, tmp_path / "a")
    second = trainer.train(rows, config, 7, tmp_path / "b")
    assert used and all(w == config["cost_weight"] for w in used)
    texts = [r["text"] for r in rows[:10]]
    la = predictor.logits(first, texts, 16, 4)
    lb = predictor.logits(second, texts, 16, 4)
    assert la.shape == (10, 3) and np.isfinite(la).all()
    assert np.array_equal(la, lb)


def test_the_committed_default_config_is_the_code_default():
    committed = json.loads((ML_ROOT / "training/configs/pipeline_default.json").read_text())
    assert committed == pl.DEFAULT_CONFIG
    assert pl.validate_config(committed) == []
