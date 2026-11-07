"""Market and selection canonicalization.

This module decides what a site's bet actually is. It is allowed - and
expected - to return None for anything it does not recognise with certainty.
A silent wrong mapping here produces an arbitrage that does not exist, which
is far worse than a missed one.
"""

from __future__ import annotations

from decimal import Decimal

from arbx.models import MarketKey, Selection


def parse_market(raw_label: str, sport: str) -> MarketKey | None:
    """Map a site's market label onto a MarketKey. None when unrecognised."""
    raise NotImplementedError


def parse_selection(raw_label: str, kind: MarketKey) -> Selection | None:
    """Map a site's outcome label onto a Selection. None when unrecognised."""
    raise NotImplementedError


def parse_line(raw_label: str) -> Decimal | None:
    """Pull the handicap or total line out of a label, e.g. "Total over 2.5" -> 2.5."""
    raise NotImplementedError
