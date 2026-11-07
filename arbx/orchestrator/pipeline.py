"""One full cycle: collect -> normalize -> match -> detect -> notify.

Stages are exposed individually as well as combined, because the notebook
drives them one at a time and ``run_cycle`` just chains the same calls.
A source that fails is logged and skipped; one broken bookmaker must not
take the cycle down.
"""

from __future__ import annotations

from dataclasses import dataclass

from arbx.config import Settings
from arbx.models import ArbOpportunity, MatchedEvent, Quote, SourceEvent


@dataclass(slots=True)
class CycleResult:
    events: list[SourceEvent]
    quotes: list[Quote]
    matched: list[MatchedEvent]
    opportunities: list[ArbOpportunity]
    errors: dict[str, str]


def collect_all(settings: Settings) -> tuple[list[SourceEvent], list[Quote], dict[str, str]]:
    """Run every enabled source, saving raw snapshots. Returns errors per source."""
    raise NotImplementedError


def replay_latest(settings: Settings) -> tuple[list[SourceEvent], list[Quote], dict[str, str]]:
    """Same as collect_all but parses the newest saved snapshots instead of fetching."""
    raise NotImplementedError


def run_cycle(settings: Settings, notify: bool = True, offline: bool = False) -> CycleResult:
    raise NotImplementedError
