"""Phrase form: noun phrases take a subject, utterances do not.

The speaker rewrote the corpus as full patient utterances, which the original
subject-injecting frame turns into "Umugabo wanjye afite ndakorora cyane".
These tests pin the two rendering paths and, most importantly, that declaring
nothing reproduces v1 exactly.
"""

from __future__ import annotations

import pytest

from dataset.generate_large_dataset import (
    DEFAULT_FORM,
    NOUN_PHRASE,
    UTTERANCE,
    Family,
    build_families,
    phrase_form,
)


def test_undeclared_phrases_default_to_noun_phrase() -> None:
    """v1 declares nothing; every phrase must behave exactly as before."""
    assert DEFAULT_FORM == NOUN_PHRASE
    assert phrase_form("a phrase nobody declared") == NOUN_PHRASE


def test_v1_vocabulary_produces_only_noun_phrase_families() -> None:
    forms = {f.form for f in build_families()}
    assert forms == {NOUN_PHRASE}, (
        "a phrase has been declared an utterance in the committed vocabulary; "
        "that changes the corpus and invalidates the v1 manifests"
    )


def make(form: str, phrases: tuple[str, ...], subjects: tuple[str, ...]) -> Family:
    return Family(
        language="kinyarwanda", urgency="URGENT", domain="cardiac_respiratory",
        frame_language="kinyarwanda", phrase_language="kinyarwanda",
        slots=(("", "Muganga, "), subjects, phrases, ("", " kuva ejo"), ("",), ("", ". Nkora iki?")),
        form=form,
    )


def test_noun_phrase_renders_with_a_subject() -> None:
    f = make(NOUN_PHRASE, ("inkorora ikaze",), ("Mfite", "Umwana wanjye afite"))
    rendered = {f.render(i) for i in range(f.combinations)}
    assert any(r.startswith("Umwana wanjye afite inkorora ikaze") for r in rendered)


def test_utterance_renders_without_a_subject() -> None:
    f = make(UTTERANCE, ("ndakorora cyane",), ("",))
    rendered = {f.render(i) for i in range(f.combinations)}
    assert "Ndakorora cyane" in rendered
    for r in rendered:
        assert "afite ndakorora" not in r, "a subject was injected before an utterance"


def test_utterance_capitalises_only_when_it_starts_the_sentence() -> None:
    f = make(UTTERANCE, ("ndakorora cyane",), ("",))
    rendered = {f.render(i) for i in range(f.combinations)}
    assert "Ndakorora cyane" in rendered, "no opener: the utterance starts the sentence"
    assert any(r.startswith("Muganga, ndakorora") for r in rendered), (
        "after a greeting the utterance continues mid-sentence and stays lowercase"
    )


def test_a_cell_with_both_forms_splits_into_two_families() -> None:
    """Different forms take different slot sets, so they cannot share a family.

    The subject slot is what differs: a noun phrase multiplies by every subject,
    an utterance by one empty string. With the real ten subjects that is a 10x
    difference in combinations for the same single phrase.
    """
    ten_subjects = tuple(f"Subject{i} afite" for i in range(10))
    noun = make(NOUN_PHRASE, ("inkorora ikaze",), ten_subjects)
    utt = make(UTTERANCE, ("ndakorora cyane",), ("",))
    assert noun.form != utt.form
    assert noun.combinations == utt.combinations * len(ten_subjects), (
        f"expected a {len(ten_subjects)}x gap, got {noun.combinations} vs {utt.combinations}"
    )


@pytest.mark.parametrize("form", [NOUN_PHRASE, UTTERANCE])
def test_render_covers_every_index_without_error(form: str) -> None:
    subjects = ("Mfite",) if form == NOUN_PHRASE else ("",)
    f = make(form, ("ndakorora cyane",), subjects)
    assert len({f.render(i) for i in range(f.combinations)}) == f.combinations
