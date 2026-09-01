"""Attribution over the real authored corpus, not constructed examples.

`attribute_phrase` has failed silently twice. It was case-sensitive and lost
every row carrying an opener; then its `{REL}` match deleted the placeholder and
lost every phrase where `{REL}` was not phrase-initial. Both hollowed out the
phrase holdout without raising anything, and both survived a green suite because
the tests that covered attribution used phrases someone wrote for the test.

`make verify-full` cannot catch this class of bug either: v1 has no `{REL}`
phrases, so the frozen corpus never exercises the path.

So this check drives the real generator over the real brief. Every authored
phrase is expanded across the relations its concept actually allows, rendered
through `Family.render` across every frame combination, and must attribute back
to its canonical form. A `None` is the silent failure and fails the test.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

BRIEF = Path("review/speaker_brief_kinyarwanda_v2.csv")


def authored_phrases(ml_root: Path) -> list[tuple[str, str, str]]:
    """(phrase, urgency, domain) for every phrase the speaker has authored."""
    path = ml_root / BRIEF
    if not path.exists():                                   # pragma: no cover
        pytest.skip(f"{BRIEF} not present")
    out = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            phrase = (row.get("your_phrasing") or "").strip()
            if not phrase or (row.get("applies") or "yes").strip().lower() == "no":
                continue
            out.append((phrase, row["proposed_urgency"], row["domain"]))
    return out


def families_for(phrase: str, urgency: str, domain: str, form: str):
    """The real families the generator would build for this one phrase."""
    import dataset.vocabulary as V
    from dataset.generate_large_dataset import LANGUAGES, build_families

    saved_symptoms, saved_forms = V.SYMPTOMS, dict(V.PHRASE_FORMS)
    try:
        V.SYMPTOMS = {lang: {} for lang in LANGUAGES}
        V.SYMPTOMS["kinyarwanda"] = {urgency: {domain: (phrase,)}}
        V.PHRASE_FORMS[phrase] = form
        import dataset.generate_large_dataset as G
        saved_g = G.SYMPTOMS
        G.SYMPTOMS = V.SYMPTOMS
        try:
            return [f for f in build_families() if f.phrase_language == "kinyarwanda"]
        finally:
            G.SYMPTOMS = saved_g
    finally:
        V.SYMPTOMS = saved_symptoms
        V.PHRASE_FORMS.clear()
        V.PHRASE_FORMS.update(saved_forms)


def test_every_authored_phrase_attributes_in_every_rendering(ml_root: Path) -> None:
    """Exhaustive: every phrase x every valid relation x every frame combination.

    The index holds only the phrase under test, which is what makes the sweep
    affordable and isolates the property this guards — that a rendering never
    loses its own phrase. Cross-phrase attribution is checked separately below.
    """
    from dataset.generate_large_dataset import UTTERANCE
    from dataset.split_dataset import attribute_phrase

    phrases = authored_phrases(ml_root)
    assert phrases, "no authored phrases found — the check would pass vacuously"

    renderings = 0
    for phrase, urgency, domain in phrases:
        index = {"kinyarwanda": [phrase]}
        for family in families_for(phrase, urgency, domain, UTTERANCE):
            for i in range(family.combinations):
                text = family.render(i)
                got = attribute_phrase(text, family.family_id, index)
                assert got == phrase, (
                    f"{phrase!r} ({urgency}/{domain}) did not attribute its own rendering.\n"
                    f"  rendered: {text!r}\n  got     : {got!r}\n"
                    "A None here means these rows leave the phrase holdout silently."
                )
                renderings += 1
    assert renderings > 10_000, f"only {renderings} renderings swept; the sweep has collapsed"


def test_no_authored_phrase_is_attributed_to_another(ml_root: Path) -> None:
    """With the whole inventory in the index, a rendering must still resolve to
    its own phrase — a near-duplicate must not capture its neighbour's rows.

    Frame combinations are sampled deterministically here; the exhaustive sweep
    above covers the rendering space, and this covers the index interaction.
    """
    from dataset.generate_large_dataset import UTTERANCE
    from dataset.split_dataset import attribute_phrase

    phrases = authored_phrases(ml_root)
    # longest first, which is the order attribution relies on for "longest wins"
    index = {"kinyarwanda": sorted({p for p, _, _ in phrases}, key=len, reverse=True)}

    for phrase, urgency, domain in phrases:
        for family in families_for(phrase, urgency, domain, UTTERANCE):
            total = family.combinations
            for i in range(0, total, max(1, total // 24)):
                text = family.render(i)
                got = attribute_phrase(text, family.family_id, index)
                assert got == phrase, (
                    f"{phrase!r} ({urgency}/{domain}) was attributed elsewhere.\n"
                    f"  rendered: {text!r}\n  got     : {got!r}\n"
                    "Two phrases this close would split across the phrase holdout."
                )
