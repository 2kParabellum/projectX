"""SQLite connection and schema for state that must survive a restart."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS aliases (
    alias      TEXT NOT NULL,
    canonical  TEXT NOT NULL,
    kind       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (alias, kind)
);

CREATE TABLE IF NOT EXISTS event_links (
    event_key       TEXT NOT NULL,
    source          TEXT NOT NULL,
    source_event_id TEXT NOT NULL,
    confidence      REAL NOT NULL,
    confirmed_by    TEXT,
    created_at      TEXT NOT NULL,
    PRIMARY KEY (source, source_event_id)
);

CREATE TABLE IF NOT EXISTS pending_links (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    left_source   TEXT NOT NULL,
    left_event_id TEXT NOT NULL,
    right_source  TEXT NOT NULL,
    right_event_id TEXT NOT NULL,
    score         REAL NOT NULL,
    payload       TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunities (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key   TEXT NOT NULL,
    detected_at  TEXT NOT NULL,
    gross_margin REAL NOT NULL,
    net_margin   REAL NOT NULL,
    payload      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opportunities_key ON opportunities (dedupe_key);

CREATE TABLE IF NOT EXISTS alerts_sent (
    dedupe_key  TEXT PRIMARY KEY,
    sent_at     TEXT NOT NULL,
    net_margin  REAL NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database, creating it and applying the schema if needed."""
    raise NotImplementedError


def init_schema(conn: sqlite3.Connection) -> None:
    raise NotImplementedError
