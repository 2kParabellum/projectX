"""Odds math is pure, so it gets the strictest tests in the project."""

from __future__ import annotations

from decimal import Decimal

import pytest

from arbx.odds import book_sum, margin, odds_to_probability, probability_to_odds, stake_split


def test_probability_round_trip():
    assert odds_to_probability(probability_to_odds(Decimal("0.25"))) == Decimal("0.25")


def test_book_sum_detects_arbitrage():
    # 2.10 and 2.10 on a two-way market: 0.476 + 0.476 < 1
    assert book_sum([Decimal("2.10"), Decimal("2.10")]) < 1
    assert margin([Decimal("2.10"), Decimal("2.10")]) > 0


def test_book_sum_rejects_normal_book():
    assert margin([Decimal("1.90"), Decimal("1.90")]) < 0


def test_stake_split_equalises_payouts():
    odds = {"home": Decimal("2.10"), "away": Decimal("2.10")}
    stakes = stake_split(odds, Decimal("1000"))
    payouts = [stakes[k] * odds[k] for k in odds]
    assert max(payouts) - min(payouts) < Decimal("0.01")
    assert sum(stakes.values()) == pytest.approx(Decimal("1000"))
