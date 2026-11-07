"""Snapshot and quote files on disk.

Raw snapshots are append-only and never rewritten. They are the reason stages
2-4 can be rerun offline, in a notebook, against exactly the data that caused
a bug.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from arbx.models import Quote, RawSnapshot


def save_raw(snapshot: RawSnapshot, data_dir: Path) -> Path:
    """Write to data/raw/<source>/<YYYY-MM-DD>/<timestamp>.json."""
    raise NotImplementedError


def load_raw(path: Path) -> RawSnapshot:
    raise NotImplementedError


def latest_raw(source: str, data_dir: Path) -> Path | None:
    """Most recent snapshot for a source, for replaying without a fetch."""
    raise NotImplementedError


def quotes_to_frame(quotes: list[Quote]) -> pd.DataFrame:
    """Flat table of quotes, for inspection in a notebook."""
    raise NotImplementedError


def save_quotes(quotes: list[Quote], data_dir: Path) -> Path:
    """Write data/normalized/<timestamp>.parquet."""
    raise NotImplementedError
