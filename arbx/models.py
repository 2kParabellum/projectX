"""Canonical data types shared by every stage of the pipeline.

This module is the contract between sources, matching, arbitrage and notify.
It imports nothing from the rest of ``arbx``; everything else imports it.

Invariants enforced here, not by convention:
  - prices are decimal odds (``Decimal``), never probabilities or floats;
  - timestamps are timezone-aware UTC;
  - selections and market kinds are enums, never free text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping


class Sport(str, Enum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    ICEHOCKEY = "icehockey"
    OTHER = "other"


class MarketKind(str, Enum):
    """Type of bet. Determines which selections form a complete outcome set."""

    MONEYLINE_2WAY = "moneyline_2way"
    ONE_X_TWO = "one_x_two"
    TOTAL = "total"
    HANDICAP = "handicap"


class Selection(str, Enum):
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"
    OVER = "over"
    UNDER = "under"


class Period(str, Enum):
    FULL_TIME = "ft"
    FIRST_HALF = "h1"
    SECOND_HALF = "h2"


#: The exact set of selections that must all be priced before a market can be
#: checked for arbitrage. A partial set is never evaluated.
COMPLETE_OUTCOME_SETS: Mapping[MarketKind, frozenset[Selection]] = {
    MarketKind.MONEYLINE_2WAY: frozenset({Selection.HOME, Selection.AWAY}),
    MarketKind.ONE_X_TWO: frozenset({Selection.HOME, Selection.DRAW, Selection.AWAY}),
    MarketKind.TOTAL: frozenset({Selection.OVER, Selection.UNDER}),
    MarketKind.HANDICAP: frozenset({Selection.HOME, Selection.AWAY}),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class RawSnapshot:
    """Untouched response from a site, kept so stages 2-4 can be replayed offline."""

    source: str
    fetched_at: datetime
    payload: Any
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceEvent:
    """A sporting event as one source describes it, before any cross-source linking."""

    source: str
    source_event_id: str
    sport: Sport
    home: str
    away: str
    start_time: datetime
    league: str | None = None
    url: str | None = None
    #: Names after normalization, used by matching. Filled by stage 2.
    home_norm: str | None = None
    away_norm: str | None = None
    league_norm: str | None = None


@dataclass(frozen=True, slots=True)
class MarketKey:
    """Identifies a market precisely enough to compare it across sources.

    Two markets are the same market only if their keys are equal, line
    included: ``TOTAL 2.5`` and ``TOTAL 3.0`` are different markets.
    """

    kind: MarketKind
    period: Period = Period.FULL_TIME
    line: Decimal | None = None

    def __post_init__(self) -> None:
        needs_line = self.kind in (MarketKind.TOTAL, MarketKind.HANDICAP)
        if needs_line and self.line is None:
            raise ValueError(f"{self.kind.value} requires a line")
        if not needs_line and self.line is not None:
            raise ValueError(f"{self.kind.value} must not carry a line")


@dataclass(frozen=True, slots=True)
class Quote:
    """One price for one selection of one market at one source."""

    source: str
    source_event_id: str
    market: MarketKey
    selection: Selection
    decimal_odds: Decimal
    fetched_at: datetime
    #: Largest stake the source will accept, in account currency. None = unknown.
    max_stake: Decimal | None = None
    #: Money available at this price (Polymarket order book depth). None = unknown.
    depth: Decimal | None = None
    #: Where in the raw snapshot this came from, for debugging.
    raw_ref: str | None = None

    @property
    def implied_probability(self) -> Decimal:
        return Decimal(1) / self.decimal_odds

    def age_seconds(self, now: datetime | None = None) -> float:
        return ((now or utcnow()) - self.fetched_at).total_seconds()


@dataclass(frozen=True, slots=True)
class MatchedEvent:
    """One logical event, linking the per-source events that describe it."""

    event_key: str
    sport: Sport
    home: str
    away: str
    start_time: datetime
    members: tuple[SourceEvent, ...]
    #: Matching confidence, 0-100. 100 means a confirmed alias hit.
    confidence: float = 100.0

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(m.source for m in self.members)


@dataclass(frozen=True, slots=True)
class ArbOpportunity:
    """A complete outcome set whose best prices sum to less than 1."""

    event: MatchedEvent
    market: MarketKey
    #: Best quote per selection; keys always equal COMPLETE_OUTCOME_SETS[market.kind].
    legs: Mapping[Selection, Quote]
    #: Sum of implied probabilities before costs. Below 1 means an edge exists.
    book_sum: Decimal
    #: 1 - book_sum, before costs.
    gross_margin: Decimal
    #: Margin after fees and slippage assumptions.
    net_margin: Decimal
    #: Stake per selection for the configured bankroll.
    stakes: Mapping[Selection, Decimal]
    detected_at: datetime

    @property
    def dedupe_key(self) -> str:
        line = "" if self.market.line is None else f"@{self.market.line}"
        return f"{self.event.event_key}|{self.market.kind.value}{line}|{self.market.period.value}"
