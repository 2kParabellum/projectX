"""Rules that reject an opportunity before it reaches a notification."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from arbx.models import ArbOpportunity, Quote


def is_fresh(quote: Quote, max_age_seconds: int, now: datetime | None = None) -> bool:
    """Reject quotes older than the window. Odds move in seconds."""
    raise NotImplementedError


def clears_margin(opportunity: ArbOpportunity, min_margin: Decimal) -> bool:
    raise NotImplementedError


def has_usable_size(opportunity: ArbOpportunity, min_stake: Decimal) -> bool:
    """Reject edges too thin or too shallow to be worth acting on."""
    raise NotImplementedError


def legs_span_multiple_sources(opportunity: ArbOpportunity) -> bool:
    """Guard against an 'arbitrage' built from a single source's own prices."""
    raise NotImplementedError
