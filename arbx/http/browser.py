"""Playwright helper for bookmaker sites that will not serve plain JSON.

Playwright is imported lazily inside the functions so the project runs without
it installed until a source actually needs a browser.
"""

from __future__ import annotations

from typing import Any


def fetch_page_html(url: str, wait_selector: str | None = None, timeout_ms: int = 30_000) -> str:
    """Render a page in headless Chromium and return its HTML."""
    raise NotImplementedError


def capture_xhr(url: str, url_pattern: str, timeout_ms: int = 30_000) -> list[Any]:
    """Open a page and collect JSON bodies of XHR responses matching a pattern.

    This is how a bookmaker's hidden API endpoint gets discovered and then
    called directly, without a browser, from that point on.
    """
    raise NotImplementedError
