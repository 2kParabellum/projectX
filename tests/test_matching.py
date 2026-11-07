"""Matching tests. The cases that matter are the ones that must NOT match."""

from __future__ import annotations

import pytest

pytest.skip("matching not implemented yet", allow_module_level=True)


def test_same_fixture_across_languages_matches():
    """'Manchester United vs Arsenal' == 'Манчестер Юнайтед — Арсенал'."""


def test_different_fixture_same_club_does_not_match():
    """Man Utd vs Arsenal must not match Man Utd vs Chelsea."""


def test_same_clubs_different_date_does_not_match():
    """Home and away legs of a tie are separate events."""


def test_reserve_teams_do_not_match_first_teams():
    """'Арсенал (мол)' is not Arsenal."""
