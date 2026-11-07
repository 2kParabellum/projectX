"""Gamma/CLOB JSON -> canonical events and quotes.

Donor code: fetching_old/fetching/parsing.py already solves reading
``outcomes`` / ``outcomePrices`` / ``clobTokenIds``, each of which may arrive
as either a list or a JSON-encoded string.

The hard part specific to this project is below: a Polymarket sports market is
a question in English ("Will Arsenal beat Chelsea?"), not a structured
home/away/market triple. Extracting that structure is what makes the market
comparable with a bookmaker line at all.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from arbx.models import MarketKey, Quote, RawSnapshot, SourceEvent


def extract_participants(event: dict[str, Any]) -> tuple[str, str] | None:
    """Pull (home, away) out of a Gamma event title or slug. None if not a match."""
    raise NotImplementedError


def classify_market(market: dict[str, Any]) -> MarketKey | None:
    """Decide which MarketKind and line a Gamma market represents.

    Returns None when the market does not map cleanly onto a known kind. A
    None here is correct and expected: an unmapped market is skipped, never
    guessed at, because a wrong mapping produces a fake arbitrage.
    """
    raise NotImplementedError


def best_ask(order_book: dict[str, Any]) -> tuple[Decimal, Decimal] | None:
    """Return (price, size) of the best ask, i.e. the real cost to buy now."""
    raise NotImplementedError


def parse_snapshot(snapshot: RawSnapshot) -> tuple[list[SourceEvent], list[Quote]]:
    """Full snapshot -> canonical events and quotes."""
    raise NotImplementedError
