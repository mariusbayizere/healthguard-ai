"""Accent folding shared by language detection and the red-flag layer.

One definition, so that the two can never disagree about what a word is.
"""

from __future__ import annotations

import unicodedata


def fold(text: str) -> str:
    """Strip accents so that "fievre" matches "fièvre".

    Patients type symptoms on feature-phone keypads and through USSD, where
    accented characters are routinely dropped. Matching on the folded form means
    accent-free French and Kinyarwanda still match.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))
