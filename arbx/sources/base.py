"""The interface every site adapter implements.

A source knows how to reach one site and how to read its response. It knows
nothing about matching, arbitrage or notification, and must not import them.

``fetch`` and ``parse`` are deliberately separate: ``parse`` is a pure function
of a saved snapshot, so it can be exercised on fixtures with no network.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from arbx.models import Quote, RawSnapshot, SourceEvent, Sport


class BaseSource(ABC):
    #: Stable identifier used in config, storage paths and quote records.
    name: str

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @abstractmethod
    def fetch(self, sports: list[Sport]) -> RawSnapshot:
        """Hit the site and return its response untouched."""

    @abstractmethod
    def parse(self, snapshot: RawSnapshot) -> tuple[list[SourceEvent], list[Quote]]:
        """Turn a snapshot into canonical events and quotes."""

    def collect(self, sports: list[Sport]) -> tuple[RawSnapshot, list[SourceEvent], list[Quote]]:
        """Convenience: fetch then parse, returning all three for the caller to store."""
        snapshot = self.fetch(sports)
        events, quotes = self.parse(snapshot)
        return snapshot, events, quotes
