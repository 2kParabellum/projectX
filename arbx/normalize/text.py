"""String cleanup shared by all sources. No network, no state."""

from __future__ import annotations


def clean(value: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation and diacritics."""
    raise NotImplementedError


def transliterate_ru(value: str) -> str:
    """Cyrillic -> Latin, so Russian bookmaker names can be compared to English ones."""
    raise NotImplementedError


def strip_club_noise(value: str) -> str:
    """Drop tokens that carry no identity: fc, cf, afc, club, "(м)", city suffixes."""
    raise NotImplementedError
