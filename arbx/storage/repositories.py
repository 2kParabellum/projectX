"""Entity-level reads and writes. The only module that issues SQL."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from arbx.models import ArbOpportunity, SourceEvent


class AliasRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def all(self) -> dict[str, str]:
        raise NotImplementedError

    def add(self, alias: str, canonical: str, kind: str) -> None:
        raise NotImplementedError


class LinkRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def confirmed_key(self, source: str, source_event_id: str) -> str | None:
        raise NotImplementedError

    def save_link(self, event_key: str, event: SourceEvent, confidence: float) -> None:
        raise NotImplementedError

    def queue_for_review(self, left: SourceEvent, right: SourceEvent, score: float) -> None:
        raise NotImplementedError

    def pending(self) -> list[dict]:
        raise NotImplementedError


class OpportunityRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save(self, opportunity: ArbOpportunity) -> None:
        raise NotImplementedError

    def last_alert(self, dedupe_key: str) -> tuple[datetime, float] | None:
        """When this opportunity was last alerted and at what margin."""
        raise NotImplementedError

    def mark_alerted(self, opportunity: ArbOpportunity) -> None:
        raise NotImplementedError
