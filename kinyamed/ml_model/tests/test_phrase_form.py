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


def test_attribution_survives_capitalisation() -> None:
    """An utterance is capitalised at a sentence start and lowercased after a
    greeting. A case-sensitive match loses every row with an opener, and those
    rows drop out of the phrase holdout and the leakage analysis silently."""
    from dataset.split_dataset import attribute_phrase

    phrase = "Ndakorora cyane."
    family = "kinyarwanda->kinyarwanda:URGENT:cardiac_respiratory"
    index = {"kinyarwanda": [phrase]}
    f = Family(
        language="kinyarwanda", urgency="URGENT", domain="cardiac_respiratory",
        frame_language="kinyarwanda", phrase_language="kinyarwanda",
        slots=(("", "Muganga, "), ("",), (phrase,), ("",), ("",), ("", ". Nkora iki?")),
        form=UTTERANCE,
    )
    for i in range(f.combinations):
        text = f.render(i)
        assert attribute_phrase(text, family, index) == phrase, (
            f"attribution lost for {text!r}"
        )


def test_render_collapses_duplicate_sentence_punctuation() -> None:
    f = Family(
        language="kinyarwanda", urgency="URGENT", domain="cardiac_respiratory",
        frame_language="kinyarwanda", phrase_language="kinyarwanda",
        slots=(("",), ("",), ("Ndakorora cyane.",), ("",),
               (". Byatangiye gitunguranye.",), (". Nkora iki?",)),
        form=UTTERANCE,
    )
    out = f.render(0)
    assert ".." not in out, out
    assert out == "Ndakorora cyane. Byatangiye gitunguranye. Nkora iki?", out


def test_rel_placeholder_expands_over_every_relation() -> None:
    """One authored sentence must render as all eight relations."""
    import dataset.vocabulary as V
    import dataset.generate_large_dataset as G

    canonical = "{REL} ntashobora guhumeka neza."
    V.PHRASE_FORMS[canonical] = UTTERANCE
    G.PHRASE_FORMS = V.PHRASE_FORMS
    saved = V.SYMPTOMS["kinyarwanda"]["URGENT"]["cardiac_respiratory"]
    V.SYMPTOMS["kinyarwanda"]["URGENT"]["cardiac_respiratory"] = (canonical,)
    G.SYMPTOMS = V.SYMPTOMS
    try:
        f = next(x for x in build_families()
                 if x.language == "kinyarwanda" and x.domain == "cardiac_respiratory"
                 and x.urgency == "URGENT")
        assert len(f.slots[2]) == len(V.RELATIONS["kinyarwanda"])
        assert "{REL}" not in " ".join(f.slots[2]), "placeholder left unexpanded"
    finally:
        V.SYMPTOMS["kinyarwanda"]["URGENT"]["cardiac_respiratory"] = saved
        V.PHRASE_FORMS.pop(canonical, None)
        G.SYMPTOMS = V.SYMPTOMS


def test_rel_expansions_share_one_phrase_identity() -> None:
    """All eight relations must attribute to the canonical phrase, or the
    holdout could put 'umwana wanjye' in train and 'mama' in eval."""
    from dataset.split_dataset import attribute_phrase
    import dataset.vocabulary as V

    canonical = "{REL} ntashobora guhumeka neza."
    family = "kinyarwanda->kinyarwanda:URGENT:cardiac_respiratory"
    index = {"kinyarwanda": [canonical]}
    for rel in V.RELATIONS["kinyarwanda"]:
        text = canonical.replace("{REL}", rel)
        assert attribute_phrase(text, family, index) == canonical
        assert attribute_phrase("Muganga, " + text[0].lower() + text[1:], family, index) == canonical


def test_terminal_stop_dropped_before_a_continuation() -> None:
    f = Family(
        language="kinyarwanda", urgency="URGENT", domain="cardiac_respiratory",
        frame_language="kinyarwanda", phrase_language="kinyarwanda",
        slots=(("",), ("",), ("Ndakorora cyane.",), (" kuva ejo",), ("",), ("",)),
        form=UTTERANCE,
    )
    assert f.render(0) == "Ndakorora cyane kuva ejo", f.render(0)


def test_terminal_stop_kept_before_a_new_sentence() -> None:
    f = Family(
        language="kinyarwanda", urgency="URGENT", domain="cardiac_respiratory",
        frame_language="kinyarwanda", phrase_language="kinyarwanda",
        slots=(("",), ("",), ("Ndakorora cyane.",), ("",),
               (". Byatangiye gitunguranye.",), ("",)),
        form=UTTERANCE,
    )
    assert f.render(0) == "Ndakorora cyane. Byatangiye gitunguranye.", f.render(0)


def test_relation_is_lowercased_mid_sentence() -> None:
    """A relation is written capitalised but is not always sentence-initial.

    "Iyo {REL} ahumeka..." must render "Iyo umwana wanjye ahumeka", not
    "Iyo Umwana wanjye ahumeka".
    """
    import dataset.vocabulary as V
    import dataset.generate_large_dataset as G

    head_phrase = "{REL} arakorora cyane."
    mid_phrase = "Iyo {REL} ahumeka, birababaza."
    saved_sym = V.SYMPTOMS["kinyarwanda"]["URGENT"]["paediatric"]
    saved_rel = V.RELATIONS["kinyarwanda"]
    saved_dom = V.DOMAIN_RELATIONS.pop("paediatric", None)
    V.RELATIONS["kinyarwanda"] = ("Umwana wanjye",)
    for p in (head_phrase, mid_phrase):
        V.PHRASE_FORMS[p] = UTTERANCE
    V.SYMPTOMS["kinyarwanda"]["URGENT"]["paediatric"] = (head_phrase, mid_phrase)
    G.SYMPTOMS, G.PHRASE_FORMS, G.RELATIONS = V.SYMPTOMS, V.PHRASE_FORMS, V.RELATIONS
    G.DOMAIN_RELATIONS = V.DOMAIN_RELATIONS
    try:
        f = next(x for x in build_families()
                 if x.language == "kinyarwanda" and x.domain == "paediatric"
                 and x.urgency == "URGENT")
        rendered = set(f.slots[2])
        assert "Umwana wanjye arakorora cyane." in rendered, rendered
        assert "Iyo umwana wanjye ahumeka, birababaza." in rendered, rendered
        assert "Iyo Umwana wanjye ahumeka, birababaza." not in rendered
    finally:
        V.SYMPTOMS["kinyarwanda"]["URGENT"]["paediatric"] = saved_sym
        V.RELATIONS["kinyarwanda"] = saved_rel
        if saved_dom is not None:
            V.DOMAIN_RELATIONS["paediatric"] = saved_dom
        for p in (head_phrase, mid_phrase):
            V.PHRASE_FORMS.pop(p, None)
        G.SYMPTOMS, G.RELATIONS = V.SYMPTOMS, V.RELATIONS


def test_domain_relation_set_restricts_expansion() -> None:
    import dataset.vocabulary as V
    import dataset.generate_large_dataset as G

    phrase = "{REL} aratwite."
    saved = V.SYMPTOMS["kinyarwanda"]["CRITICAL"]["obstetric"]
    V.PHRASE_FORMS[phrase] = UTTERANCE
    V.SYMPTOMS["kinyarwanda"]["CRITICAL"]["obstetric"] = (phrase,)
    G.SYMPTOMS, G.PHRASE_FORMS = V.SYMPTOMS, V.PHRASE_FORMS
    try:
        f = next(x for x in build_families()
                 if x.language == "kinyarwanda" and x.domain == "obstetric")
        assert len(f.slots[2]) == len(V.DOMAIN_RELATIONS["obstetric"])
        joined = " ".join(f.slots[2])
        for excluded in ("Umugabo wanjye", "Papa", "Umukecuru"):
            assert excluded not in joined, f"{excluded} must not appear in obstetric"
    finally:
        V.SYMPTOMS["kinyarwanda"]["CRITICAL"]["obstetric"] = saved
        V.PHRASE_FORMS.pop(phrase, None)
        G.SYMPTOMS = V.SYMPTOMS


def test_empty_relation_set_produces_no_third_person_rows() -> None:
    """NO_RELATIONS means the concept has no third-person form.

    That is a restriction, not a deletion: the concept keeps its first-person
    phrase and simply contributes nothing in third person. It must not raise,
    and it must not silently fall back to the full relation list.
    """
    import dataset.vocabulary as V
    import dataset.generate_large_dataset as G

    phrase = "{REL} ashaka kongererwa imiti."
    saved = V.SYMPTOMS["kinyarwanda"]["ROUTINE"]["chronic_care"]
    V.PHRASE_FORMS[phrase] = UTTERANCE
    V.CONCEPT_RELATIONS[phrase] = V.NO_RELATIONS
    V.SYMPTOMS["kinyarwanda"]["ROUTINE"]["chronic_care"] = (phrase,)
    G.SYMPTOMS, G.PHRASE_FORMS, G.CONCEPT_RELATIONS = V.SYMPTOMS, V.PHRASE_FORMS, V.CONCEPT_RELATIONS
    try:
        fams = [x for x in build_families()
                if x.language == "kinyarwanda" and x.domain == "chronic_care"
                and x.urgency == "ROUTINE"]
        for f in fams:
            assert phrase not in f.slots[2], "an empty set must contribute no rows"
            for rel in V.RELATIONS["kinyarwanda"]:
                assert not any(rel in p for p in f.slots[2]), (
                    f"{rel} leaked in despite NO_RELATIONS"
                )
    finally:
        V.SYMPTOMS["kinyarwanda"]["ROUTINE"]["chronic_care"] = saved
        V.PHRASE_FORMS.pop(phrase, None)
        V.CONCEPT_RELATIONS.pop(phrase, None)
        G.SYMPTOMS = V.SYMPTOMS


def test_misconfigured_relation_set_raises() -> None:
    """A non-empty set naming nothing available is a bug, not an intention."""
    import pytest as _pytest
    import dataset.vocabulary as V
    import dataset.generate_large_dataset as G

    phrase = "{REL} arwaye."
    saved = V.SYMPTOMS["kinyarwanda"]["ROUTINE"]["chronic_care"]
    V.PHRASE_FORMS[phrase] = UTTERANCE
    V.CONCEPT_RELATIONS[phrase] = ("Somebody Who Does Not Exist",)
    V.SYMPTOMS["kinyarwanda"]["ROUTINE"]["chronic_care"] = (phrase,)
    G.SYMPTOMS, G.PHRASE_FORMS, G.CONCEPT_RELATIONS = V.SYMPTOMS, V.PHRASE_FORMS, V.CONCEPT_RELATIONS
    try:
        with _pytest.raises(SystemExit, match="misconfiguration"):
            build_families()
    finally:
        V.SYMPTOMS["kinyarwanda"]["ROUTINE"]["chronic_care"] = saved
        V.PHRASE_FORMS.pop(phrase, None)
        V.CONCEPT_RELATIONS.pop(phrase, None)
        G.SYMPTOMS = V.SYMPTOMS
