"""Checks for the three defects that stopped the paper compiling on 2026-09-19.

None of these is about what a number is. Each is about a value and the text or
the document around it disagreeing, which is the failure this project keeps
producing and keeps catching by accident.

1. `\\path` inside a `\\caption`. `\\path` is fragile and a caption is a moving
   argument, so it expands to "! Undefined control sequence. \\Url Error ->\\url
   used in a moving argument" and NO PDF IS PRODUCED. One instance in a
   generated caption killed the build; a second, in sections/seed_figure.tex,
   was waiting behind it and would have killed the next run.

2. A module-level constant assigned twice. `PLACEHOLDER` was defined as the
   gloss placeholder and then, sixty lines later, redefined as the generator's
   relation placeholder. Python took the second. The gloss test silently became
   startswith("{REL}"), which no gloss satisfies, so every gloss counted as real
   and the caption reported 15 of 15 where the truth is 2 of 15. Nothing failed;
   the emitter ran and wrote a confident wrong number.

3. A label defined twice. The generated limitations block emitted
   \\label{sec:limitations}, which sections/limitations.tex already puts on its
   \\section. LaTeX keeps the last one, so every \\ref pointed into the middle of
   the section rather than at it.
"""

from __future__ import annotations

import ast
import collections
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
TEX_FILES = sorted(p for p in PAPER.rglob("*.tex") if not p.name.endswith(".bak"))


def _strip_comments(text: str) -> str:
    """Drop LaTeX comments, keeping `\\%`.

    Added after the first version of this file counted a `\\label{...}` written
    inside a `%` comment as a real definition, which is the same class of error
    the file exists to catch: reading text that the consumer never reads. A
    checker blind to the difference between code and a comment about code
    reports on a document nobody compiles.
    """
    out = []
    for line in text.splitlines():
        i = 0
        while i < len(line):
            if line[i] == "\\":  # \% is a literal percent, not a comment
                i += 2
                continue
            if line[i] == "%":
                line = line[:i]
                break
            i += 1
        out.append(line)
    return "\n".join(out)


def _caption_bodies(raw: str) -> list[tuple[str, bool]]:
    """Every caption body, with whether that `\\caption` has a short `[...]` form.

    Brace-matched rather than regex-terminated, because a caption containing a
    `\\textbf{}` ends at the first `}` under any cheaper rule.
    """
    text = _strip_comments(raw)
    bodies = []
    # `%` may separate \caption[...] from its body, so allow whitespace between.
    for match in re.finditer(r"\\caption(\[[^\]]*\])?\s*\{", text):
        has_short = match.group(1) is not None
        depth, i = 1, match.end()
        while i < len(text) and depth:
            if text[i] == "\\":  # skip an escaped brace
                i += 2
                continue
            depth += (text[i] == "{") - (text[i] == "}")
            i += 1
        bodies.append((text[match.end() : i - 1], has_short))
    return bodies


@pytest.mark.parametrize("tex", TEX_FILES, ids=lambda p: p.name)
def test_fragile_path_in_caption_has_a_short_caption(tex: Path) -> None:
    """\\path is fragile; a caption moves only if it has no short `[...]` form.

    Two real constraints meet here and only one arrangement satisfies both.
    A path may not be set as `\\texttt{a\\_b}`: the compiled v2 PDF dropped the
    escaped underscore and printed `eval_spec.py` as `evalspec.py`, so
    test_every_file_path_is_written_with_path requires `\\path`. But `\\path` in a
    caption with no short form is written to the .lot, where it expands to
    "\\Url Error ->\\url used in a moving argument" and no PDF is produced.

    The short optional caption resolves it: it is what gets written out, so the
    long caption stays put and may hold fragile commands. That makes the `[...]`
    load-bearing rather than decorative, which is why this test exists.
    """
    for body, has_short in _caption_bodies(tex.read_text(encoding="utf-8")):
        if "\\path{" in body:
            assert has_short, (
                f"{tex.relative_to(ROOT)}: \\path in a caption with no short "
                "[...] form. This is fatal, not cosmetic: the caption moves to "
                "the .lot and the document does not compile. Add a short caption "
                "rather than replacing \\path with \\texttt."
            )


def test_caption_check_actually_sees_a_planted_fault() -> None:
    """The check above is worthless if its parser cannot find a caption body."""
    planted = r"\caption{Data in \path{a/b_c.dat}.}\label{x}"
    assert [("\\path{" in b, short) for b, short in _caption_bodies(planted)] == [
        (True, False)
    ]
    # The same caption made safe: \path kept, short form added.
    fixed = r"\caption[Data.]{Data in \path{a/b_c.dat}.}\label{x}"
    assert [("\\path{" in b, short) for b, short in _caption_bodies(fixed)] == [
        (True, True)
    ]
    # And the `%`-separated form the emitter writes is recognised as short.
    split = "\\caption[Short.]%\n{Long with \\path{a/b_c.dat}.}"
    assert _caption_bodies(split)[0][1] is True


EMITTERS = [
    *sorted((ROOT / "review").glob("emit_*.py")),
    ROOT / "training" / "holdout_eval.py",
]


@pytest.mark.parametrize("src", EMITTERS, ids=lambda p: p.name)
def test_no_module_constant_defined_twice(src: Path) -> None:
    """The second assignment wins silently and the first one's readers change meaning."""
    tree = ast.parse(src.read_text(encoding="utf-8"))
    seen: collections.Counter[str] = collections.Counter()
    for node in tree.body:  # module level only
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    seen[target.id] += 1
    repeated = {name: n for name, n in seen.items() if n > 1}
    assert not repeated, (
        f"{src.relative_to(ROOT)}: module constant(s) assigned more than once: "
        f"{repeated}. PLACEHOLDER was defined twice here and the gloss count in "
        "Table 1's caption was wrong by a factor of seven as a result."
    )


def test_every_label_defined_exactly_once() -> None:
    """A duplicate label does not error. It silently retargets every \\ref to it."""
    where: dict[str, list[str]] = collections.defaultdict(list)
    for tex in TEX_FILES:
        body = _strip_comments(tex.read_text(encoding="utf-8"))
        for label in re.findall(r"\\label\{([^}]+)\}", body):
            where[label].append(str(tex.relative_to(PAPER)))
    dupes = {k: v for k, v in where.items() if len(v) > 1}
    # generated/limitations.tex carries a stale sec:limitations until the next
    # evaluation pass regenerates it. sections/limitations.tex neutralises it with
    # a local \renewcommand{\label}, so it reaches no .aux; the test below pins
    # that guard. Any OTHER duplicate is a real defect.
    dupes.pop("sec:limitations", None)
    assert not dupes, f"labels defined more than once: {dupes}"


def test_stale_generated_label_is_neutralised_where_it_is_input() -> None:
    """The emitter is fixed; this pins the guard covering already-generated files."""
    including = (PAPER / "sections" / "limitations.tex").read_text(encoding="utf-8")
    group = including[including.index("\\begingroup") :]
    group = group[: group.index("\\endgroup")]
    assert "\\input{generated/limitations}" in group
    assert "\\renewcommand{\\label}[1]{}" in group, (
        "the guard neutralising the generated block's stale \\label is gone; "
        "\\ref{sec:limitations} will point into Section 7 rather than at it"
    )

    generated = PAPER / "generated" / "limitations.tex"
    if generated.exists():
        labels = re.findall(
            r"\\label\{([^}]+)\}",
            _strip_comments(generated.read_text(encoding="utf-8")),
        )
        assert set(labels) <= {"sec:limitations", "sec:limits:generated"}, (
            f"the generated block now defines {labels}; suppressing \\label inside "
            "the group would swallow a label something else references"
        )


def test_emitter_no_longer_writes_the_colliding_label() -> None:
    src = (ROOT / "training" / "holdout_eval.py").read_text(encoding="utf-8")
    assert "\\\\label{sec:limits:generated}" in src
    assert "\\\\label{sec:limitations}" not in src


# --- The caption's prose must fit whatever the counts turn out to be. ---------
#
# As emitted on 2026-09-19 the caption asserted, in consecutive sentences, that
# 15 of 15 phrases carry a real gloss and that "every other phrase" carries only
# a placeholder. Both numbers were freshly computed and one was wrong, but the
# contradiction was possible only because the words around them were written for
# 2 and never re-read against 15.

import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
from review.emit_corpus_example import gloss_sentences  # noqa: E402


@pytest.mark.parametrize(
    ("total", "glossed", "concepts"),
    [(15, 2, 1), (15, 15, 8), (15, 1, 1), (15, 14, 7), (15, 0, 0), (1, 1, 1)],
)
def test_caption_never_contradicts_itself(
    total: int, glossed: int, concepts: int
) -> None:
    text = " ".join(gloss_sentences(total, glossed, concepts))
    remainder_claimed = "remaining" in text
    assert remainder_claimed == (total - glossed > 0), (
        f"{glossed} of {total} glossed, yet the sentence about the remainder is "
        f"{'present' if remainder_claimed else 'absent'}: {text!r}"
    )
    assert text.count("{") == text.count("}"), f"unbalanced braces: {text!r}"


def test_caption_agrees_in_number() -> None:
    one = " ".join(gloss_sentences(15, 1, 1))
    assert "1 carries a real English gloss" in one
    assert "it belongs to a single concept" in one and "they" not in one
    assert "2 carry a real English gloss" in " ".join(gloss_sentences(15, 2, 1))
    assert "remaining 1 phrase " in " ".join(gloss_sentences(15, 14, 7))
    assert "remaining 13 phrases " in " ".join(gloss_sentences(15, 2, 1))


def test_caption_does_not_assume_two_persons_of_one_concept() -> None:
    """The phrase that broke: written for 2/1, emitted verbatim at 15/8."""
    assert "two persons" in " ".join(gloss_sentences(15, 2, 1))
    for text in (
        " ".join(gloss_sentences(15, 15, 8)),
        " ".join(gloss_sentences(15, 5, 3)),
        " ".join(gloss_sentences(15, 4, 1)),
    ):
        assert "two persons" not in text, text


def test_caption_refuses_an_impossible_count() -> None:
    from review.emit_corpus_example import Missing

    with pytest.raises(Missing):
        gloss_sentences(15, 16, 8)


def test_comment_stripping_is_not_itself_blind() -> None:
    """A \\label in a comment is not a definition; one after \\% still is."""
    assert "\\label{real}" in _strip_comments("%\\label{fake}\n\\label{real}")
    assert "fake" not in _strip_comments("% see \\label{fake}\n\\label{real}")
    assert "\\label{kept}" in _strip_comments("100\\% done \\label{kept}")
