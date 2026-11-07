"""Polymarket adapter.

``fetch`` collects the raw sports and esports snapshot. ``parse`` is still a
stub: the raw payload is what we inspect before choosing a canonical layout.
"""

from __future__ import annotations

from arbx.models import Quote, RawSnapshot, SourceEvent, Sport
from arbx.sources.base import BaseSource
from arbx.sources.polymarket.client import collect_raw


class PolymarketSource(BaseSource):
    name = "polymarket"

    def fetch(self, sports: list[Sport]) -> RawSnapshot:
        # League series, not the Sport enum, decide what gets downloaded.
        # Esports is not in that enum yet and lives in the same Gamma catalog.
        return collect_raw(config=self.config)

    def parse(self, snapshot: RawSnapshot) -> tuple[list[SourceEvent], list[Quote]]:
        raise NotImplementedError(
            "raw collection only; canonical parsing is not decided yet"
        )
