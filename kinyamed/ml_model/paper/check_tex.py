#!/usr/bin/env python
"""Structural checks on the paper sources, for a machine with no TeX engine.

THIS IS NOT A COMPILER AND DOES NOT CLAIM TO BE. It cannot tell you that a
table overflows the column, that a float lands badly, or that a package is
missing. It catches the class of error that would stop a build outright and
the class that silently prints the wrong thing:

  1. an \\input target that does not exist
  2. a macro used in prose that nothing defines  -> LaTeX prints "Undefined
     control sequence" and stops
  3. a \\ref with no matching \\label            -> LaTeX silently prints "??"
  4. unbalanced \\begin/\\end environments
  5. a number typed literally into prose instead of coming from a macro,
     which is the failure the generated-file machinery exists to prevent

Run it before committing paper changes, and run a real build when a TeX engine
is available.

    python paper/check_tex.py paper/main.tex
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Numbers that are structure or configuration rather than measurements, so
# finding them written out in prose is not a provenance failure.
ALLOWED_LITERALS = {
    "1", "2", "3", "4", "5", "11",           # counts, list items, font size
    "0.95", "2", "3",                        # thresholds named in the gate prose
    "1.5", "10",                             # sweep ratios and exponents
}


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def resolve(root: Path, name: str) -> Path:
    path = root / name
    return path if path.suffix else path.with_suffix(".tex")


def collect(entry: Path) -> tuple[dict[Path, str], list[str]]:
    """Follow \\input from the entry point. Returns (sources, problems)."""
    sources: dict[Path, str] = {}
    problems: list[str] = []
    pending = [entry]
    while pending:
        path = pending.pop()
        if path in sources:
            continue
        if not path.exists():
            problems.append(f"missing file: {path}")
            continue
        body = strip_comments(path.read_text(encoding="utf-8"))
        sources[path] = body
        for name in re.findall(r"\\input\{([^}]+)\}", body):
            target = resolve(entry.parent, name)
            if not target.exists():
                problems.append(f"{path.name}: \\input{{{name}}} -> {target} does not exist")
            else:
                pending.append(target)
    return sources, problems


def main() -> int:
    entry = Path(sys.argv[1] if len(sys.argv) > 1 else "paper/main.tex")
    sources, problems = collect(entry)
    if not sources:
        raise SystemExit(f"nothing to check from {entry}")
    blob = "\n".join(sources.values())

    defined = set(re.findall(r"\\newcommand\{\\(\w+)\}", blob))
    # Only project macros are checked; LaTeX's own control sequences are not
    # ours to verify and a whitelist of them would rot.
    used = set(re.findall(r"\\(Result\w+|Degenerate\w+)", blob))
    for name in sorted(used - defined):
        problems.append(f"macro \\{name} is used but never defined")

    labels = set(re.findall(r"\\label\{([^}]+)\}", blob))
    for name in sorted(set(re.findall(r"\\ref\{([^}]+)\}", blob)) - labels):
        problems.append(f"\\ref{{{name}}} has no \\label — LaTeX will print '??'")

    for path, body in sources.items():
        opened = re.findall(r"\\begin\{(\w+\*?)\}", body)
        closed = re.findall(r"\\end\{(\w+\*?)\}", body)
        for env in set(opened) | set(closed):
            if opened.count(env) != closed.count(env):
                problems.append(f"{path.name}: {env} opened {opened.count(env)}x, "
                                f"closed {closed.count(env)}x")
        if body.count("{") != body.count("}"):
            problems.append(f"{path.name}: {body.count('{')} '{{' vs "
                            f"{body.count('}')} '}}'")

    # Literal numbers in hand-written prose. Generated files are exempt: their
    # numbers are computed, which is the whole point of generating them.
    for path, body in sources.items():
        if "generated" in str(path):
            continue
        prose = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})?", " ", body)
        for literal in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", prose):
            if literal not in ALLOWED_LITERALS:
                problems.append(
                    f"{path.name}: literal number {literal!r} typed in prose — "
                    "it should be a macro from results_macros.tex")

    print(f"checked {len(sources)} file(s) from {entry}")
    for path in sorted(sources, key=str):
        print(f"  {path.relative_to(entry.parent.parent)}")
    print(f"  {len(defined)} macros defined, {len(used)} used, {len(labels)} labels")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  ! {problem}")
        return 1
    print("\nno structural problems. THIS IS NOT A COMPILE — run a TeX engine "
          "when one is available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
