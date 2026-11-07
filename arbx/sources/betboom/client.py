"""BetBoom line access. See arbx/sources/_template/source.py for the procedure."""

from __future__ import annotations

from typing import Any

import requests


def fetch_line(session: requests.Session, base_url: str, timeout: int = 20) -> dict[str, Any]:
    raise NotImplementedError
