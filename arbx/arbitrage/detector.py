"""Find arbitrage in matched markets. Pure functions over Quote objects.

No network, no files, no database here - which is what makes this layer
cheap to test exhaustively.
"""

from __future__ import annotations

from arbx.models import ArbOpportunity, MarketKey, MatchedEvent, Quote, Selection


def group_quotes_by_market(
    quotes: list[Quote],
    event: MatchedEvent,
) -> dict[MarketKey, list[Quote]]:
    """Bucket an event's quotes from all sources by identical market key."""
    raise NotImplementedError


def best_quote_per_selection(quotes: list[Quote]) -> dict[Selection, Quote]:
    """Highest decimal odds for each selection across sources."""
    raise NotImplementedError


def is_complete_outcome_set(kind: MarketKey, legs: dict[Selection, Quote]) -> bool:
    """True only when every selection the market requires has a price.

    An incomplete set is never evaluated. A two-way Polymarket question
    compared against a three-way bookmaker market would otherwise show a huge
    phantom edge purely because the draw is missing.
    """
    raise NotImplementedError


def detect(
    event: MatchedEvent,
    quotes: list[Quote],
    min_margin,
    bankroll,
    fees: dict[str, object],
) -> list[ArbOpportunity]:
    """All opportunities in one matched event that clear the margin threshold."""
    raise NotImplementedError
