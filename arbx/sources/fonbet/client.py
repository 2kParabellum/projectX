"""Fonbet line access.

Fonbet serves its line as JSON to its own front end. The task is to find that
endpoint and call it directly; see arbx/sources/_template/source.py for the
discovery procedure.
"""

from __future__ import annotations

from typing import Any

import requests


def fetch_line(session: requests.Session, base_url: str, timeout: int = 20) -> dict[str, Any]:
    """Fetch the current line payload."""
    raise NotImplementedError
