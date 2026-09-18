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
DEFINITIONS_ONLY = {
    "generated/results_macros.tex",
    # Corpus counts, emitted from the authoring record by
    # review/emit_corpus_counts.py. Plain values only -- the prose that
    # uses them is in sections/appendix.tex, so there is nothing here for
    # the reading copy to be short of.
    "generated/corpus_counts.tex",
    # Seed-curve annotations, emitted with the figure's data file by
    # review/emit_seed_curve.py. Values only; the figure and its caption
    # are in sections/seed_figure.tex.
    "generated/seed_curve_macros.tex",
}


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


def typeset_body(name: str) -> str:
    """The part of a file that reaches the page.

    Comments go, then math, then the arguments of the macros that take a label,
    a key or a verbatim path rather than prose. What is left is what a reader
    sees, which is the only place an underscore rule can be enforced.
    """
    body = re.sub(r"(?m)(?<!\\)%.*$", "", read(name))
    # \makeatletter ... \makeatother holds macro definitions, not prose. The
    # \RequireGenerated error message names the emitter and its output file;
    # that text goes to the build log, never to the page.
    body = re.sub(r"(?s)\\makeatletter.*?\\makeatother", " ", body)
    # A tikzpicture holds drawing instructions and file references, not prose.
    # \addplot table {generated/seed_curve.dat} names a data file, and that
    # underscore is an argument rather than a character to set. This rule is
    # about glyphs that vanish silently; a bare underscore inside a picture is
    # a hard LaTeX error, which the compile catches loudly on its own.
    body = re.sub(r"(?s)\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", " ", body)
    body = re.sub(r"\$[^$]*\$", " ", body)
    body = re.sub(r"(?s)\\\[.*?\\\]", " ", body)
    for macro in (
        "input",
        "label",
        "ref",
        "cite",
        "citep",
        "path",
        "url",
        "bibliography",
        "bibliographystyle",
        "RequireGenerated",
        "usepackage",
        "documentclass",
        "hypersetup",
        "newcommand",
        "renewcommand",
        "GenericError",
    ):
        body = re.sub(rf"\\{macro}\b(\[[^\]]*\])?(\{{[^{{}}]*\}})?", " ", body)
    return body


# Extensions that make a token a file path rather than a word.
PATH_SUFFIXES = ("py", "md", "tex", "json", "csv", "pdf", "txt", "yml", "yaml")


def test_no_bare_underscore_is_typeset() -> None:
    """A bare `_` outside math stops the build, or prints as a subscript.

    Every underscore that reaches the page must be inside \\path{...}, which
    takes its argument verbatim. This is the cheap half of the rule; the
    expensive half is that a path written any other way loses the character
    silently, which is what the next test is for.
    """
    offenders: list[str] = []
    for name in ["main.tex", *sorted(reached("main.tex"))]:
        for line_no, line in enumerate(typeset_body(name).splitlines(), 1):
            if re.search(r"(?<!\\)_", line):
                offenders.append(f"{name}:{line_no}: {line.strip()[:90]}")
    assert not offenders, "a bare underscore would be typeset:\n" + "\n".join(offenders)


def test_every_file_path_is_written_with_path() -> None:
    """File paths go in \\path{...}, never \\texttt{...} with escaped underscores.

    WHY THIS FILE'S RULE IS \\path AND NOT \\texttt. The compiled v2 PDF printed
    `eval_spec.py` as `evalspec.py`, and the same for nine other scripts: the
    sources escaped the underscore correctly as `\\_`, but the document had no
    T1 font encoding, so the glyph was not reliably there to set. A paper whose
    argument is that a reader must be able to re-run the code was naming the
    code under names that do not exist.

    fontenc is now loaded, which fixes the glyph. This test fixes the class:
    \\path takes its argument verbatim, so a path is written exactly as it
    appears on disk and there is no escape to forget or lose.
    """
    suffixes = "|".join(PATH_SUFFIXES)
    looks_like_a_path = re.compile(rf"[\w/\\.-]+\\?_[\w/\\.-]*\.({suffixes})\b")
    offenders: list[str] = []
    for name in ["main.tex", *sorted(reached("main.tex"))]:
        # typeset_body already drops comments, math, definitions and the
        # macros whose arguments are keys rather than prose, \path among them.
        body = typeset_body(name)
        for match in looks_like_a_path.finditer(body):
            offenders.append(f"{name}: {match.group(0)}")
    assert not offenders, (
        "file paths with an underscore must be written \\path{...} so the "
        "character cannot be lost: " + "; ".join(offenders)
    )


def test_fontenc_is_loaded_before_the_document_body() -> None:
    """T1 is what makes the underscore glyph available at all.

    Without it the two tests above can pass on sources that still print the
    wrong thing, because the defect is in the encoding rather than the markup.
    """
    main = re.sub(r"(?m)(?<!\\)%.*$", "", read("main.tex"))
    assert "\\usepackage[T1]{fontenc}" in main, (
        "T1 font encoding is not loaded; underscores in typewriter text are "
        "not reliably available under the default OT1 encoding"
    )
    assert "\\usepackage{url}" in main, (
        "the url package is not loaded, so \\path is undefined"
    )
    assert main.index("\\usepackage[T1]{fontenc}") < main.index("\\begin{document}")


def test_arxiv_abstract_fits_the_submission_field() -> None:
    """The abstract must fit arXiv's 1,920-character field, and match the paper.

    arXiv truncates a longer abstract silently. The compiled v2 abstract was
    2,768 characters, so the submitted version would have lost its last third,
    including the sentence saying that no figure in the paper is evidence of
    model quality. That is the one sentence least safe to lose.

    reports/ARXIV_ABSTRACT.txt is emitted from sections/abstract.tex rather than
    written beside it, so the two cannot disagree.
    """
    sys.path.insert(0, str(PAPER))
    emit = pytest.importorskip("emit_arxiv_abstract")

    rendered = emit.render()
    length = len(rendered.rstrip("\n"))
    assert length <= emit.ARXIV_LIMIT, (
        f"the abstract is {length:,} characters; arXiv accepts "
        f"{emit.ARXIV_LIMIT:,} and truncates the rest without warning"
    )

    committed = emit.OUT
    assert committed.exists(), (
        "reports/ARXIV_ABSTRACT.txt is missing; run paper/emit_arxiv_abstract.py"
    )
    assert committed.read_text(encoding="utf-8") == rendered, (
        "reports/ARXIV_ABSTRACT.txt is stale; re-run paper/emit_arxiv_abstract.py"
    )


def test_no_link_border_is_drawn_and_acl_owns_hyperref() -> None:
    """No link border is drawn, and the document does not fight acl.sty over it.

    THIS TEST CHANGED WHEN THE PAPER MOVED TO THE ACL TEMPLATE. It used to
    require \\hypersetup{hidelinks} and forbid `colorlinks` anywhere. Under
    acl.sty neither holds: the style loads hyperref itself and sets
    `colorlinks=true` with dark blue link, cite and url colours, which is the
    ACL house style and also removes the border, since a coloured-text link has
    no frame. Keeping the old assertion would have meant either deleting the
    guard or overriding the template, so it is restated against what actually
    threatens the output now.

    What still must not happen is a second, conflicting hyperref setup in our
    own sources, or an option that puts a frame back.
    """
    files = ["main.tex", *sorted(reached("main.tex"))]
    body = "\n".join(re.sub(r"(?m)(?<!\\)%.*$", "", read(n)) for n in files)
    main = re.sub(r"(?m)(?<!\\)%.*$", "", read("main.tex"))

    assert "\\usepackage[preprint]{acl}" in main, "the ACL style is not loaded"

    # acl.sty \RequirePackage-s these three. Loading any of them again with our
    # own options is an option clash, and geometry silently takes the last call.
    for package in ("geometry", "natbib", "hyperref"):
        assert not re.search(rf"\\usepackage(\[[^\]]*\])?\{{{package}\}}", main), (
            f"{package} is loaded in main.tex, but acl.sty loads it already; "
            "the second load clashes or silently overrides the template"
        )

    for option in ("linkbordercolor", "citebordercolor", "urlbordercolor", "pdfborder"):
        assert option not in body, f"{option} would draw a border around links"

    ours = re.findall(r"\\hypersetup\{([^}]*)\}", body)
    assert not ours, f"main.tex sets hyperref options that acl.sty already owns: {ours}"


def test_acl_style_files_are_vendored() -> None:
    """acl.sty and acl_natbib.bst are in the repository, not assumed present.

    A style file taken from whatever TeX Live the compiling machine carries can
    differ between machines, and this one decides the page count, which is a
    submission constraint. They are committed beside the paper and travel in the
    Overleaf archive.
    """
    for name, floor in (("acl.sty", 8_000), ("acl_natbib.bst", 20_000)):
        path = PAPER / name
        assert path.exists(), f"{name} is not vendored in paper/"
        assert path.stat().st_size > floor, (
            f"{name} is {path.stat().st_size} bytes, which is too small to be "
            "the real file; the download probably returned an error page"
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
