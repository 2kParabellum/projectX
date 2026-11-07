"""Repeat the cycle on an interval, surviving individual cycle failures."""

from __future__ import annotations

from arbx.config import Settings


def run_forever(settings: Settings) -> None:
    """Loop run_cycle every cycle_interval_seconds until interrupted."""
    raise NotImplementedError
