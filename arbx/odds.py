"""Odds arithmetic. Pure functions, no I/O, no imports from the rest of arbx."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, TypeVar

K = TypeVar("K")

#: Polymarket share prices outside this band are treated as untradeable noise.
MIN_SHARE_PRICE = Decimal("0.001")
MAX_SHARE_PRICE = Decimal("0.999")


def to_decimal(value: object) -> Decimal | None:
    """Best-effort conversion of a site value to ``Decimal``; None when unusable."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def probability_to_odds(probability: Decimal) -> Decimal:
    """Convert a Polymarket share price (USDC per $1 payout) to decimal odds."""
    if not (MIN_SHARE_PRICE <= probability <= MAX_SHARE_PRICE):
        raise ValueError(f"share price out of tradeable range: {probability}")
    return Decimal(1) / probability


def odds_to_probability(decimal_odds: Decimal) -> Decimal:
    if decimal_odds <= 1:
        raise ValueError(f"decimal odds must exceed 1, got {decimal_odds}")
    return Decimal(1) / decimal_odds


def book_sum(odds: Iterable[Decimal]) -> Decimal:
    """Sum of implied probabilities. Below 1 means an arbitrage exists."""
    return sum((odds_to_probability(o) for o in odds), Decimal(0))


def margin(odds: Iterable[Decimal]) -> Decimal:
    """Profit as a fraction of total stake, before costs. Negative means no edge."""
    return Decimal(1) - book_sum(odds)


def stake_split(odds: Mapping[K, Decimal], bankroll: Decimal) -> dict[K, Decimal]:
    """Split ``bankroll`` so every outcome returns the same amount.

    Stake on outcome i is proportional to 1/odds_i, which equalises payouts.
    """
    total = book_sum(odds.values())
    if total <= 0:
        raise ValueError("book sum must be positive")
    return {key: bankroll * odds_to_probability(o) / total for key, o in odds.items()}


def apply_fee(decimal_odds: Decimal, fee: Decimal) -> Decimal:
    """Shade odds down for a fee charged as a fraction of net winnings.

    A fee makes a bet worse, so effective odds fall: 1 + (d - 1) * (1 - fee).
    """
    if not (Decimal(0) <= fee < Decimal(1)):
        raise ValueError(f"fee must be in [0, 1), got {fee}")
    return Decimal(1) + (decimal_odds - Decimal(1)) * (Decimal(1) - fee)


def remove_vig(odds: Mapping[K, Decimal]) -> dict[K, Decimal]:
    """Fair probabilities with the bookmaker margin removed proportionally.

    Useful for judging which side of a disagreement is mispriced; not used in
    arbitrage detection itself, which works on raw tradeable prices.
    """
    total = book_sum(odds.values())
    return {key: odds_to_probability(o) / total for key, o in odds.items()}
