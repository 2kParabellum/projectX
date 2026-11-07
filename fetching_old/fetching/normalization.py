from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .parsing import (
    _event_id_as_str,
    _maturity_from_slug,
    _pick_category,
    _to_float,
    _token_ids_from_market,
    _yes_probability_from_market,
    calc_days_to_maturity,
    get_tag_labels,
    resolve_market_maturity,
)


def event_to_base_fields(ev: Dict[str, Any]) -> Dict[str, Any]:
    """Extract shared event-level fields used when building dataframe rows.

    Reads id, slug, creation date, title, volume, and tag metadata from a Gamma
    API event dict. Tags are flattened to a comma-separated string; the first
    tag label is also chosen as the event ``category`` (same rule as the rest
    of the pipeline).

    ``event_title`` and ``event_volume`` are included for reuse by row builders
    but are not meant to appear as dataframe columns by themselves; market rows
    use question text and per-market or event volume instead.

    Returns a plain dict so callers can spread or merge fields without coupling
    to a custom type.
    """
    ev_id = _event_id_as_str(ev)
    event_slug = ev.get("slug")
    creation_date = ev.get("creationDate")
    event_title = ev.get("title")
    event_volume = _to_float(ev.get("volume"))
    tag_labels = get_tag_labels(ev)
    category = _pick_category(tag_labels)
    tags_csv = ", ".join(tag_labels) if tag_labels else None
    return {
        "category": category,
        "event_id": ev_id,
        "event_slug": event_slug,
        "creation_date": creation_date,
        "event_title": event_title,
        "event_volume": event_volume,
        "tags": tags_csv,
    }


def event_without_markets_to_row(ev: Dict[str, Any], now_utc: pd.Timestamp) -> Dict[str, Any]:
    """Build a single market-style row for an event that has no ``markets`` list.

    Some active events arrive with an empty market list; we still emit one row so
    downstream code sees the event. The row uses the event title as ``question``,
    leaves market id/slug and probabilities unset, and carries event-level volume.

    Maturity is inferred only from the event slug (not per-market end dates).
    ``days_to_maturity`` is the fractional day count from ``now_utc`` when a slug
    maturity exists.

    This mirrors the legacy single-row path for empty ``markets`` and keeps the
    same column names as multi-market events.
    """
    base = event_to_base_fields(ev)
    event_slug = base["event_slug"] or ""
    event_maturity, event_maturity_source = _maturity_from_slug(event_slug)
    maturity_date = event_maturity
    maturity_source = event_maturity_source
    days_to_mat = (
        (maturity_date - now_utc).total_seconds() / 86400
        if maturity_date is not None
        else None
    )
    return {
        "category": base["category"],
        "event_id": base["event_id"],
        "event_slug": base["event_slug"],
        "market_id": None,
        "market_slug": None,
        "question": base["event_title"],
        "creation_date": base["creation_date"],
        "maturity_date": maturity_date,
        "maturity_source": maturity_source,
        "yes_prob": None,
        "no_prob": None,
        "days_to_maturity": days_to_mat,
        "yes_token_id": None,
        "no_token_id": None,
        "total_volume": base["event_volume"],
        "tags": base["tags"],
    }


def market_to_row(
    ev: Dict[str, Any],
    market: Dict[str, Any],
    now_utc: pd.Timestamp,
) -> Dict[str, Any]:
    """Turn one Gamma ``market`` dict (plus its parent event) into a flat row dict.

    Joins event-level category, ids, slug, creation date, and tags with
    market-specific question, slug, volume, and id. Maturity is resolved in
    slug–API–event fallback order via ``resolve_market_maturity``.

    Yes probability comes from outcome prices when available; ``no_prob`` is
    ``1 - yes_prob`` when yes is known.

    ``total_volume`` prefers the market's own volume and falls back to the
    event volume when the market does not report one.
    """
    base = event_to_base_fields(ev)
    event_slug = base["event_slug"] or ""
    event_maturity, event_maturity_source = _maturity_from_slug(event_slug)
    market_id = market.get("id")
    market_slug = market.get("slug")
    question = market.get("question") or market_slug
    maturity_date, maturity_source = resolve_market_maturity(
        market,
        ev,
        market_slug,
        event_maturity,
        event_maturity_source,
    )
    yes_prob = _yes_probability_from_market(market)
    no_prob = (1.0 - yes_prob) if yes_prob is not None else None
    days_to_mat = calc_days_to_maturity(maturity_date, now_utc)
    yes_token_id, no_token_id = _token_ids_from_market(market)
    return {
        "category": base["category"],
        "event_id": base["event_id"],
        "event_slug": base["event_slug"],
        "market_id": str(market_id) if market_id is not None else None,
        "market_slug": market_slug,
        "question": question,
        "creation_date": base["creation_date"],
        "maturity_date": maturity_date,
        "maturity_source": maturity_source,
        "yes_prob": yes_prob,
        "no_prob": no_prob,
        "days_to_maturity": days_to_mat,
        "yes_token_id": yes_token_id,
        "no_token_id": no_token_id,
        "total_volume": _to_float(market.get("volume")) or base["event_volume"],
        "tags": base["tags"],
    }


def normalize_event_to_rows(
    ev: Dict[str, Any],
    now_utc: pd.Timestamp,
) -> List[Dict[str, Any]]:
    """Expand one Gamma event into one or more row dicts at market granularity.

    If ``markets`` is missing or empty, returns a one-element list from
    ``event_without_markets_to_row`` so the event is still represented. If the
    event has markets, returns one row per market via ``market_to_row``, all
    sharing the same ``now_utc`` snapshot for consistent maturity math.

    The return value is always a list (never a single dict) so callers can
    ``extend`` into a flat list without branching on type.

    Row dicts use the final dataframe column names; they are not yet typed or
    coerced—``rows_to_dataframe`` applies dtypes afterward.
    """
    markets = ev.get("markets") or []
    if not markets:
        return [event_without_markets_to_row(ev, now_utc)]
    return [market_to_row(ev, m, now_utc) for m in markets]


def normalize_events_to_market_rows(
    events: List[Dict[str, Any]],
    now_utc: pd.Timestamp,
) -> List[Dict[str, Any]]:
    """Flatten a sequence of events into a single list of market-level row dicts.

    Applies ``normalize_event_to_rows`` to each event and concatenates results
    in order. Useful when you already have an in-memory list of events (for
    example from tests or a cached API payload) instead of streaming from
    ``iter_active_events``.

    All rows share the same ``now_utc``, so maturity calculations are comparable
    across the batch. Does not deduplicate events; that is
    handled earlier in the HTTP pagination layer when using the full fetch path.

    Returns an empty list when ``events`` is empty.
    """
    rows: List[Dict[str, Any]] = []
    for ev in events:
        rows.extend(normalize_event_to_rows(ev, now_utc))
    return rows


def rows_to_dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """Materialize row dicts as a ``DataFrame`` with stable dtypes.

    Builds a frame from the list of dicts. For non-empty frames, parses
    ``creation_date`` and ``maturity_date`` as UTC-aware datetimes (invalid
    values become NaT). Coerces numeric columns—yes/no prob, days to maturity,
    and volume—to numeric with ``errors='coerce'`` so mixed API
    strings do not break aggregation.

    An empty input yields an empty DataFrame with no column coercion; callers
    should handle ``df.empty`` before assuming dtypes exist.

    Column set and order follow whatever keys appear in ``rows``; the fetch
    pipeline always supplies the full enriched market schema.
    """
    df = pd.DataFrame(rows)
    if not df.empty:
        df["creation_date"] = pd.to_datetime(df["creation_date"], errors="coerce", utc=True)
        df["maturity_date"] = pd.to_datetime(df["maturity_date"], errors="coerce", utc=True)
        for c in [
            "yes_prob",
            "no_prob",
            "days_to_maturity",
            "total_volume",
        ]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def make_excel_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with timezone-aware datetimes made Excel-friendly.

    Strips timezone from datetime64 columns (``tz_localize(None)``) so
    ``to_excel`` does not fail on tz-aware dtypes. Other columns are unchanged.
    """
    df = df.copy()

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            try:
                if df[col].dt.tz is not None:
                    df[col] = df[col].dt.tz_localize(None)
            except TypeError:
                pass

    return df
