"""Scoring of a candidate pair of events, 0-100."""

from __future__ import annotations

from arbx.models import SourceEvent


def score_pair(left: SourceEvent, right: SourceEvent) -> float:
    """Combined confidence that two source events are the same match.

    Both participants must score well independently; a strong home-team match
    cannot carry a weak away-team match, since that is exactly how a derby
    gets confused with a different fixture involving the same club.
    """
    raise NotImplementedError


def score_names(left: str, right: str) -> float:
    """rapidfuzz token-set similarity of two normalized names."""
    raise NotImplementedError


def score_start_time(left: SourceEvent, right: SourceEvent) -> float:
    """Closeness of kickoff times, decaying with the gap."""
    raise NotImplementedError
