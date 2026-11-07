"""HTTP access to Polymarket's public APIs.

Gamma serves event and market metadata; CLOB serves the order book. Only
public read endpoints are used - no wallet, no authentication, no trading.

Pagination logic is ported from fetching_old/fetching/gamma.py, which already
handles the two traps in Gamma's feed: cursors that stop advancing and pages
that repeat themselves.
"""

from __future__ import annotations

from typing import Any, Iterator

import requests


def iter_sports_events(
    session: requests.Session,
    gamma_base_url: str,
    tag: str = "Sports",
    page_size: int = 100,
    timeout: int = 30,
    max_events: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield active sports events from Gamma, deduplicated by event id."""
    raise NotImplementedError


def fetch_order_books(
    session: requests.Session,
    clob_base_url: str,
    token_ids: list[str],
    timeout: int = 30,
) -> dict[str, Any]:
    """Fetch order books for CLOB token ids, keyed by token id.

    The book is what makes a Polymarket price tradeable rather than notional:
    the best ask and the size behind it decide the real entry price.
    """
    raise NotImplementedError
