"""The takeaway boxes are one macro, numbered by a counter, styled in one place.

Three things can drift here and each has already happened somewhere in this
paper, so each is pinned rather than trusted:

1. A box built by hand instead of through the macro. It would look almost right
   and would not follow when the style changes, which is how a "consistent"
   style stops being one.
2. A number written as literal text. The headings read "Takeaway 1:",
   "Takeaway 2:" and "Takeaway 3:" as text until 2026-09-19, so inserting a
   takeaway in the middle would have left the rest renumbering nothing and
   saying nothing about it. This is the same shape as the counts recorded in
   Section~\\ref{sec:disc:unread}: correct when written, wrong after a change,
   with no consumer to notice.
3. A colour written inline at a use site, so two boxes can disagree about what
   the house style is.

NOT CHECKED HERE, AND NOT CHECKABLE WITHOUT A TeX ENGINE: how any of it renders.
These are structural checks on the source. Whether the accent bar sits where it
should, whether the tint is too light to see, and whether a box splits cleanly
across a column break can only be read off a compiled PDF.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
MAIN = PAPER / "main.tex"
TEX_FILES = sorted(p for p in PAPER.rglob("*.tex") if not p.name.endswith(".bak"))


def _strip_comments(text: str) -> str:
    """Drop LaTeX comments, keeping `\\%`."""
    out = []
    for line in text.splitlines():
        i = 0
        while i < len(line):
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == "%":
                line = line[:i]
                break
            i += 1
        out.append(line)
    return "\n".join(out)


def _body(path: Path) -> str:
    return _strip_comments(path.read_text(encoding="utf-8"))


def test_takeaway_is_defined_once_and_through_tcolorbox() -> None:
    main = _body(MAIN)
    assert main.count("\\newcommand{\\takeaway}") == 1, (
        "\\takeaway defined more than once"
    )
    assert "\\newtcolorbox{takeawaybox}" in main
    assert "\\begin{takeawaybox}" in main, "the macro does not use the box it defines"
    assert "\\fbox" not in main.split("\\newcommand{\\takeaway}")[1].split("\n}")[0], (
        "\\takeaway still draws an \\fbox"
    )


def test_tcolorbox_is_loaded_after_acl_with_the_needed_libraries() -> None:
    main = _body(MAIN)
    assert main.index("\\usepackage[preprint]{acl}") < main.index(
        "\\usepackage{tcolorbox}"
    ), "tcolorbox must load after acl.sty"
    libs = re.search(r"\\tcbuselibrary\{([^}]*)\}", main)
    assert libs, "\\tcbuselibrary is missing"
    named = {s.strip() for s in libs.group(1).split(",")}
    # skins gives `enhanced`, without which `borderline west` silently does nothing.
    assert "skins" in named, "without skins the left accent bar is not drawn at all"
    # breakable lets a box at the foot of a column split instead of overflowing.
    assert "breakable" in named
    assert "breakable" in main.split("\\newtcolorbox{takeawaybox}")[1].split("}")[0], (
        "the box is not declared breakable, so one landing at a column break "
        "will overflow rather than split"
    )


def test_xcolor_is_never_loaded_with_options() -> None:
    """An option clash needs two loads with DIFFERENT options; optionless is safe.

    acl.sty loads xcolor, main.tex loads xcolor, and tcolorbox requires it. All
    three must stay optionless or the document stops loading with
    "Option clash for package xcolor".
    """
    for path in (MAIN, PAPER / "acl.sty"):
        for match in re.finditer(
            r"\\(?:usepackage|RequirePackage)(\[[^\]]*\])?\{([^}]*)\}", _body(path)
        ):
            packages = {p.strip() for p in match.group(2).split(",")}
            if "xcolor" in packages:
                assert match.group(1) is None, (
                    f"{path.name}: xcolor loaded with options {match.group(1)}; "
                    "every other load of it in this document is optionless"
                )


def test_no_takeaway_is_hand_built() -> None:
    """A box assembled at a use site would not follow the style when it changes."""
    for tex in TEX_FILES:
        if tex == MAIN:
            continue
        body = _body(tex)
        assert "takeawaybox" not in body, (
            f"{tex.name}: uses the box environment directly; call \\takeaway"
        )
        assert "takeawayaccent" not in body and "takeawaytint" not in body, (
            f"{tex.name}: names a takeaway colour at a use site; the colours are "
            "defined once in main.tex and referenced only by the macro"
        )


def test_numbers_come_from_the_counter_not_from_the_text() -> None:
    """A hand-typed number renumbers nothing when a box is inserted before it."""
    main = _body(MAIN)
    assert "\\newcounter{takeaway}" in main
    assert "\\refstepcounter{takeaway}" in main
    assert "\\thetakeaway" in main

    offenders = []
    for tex in TEX_FILES:
        if tex == MAIN:
            continue
        for match in re.finditer(r"\\takeaway\{(.*?)\}\{", _body(tex), re.DOTALL):
            if re.search(r"Takeaway\s*\d", match.group(1)):
                offenders.append(f"{tex.name}: {' '.join(match.group(1).split())}")
    assert not offenders, "takeaway titles carrying their own number: " + "; ".join(
        offenders
    )


def test_every_takeaway_call_is_well_formed() -> None:
    """Two arguments, a title that is not empty, and no stray numbering."""
    calls = 0
    for tex in TEX_FILES:
        if tex == MAIN:
            continue
        body = _body(tex)
        for match in re.finditer(r"\\takeaway(?=[\{\[])", body):
            calls += 1
            title, rest = _two_args(body, match.end())
            assert title.strip(), f"{tex.name}: empty takeaway title"
            assert rest.strip(), f"{tex.name}: empty takeaway body"
    assert calls >= 3, f"expected at least the three results takeaways, found {calls}"


def _two_args(text: str, i: int) -> tuple[str, str]:
    """Read two brace-matched arguments starting at `i`."""
    args = []
    for _ in range(2):
        while i < len(text) and text[i] in " \n\t":
            i += 1
        assert text[i] == "{", "takeaway call is missing an argument"
        depth, start = 1, i + 1
        i += 1
        while i < len(text) and depth:
            if text[i] == "\\":
                i += 2
                continue
            depth += (text[i] == "{") - (text[i] == "}")
            i += 1
        args.append(text[start : i - 1])
    return args[0], args[1]


def test_colours_are_named_once_and_are_not_saturated() -> None:
    """Defined in one place, and muted, which was the point of restyling them."""
    main = _body(MAIN)
    found = dict(
        re.findall(r"\\definecolor\{(takeaway\w+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}", main)
    )
    assert set(found) == {"takeawayaccent", "takeawaytint"}, found
    for name, hexcode in found.items():
        r, g, b = (int(hexcode[i : i + 2], 16) for i in (0, 2, 4))
        highest, lowest = max(r, g, b), min(r, g, b)
        saturation = 0.0 if highest == 0 else (highest - lowest) / highest
        assert saturation < 0.5, (
            f"{name} (#{hexcode}) has saturation {saturation:.2f}; this is a "
            "clinical-safety paper and a loud box reads as a warning"
        )


def test_no_null_control_sequence_anywhere_in_the_preamble() -> None:
    r"""A `\` at the very end of a line is the NULL control sequence, not `\ `.

    It looks like a thin space in the source and is an "Undefined control
    sequence" at compile time. The first draft of \takeaway above contained one,
    written while fixing a different fatal macro error in the same document.
    """
    offenders = []
    for tex in TEX_FILES:
        for number, line in enumerate(_body(tex).splitlines(), 1):
            stripped = line.rstrip(" \t")
            if not stripped.endswith("\\"):
                continue
            if stripped.endswith("\\\\"):  # a real line break in a tabular
                continue
            offenders.append(f"{tex.name}:{number}")
    assert not offenders, (
        "a backslash ends these lines, which TeX reads as the null control "
        "sequence rather than a space: " + "; ".join(offenders)
    )
