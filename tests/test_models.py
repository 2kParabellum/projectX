from __future__ import annotations

from decimal import Decimal

import pytest

from arbx.models import MarketKey, MarketKind, Period


def test_total_requires_a_line():
    with pytest.raises(ValueError):
        MarketKey(kind=MarketKind.TOTAL)


def test_moneyline_rejects_a_line():
    with pytest.raises(ValueError):
        MarketKey(kind=MarketKind.ONE_X_TWO, line=Decimal("2.5"))


def test_different_lines_are_different_markets():
    a = MarketKey(MarketKind.TOTAL, Period.FULL_TIME, Decimal("2.5"))
    b = MarketKey(MarketKind.TOTAL, Period.FULL_TIME, Decimal("3.0"))
    assert a != b
    assert len({a, b}) == 2
