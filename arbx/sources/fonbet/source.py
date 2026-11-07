"""Fonbet adapter."""

from __future__ import annotations

from arbx.models import Quote, RawSnapshot, SourceEvent, Sport
from arbx.sources.base import BaseSource


class FonbetSource(BaseSource):
    name = "fonbet"

    def fetch(self, sports: list[Sport]) -> RawSnapshot:
        raise NotImplementedError

    def parse(self, snapshot: RawSnapshot) -> tuple[list[SourceEvent], list[Quote]]:
        raise NotImplementedError
