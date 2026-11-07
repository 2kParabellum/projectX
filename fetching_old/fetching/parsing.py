from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import _MONTHS


def _to_float(x):
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _event_id_as_str(ev: Dict[str, Any]) -> Optional[str]:
    x = ev.get("id")
    return str(x) if x is not None else None


def _page_signature(batch: List[Dict[str, Any]], n: int = 5) -> Tuple[str, ...]:
    out = []
    for ev in batch[:n]:
        ev_id = ev.get("id")
        slug = ev.get("slug")
        out.append(f"{ev_id}|{slug}")
    return tuple(out)


def _pick_category(tag_labels: List[str]) -> Optional[str]:
    if not tag_labels:
        return None
    return tag_labels[0]


def get_tag_labels(ev: Dict[str, Any]) -> List[str]:
    ev_tags = ev.get("tags") or []
    tag_labels: List[str] = []
    for t in ev_tags:
        if isinstance(t, dict) and t.get("label"):
            tag_labels.append(t["label"])
    return tag_labels


def _yes_probability_from_market(m: Dict[str, Any]) -> Optional[float]:
    yes_price = m.get("yesPrice")
    if yes_price is not None:
        p = _to_float(yes_price)
        if p is not None:
            if p > 1:
                p = p / 100.0
            if 0 <= p <= 1:
                return p

    outcomes = m.get("outcomes")
    outcome_prices = m.get("outcomePrices")

    try:
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if isinstance(outcome_prices, str):
            outcome_prices = json.loads(outcome_prices)

        if outcomes and outcome_prices and len(outcomes) == len(outcome_prices):
            for name, px in zip(outcomes, outcome_prices):
                if str(name).strip().lower() == "yes":
                    p = _to_float(px)
                    if p is not None:
                        if p > 1:
                            p = p / 100.0
                        if 0 <= p <= 1:
                            return p
    except Exception:
        pass

    return None


def _token_ids_from_market(m: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Map CLOB token ids to Yes/No by aligning ``outcomes`` with ``clobTokenIds``.

    Both fields may be a list or a JSON string. Returns ``(yes_token_id,
    no_token_id)`` with ids as strings; uses outcome labels ``yes`` / ``no``
    (case-insensitive, stripped). Returns ``(None, None)`` on parse errors,
    type mismatches, length mismatch, or missing keys.
    """
    try:
        outcomes = m.get("outcomes")
        token_ids = m.get("clobTokenIds")

        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if isinstance(token_ids, str):
            token_ids = json.loads(token_ids)

        if not isinstance(outcomes, list) or not isinstance(token_ids, list):
            return None, None
        if len(outcomes) != len(token_ids):
            return None, None

        yes_token_id: Optional[str] = None
        no_token_id: Optional[str] = None

        for out, tid in zip(outcomes, token_ids):
            label = str(out).strip().lower()
            if tid is None:
                tid_str: Optional[str] = None
            else:
                tid_str = str(tid)
            if label == "yes":
                yes_token_id = tid_str
            elif label == "no":
                no_token_id = tid_str

        return yes_token_id, no_token_id
    except Exception:
        return None, None


def _maturity_from_slug(slug: str) -> tuple[pd.Timestamp | None, str | None]:
    """
    Parse maturity date ONLY from slug.

    Supported patterns (with optional trailing "-<digits>" chains):
      - ...-by-march-31-2026[-627-999-...]   -> 2026-03-31
      - ...-by-september-30[-627-...]        -> current_year-09-30
      - ...-in-2025[-999-...]                -> 2025-12-31

    Returns (timestamp_utc, source_label) or (None, None).
    """
    if not slug:
        return None, None

    s = str(slug).strip().lower()

    m = re.search(r"-by-([a-z]+)-(\d{1,2})-(\d{4})(?:-\d+)*$", s)
    if m:
        month_name, day, year = m.group(1), int(m.group(2)), int(m.group(3))
        month = _MONTHS.get(month_name)
        if month:
            try:
                return (
                    pd.Timestamp(year=year, month=month, day=day, tz="UTC"),
                    "slug:by-mdY",
                )
            except Exception:
                return None, None

    m = re.search(r"-by-([a-z]+)-(\d{1,2})(?:-\d+)*$", s)
    if m:
        month_name, day = m.group(1), int(m.group(2))
        month = _MONTHS.get(month_name)
        if month:
            year = pd.Timestamp.now(tz="UTC").year
            try:
                return (
                    pd.Timestamp(year=year, month=month, day=day, tz="UTC"),
                    "slug:by-md (assumed current year)",
                )
            except Exception:
                return None, None

    m = re.search(r"-in-(\d{4})(?:-\d+)*$", s)
    if m:
        year = int(m.group(1))
        try:
            return (
                pd.Timestamp(year=year, month=12, day=31, tz="UTC"),
                "slug:in-year (EOY)",
            )
        except Exception:
            return None, None

    return None, None


def calc_days_to_maturity(
    maturity_date: Any,
    now_utc: pd.Timestamp,
) -> Optional[float]:
    if maturity_date is None:
        return None
    if pd.isna(maturity_date):
        return None
    return (maturity_date - now_utc).total_seconds() / 86400


def resolve_market_maturity(
    market: Dict[str, Any],
    event: Dict[str, Any],
    market_slug: Optional[str],
    event_maturity: Optional[pd.Timestamp],
    event_maturity_source: Optional[str],
) -> Tuple[Any, Optional[str]]:
    maturity_date, maturity_source = _maturity_from_slug(market_slug or "")
    if maturity_date is None:
        api_end = market.get("endDate") or event.get("endDate")
        maturity_date = (
            pd.to_datetime(api_end, errors="coerce", utc=True) if api_end else None
        )
        maturity_source = (
            "api:endDate"
            if maturity_date is not None and not pd.isna(maturity_date)
            else None
        )
    if maturity_date is None or pd.isna(maturity_date):
        maturity_date, maturity_source = event_maturity, event_maturity_source
    return maturity_date, maturity_source
