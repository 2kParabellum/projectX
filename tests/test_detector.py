"""Detector tests. The incomplete-outcome-set case is the important one."""

from __future__ import annotations

import pytest

pytest.skip("detector not implemented yet", allow_module_level=True)


def test_two_way_arbitrage_is_found():
    """2.10 / 2.10 across two sources is reported."""


def test_normal_book_is_not_reported():
    """1.90 / 1.90 produces nothing."""


def test_incomplete_outcome_set_is_skipped():
    """A 1X2 market missing the draw must produce no opportunity at all."""


def test_single_source_legs_are_rejected():
    """Both legs from the same bookmaker is not an arbitrage."""


def test_stale_quotes_are_excluded():
    """A quote older than max_quote_age_seconds cannot form a leg."""
