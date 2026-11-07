"""Turn per-source events into linked logical events.

Three outcomes per candidate pair, decided by thresholds in settings.yaml:
  score >= score_auto_link -> linked automatically
  score >= score_review    -> queued for manual review, not used this cycle
  below that               -> discarded
"""

from __future__ import annotations

from arbx.models import MatchedEvent, SourceEvent


def match_events(
    events: list[SourceEvent],
    window_minutes: int,
    score_auto_link: float,
    score_review: float,
) -> tuple[list[MatchedEvent], list[tuple[SourceEvent, SourceEvent, float]]]:
    """Return (linked events, pairs needing review).

    Only events present in at least two sources are returned as matches; a
    single-source event cannot produce an arbitrage.
    """
    raise NotImplementedError
