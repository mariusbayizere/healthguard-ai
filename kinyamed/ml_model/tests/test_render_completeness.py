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


def test_hyperref_draws_no_visible_border() -> None:
    """hidelinks is set after hyperref loads, and nothing re-enables borders.

    This is a source-level assertion, not a check of a rendered PDF. It cannot
    see the PDF; it can see that the only setting in the build is the one that
    removes the border, and that no later \\hypersetup or package option puts a
    coloured frame back.
    """
    files = ["main.tex", *sorted(reached("main.tex"))]
    body = "\n".join(re.sub(r"(?m)(?<!\\)%.*$", "", read(n)) for n in files)

    main = re.sub(r"(?m)(?<!\\)%.*$", "", read("main.tex"))
    load = main.find("\\usepackage{hyperref}")
    hide = main.find("\\hypersetup{hidelinks}")
    assert load != -1, "hyperref is not loaded"
    assert hide != -1, "\\hypersetup{hidelinks} is missing"
    assert hide > load, "hidelinks is set before hyperref loads, so it is ignored"

    for option in (
        "colorlinks",
        "linkbordercolor",
        "citebordercolor",
        "urlbordercolor",
        "pdfborder",
    ):
        assert option not in body, (
            f"{option} would override hidelinks and draw or colour a link border"
        )

    extra = re.findall(r"\\hypersetup\{([^}]*)\}", body)
    assert extra == ["hidelinks"], (
        f"more than one \\hypersetup in the build; borders may return: {extra}"
    )


def test_title_is_bold_and_subtitle_is_not() -> None:
    """The title line is bold, the subtitle stays \\large and unbolded."""
    main = re.sub(r"(?m)(?<!\\)%.*$", "", read("main.tex"))
    title = re.search(r"\\title\{(.*?)\n\\author", main, flags=re.S)
    assert title, "no \\title block found"
    first, _, rest = title.group(1).partition("\\\\")
    assert "\\textbf{" in first, "the title line is not bold"
    assert "\\large" in rest, "the subtitle is not set at \\large"
    subtitle = rest.split("\\thanks")[0]
    assert "\\textbf" not in subtitle, "the subtitle is bold; it should not be"


def test_title_page_carries_the_repository() -> None:
    """A reader is told where the code is.

    The footnote's claim is that every number re-derives from a clean clone with
    `make reproduce`. That held only on a branch until 2026-09-17, when the work
    was fast-forwarded onto main and the branch name was dropped from the
    footnote. Verified by cloning main into /tmp under `env -i` and running all
    eight steps; this test guards the URL, not the clone.
    """
    main = re.sub(r"(?m)(?<!\\)%.*$", "", read("main.tex"))
    assert "\\url{https://github.com/mariusbayizere/healthguard-ai}" in main, (
        "the title page does not carry the repository URL"
    )
    assert "audit-p0-p1-and-frontend" not in main, (
        "the footnote still names a branch; main carries the work now"
    )


def _macros() -> dict[str, str]:
    text = read("generated/results_macros")
    return dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", text))


def test_every_require_generated_names_a_macro_the_paper_prints() -> None:
    """A \\RequireGenerated for a figure nothing prints guards nothing.

    The list held 21 entries, 20 of which named macros no part of the document
    used. They read as provenance and provided none. This keeps the list honest:
    assert a macro only where the prose depends on it.
    """
    main = re.sub(r"(?m)(?<!\\)%.*$", "", read("main.tex"))
    required = re.findall(r"\\RequireGenerated\{(\w+)\}", main)
    assert required, "no macro is asserted at all"

    prose = re.sub(r"\\RequireGenerated\{\w+\}", "", main)
    for name in [
        "results.tex",
        *sorted(str(p) for p in (PAPER / "sections").glob("*.tex")),
    ]:
        prose += re.sub(r"(?m)(?<!\\)%.*$", "", read(name))
    for path in sorted((PAPER / "generated").glob("*.tex")):
        if path.name != "results_macros.tex":
            prose += re.sub(r"(?m)(?<!\\)%.*$", "", path.read_text())

    unused = [n for n in required if not re.search(rf"\\{n}\b", prose)]
    assert not unused, (
        "asserted by \\RequireGenerated but never printed, so the guard cannot "
        f"fail in any way that matters: {unused}"
    )


def test_counts_stated_in_prose_match_the_emitter() -> None:
    """results.tex states four structural counts that the emitter also computes.

    Those four are the only figures written in two places, so they are the only
    ones where regenerating could leave the text disagreeing with the tables
    beside it. Everything else reaches the paper solely as emitted text.
    """
    macros = _macros()
    prose = re.sub(r"(?m)(?<!\\)%.*$", "", read("results.tex"))
    duplicated = [
        "ResultEvalRows",
        "ResultEvalPhrases",
        "ResultEvalGroups",
        "ResultCriticalSentences",
    ]
    missing = []
    for name in duplicated:
        value = macros.get(name)
        if value is None:
            missing.append(f"{name}: emitter no longer defines it")
            continue
        if not (value in prose or value.replace(",", "{,}") in prose):
            missing.append(
                f"{name}: emitter says {value}, results.tex does not state it"
            )
    assert not missing, (
        "the prose disagrees with the emitter on a count it repeats: "
        + "; ".join(missing)
    )
