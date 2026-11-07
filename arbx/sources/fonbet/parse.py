"""Fonbet JSON -> canonical events and quotes.

Team names arrive in Russian, so every name goes through arbx.normalize.teams
before matching sees it.
"""

from __future__ import annotations

from arbx.models import Quote, RawSnapshot, SourceEvent


def parse_snapshot(snapshot: RawSnapshot) -> tuple[list[SourceEvent], list[Quote]]:
    raise NotImplementedError
