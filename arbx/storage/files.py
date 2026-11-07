"""Snapshot files on disk.

Raw snapshots are append-only and never rewritten. They are the reason later
stages can be rerun offline, in a notebook, against exactly the response that
was collected.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arbx.config import PROJECT_ROOT
from arbx.models import Quote, RawSnapshot


def _data_dir(data_dir: Path | None) -> Path:
    return data_dir if data_dir is not None else PROJECT_ROOT / "data"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("fetched_at must be timezone-aware")
    return value.astimezone(timezone.utc)


def save_raw(snapshot: RawSnapshot, data_dir: Path | None = None) -> Path:
    """Write data/raw/<source>/<YYYY-MM-DD>/<timestamp>.json. Never overwrites."""
    fetched_at = _as_utc(snapshot.fetched_at)
    day = fetched_at.strftime("%Y-%m-%d")
    stamp = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    directory = _data_dir(data_dir) / "raw" / snapshot.source / day
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / f"{stamp}.json"
    suffix = 1
    while path.exists():
        path = directory / f"{stamp}_{suffix}.json"
        suffix += 1

    document = {
        "source": snapshot.source,
        "fetched_at": fetched_at.isoformat(),
        "meta": snapshot.meta,
        "payload": snapshot.payload,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False)
    return path


def load_raw(path: Path) -> RawSnapshot:
    with Path(path).open(encoding="utf-8") as handle:
        document = json.load(handle)
    fetched_at = datetime.fromisoformat(document["fetched_at"])
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return RawSnapshot(
        source=document["source"],
        fetched_at=fetched_at,
        payload=document["payload"],
        meta=document.get("meta") or {},
    )


def latest_raw(source: str, data_dir: Path | None = None) -> Path | None:
    """Most recent snapshot for a source, for replaying without a fetch."""
    root = _data_dir(data_dir) / "raw" / source
    if not root.exists():
        return None
    paths = [path for path in root.rglob("*.json") if path.is_file()]
    if not paths:
        return None
    return max(paths, key=lambda path: path.name)


def quotes_to_frame(quotes: list[Quote]) -> Any:
    """Flat table of quotes, for inspection in a notebook."""
    raise NotImplementedError


def save_quotes(quotes: list[Quote], data_dir: Path) -> Path:
    """Write data/normalized/<timestamp>.parquet."""
    raise NotImplementedError
