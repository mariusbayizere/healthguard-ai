"""The preamble pairs T1 encoding with a Type 1 font, not with bitmaps.

`\\usepackage[T1]{fontenc}` on its own asks pdflatex for a T1-encoded font and,
with no scalable one loaded, it falls back to the bitmapped EC fonts. Those
embed as **Type 3**: blurry on screen, poor in print, and flagged by arXiv on
submission. The paper shipped that way and rendered visibly softer than the
comparison it was modelled on, which is how it was found -- by eye, on a page
put side by side with another, not by anything in this repository.

That is the trap worth naming. T1 was added deliberately and for a good reason:
`_` in typewriter text was not reliably available as a glyph and the compiled v2
PDF dropped it from every file path it printed. The fix was correct and created
a new defect with no error, no warning and no failing check, visible only to
someone who looked at the output next to a reference.

So this file checks the pair rather than either half. Neither `[T1]{fontenc}`
alone nor a font package alone is the thing that must hold.

NOT CHECKABLE HERE: what fonts the PDF actually embeds. That needs a compile and
`pdffonts`. These are checks on the source.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "paper" / "main.tex"

# Packages that supply scalable Type 1 (or OpenType) text fonts. Any one of
# these keeps pdflatex off the bitmapped EC fallback.
#
# lmodern is here and is the one to reach for if Computer Modern's LOOK is
# wanted: it is Latin Modern, the Type 1 version of the same design, and it
# fixes the embedding without changing the typeface. mathptmx is what this paper
# uses, for Times, which is what the ACL templates set.
TYPE1_PACKAGES = frozenset(
    {
        "mathptmx",
        "times",
        "newtxtext",
        "newtxmath",
        "txfonts",
        "lmodern",
        "newpxtext",
        "newpxmath",
        "pxfonts",
        "libertine",
        "libertinus",
        "kpfonts",
        "fourier",
        "charter",
        "mathpazo",
        "palatino",
    }
)


def _loaded_packages(text: str) -> set[str]:
    """Every package name the preamble requests, options ignored."""
    loaded: set[str] = set()
    for line in text.splitlines():
        line = line.split("%", 1)[0]  # a commented-out load is not a load
        for match in re.finditer(
            r"\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\{([^}]*)\}", line
        ):
            loaded.update(name.strip() for name in match.group(1).split(","))
    return loaded


def test_a_type1_font_package_is_loaded() -> None:
    """Without one, T1 encoding silently falls back to bitmapped EC fonts."""
    loaded = _loaded_packages(MAIN.read_text(encoding="utf-8"))
    found = loaded & TYPE1_PACKAGES
    assert found, (
        "no Type 1 font package in main.tex. With \\usepackage[T1]{fontenc} and "
        "none of "
        f"{sorted(TYPE1_PACKAGES)}, pdflatex falls back to the bitmapped EC "
        "fonts, which embed as Type 3 and are flagged by arXiv. Nothing in the "
        "compile says so; the only symptom is that the PDF looks soft."
    )


def test_t1_encoding_is_still_requested() -> None:
    """The reason T1 was added has not gone away: \\path needs the underscore."""
    body = MAIN.read_text(encoding="utf-8")
    assert re.search(r"\\usepackage\[T1\]\{fontenc\}", body), (
        "[T1]{fontenc} is gone; file paths printed in typewriter text will lose "
        "their underscores again, as they did in the compiled v2 PDF"
    )


def test_the_check_would_fail_on_the_preamble_that_shipped_type3() -> None:
    """A check that cannot fail is the failure this project keeps recording."""
    shipped = "\n".join(
        [
            r"\usepackage[preprint]{acl}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{url}",
            r"\usepackage{booktabs}",
        ]
    )
    assert not (_loaded_packages(shipped) & TYPE1_PACKAGES)

    fixed = shipped + "\n" + r"\usepackage{mathptmx}"
    assert _loaded_packages(fixed) & TYPE1_PACKAGES == {"mathptmx"}

    # A commented-out load must not count as one.
    commented = shipped + "\n" + r"% \usepackage{mathptmx}"
    assert not (_loaded_packages(commented) & TYPE1_PACKAGES)
