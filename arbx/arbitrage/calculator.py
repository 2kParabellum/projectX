"""Sizing and cost modelling for a candidate opportunity.

Gross margin from raw prices is the optimistic number. What matters is the
net margin after the things that actually eat the edge:

  - per-source fees (Polymarket charges takers on sports markets);
  - slippage: the best ask on Polymarket only covers so much size, so a stake
    larger than the top of book fills at a worse average price;
  - stake caps: a bookmaker leg that cannot absorb its share of the bankroll
    caps the whole position, since the legs must stay in proportion.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from arbx.models import Quote, Selection


def effective_odds(quote: Quote, fee: Decimal, stake: Decimal) -> Decimal:
    """Odds the stake would actually get, after fee and walking the book."""
    raise NotImplementedError


def average_fill_price(levels: list[tuple[Decimal, Decimal]], size: Decimal) -> Decimal | None:
    """Volume-weighted price for buying ``size`` across order book levels.

    None when the book cannot absorb the size at all.
    """
    raise NotImplementedError


def max_feasible_bankroll(legs: Mapping[Selection, Quote], bankroll: Decimal) -> Decimal:
    """Largest bankroll every leg can take, given stake caps and book depth."""
    raise NotImplementedError


def size_position(
    legs: Mapping[Selection, Quote],
    bankroll: Decimal,
    fees: Mapping[str, Decimal],
) -> tuple[dict[Selection, Decimal], Decimal]:
    """Return (stake per selection, net margin after costs)."""
    raise NotImplementedError
