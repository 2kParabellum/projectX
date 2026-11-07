"""Narrow the candidate pairs before any expensive comparison runs.

Comparing every event against every other is quadratic and mostly wasted
effort. Grouping by sport and start-time bucket first cuts the work to a
fraction of that, and the pairs it removes could never have matched anyway.
"""

from __future__ import annotations

from arbx.models import SourceEvent


def blocking_key(event: SourceEvent, window_minutes: int) -> tuple[str, str]:
    """(sport, time bucket) key. Events sharing a key are compared."""
    raise NotImplementedError


def candidate_pairs(
    events: list[SourceEvent],
    window_minutes: int,
) -> list[tuple[SourceEvent, SourceEvent]]:
    """All cross-source pairs that share a blocking key."""
    raise NotImplementedError
