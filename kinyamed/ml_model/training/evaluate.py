#!/usr/bin/env python
"""Evaluate a trained model on a frozen split and emit the paper's numbers.

Every figure the paper reports is written from here into LaTeX that the
document \\inputs, so a number can only appear in the paper if a real run
produced it. There is no path by which a hand-typed figure survives: the macros
the paper uses are defined in the generated file, and the committed placeholder
defines them as visible TBD tokens.

The split comes from a frozen manifest and its SHA-256 digests are verified
before inference, so a reported score is always traceable to exactly the rows
that produced it. The previous version of this script evaluated
dataset/processed/test.csv — a random split with no leakage control — which is
not a defensible basis for any published claim.

Usage:
    python training/evaluate.py --model saved_model_holdout
    python training/evaluate.py --manifest dataset/processed/eval_manifest_family_v1.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.atomicio import atomic_write  # noqa: E402
from training.config import ID_TO_LABEL, LABEL_MAP, NUM_LABELS  # noqa: E402

CLASS_ORDER = ("CRITICAL", "URGENT", "ROUTINE")
LANGUAGE_ORDER = ("kinyarwanda", "english", "french", "swahili", "mixed")
# Missing a CRITICAL case is the failure that matters in triage.
MINIMUM_CRITICAL_RECALL = 0.95


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def load_manifest(path: Path) -> dict:
    """Load a frozen manifest and verify every digest before trusting it."""
    from dataset.freeze_eval import sha256

    manifest = json.loads(path.read_text())
    for name, entry in manifest["files"].items():
        target = Path(entry["path"])
        if not target.exists():
            raise SystemExit(
                f"{name} split missing: {target}\n"
                "Run `make dataset && make splits` to rebuild it."
            )
        actual = sha256(target)
        if actual != entry["sha256"]:
            raise SystemExit(
                f"{name} split has drifted from {path.name}.\n"
                f"  expected {entry['sha256']}\n  actual   {actual}\n"
                "Refusing to evaluate: the score would not describe the frozen split."
            )
    return manifest


def predict(model, tokenizer, texts: list[str], device, batch_size: int, max_length: int) -> list[int]:
    """Batched inference. One pass over the eval set, reused for every breakdown."""
    import torch

    predictions: list[int] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = tokenizer(batch, max_length=max_length, padding=True,
                            truncation=True, return_tensors="pt")
        encoded = {k: v.to(device) for k, v in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
        predictions.extend(logits.argmax(dim=-1).cpu().tolist())
        done = min(start + batch_size, len(texts))
        print(f"\r  {done:,}/{len(texts):,} rows", end="", flush=True)
    print()
    return predictions


def tex_escape(value: str) -> str:
    for old, new in (("\\", r"\textbackslash "), ("_", r"\_"), ("%", r"\%"),
                     ("&", r"\&"), ("#", r"\#")):
        value = value.replace(old, new)
    return value


def write_macros(path: Path, values: dict[str, str], provenance: dict[str, str]) -> None:
    """Define every number the prose quotes, so none can be typed by hand."""
    with atomic_write(path, "w", encoding="utf-8") as handle:
        handle.write("% GENERATED FILE — DO NOT EDIT BY HAND.\n")
        handle.write("% Written by training/evaluate.py from a verified run.\n")
        handle.write("% Editing this file to change a reported number is fabrication;\n")
        handle.write("% re-run the evaluation instead.\n%\n")
        for key, val in provenance.items():
            handle.write(f"% {key}: {val}\n")
        handle.write("\n")
        for name, val in values.items():
            handle.write(f"\\newcommand{{\\{name}}}{{{val}}}\n")


def write_table(path: Path, per_class: dict, per_language: dict,
                provenance: dict[str, str], totals: dict) -> None:
    with atomic_write(path, "w", encoding="utf-8") as handle:
        w = handle.write
        w("% GENERATED FILE — DO NOT EDIT BY HAND.\n")
        w("% Written by training/evaluate.py from a verified run.\n%\n")
        for key, val in provenance.items():
            w(f"% {key}: {val}\n")
        w("\n\\begin{table}[t]\n\\centering\n")
        w("\\caption{Triage performance on the frozen %s holdout "
          "(%s eval rows, split seed %s). Digests verified against \\texttt{%s}.}\n"
          % (tex_escape(provenance["strategy"]), totals["rows"],
             provenance["split_seed"], tex_escape(provenance["manifest"])))
        w("\\label{tab:results}\n")
        w("\\begin{tabular}{lrrrr}\n\\toprule\n")
        w("Class & Precision & Recall & F1 & Support \\\\\n\\midrule\n")
        for name in CLASS_ORDER:
            row = per_class[name]
            w(f"{name} & {row['precision']:.4f} & {row['recall']:.4f} & "
              f"{row['f1-score']:.4f} & {int(row['support']):,} \\\\\n")
        w("\\midrule\n")
        w(f"Macro avg & {per_class['macro avg']['precision']:.4f} & "
          f"{per_class['macro avg']['recall']:.4f} & "
          f"{per_class['macro avg']['f1-score']:.4f} & {totals['rows']} \\\\\n")
        w("\\bottomrule\n\\end{tabular}\n\n")

        w("\\vspace{1em}\n\\begin{tabular}{lrr}\n\\toprule\n")
        w("Language & Accuracy & Eval rows \\\\\n\\midrule\n")
        for language in LANGUAGE_ORDER:
            if language not in per_language:
                continue
            entry = per_language[language]
            w(f"{language} & {entry['accuracy']:.4f} & {entry['rows']:,} \\\\\n")
        w("\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=Path("dataset/processed/eval_manifest_phrase_v1.json"))
    parser.add_argument("--model", type=Path, default=Path("saved_model_holdout"))
    parser.add_argument("--tex-out", type=Path, default=Path("paper/generated"))
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-length", type=int, default=64)
    parser.add_argument("--limit", type=int, default=None, help="Cap eval rows (debugging).")
    args = parser.parse_args()

    if not args.model.exists():
        raise SystemExit(
            f"No trained model at {args.model}.\n"
            "Nothing has been trained yet, so there are no numbers to report.\n"
            "The committed placeholder in paper/generated/ keeps the paper's macros\n"
            "showing TBD tokens until a real run replaces them."
        )

    import pandas as pd
    import torch
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    manifest = load_manifest(args.manifest)
    print(f"Manifest   : {args.manifest} (strategy {manifest['strategy']}, digests verified)")

    frame = pd.read_csv(manifest["files"]["eval"]["path"])
    if args.limit:
        frame = frame.head(args.limit)
    frame["label_id"] = frame["label"].map(LABEL_MAP)
    print(f"Eval rows  : {len(frame):,}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(args.model / "tokenizer")
                                              if (args.model / "tokenizer").exists()
                                              else str(args.model))
    model = AutoModelForSequenceClassification.from_pretrained(str(args.model)).to(device)
    model.eval()
    print(f"Model      : {args.model}  device {device}\n")

    predictions = predict(model, tokenizer, frame["text"].tolist(), device,
                          args.batch_size, args.max_length)
    truths = frame["label_id"].tolist()

    report = classification_report(truths, predictions, output_dict=True, zero_division=0,
                                   labels=list(range(NUM_LABELS)),
                                   target_names=[ID_TO_LABEL[i] for i in range(NUM_LABELS)])
    accuracy = accuracy_score(truths, predictions)
    critical_recall = report["CRITICAL"]["recall"]

    per_language: dict[str, dict] = {}
    frame = frame.assign(prediction=predictions)
    for language, group in frame.groupby("language"):
        per_language[language] = {
            "accuracy": accuracy_score(group["label_id"], group["prediction"]),
            "rows": len(group),
        }

    provenance = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "manifest": str(args.manifest),
        "strategy": manifest["strategy"],
        "split_seed": str(manifest["split_seed"]),
        "source_sha256": manifest["source"]["sha256"],
        "eval_sha256": manifest["files"]["eval"]["sha256"],
        "model": str(args.model),
    }

    values = {
        "ResultAccuracy": f"{accuracy * 100:.1f}\\%",
        "ResultAccuracyRaw": f"{accuracy:.4f}",
        "ResultCriticalRecall": f"{critical_recall:.3f}",
        "ResultMacroFOne": f"{report['macro avg']['f1-score']:.3f}",
        "ResultWeightedFOne": f"{report['weighted avg']['f1-score']:.3f}",
        "ResultEvalRows": f"{len(frame):,}",
        "ResultSplitStrategy": manifest["strategy"],
        "ResultSplitSeed": str(manifest["split_seed"]),
        "ResultGitCommit": tex_escape(provenance["git_commit"]),
    }

    args.tex_out.mkdir(parents=True, exist_ok=True)
    write_macros(args.tex_out / "results_macros.tex", values, provenance)
    write_table(args.tex_out / "results_table.tex", report, per_language, provenance,
                {"rows": f"{len(frame):,}"})

    print("=" * 60)
    print(f"  accuracy         : {accuracy:.4f}")
    print(f"  macro F1         : {report['macro avg']['f1-score']:.4f}")
    print(f"  CRITICAL recall  : {critical_recall:.4f} "
          f"(target >= {MINIMUM_CRITICAL_RECALL}) -> "
          f"{'PASS' if critical_recall >= MINIMUM_CRITICAL_RECALL else 'BELOW TARGET'}")
    print("\nConfusion matrix (rows = truth, cols = predicted)")
    print("            " + "".join(f"{n:>10}" for n in CLASS_ORDER))
    for i, row in enumerate(confusion_matrix(truths, predictions,
                                             labels=list(range(NUM_LABELS)))):
        print(f"  {ID_TO_LABEL[i]:<10}" + "".join(f"{v:>10,}" for v in row))

    print(f"\nWrote {args.tex_out / 'results_macros.tex'}")
    print(f"Wrote {args.tex_out / 'results_table.tex'}")
    print("\nThe paper \\inputs these. Do not transcribe numbers by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
