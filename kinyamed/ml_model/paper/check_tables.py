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
WRAPPING = re.compile(r"[pmb]\{|>\{|X")
# Cells longer than this are prose, not a number or a short label.
PROSE = 45


# Geometry, from acl.sty: a4paper with a 2.5cm geometry margin and
# \columnsep 0.6cm. These are the two widths a table can overflow.
#
# \textwidth IS NOT THE COLUMN. In a two-column document \textwidth is the full
# 455.2pt page and a single column is 219.1pt, less than half of it. Every
# overflow this script was written for came from that confusion: a \parbox at
# 0.9\textwidth inside a column, a p{0.58\textwidth} column, and a proposal to
# wrap a table in \resizebox{\textwidth} inside a column, which would have
# overflowed by more than double. Inside a column the correct length is
# \columnwidth (or \linewidth); \textwidth is correct only in a table* or
# figure*, which span both columns.
PT_PER_MM = 72.27 / 25.4
TEXTWIDTH_PT = (210 - 2 * 25) * PT_PER_MM  # 455.2pt, what table* gets
COLUMN_PT = (TEXTWIDTH_PT - 6 * PT_PER_MM) / 2  # 219.1pt, what table gets

# More than this many columns in a single-column float is the shape that
# collided with body text on page 23 (six columns) and page 28 (four).
MAX_SINGLE_COLUMN_COLUMNS = 4


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


def tabular_spec(body: str) -> str:
    """The preamble of the first tabular, with nested braces balanced.

    A regex of [^}]* stops at the FIRST closing brace, so
    `*{6}{>{\\raggedright\\arraybackslash}p{1.6cm}}` was read as `*{6` and every
    column count for a spec containing p{} came out wrong. This walks the braces
    from the character immediately after \\begin{tabular}, skipping an optional
    [t]/[b] position argument.
    """
    # tabularx/tabular*: \begin{tabularx}{<width>}{<spec>}. The width is a
    # brace group BEFORE the spec, so the spec is the SECOND group. Reading
    # the first gave "\textwidth" as a column spec and a count of 0, which a
    # reader would take for "no problem" rather than "not parsed".
    width_groups = 0
    for marker, groups in (
        ("\\begin{tabularx}", 1),
        ("\\begin{tabular*}", 1),
        ("\\begin{tabular}", 0),
    ):
        at = body.find(marker)
        if at != -1:
            width_groups = groups
            break
    else:
        return ""
    i = at + len(marker)
    if i < len(body) and body[i] == "[":
        i = body.find("]", i) + 1
    for _ in range(width_groups):
        if i >= len(body) or body[i] != "{":
            return ""
        depth, i = 1, i + 1
        while i < len(body) and depth:
            depth += (body[i] == "{") - (body[i] == "}")
            i += 1
    if i >= len(body) or body[i] != "{":
        return ""
    depth, out = 1, []
    for ch in body[i + 1 :]:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        out.append(ch)
    return "".join(out)


def column_count(spec: str) -> int:
    """Columns declared by a tabular preamble, expanding *{n}{...}."""
    spec = re.sub(r"@\{[^}]*\}", "", spec)
    total = 0
    # *{6}{>{\raggedright\arraybackslash}p{1.6cm}} is six columns. Strip the
    # >{...} modifier FIRST: counting [lcrpmb] inside \raggedright and
    # \arraybackslash reported 0 columns for exactly this spec.
    for repeat, inner in re.findall(r"\*\{(\d+)\}\{(.*?)\}\}", spec):
        stripped = re.sub(r">\{[^{}]*(?:\{[^{}]*\})?[^{}]*\}", "", inner + "}")
        stripped = re.sub(r"[pmb]\{[^}]*\}", "P", stripped)
        total += int(repeat) * max(1, len(re.findall(r"[lcrP]", stripped)))
    spec = re.sub(r"\*\{\d+\}\{.*?\}\}", "", spec)
    spec = re.sub(r">\{[^}]*\}|<\{[^}]*\}", "", spec)
    spec = re.sub(r"[pmb]\{[^}]*\}", "P", spec)
    total += len(re.findall(r"[lcrPX]", spec))
    return total


def declared_width_pt(spec: str, body: str, ncols: int) -> float | None:
    """Total declared width, or None when a column has no fixed width.

    Only p/m/b columns declare a width. With an l, c, r or X column the width
    depends on the content or on the environment, so this returns None and the
    caller must not claim the table fits.
    """
    widths = re.findall(r"[pmb]\{([0-9.]+)(cm|mm|in|pt)\}", spec)
    if len(widths) != ncols:
        return None
    unit_pt = {"cm": 10 * PT_PER_MM, "mm": PT_PER_MM, "in": 72.27, "pt": 1.0}
    total = sum(float(value) * unit_pt[unit] for value, unit in widths)
    sep = re.search(r"\\setlength\{\\tabcolsep\}\{([0-9.]+)pt\}", body)
    tabcolsep = float(sep.group(1)) if sep else 6.0
    return total + 2 * ncols * tabcolsep


def tables(path: Path):
    """Yield every table environment AND every bare tabular in a file.

    A bare tabular inside a center environment is not a float and was invisible
    to the first version of this check. Both tables that collided with body text
    were exactly that: no \begin{table}, so nothing to report a float type for.
    """
    body = re.sub(r"(?m)(?<!\\)%.*$", "", path.read_text(encoding="utf-8"))
    seen_spans = []
    for match in re.finditer(
        r"\\begin\{(table\*?)\}(.*?)\\end\{\1\}", body, flags=re.S
    ):
        seen_spans.append(match.span())
        yield match.group(1), match.group(2), body[: match.start()].count("\n") + 1
    for match in re.finditer(
        r"\\begin\{tabularx?\*?\}(.*?)\\end\{tabularx?\*?\}", body, flags=re.S
    ):
        if any(a <= match.start() < b for a, b in seen_spans):
            continue
        # Include what precedes it back to \begin{center}: a bare tabular's
        # \footnotesize and \setlength{\tabcolsep} sit in the enclosing
        # environment, and yielding only the tabular reported them missing.
        start = body.rfind("\\begin{center}", 0, match.start())
        start = match.start() if start == -1 else start
        yield "bare", body[start : match.end()], body[:start].count("\n") + 1


def report(entry: Path) -> int:
    findings: list[str] = []
    total = 0

    for path in sources(entry):
        for kind, body, line in tables(path):
            total += 1
            # Both sections/limitations.tex and generated/limitations.tex
            # exist; printing the basename alone made them indistinguishable.
            name = f"{path.parent.name}/{path.name}:{line}"
            label = re.search(r"\\label\{([^}]*)\}", body)
            label = label.group(1) if label else "(no label)"

            spec = tabular_spec(body)

            # Measure the tabular only. A caption is ordinary wrapped text and
            # its length says nothing about whether a column overflows; counting
            # it reported a 603-character "cell" in a table of short numbers.
            inner = re.search(
                r"\\begin\{tabularx?\*?\}(?:\{[^}]*\})*(.*?)\\end\{tabularx?\*?\}",
                body,
                flags=re.S,
            )
            longest = 0
            for row in (inner.group(1) if inner else "").split("\\\\"):
                for cell in row.split("&"):
                    cleaned = re.sub(r"\\[a-zA-Z]+\{?|[{}]", "", cell).strip()
                    longest = max(longest, len(cleaned))

            ncols = column_count(spec)
            declared = declared_width_pt(spec, body, ncols)
            available = TEXTWIDTH_PT if kind == "table*" else COLUMN_PT
            fits = declared is not None and declared <= available
            flags = []
            if (
                kind == "bare"
                and not fits
                and (ncols > MAX_SINGLE_COLUMN_COLUMNS or longest > PROSE)
            ):
                flags.append(
                    "NOT IN A FLOAT and too wide for a column (a bare tabular "
                    "cannot move, so it overlaps whatever is beside it)"
                )
            if kind == "bare" and fits:
                # Deliberate: a non-floating table cannot drift into another
                # section, which is why one of ours was un-floated on purpose.
                pass
            elif kind in ("table", "bare") and ncols > MAX_SINGLE_COLUMN_COLUMNS:
                flags.append(
                    f"{ncols} columns in a single-column float "
                    f"(> {MAX_SINGLE_COLUMN_COLUMNS}); use table*"
                )
            if kind == "table" and longest > PROSE:
                flags.append("prose column in a single-column float; use table*")
            if kind == "table" and not flags:
                flags.append("single-column: confirm it is narrow")
            if longest > PROSE and not WRAPPING.search(spec):
                flags.append(
                    f"prose cell of {longest} chars in a non-wrapping spec "
                    f"'{spec}' (use p{{...}})"
                )
            if longest > PROSE and not any(
                sz in body for sz in ("\\small", "\\footnotesize", "\\scriptsize")
            ):
                flags.append("no size reduction")
            if longest > PROSE and "tabcolsep" not in body:
                flags.append("no reduced \\tabcolsep")

            width = (
                f"{declared:.0f}/{available:.0f}pt" if declared is not None else "w=?"
            )
            status = "; ".join(flags) if flags else "ok"
            findings.append(
                f"  {name:40} {kind:6} {label:20} cols={ncols:2} "
                f"longest={longest:4} {width:>10}  {status}"
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
