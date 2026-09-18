#!/usr/bin/env python
"""Report the float type and column spec of every table, for a machine with no TeX.

WHY THIS EXISTS. The first ACL two-column compile put three pages beyond use:
a single-column `table` printed on top of the adjacent column, and `l` columns
holding sentences ran past the ~3.1in column edge and were clipped rather than
wrapped. None of it was visible from the sources, because LaTeX reports an
Overfull \\hbox as a warning and produces a PDF anyway.

THIS IS NOT A COMPILER AND CANNOT MEASURE ANYTHING. It cannot tell you a table
fits. It can tell you which tables are still single-column, which columns hold
prose in a non-wrapping specifier, and which tables have neither \\small nor a
reduced \\tabcolsep. Those three are what went wrong, so those three are what it
reports. The page is still the only authority on whether a table fits.

    python paper/check_tables.py paper/main.tex
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A column specifier that wraps. Anything else holding a sentence will be
# clipped in a narrow column rather than broken across lines.
WRAPPING = re.compile(r"[pmb]\{|>\{")
# Cells longer than this are prose, not a number or a short label.
PROSE = 45


def sources(entry: Path) -> list[Path]:
    """Every .tex the build reaches from `entry`, transitively."""
    root = entry.parent
    seen: list[Path] = []

    def walk(path: Path) -> None:
        if not path.exists() or path in seen:
            return
        seen.append(path)
        body = re.sub(r"(?m)^\s*%.*$", "", path.read_text(encoding="utf-8"))
        for target in re.findall(r"\\input\{([^}]*)\}", body):
            name = target if target.endswith(".tex") else target + ".tex"
            walk(root / name)

    walk(entry)
    return seen


def tables(path: Path):
    """Yield (float_kind, body) for each table environment in a file."""
    body = re.sub(r"(?m)(?<!\\)%.*$", "", path.read_text(encoding="utf-8"))
    for match in re.finditer(
        r"\\begin\{(table\*?)\}(.*?)\\end\{\1\}", body, flags=re.S
    ):
        yield match.group(1), match.group(2), body[: match.start()].count("\n") + 1


def report(entry: Path) -> int:
    findings: list[str] = []
    total = 0

    for path in sources(entry):
        for kind, body, line in tables(path):
            total += 1
            name = f"{path.name}:{line}"
            label = re.search(r"\\label\{([^}]*)\}", body)
            label = label.group(1) if label else "(no label)"

            spec = re.search(r"\\begin\{tabular\}\{([^}]*)\}", body)
            spec = spec.group(1) if spec else ""

            # Measure the tabular only. A caption is ordinary wrapped text and
            # its length says nothing about whether a column overflows; counting
            # it reported a 603-character "cell" in a table of short numbers.
            inner = re.search(
                r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}", body, flags=re.S
            )
            longest = 0
            for row in (inner.group(1) if inner else "").split("\\\\"):
                for cell in row.split("&"):
                    cleaned = re.sub(r"\\[a-zA-Z]+\{?|[{}]", "", cell).strip()
                    longest = max(longest, len(cleaned))

            flags = []
            if kind == "table":
                flags.append("SINGLE-COLUMN (use table* if it is wide)")
            if longest > PROSE and not WRAPPING.search(spec):
                flags.append(
                    f"prose cell of {longest} chars in a non-wrapping spec "
                    f"'{spec}' (use p{{...}})"
                )
            if longest > PROSE and "\\small" not in body:
                flags.append("no \\small")
            if longest > PROSE and "tabcolsep" not in body:
                flags.append("no reduced \\tabcolsep")

            status = "; ".join(flags) if flags else "ok"
            findings.append(
                f"  {name:34} {kind:7} {label:22} spec={spec or '?':24} "
                f"longest_cell={longest:4}  {status}"
            )

    print(f"{total} table environment(s) reached from {entry}\n")
    print("\n".join(findings))
    risky = [f for f in findings if "ok" not in f.split("  ")[-1]]
    print(f"\n{len(risky)} table(s) carry at least one risk flag.")
    print(
        "\nNOT CHECKED, AND NOT CHECKABLE HERE: whether any table actually fits. "
        "That needs a compile. Read the Overfull \\hbox warnings."
    )
    return 1 if risky else 0


if __name__ == "__main__":
    entry = Path(sys.argv[1] if len(sys.argv) > 1 else "paper/main.tex")
    raise SystemExit(report(entry))
