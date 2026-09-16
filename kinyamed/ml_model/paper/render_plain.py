#!/usr/bin/env python
"""Render the paper to plain text for reading, expanding generated macros.

    python paper/render_plain.py > paper/generated/full_text.txt

Not a typesetter. It exists so the paper can be read end to end on a machine with
no LaTeX toolchain, and so that what is read is what the sources say: every
\newcommand from generated/ is expanded to its value rather than shown as a name.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def macros() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in (HERE / "generated").glob("*.tex"):
        for name, value in re.findall(
            r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", path.read_text()
        ):
            out[name] = value
    return out


def strip(text: str, macro: dict[str, str]) -> str:
    text = re.sub(r"(?m)^\s*%.*$", "", text)
    # \renewcommand / \newcommand lines are typesetting plumbing, not prose
    text = re.sub(r"(?m)^\s*\\(re)?newcommand.*$", "", text)
    for name, value in macro.items():
        text = re.sub(rf"\\{name}\b\\?", value, text)
    text = re.sub(
        r"\\(section|subsection)\*?\{([^}]*)\}",
        lambda m: f"\n\n## {m.group(2).upper()}\n",
        text,
    )
    text = re.sub(r"\\paragraph\{([^}]*)\}", lambda m: f"\n\n{m.group(1)}", text)
    text = re.sub(
        r"\\(textbf|emph|texttt|ref|label|input|cite\w*)\{([^}]*)\}", r"\2", text
    )
    text = re.sub(
        r"\\begin\{(itemize|center|tabular|table|abstract)\}(\[[^]]*\])?", "", text
    )
    text = re.sub(r"\\end\{(itemize|center|tabular|table|abstract)\}", "", text)
    text = text.replace(r"\item", "  -").replace(r"\\", "").replace("&", " | ")
    text = re.sub(
        r"\\(toprule|midrule|bottomrule|small|centering|newpage|noindent|par)\b",
        "",
        text,
    )
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "").replace("~", " ").replace("---", "—")
    text = text.replace(r"\%", "%").replace("\\_", "_").replace("$", "")
    return re.sub(r"\n{3,}", "\n\n", text)


def main() -> int:
    macro = macros()
    order = [
        "sections/abstract.tex",
        "sections/introduction.tex",
        "sections/related_work.tex",
        "sections/method.tex",
        "results.tex",
        "sections/system.tex",
        "sections/discussion.tex",
        "sections/limitations.tex",
        "sections/future_work.tex",
        "sections/conclusion.tex",
    ]
    for name in order:
        path = HERE / name
        if not path.exists():
            continue
        print(strip(path.read_text(), macro).strip())
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
