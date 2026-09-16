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


ORDER = [
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
    # The appendices were absent from this list until 2026-09-16, so every
    # rendered plain text before that date was main text only and silently
    # short of the appendix material the pointers refer to.
    "sections/appendix.tex",
]


def _read(name: str) -> str:
    path = HERE / (name if name.endswith(".tex") else name + ".tex")
    return path.read_text() if path.exists() else ""


def numbering() -> dict[str, str]:
    """Map every \\label to the number LaTeX would print for it.

    Without this a \\ref rendered as its own label ("Appendix app:leakage"),
    which is the same class of defect as LaTeX printing "??": the reader is
    shown the internal name instead of the pointer.
    """
    out: dict[str, str] = {}
    section = 0
    sub = 0
    current = ""
    for name in ORDER:
        path = HERE / name
        if not path.exists():
            continue
        appendix = name.endswith("appendix.tex")
        body = re.sub(r"(?m)^\s*%.*$", "", path.read_text())
        # \input-ed files carry labels too (the generated tables do), and a
        # \ref to one of them renders "??" if they are not scanned here.
        body = re.sub(
            r"\\input\{([^}]*)\}",
            lambda m: _read(m.group(1)),
            body,
        )
        for kind, arg in re.findall(
            r"\\(section|subsection|label)\*?\{(.*?)\}", body, re.S
        ):
            if kind == "section":
                section = section + 1 if not appendix else section
                if appendix:
                    sub = 0
                    current = chr(ord("A") + out.setdefault("__app__", 0))
                    out["__app__"] += 1
                else:
                    sub = 0
                    current = str(section)
            elif kind == "subsection":
                sub += 1
                current = f"{current.split('.')[0]}.{sub}"
            else:
                out[arg.strip()] = current
    out.pop("__app__", None)
    return out


def _tabular(body: str) -> str:
    rows = []
    for raw in re.split(r"\\\\", body):
        raw = re.sub(r"\\(toprule|midrule|bottomrule)\b", "", raw)
        cells = [" ".join(c.split()) for c in raw.split("&")]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n\n" + "\n".join(rows) + "\n\n"


def expand(text: str, depth: int = 0) -> str:
    """Splice in every \\input target, as the LaTeX build does.

    Without this the render silently omits whatever a section \\inputs. Three
    generated files carry prose and two of them are whole subsections, so the
    reading copy was short of them while the typeset paper was not: the same
    defect as sections/appendix.tex missing from the file list, one level down.
    """
    if depth > 8:
        return text
    return re.sub(
        r"\\input\{([^}]*)\}",
        lambda m: expand(_read(m.group(1)), depth + 1),
        text,
    )


def strip(
    text: str, macro: dict[str, str], number: dict[str, str] | None = None
) -> str:
    text = expand(text)
    text = re.sub(r"(?m)^\s*%.*$", "", text)
    # \begingroup ... \renewcommand{\subsection}[1]{} ... \endgroup suppresses
    # the heading of an \input-ed block in the typeset paper. Honouring it here
    # keeps the two builds saying the same thing; ignoring it printed a second
    # "Limitations" heading that the PDF does not have.
    text = re.sub(
        r"\\begingroup(.*?)\\endgroup",
        lambda m: (
            re.sub(r"\\subsection\*?\{.*?\}", "", m.group(1), flags=re.S)
            if re.search(r"\\renewcommand\{\\subsection\}", m.group(1))
            else m.group(1)
        ),
        text,
        flags=re.S,
    )
    # \renewcommand / \newcommand lines are typesetting plumbing, not prose
    text = re.sub(r"(?m)^\s*\\(re)?newcommand.*$", "", text)
    for name, value in macro.items():
        text = re.sub(rf"\\{name}\b\\?", value, text)
    text = re.sub(
        r"\\(section|subsection)\*?\{(.*?)\}",
        lambda m: f"\n\n## {' '.join(m.group(2).split()).upper()}\n",
        text,
        flags=re.S,
    )
    text = re.sub(
        r"\\paragraph\{((?:[^{}]|\{[^{}]*\})*)\}",
        lambda m: f"\n\n{m.group(1)}",
        text,
    )
    number = number or {}
    text = re.sub(
        r"\\ref\{([^}]*)\}", lambda m: number.get(m.group(1).strip(), "??"), text
    )
    text = re.sub(r"\\label\{[^}]*\}", "", text)
    text = re.sub(r"\\(textbf|emph|texttt|input|cite\w*)\{([^}]*)\}", r"\2", text)
    # A tabular is flattened to one line per row. Doing it here, rather than by
    # deleting \\begin/\\end and hoping, keeps two things right that the naive
    # version got wrong: the column specification ({lp{0.62\\textwidth}}) is
    # dropped instead of surfacing as "lp0.62", and a cell wrapped across source
    # lines stays in its row instead of being orphaned into the prose after the
    # table.
    text = re.sub(
        r"\\begin\{tabular\}\s*(\{(?:[^{}]|\{[^{}]*\})*\})?(.*?)\\end\{tabular\}",
        lambda m: _tabular(m.group(2)),
        text,
        flags=re.S,
    )
    text = re.sub(r"\\begin\{(itemize|center|table|abstract)\}(\[[^]]*\])?", "", text)
    text = re.sub(r"\\end\{(itemize|center|table|abstract)\}", "", text)
    text = text.replace(r"\item", "  -").replace(r"\\", "").replace("&", " | ")
    text = re.sub(
        r"\\(toprule|midrule|bottomrule|small|centering|newpage|noindent|par)\b",
        "",
        text,
    )
    for tex, plain in (
        (r"\rightarrow", "\u2192"),
        (r"\leftarrow", "\u2190"),
        (r"\,", "\u2009"),
        (r"\ldots", "\u2026"),
        (r"\times", "\u00d7"),
        (r"\leq", "\u2264"),
        (r"\geq", "\u2265"),
    ):
        text = text.replace(tex, plain)
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "").replace("~", " ").replace("---", "—")
    text = text.replace(r"\%", "%").replace("\\_", "_").replace("$", "")
    return re.sub(r"\n{3,}", "\n\n", text)


def main() -> int:
    macro = macros()
    number = numbering()
    for name in ORDER:
        path = HERE / name
        if not path.exists():
            continue
        print(strip(path.read_text(), macro, number).strip())
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
