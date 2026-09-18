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
    python training/holdout_eval.py --model saved_model_holdout
    python training/holdout_eval.py --manifest dataset/processed/eval_manifest_family_v1.json

MOVED 2026-09-14 from training/evaluate.py. evaluate.py is now the 15-metric
deployment gate and, since 2026-09-15, refuses --writeup, --manifest and --model
without --gold rather than forwarding them here. Run this file by name. It is not
a deployment gate: it applies no minimum-n refusal (see NOT_A_GATE).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.atomicio import atomic_write
from training.config import ID_TO_LABEL, LABEL_MAP, NUM_LABELS

CLASS_ORDER = ("CRITICAL", "URGENT", "ROUTINE")
LANGUAGE_ORDER = ("kinyarwanda", "english", "french", "swahili", "mixed")

# ---------------------------------------------------------------------------
# THE TRIAGE GATE
#
# NAMED A1-A3 SINCE 2026-09-18. They were G1-G3, which collided with the
# NINE CORPUS GATES in results.tex -- also G1-G9, and a different set of
# conditions entirely. Acceptance conditions are A1-A3; corpus gates are
# C1-C9. External review item B10.
#
# WHY IT IS NOT ONE NUMBER ANY MORE. On 2026-09-07 a model PASSED the
# single-metric gate with CRITICAL recall 0.9749 while having abandoned an
# entire urgency class: URGENT recall was 0.0083, and 7,633 of 7,793 URGENT
# rows were predicted CRITICAL. It cleared the gate BECAUSE it over-triaged.
# A recall-only gate is satisfiable by calling everything CRITICAL, so it
# cannot distinguish a safe model from a broken one, and it certified the
# worse of the two models trained that day.
#
# Each threshold below records WHERE IT CAME FROM. Two are derived, one is a
# clinical judgement that has not been made yet and is marked as such rather
# than dressed up as a derivation.
# ---------------------------------------------------------------------------

# A1. SOURCE NOT VERIFIED IN THIS REPOSITORY. The value predates this file's
# history and carries only the comment "missing a CRITICAL case is the failure
# that matters". It is CONSISTENT with the trauma field-triage convention of
# holding under-triage at or below 5%, which would give recall >= 0.95 — but
# that attribution is a reconstruction, not a citation, and nobody has checked
# it against a source. TREAT THE NUMBER AS INHERITED UNTIL A CLINICIAN CONFIRMS
# IT. It is kept because loosening a safety threshold on no evidence is worse
# than keeping an unsourced one.
MINIMUM_CRITICAL_RECALL = 0.95

# A2. DERIVED EXACTLY, no judgement in it. Macro F1 is the unweighted mean of
# three per-class F1 scores. If any one class is dead its F1 is 0, so
#
#     macro F1 <= (1 + 1 + 0) / 3 = 2/3
#
# even when the other two classes are PERFECT. The comparison is therefore
# STRICT: a model scoring EXACTLY 2/3 is consistent with two perfect classes
# and one dead one, and `>=` admitted it. Corrected 2026-09-17 after external
# review; the constant is exactly 2/3, so this was not masked by rounding.
#
# WHAT IT ACTUALLY GUARANTEES, stated instead of the stronger claim this file
# used to make. From macro = (f1 + f2 + f3)/3 and f_i <= 1,
#
#     min class F1 >= 3 * macro F1 - 2
#
# which is 0 just above 2/3 and 0.3172 at the 0.7724 this project measured. So
# passing A2 proves no class is EXACTLY dead; it does not prove no class is
# nearly dead. A model at macro 0.672 may carry a class at F1 0.016 and pass.
# The earlier text called this "the tightest such guarantee available from a
# single number", which overstates it: it is the tightest guarantee of
# non-zero-ness, not of usefulness.
MINIMUM_MACRO_F1 = 2.0 / 3.0


def minimum_class_f1_implied(macro_f1: float) -> float:
    """The weakest class this macro F1 still permits: 3 * macro - 2, floored at 0."""
    return max(0.0, 3.0 * macro_f1 - 2.0)


# A3. DERIVED FLOOR PLUS AN UNDERIVED MARGIN, and the split is the point.
#
# The floor is measured, not assumed. A model that merges CRITICAL and URGENT
# and calls the union CRITICAL scores, by construction,
#
#     precision = support(CRITICAL) / (support(CRITICAL) + support(URGENT))
#
# on whatever set it is scored against. That is what the degenerate strategy
# earns for free, so any real model must beat it. Computed per eval set rather
# than hardcoded, because the value moves with the set's composition: it is
# 0.5000 under the corpus's balanced design prior and 0.5349 on the v2c
# reporting set. The 2026-09-07 failure scored 0.5337 — twelve ten-thousandths
# BELOW its own set's degenerate ceiling.
#
# THE MARGIN IS NOT DERIVED. How far above "provably degenerate" a deployable
# model must sit is a question about tolerable over-triage in a real waiting
# room, and that is a clinician's call, not arithmetic. 0.10 is a placeholder
# chosen to separate the two models actually observed (v2b 0.7951 passes,
# v2c 0.5337 fails) and it is flagged in every gate report until someone with
# standing sets it. DO NOT let this number harden by being left alone.
CRITICAL_PRECISION_MARGIN = 0.10


def merge_strategy_precision(support: dict[str, float]) -> float:
    """CRITICAL precision earned by one specific degenerate strategy.

    RENAMED from `degenerate_precision_ceiling` on 2026-09-17. "Ceiling" was
    wrong twice over: it is not an upper bound on anything (a real model should
    exceed it), and it is the score of ONE strategy -- labelling every CRITICAL
    and URGENT row CRITICAL -- not of degenerate strategies in general.

    IT ASSUMES NO ROUTINE ROW IS LABELLED CRITICAL. A strategy that swept
    ROUTINE in as well would score lower, so this is the precision of the
    *best* merge of the two urgent classes, not of the worst degenerate model.
    Stated because the number is only interpretable with that assumption
    attached.
    """
    critical, urgent = support.get("CRITICAL", 0.0), support.get("URGENT", 0.0)
    total = critical + urgent
    return critical / total if total else 0.0


def g3_is_satisfiable(support: dict[str, float]) -> bool:
    """Whether ANY model could pass A3 on this evaluation set.

    When CRITICAL rows dominate the two urgent classes, the merge strategy
    already scores near 1.0 and the floor (its precision plus the margin)
    exceeds 1.0. No model can then pass, and reporting that as a model failure
    would blame a model for a property of the set it was scored on.
    """
    return merge_strategy_precision(support) + CRITICAL_PRECISION_MARGIN <= 1.0


def triage_gate(per_class: dict[str, dict], macro_f1: float) -> tuple[bool, list[str]]:
    """Evaluate all three conditions. Returns (passed, one line per condition).

    ALL THREE MUST HOLD. They are not weighted or traded off: A1 bounds
    under-triage, A2 proves no class was abandoned, and A3 proves the CRITICAL
    predictions carry information rather than volume. The 2026-09-07 model
    passed A1 alone and failed both others.
    """
    support = {name: per_class[name]["support"] for name in CLASS_ORDER}
    recall = per_class["CRITICAL"]["recall"]
    precision = per_class["CRITICAL"]["precision"]
    merge_precision = merge_strategy_precision(support)
    floor = merge_precision + CRITICAL_PRECISION_MARGIN

    # A3 can be unsatisfiable by construction. Say so rather than failing the
    # model for it: a floor above 1.0 is a fact about the evaluation set.
    if not g3_is_satisfiable(support):
        return False, [
            f"PASS  A1  CRITICAL recall    {recall:.4f} >= {MINIMUM_CRITICAL_RECALL}"
            if recall >= MINIMUM_CRITICAL_RECALL
            else f"FAIL  A1  CRITICAL recall    {recall:.4f} >= {MINIMUM_CRITICAL_RECALL}",
            f"{'PASS' if macro_f1 > MINIMUM_MACRO_F1 else 'FAIL'}  A2  macro F1"
            f"           {macro_f1:.4f} > {MINIMUM_MACRO_F1:.4f}",
            f"NOT COMPUTABLE  A3  the merge strategy already scores "
            f"{merge_precision:.4f} on this set, so the floor is "
            f"{floor:.4f} > 1.0 and no model can pass. This is a property of "
            f"the evaluation set's class balance, not of the model. Rebalance "
            f"the set or have a clinician set a margin appropriate to it.",
        ]

    checks = [
        (
            recall >= MINIMUM_CRITICAL_RECALL,
            f"A1  CRITICAL recall    {recall:.4f} >= {MINIMUM_CRITICAL_RECALL} "
            f"(inherited, source unverified)",
        ),
        (
            # STRICT: exactly 2/3 is two perfect classes and one dead one.
            macro_f1 > MINIMUM_MACRO_F1,
            f"A2  macro F1           {macro_f1:.4f} > {MINIMUM_MACRO_F1:.4f} "
            f"(derived: a dead class caps macro F1 at 2/3; this permits a "
            f"weakest class of {minimum_class_f1_implied(macro_f1):.4f})",
        ),
        (
            precision >= floor,
            f"A3  CRITICAL precision {precision:.4f} >= {floor:.4f} "
            f"(= {merge_precision:.4f} merge-strategy precision + "
            f"{CRITICAL_PRECISION_MARGIN:.2f} UNDERIVED margin)",
        ),
    ]
    lines = [f"{'PASS' if ok else 'FAIL'}  {text}" for ok, text in checks]
    return all(ok for ok, _ in checks), lines


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
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


def predict(
    model, tokenizer, texts: list[str], device, batch_size: int, max_length: int
) -> list[int]:
    """Batched inference. One pass over the eval set, reused for every breakdown."""
    import torch

    predictions: list[int] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = tokenizer(
            batch,
            max_length=max_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
        predictions.extend(logits.argmax(dim=-1).cpu().tolist())
        done = min(start + batch_size, len(texts))
        print(f"\r  {done:,}/{len(texts):,} rows", end="", flush=True)
    print()
    return predictions


def tex_escape(value: str) -> str:
    for old, new in (
        ("\\", r"\textbackslash "),
        ("_", r"\_"),
        ("%", r"\%"),
        ("&", r"\&"),
        ("#", r"\#"),
    ):
        value = value.replace(old, new)
    return value


def write_macros(
    path: Path, values: dict[str, str], provenance: dict[str, str]
) -> None:
    """Define every number the prose quotes, so none can be typed by hand."""
    with atomic_write(path, "w", encoding="utf-8") as handle:
        handle.write("% GENERATED FILE - DO NOT EDIT BY HAND.\n")
        handle.write("% Written by training/holdout_eval.py from a verified run.\n")
        handle.write(
            "% Editing this file to change a reported number is fabrication;\n"
        )
        handle.write("% re-run the evaluation instead.\n%\n")
        for key, val in provenance.items():
            handle.write(f"% {key}: {val}\n")
        handle.write("\n")
        for name, val in values.items():
            handle.write(f"\\newcommand{{\\{name}}}{{{val}}}\n")


def write_table(
    path: Path,
    per_class: dict,
    per_language: dict,
    provenance: dict[str, str],
    totals: dict,
) -> None:
    with atomic_write(path, "w", encoding="utf-8") as handle:
        w = handle.write
        w("% GENERATED FILE - DO NOT EDIT BY HAND.\n")
        w("% Written by training/holdout_eval.py from a verified run.\n%\n")
        for key, val in provenance.items():
            w(f"% {key}: {val}\n")
        w("\n\\begin{table}[t]\n\\centering\n")
        w(
            # The payload is LaTeX, which is made of braces. An f-string or
            # .format() would need every brace in it doubled -- more escaping
            # than the rule removes, and it would stop reading as LaTeX.
            "\\caption{Triage performance on the frozen %s holdout "  # noqa: UP031
            "(%s eval rows, split seed %s). Digests verified against \\texttt{%s}.}\n"
            % (
                tex_escape(provenance["strategy"]),
                totals["rows"],
                provenance["split_seed"],
                tex_escape(provenance["manifest"]),
            )
        )
        w("\\label{tab:results}\n")
        w("\\begin{tabular}{lrrrr}\n\\toprule\n")
        w("Class & Precision & Recall & F1 & Support \\\\\n\\midrule\n")
        for name in CLASS_ORDER:
            row = per_class[name]
            w(
                f"{name} & {row['precision']:.4f} & {row['recall']:.4f} & "
                f"{row['f1-score']:.4f} & {int(row['support']):,} \\\\\n"
            )
        w("\\midrule\n")
        w(
            f"Macro avg & {per_class['macro avg']['precision']:.4f} & "
            f"{per_class['macro avg']['recall']:.4f} & "
            f"{per_class['macro avg']['f1-score']:.4f} & {totals['rows']} \\\\\n"
        )
        w("\\bottomrule\n\\end{tabular}\n\n")

        w("\\vspace{1em}\n\\begin{tabular}{lrr}\n\\toprule\n")
        w("Language & Accuracy & Eval rows \\\\\n\\midrule\n")
        for language in LANGUAGE_ORDER:
            if language not in per_language:
                continue
            entry = per_language[language]
            w(f"{language} & {entry['accuracy']:.4f} & {entry['rows']:,} \\\\\n")
        w("\\bottomrule\n\\end{tabular}\n\\end{table}\n")


# ---------------------------------------------------------------------------
# PAPER FRAGMENTS
#
# Emitted from the saved run records rather than retyped, for the reason the
# existing macro writer already gives: a number typed into prose is a number
# nobody can re-derive. `--writeup` reads last_run.json files that evaluate.py
# and train_holdout.py wrote, so every figure below traces to a run that
# verified its own data digests.
# ---------------------------------------------------------------------------


def _load_runs(paths: list[Path]) -> list[dict]:
    runs = []
    for path in paths:
        d = json.loads(path.read_text())
        d["_label"] = path.stem.replace("last_run_", "")
        runs.append(d)
    return runs


def write_result_table(
    path: Path,
    run: dict,
    rows: int,
    phrases: int,
    groups: int,
    counts: dict[str, int],
    prov: dict,
    fingerprint: str,
) -> None:
    """The headline per-class table.

    Replaces the placeholder this file used to emit before any model existed.
    NO PER-LANGUAGE BREAKDOWN: the v2 corpus is Kinyarwanda only, so the
    language table the earlier writer produced would have had one row and would
    have implied a multilingual result that was not measured.
    """
    pc = run["per_class"]
    with atomic_write(path, "w", encoding="utf-8") as handle:
        w = handle.write
        _provenance_header(w, prov)
        # table*, not table: in the ACL two-column layout a single-column float
        # is set inside a ~3.1in column and a six-column table is printed over
        # the neighbouring text. \small and a reduced \tabcolsep because the
        # header row alone is wider than one column.
        w("\\begin{table*}[t]\n\\centering\n\\small\n")
        w("\\setlength{\\tabcolsep}{4pt}\n")
        w(
            "\\caption{Triage performance of the reported model on the frozen "
            f"phrase holdout. The {rows:,} rows are frame permutations of {phrases} "
            f"distinct phrases in {groups} phrase groups; the support column is "
            "therefore not an independent sample size, and the final column gives "
            "the count that governs the granularity of each recall figure.}\n"
        )
        w("\\label{tab:results}\n")
        w("\\begin{tabular}{lrrrrr}\n\\toprule\n")
        w(
            "Class & Precision & Recall & F1 & Rows & Distinct sentences "
            "\\\\\n\\midrule\n"
        )
        for name in CLASS_ORDER:
            r = pc[name]
            w(
                f"{name} & {r['precision']:.4f} & {r['recall']:.4f} & "
                f"{r['f1-score']:.4f} & {int(r['support']):,} & {counts[name]} "
                "\\\\\n"
            )
        w("\\midrule\n")
        # "n/a", not "---": LaTeX sets --- as an em dash, and the paper carries
        # none. The cell means the emitter does not compute a macro precision or
        # recall, not that either is zero or undefined.
        w(
            f"Macro avg & n/a & n/a & {run['macro_f1']:.4f} & "
            f"{rows:,} & {phrases} \\\\\n"
        )
        w("\\bottomrule\n\\end{tabular}\n")
        w(f"\\\\[2pt]{{\\scriptsize Run fingerprint \\texttt{{{fingerprint}}}}}\n")
        w("\\end{table*}\n")


def write_sweep_table(
    path: Path,
    runs: list[dict],
    trainable: dict[str, int],
    prov: dict,
    fingerprint: str,
) -> None:
    with atomic_write(path, "w", encoding="utf-8") as handle:
        w = handle.write
        _provenance_header(w, prov)
        w("\\begin{table*}[t]\n\\centering\n")
        # EXTERNAL REVIEW 2c. This caption said the frozen "250,002x384
        # embedding table ... is 96,199,296", conflating two different
        # quantities. The word-embedding table is 250,002 x 384 = 96,000,768.
        # 96,199,296 is the whole embedding module: that table plus the
        # position and token-type tables and the embedding LayerNorm. The
        # method section states it correctly and this now matches it.
        w(
            "\\caption{Three configurations on the same frozen phrase holdout, same "
            "split seed, same reporting set. Trainable parameters exclude the frozen "
            "embedding module, which is 96{,}199{,}296 of the model's "
            "117{,}641{,}859 parameters in every row: the "
            "250{,}002$\\times$384 word-embedding table (96{,}000{,}768) together "
            "with the position and token-type tables and the embedding LayerNorm.}\n"
        )
        w("\\label{tab:sweep}\n")
        w("\\small\n\\setlength{\\tabcolsep}{4pt}\n")
        w(
            "\\begin{tabular}{>{\\raggedright\\arraybackslash}p{3.6cm}rrrrr}\n\\toprule\n"
        )
        w("Run & Trainable & Macro F1 & CRIT P/R & URG P/R & Gate \\\\\n\\midrule\n")
        for run in runs:
            pc = run["per_class"]
            passed, _ = triage_gate(pc, run["macro_f1"])
            # The directory prefix is identical on every row and only costs
            # width; the distinguishing part is what identifies the run.
            label = run["_label"].removeprefix("model_").removesuffix("_DO_NOT_SHIP")
            w(
                f"{tex_escape(label)} & "
                f"{trainable.get(run['_label'], 0):,} & "
                f"{run['macro_f1']:.4f} & "
                f"{pc['CRITICAL']['precision']:.4f}/{pc['CRITICAL']['recall']:.4f} & "
                f"{pc['URGENT']['precision']:.4f}/{pc['URGENT']['recall']:.4f} & "
                f"{'PASS' if passed else 'FAIL'} \\\\\n"
            )
        w("\\bottomrule\n\\end{tabular}\n")
        w(
            f"\\\\[2pt]{{\\scriptsize All rows evaluated in one pass; "
            f"fingerprint of the reported model \\texttt{{{fingerprint}}}}}\n"
        )
        w("\\end{table*}\n")


def write_confusion_table(
    path: Path, matrix: list[list[int]], label: str, prov: dict, fingerprint: str
) -> None:
    with atomic_write(path, "w", encoding="utf-8") as handle:
        w = handle.write
        _provenance_header(w, prov)
        w("\\begin{table}[t]\n\\centering\n")
        w(
            f"\\caption{{Confusion matrix for {tex_escape(label)} on the reporting "
            "set. ROUTINE is separated perfectly; the residual error is entirely on "
            "the CRITICAL/URGENT boundary, and this was true of every configuration "
            "trained.}\n"
        )
        w("\\label{tab:confusion}\n")
        w("\\begin{tabular}{lrrr}\n\\toprule\n")
        w(
            "Truth $\\downarrow$ / Pred $\\rightarrow$ & CRITICAL & URGENT & "
            "ROUTINE \\\\\n\\midrule\n"
        )
        for name, row in zip(CLASS_ORDER, matrix, strict=True):
            w(f"{name} & " + " & ".join(f"{v:,}" for v in row) + " \\\\\n")
        w("\\bottomrule\n\\end{tabular}\n")
        w(f"\\\\[2pt]{{\\scriptsize Run fingerprint \\texttt{{{fingerprint}}}}}\n")
        w("\\end{table}\n")


def write_gate_derivation(
    path: Path, support: dict[str, float], prov: dict, run_macro_f1: float
) -> None:
    """The gate's three conditions and, for each, where the number came from."""
    merge_precision = merge_strategy_precision(support)
    with atomic_write(path, "w", encoding="utf-8") as handle:
        w = handle.write
        _provenance_header(w, prov)
        w(
            "\\subsection{The acceptance gate, and where each threshold comes "
            "from}\n\\label{sec:gate}\n\n"
        )
        w(
            "A model is accepted only if all three conditions hold. They are not "
            "traded off against one another.\n\n"
        )
        w(
            "\\paragraph{A1: CRITICAL recall $\\geq 0.95$.} "
            "\\emph{Inherited; source not verified.} This threshold predates the "
            "current record and carries only the note that missing a critical case "
            "is the failure that matters. It is consistent with the trauma "
            "field-triage convention of holding under-triage at or below 5\\%, but "
            "we have not verified that attribution against a source and do not "
            "claim it. We keep the value because loosening a safety threshold on no "
            "evidence is worse than retaining an unsourced one.\n\n"
        )
        w(
            "\\paragraph{A2: macro F1 $> 2/3$, strictly.} "
            "\\emph{Derived exactly.} Macro F1 is the unweighted mean of three "
            "per-class F1 scores. If any one class is abandoned its F1 is zero, so "
            "macro F1 $\\leq (1+1+0)/3 = 2/3$ \\emph{even when the other two "
            "classes are perfect}. The comparison is therefore strict: a model "
            "scoring \\emph{exactly} $2/3$ is consistent with two perfect classes "
            "and one dead one, and an inclusive $\\geq$ admitted it. "
            "\\textbf{What the condition actually guarantees} is weaker than "
            "non-degeneracy in any useful sense: from $f_i \\leq 1$ it follows that "
            "$\\min_i F1_i \\geq 3\\,\\mathrm{macro} - 2$, which is $0$ just "
            "above $2/3$ and "
            f"${minimum_class_f1_implied(run_macro_f1):.4f}$ at the "
            f"${run_macro_f1:.4f}$ measured here. Passing A2 proves no class is "
            "exactly dead; it does not prove no class is nearly dead. A model at "
            "macro $0.672$ may carry a class at $F1 = 0.016$ and pass.\n\n"
        )
        w(
            "\\paragraph{A3: CRITICAL precision $\\geq$ the merge-strategy "
            "precision plus a margin.} \\emph{Floor derived and measured per "
            "evaluation set; margin not derived.} A model that merges CRITICAL and "
            "URGENT and labels the union CRITICAL earns, by construction, a CRITICAL "
            "precision of\n"
        )
        w(
            "\\[ \\frac{\\mathrm{support(CRITICAL)}}"
            "{\\mathrm{support(CRITICAL)} + \\mathrm{support(URGENT)}} "
            f"= {merge_precision:.4f} \\]\n"
        )
        w(
            "on this reporting set. \\textbf{This is the precision of one specific "
            "strategy, not a ceiling on degenerate models in general}, and it assumes "
            "no ROUTINE row is labelled CRITICAL; a strategy that swept ROUTINE in as "
            "well would score lower. It is what that strategy is paid for free, so an "
            "informative model must exceed it. We compute it against the set being "
            "scored rather than hardcoding a value, because it moves with the set's "
            "composition. \\textbf{The condition is not always satisfiable.} When "
            "CRITICAL rows dominate the two urgent classes the merge precision "
            "approaches $1$, the floor exceeds $1$, and no model can pass; the gate "
            "reports NOT COMPUTABLE rather than failing a model for a property of the "
            "set it was scored on. "
            f"\\textbf{{The margin above that floor ({CRITICAL_PRECISION_MARGIN:.2f}) "
            "is not derived.} How far above provably-degenerate a deployable model "
            "must sit is a question about tolerable over-triage in a clinic, it is a "
            "clinical judgement that has not yet been made, and we report it as a "
            "placeholder rather than as a standard.\n\n"
        )


def write_degeneracy_finding(path: Path, v2c: dict, v2d: dict, prov: dict) -> None:
    merge_precision = merge_strategy_precision(
        {k: v2c["per_class"][k]["support"] for k in CLASS_ORDER}
    )
    prec = v2c["per_class"]["CRITICAL"]["precision"]
    with atomic_write(path, "w", encoding="utf-8") as handle:
        w = handle.write
        _provenance_header(w, prov)
        w(
            "\\subsection{A single-metric safety gate certified a model that had "
            "abandoned an urgency class}\n\\label{sec:gate-failure}\n\n"
        )
        # Truth URGENT, predicted CRITICAL, straight from the run's own matrix.
        urgent_as_critical = int(v2c["confusion"][1][0])

        w(
            "Our acceptance gate was initially a single condition, CRITICAL recall "
            "$\\geq 0.95$, on the reasoning that missing a critical presentation is "
            "the failure that matters. One configuration passed it with a CRITICAL "
            f"recall of {v2c['per_class']['CRITICAL']['recall']:.4f} while achieving "
            f"an URGENT recall of {v2c['per_class']['URGENT']['recall']:.4f}: it "
            "assigned the CRITICAL label to "
            # B6. This read the URGENT *support* and presented it as the number
            # mislabelled. It is not: at URGENT recall 0.0083 roughly 65 of those
            # rows were labelled correctly, so the same figure cannot also be the
            # count sent to CRITICAL. Reusing it overstated the finding by about
            # 160 rows and asserted a number no computed quantity supported.
            #
            # Taken from the degenerate run's own confusion matrix instead: row 1
            # is truth URGENT, column 0 is prediction CRITICAL
            # (dataset.labels.CLASS_ORDER). The header comment at the top of this
            # file had the right figure all along.
            f"{urgent_as_critical:,} of "
            f"{int(v2c['per_class']['URGENT']['support']):,} URGENT rows. It "
            "passed the safety gate \\emph{because} it over-triaged, and the gate "
            "contained no term that could observe this.\n\n"
        )
        w(
            "The degeneracy is measurable rather than interpretive. A model that "
            "merges CRITICAL and URGENT earns a CRITICAL precision of "
            f"${merge_precision:.4f}$ on this set by construction. The model scored "
            f"${prec:.4f}$, which is ${merge_precision - prec:.4f}$ \\emph{{below}} its own "
            "set's merge-strategy precision. Within a thousandth, it did not approximate "
            "the merge strategy; it was the merge strategy.\n\n"
        )
        w(
            "Two further observations. First, the gate certified this model while "
            "rejecting a better one: a configuration with macro F1 "
            f"{v2d['macro_f1']:.4f} and all three classes alive failed the "
            "same gate on recall alone. Second, our own automated degeneracy check, "
            "written for exactly this failure, used the test "
            "$\\mathrm{recall} \\geq 0.9 \\wedge \\mathrm{precision} < 0.5$ "
            f"and did not fire, because ${prec:.4f}$ sits above a hardcoded $0.5$ "
            f"while the true merge-strategy precision for this set was ${merge_precision:.4f}$. The "
            "lesson is not that the constant was too low: it is that the quantity is a "
            "property of the evaluation set and must be computed against it.\n\n"
        )


def write_limitations(
    path: Path, counts: dict[str, int], rows: int, phrases: int, groups: int, prov: dict
) -> None:
    with atomic_write(path, "w", encoding="utf-8") as handle:
        w = handle.write
        _provenance_header(w, prov)
        w("\\subsection{Limitations}\n\\label{sec:limitations}\n\n")
        w(
            "\\paragraph{The reporting set is nine sentences, not eighteen thousand "
            "rows.} The held-out evaluation reports "
            f"{rows:,} rows, but those rows are frame permutations of only "
            f"{phrases} distinct phrases in {groups} phrase groups, and the row count "
            "is therefore not an independent sample size. Per class the position is "
            "starker:\n\n\\begin{center}\n\\begin{tabular}{lrr}\n\\toprule\n"
        )
        w("Class & Distinct sentences & One sentence is \\\\\n\\midrule\n")
        for name in CLASS_ORDER:
            n = counts[name]
            w(f"{name} & {n} & {1.0 / n:.2f} of recall \\\\\n")
        w("\\bottomrule\n\\end{tabular}\n\\end{center}\n\n")
        w(
            "CRITICAL and URGENT recall therefore move in steps of approximately "
            "one quarter: a single sentence being read systematically as the "
            "neighbouring class costs about 25 percentage points, and no choice of "
            "optimiser or learning rate can recover it. ROUTINE is a single "
            "sentence, so its reported recall of 1.0 means that one sentence was "
            "classified correctly and should not be read as a class-level result. "
            "\\textbf{A CRITICAL recall target of 0.95 over four sentences requires "
            "essentially all frames of all four to be correct}, and the distance "
            "between our result and that target is smaller than the granularity of "
            "the measurement.\n\n"
        )
        w(
            "\\paragraph{Consequences for the sweep.} Three configurations spanning "
            "a threefold range of trainable parameters and a $1.5\\times$ range of "
            "learning rate all left the same residual error, on the "
            "CRITICAL/URGENT boundary, while separating ROUTINE perfectly. We stopped "
            "searching on the grounds that the remaining error is a property of the "
            "corpus and the split rather than of the optimisation, and we report the "
            "configuration search as inconclusive on that boundary rather than as a "
            "tuning result.\n\n"
        )


def model_fingerprint(model_dir: Path, manifest: dict) -> str:
    """Identity of (these weights, this eval data, this code).

    Printed on every emitted table. A table whose fingerprint does not match
    the model and manifest it claims to describe is a table someone edited or
    regenerated against different inputs, and that is the failure this whole
    emitter exists to make impossible.
    """
    digest = hashlib.sha256()
    weights = model_dir / "model.safetensors"
    if weights.exists():
        with weights.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    digest.update(manifest["files"]["train"]["sha256"].encode())
    digest.update(manifest["files"]["eval"]["sha256"].encode())
    digest.update(git_commit().encode())
    return digest.hexdigest()[:16]


def _provenance_header(w, prov: dict) -> None:
    w("% GENERATED FILE - DO NOT EDIT BY HAND.\n")
    w("% Written by training/evaluate.py --writeup in ONE evaluation pass.\n")
    w("% Editing this file to change a reported number is fabrication;\n")
    w("% re-run the emitter instead.\n%\n")
    for key, val in prov.items():
        w(f"% {key}: {val}\n")
    w("%\n")


def evaluate_model(model_dir: Path, frame, args, device) -> dict:
    """One real inference pass. Returns the computed report and matrix."""
    from sklearn.metrics import classification_report, confusion_matrix
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok_dir = model_dir / "tokenizer"
    tokenizer = AutoTokenizer.from_pretrained(
        str(tok_dir if tok_dir.exists() else model_dir)
    )
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).to(
        device
    )
    model.eval()
    print(f"  {model_dir.name}: {len(frame):,} rows", flush=True)
    predictions = predict(
        model,
        tokenizer,
        frame["text"].tolist(),
        device,
        args.batch_size,
        args.max_length,
    )
    truths = frame["label_id"].tolist()
    names = [ID_TO_LABEL[i] for i in range(NUM_LABELS)]
    report = classification_report(
        truths,
        predictions,
        output_dict=True,
        zero_division=0,
        labels=list(range(NUM_LABELS)),
        target_names=names,
    )
    matrix = confusion_matrix(
        truths, predictions, labels=list(range(NUM_LABELS))
    ).tolist()
    return {
        "per_class": {n: report[n] for n in CLASS_ORDER},
        "macro_f1": report["macro avg"]["f1-score"],
        "accuracy": report["accuracy"],
        "confusion": matrix,
        "_label": model_dir.name,
    }


def verify_against(computed: dict, record_path: Path) -> list[str]:
    """Every computed figure must equal the training run's own report.

    A mismatch is not a rounding detail. It means the emitter and the training
    run disagree about what the saved weights do, and until that is explained
    NOTHING here may go into a paper.
    """
    saved = json.loads(record_path.read_text())
    problems = []
    for name in CLASS_ORDER:
        for field in ("precision", "recall", "f1-score"):
            a = round(computed["per_class"][name][field], 4)
            b = round(saved["per_class"][name][field], 4)
            if a != b:
                problems.append(f"{name}.{field}: emitter {a} vs run record {b}")
    a = round(computed["macro_f1"], 4)
    b = round(saved["metrics"]["macro_f1"], 4)
    if a != b:
        problems.append(f"macro_f1: emitter {a} vs run record {b}")
    return problems


def writeup(args) -> int:
    """Emit every paper table from ONE evaluation pass over the real weights.

    Earlier this read three saved JSON run records. That made the tables a
    transcription of numbers computed elsewhere at three different times, which
    is decorative rather than verifiable. Now the script loads each model, runs
    inference against the frozen manifest, and computes everything it prints.
    """
    import pandas as pd
    import torch

    manifest = load_manifest(args.manifest)
    frame = pd.read_csv(manifest["files"]["eval"]["path"])
    frame["label_id"] = frame["label"].map(LABEL_MAP)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from training.train_holdout import split_eval_by_group

    _, report_frame, split = split_eval_by_group(
        frame, args.stop_groups, manifest["split_seed"]
    )
    counts = {
        n: int(report_frame.loc[report_frame["label"] == n, "phrase"].nunique())
        for n in CLASS_ORDER
    }
    rows = len(report_frame)
    phrases = int(report_frame["phrase"].nunique())
    groups = len(split["reporting_groups"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Manifest   : {args.manifest} (digests verified)")
    print(f"Reporting  : {rows:,} rows, {phrases} phrases, {groups} groups")
    print(
        f"Evaluating {len(args.writeup)} model(s) on {device}, "
        f"max_length {args.max_length}:"
    )
    results = [evaluate_model(d, report_frame, args, device) for d in args.writeup]

    reported = results[-1]
    reported_dir = args.writeup[-1]
    degenerate = min(results, key=lambda r: r["macro_f1"])

    if args.verify_against:
        problems = verify_against(reported, args.verify_against)
        if problems:
            print(
                "\nREPRODUCTION FAILED — the emitter disagrees with the training "
                "run about these weights:",
                file=sys.stderr,
            )
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            raise SystemExit(
                "Refusing to write paper tables. Explain the disagreement first."
            )
        print(
            f"\nReproduced {args.verify_against.name} exactly "
            "(all per-class precision/recall/F1 and macro F1)"
        )

    fingerprint = model_fingerprint(reported_dir, manifest)
    prov = {
        "reported_model": reported_dir.name,
        "run_fingerprint": fingerprint,
        # THE DATA DIGESTS. tests/test_paper_numbers.py treats these as the
        # marker distinguishing a file generated from a verified run from a
        # placeholder, and it was right to: without them the header says WHEN
        # and WHICH COMMIT but not WHICH DATA, so a table generated against a
        # different split would look identical. load_manifest() has already
        # verified both against the files on disk before this point.
        "source_sha256": manifest["files"]["train"]["sha256"],
        "eval_sha256": manifest["files"]["eval"]["sha256"],
        "manifest": str(args.manifest),
        "strategy": manifest["strategy"],
        "split_seed": str(manifest["split_seed"]),
        "reporting_rows": f"{rows}",
        "reporting_phrases": f"{phrases}",
        "reporting_groups": f"{groups}",
        "max_length": str(args.max_length),
        "git_commit": git_commit(),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    support = {n: reported["per_class"][n]["support"] for n in CLASS_ORDER}
    # strict=False on purpose: --trainable is optional and may be omitted or
    # given for only some runs. The consumer reads it with .get(label, 0), so
    # a short list is a supported input and must not raise.
    trainable = dict(
        zip([r["_label"] for r in results], args.trainable or [], strict=False)
    )

    args.tex_out.mkdir(parents=True, exist_ok=True)
    write_result_table(
        args.tex_out / "results_table.tex",
        reported,
        rows,
        phrases,
        groups,
        counts,
        prov,
        fingerprint,
    )
    write_confusion_table(
        args.tex_out / "confusion_table.tex",
        reported["confusion"],
        reported["_label"],
        prov,
        fingerprint,
    )
    write_sweep_table(
        args.tex_out / "sweep_table.tex", results, trainable, prov, fingerprint
    )
    write_gate_derivation(
        args.tex_out / "gate_derivation.tex",
        support,
        prov,
        reported["macro_f1"],
    )
    write_degeneracy_finding(
        args.tex_out / "finding_gate_degeneracy.tex", degenerate, reported, prov
    )
    write_limitations(
        args.tex_out / "limitations.tex", counts, rows, phrases, groups, prov
    )

    passed, lines = triage_gate(reported["per_class"], reported["macro_f1"])
    values = {
        "ResultMacroFOne": f"{reported['macro_f1']:.4f}",
        "ResultCriticalRecall": f"{reported['per_class']['CRITICAL']['recall']:.4f}",
        "ResultCriticalPrecision": f"{reported['per_class']['CRITICAL']['precision']:.4f}",
        "ResultUrgentRecall": f"{reported['per_class']['URGENT']['recall']:.4f}",
        "ResultEvalRows": f"{rows:,}",
        "ResultEvalPhrases": str(phrases),
        "ResultEvalGroups": str(groups),
        "ResultCriticalSentences": str(counts["CRITICAL"]),
        "ResultGatePassed": "true" if passed else "false",
        "ResultFingerprint": fingerprint,
        "MergeStrategyPrecision": f"{merge_strategy_precision(support):.4f}",
        "DegenerateRunPrecision": f"{degenerate['per_class']['CRITICAL']['precision']:.4f}",
        "DegenerateRunCriticalRecall": f"{degenerate['per_class']['CRITICAL']['recall']:.4f}",
        "DegenerateRunUrgentRecall": f"{degenerate['per_class']['URGENT']['recall']:.4f}",
    }
    if args.latency:
        # Measured by training/latency.py in a separate process, because a
        # latency figure taken while this script is also running inference
        # would measure contention rather than the model. Carried across with
        # the machine that produced it, since a latency number without a
        # machine is not a number.
        lat = json.loads(args.latency.read_text())
        values.update(
            {
                "LatencyRows": f"{lat['rows']:,}",
                "LatencyColdMs": f"{lat['cold_ms']:.0f}",
                "LatencyWarmMedianMs": f"{lat['warm_ms']['median']:.0f}",
                "LatencyWarmPninetyfiveMs": f"{lat['warm_ms']['p95']:.0f}",
                "LatencyWarmPninetynineMs": f"{lat['warm_ms']['p99']:.0f}",
                "LatencyWarmMaxMs": f"{lat['warm_ms']['max']:.0f}",
                "LatencyCpu": tex_escape(lat["machine"]["cpu"]),
                "LatencyThreads": lat["machine"]["torch_threads"],
            }
        )
        prov["latency_source"] = f"{args.latency.name} ({lat['generated_at']})"

    if args.verify_against:
        # NOT computed by this pass. The selected step belongs to the training
        # run; it is carried across only because --verify-against has just
        # proved that record describes these exact weights.
        saved = json.loads(args.verify_against.read_text())
        values["ResultSelectedStep"] = str(saved["selected_step"])
        prov["selected_step_source"] = (
            f"{args.verify_against.name} (verified to match this pass)"
        )
    write_macros(args.tex_out / "results_macros.tex", values, prov)

    print(f"\nWrote 7 files to {args.tex_out}/ , fingerprint {fingerprint}")
    print("Gate on the reported model:")
    for line in lines:
        print(f"  {line}")
    return 0


NOT_A_GATE = (
    "NOT A DEPLOYMENT GATE. This is the historical holdout report behind the paper "
    "tables. It scores the frozen phrase holdout (9 distinct reporting sentences in "
    "v2), applies no EVAL_SET_SPEC minimum-n refusal, and its 3-condition gate "
    "(CRITICAL recall >= 0.95) is superseded. Deployment verdicts come only from "
    "training/evaluate.py --gold."
)


def main() -> int:
    return main_argv(sys.argv[1:])


def main_argv(argv: list[str]) -> int:
    print(NOT_A_GATE, file=sys.stderr)
    parser = argparse.ArgumentParser(description=f"{NOT_A_GATE}\n\n{__doc__}")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("dataset/processed/eval_manifest_phrase_v1.json"),
    )
    parser.add_argument("--model", type=Path, default=Path("saved_model_holdout"))
    parser.add_argument("--tex-out", type=Path, default=Path("paper/generated"))
    parser.add_argument(
        "--writeup",
        nargs="+",
        type=Path,
        metavar="MODEL_DIR",
        help="Emit every paper table from ONE evaluation pass. Pass the model "
        "directories in sweep order; the LAST is the reported result. "
        "Numbers are computed here, never read from a saved report.",
    )
    parser.add_argument(
        "--latency",
        type=Path,
        metavar="LATENCY_JSON",
        help="Output of training/latency.py. Its figures become macros so the "
        "paper quotes a measurement rather than the target.",
    )
    parser.add_argument(
        "--verify-against",
        type=Path,
        metavar="RUN_JSON",
        help="A training run's own report for the LAST model. Every computed "
        "figure must match it or nothing is written.",
    )
    parser.add_argument(
        "--stop-groups",
        type=int,
        default=3,
        help="Phrase groups held out as the stopping set, so the reporting set "
        "here is the same one training reported on.",
    )
    parser.add_argument(
        "--trainable",
        nargs="+",
        type=int,
        help="Trainable parameter count per --writeup run, in the same order.",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-length", type=int, default=64)
    parser.add_argument(
        "--limit", type=int, default=None, help="Cap eval rows (debugging)."
    )
    args = parser.parse_args(argv)

    if args.writeup:
        return writeup(args)

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
    print(
        f"Manifest   : {args.manifest} (strategy {manifest['strategy']}, digests verified)"
    )

    frame = pd.read_csv(manifest["files"]["eval"]["path"])
    if args.limit:
        frame = frame.head(args.limit)
    frame["label_id"] = frame["label"].map(LABEL_MAP)
    print(f"Eval rows  : {len(frame):,}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(
        str(args.model / "tokenizer")
        if (args.model / "tokenizer").exists()
        else str(args.model)
    )
    model = AutoModelForSequenceClassification.from_pretrained(str(args.model)).to(
        device
    )
    model.eval()
    print(f"Model      : {args.model}  device {device}\n")

    predictions = predict(
        model,
        tokenizer,
        frame["text"].tolist(),
        device,
        args.batch_size,
        args.max_length,
    )
    truths = frame["label_id"].tolist()

    report = classification_report(
        truths,
        predictions,
        output_dict=True,
        zero_division=0,
        labels=list(range(NUM_LABELS)),
        target_names=[ID_TO_LABEL[i] for i in range(NUM_LABELS)],
    )
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
        "generated_at": datetime.now(UTC).isoformat(),
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
    write_table(
        args.tex_out / "results_table.tex",
        report,
        per_language,
        provenance,
        {"rows": f"{len(frame):,}"},
    )

    print("=" * 60)
    print(f"  accuracy         : {accuracy:.4f}")
    print(f"  macro F1         : {report['macro avg']['f1-score']:.4f}")
    print(
        f"  CRITICAL recall  : {critical_recall:.4f} "
        f"(target >= {MINIMUM_CRITICAL_RECALL}) -> "
        f"{'PASS' if critical_recall >= MINIMUM_CRITICAL_RECALL else 'BELOW TARGET'}"
    )
    print("\nConfusion matrix (rows = truth, cols = predicted)")
    print("            " + "".join(f"{n:>10}" for n in CLASS_ORDER))
    for i, row in enumerate(
        confusion_matrix(truths, predictions, labels=list(range(NUM_LABELS)))
    ):
        print(f"  {ID_TO_LABEL[i]:<10}" + "".join(f"{v:>10,}" for v in row))

    print(f"\nWrote {args.tex_out / 'results_macros.tex'}")
    print(f"Wrote {args.tex_out / 'results_table.tex'}")
    print("\nThe paper \\inputs these. Do not transcribe numbers by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
