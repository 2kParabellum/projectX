"""BetBoom JSON -> canonical events and quotes."""

from __future__ import annotations

from arbx.models import Quote, RawSnapshot, SourceEvent


def parse_snapshot(snapshot: RawSnapshot) -> tuple[list[SourceEvent], list[Quote]]:
    raise NotImplementedError
