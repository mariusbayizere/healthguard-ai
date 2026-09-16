"""The plain-text render must contain everything the LaTeX build contains.

WHY THIS FILE EXISTS. Twice the reading copy was silently short of the paper:

  1. sections/appendix.tex was never in render_plain.py's file list, so every
     render since the appendices were written was main text only;
  2. \\input targets were not expanded, so two whole subsections that the PDF
     carries (the gate derivation and the gate-degeneracy finding, both
     generated) were absent from the render.

Both were invisible: the render succeeded, looked complete, and was read as if
it were the paper. The failure mode is the one the paper itself is about, so it
gets a test rather than a fix and a promise.

The test compares the two builds structurally: the set of source files reached,
and the ordered sequence of headings. It does not compare prose, because the
renderer deliberately flattens tables and expands macros.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

PAPER = Path(__file__).resolve().parents[1] / "paper"
sys.path.insert(0, str(PAPER))

render_plain = pytest.importorskip("render_plain")


def read(name: str) -> str:
    path = PAPER / (name if name.endswith(".tex") else name + ".tex")
    return path.read_text(encoding="utf-8") if path.exists() else ""


def reached(entry: str, seen: set[str] | None = None) -> set[str]:
    """Every .tex file reachable from `entry` by \\input, transitively."""
    seen = set() if seen is None else seen
    body = re.sub(r"(?m)^\s*%.*$", "", read(entry))
    for target in re.findall(r"\\input\{([^}]*)\}", body):
        name = target if target.endswith(".tex") else target + ".tex"
        if name not in seen:
            seen.add(name)
            reached(target, seen)
    return seen


def headings(text: str) -> list[str]:
    """Ordered (section|subsection) titles, whitespace collapsed."""
    text = re.sub(r"(?m)^\s*%.*$", "", text)
    # A heading suppressed by \renewcommand inside a group is not typeset.
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
    return [
        " ".join(title.split()).upper()
        for _, title in re.findall(
            r"\\(section|subsection)\*?\{(.*?)\}", text, flags=re.S
        )
    ]


# The one file the renderer legitimately does not render as prose. It holds
# \newcommand definitions only; render_plain.macros() reads it and expands each
# macro at its use site, which is why no heading or sentence of it should appear.
# Anything else missing is a defect, not an exception.
DEFINITIONS_ONLY = {"generated/results_macros.tex"}


def latex_sources() -> list[str]:
    """The files the LaTeX build compiles, in main.tex's own order."""
    body = re.sub(r"(?m)^\s*%.*$", "", read("main.tex"))
    return [
        t if t.endswith(".tex") else t + ".tex"
        for t in re.findall(r"\\input\{([^}]*)\}", body)
    ]


def test_renderer_lists_every_file_main_tex_inputs() -> None:
    """Every top-level \\input of main.tex is in the renderer's ORDER."""
    listed = set(render_plain.ORDER) | DEFINITIONS_ONLY
    missing = [name for name in latex_sources() if name not in listed]
    assert not missing, (
        "render_plain.ORDER omits files the LaTeX build compiles, so the "
        f"reading copy is short of the paper: {missing}"
    )


def test_renderer_reaches_every_transitively_input_file() -> None:
    """Files reached only through a section's own \\input are rendered too."""
    from_latex = reached("main.tex")
    from_render: set[str] = set()
    for name in render_plain.ORDER:
        from_render.add(name)
        from_render |= reached(name)

    missing = sorted(from_latex - from_render - DEFINITIONS_ONLY)
    assert not missing, (
        f"the LaTeX build reaches these files but the renderer does not: {missing}"
    )


def test_heading_sequence_matches_the_latex_build() -> None:
    """Both builds present the same headings, in the same order."""
    latex: list[str] = []
    for name in latex_sources():
        latex += headings(render_plain.expand(read(name)))

    rendered = [
        line[3:].strip()
        for line in (PAPER / "generated" / "full_text.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.startswith("## ")
    ]

    assert rendered == latex, (
        "the rendered headings differ from the typeset ones.\n"
        f"only in LaTeX:    {[h for h in latex if h not in rendered]}\n"
        f"only in render:   {[h for h in rendered if h not in latex]}"
    )


def test_no_unresolved_cross_reference_in_the_render() -> None:
    """A \\ref the renderer cannot resolve prints ??, as LaTeX would."""
    text = (PAPER / "generated" / "full_text.txt").read_text(encoding="utf-8")
    assert "??" not in text, "the render contains an unresolved cross-reference"


def test_full_text_is_current() -> None:
    """The committed render matches what the renderer produces today."""
    macro = render_plain.macros()
    number = render_plain.numbering()
    parts = []
    for name in render_plain.ORDER:
        path = PAPER / name
        if path.exists():
            parts.append(render_plain.strip(path.read_text(), macro, number).strip())
    fresh = "\n\n".join(parts) + "\n"
    committed = (PAPER / "generated" / "full_text.txt").read_text(encoding="utf-8")
    assert fresh.split() == committed.split(), (
        "paper/generated/full_text.txt is stale; re-run "
        "`python paper/render_plain.py > paper/generated/full_text.txt`"
    )


def test_no_em_dash_reaches_the_pdf() -> None:
    """No file the LaTeX build compiles prints an em dash.

    Both spellings count: the character itself, and LaTeX's "---" ligature.
    Comments are excluded because they are not typeset. The emitter that writes
    the generated files was changed to stop producing either; this asserts the
    result rather than trusting it.
    """
    offenders: list[str] = []
    for name in ["main.tex", *sorted(reached("main.tex"))]:
        body = re.sub(r"(?m)(?<!\\)%.*$", "", read(name))
        hits = len(re.findall(r"(?<!-)---(?!-)", body)) + body.count("—")
        if hits:
            offenders.append(f"{name} ({hits})")
    assert not offenders, f"em dashes would be typeset in: {offenders}"
