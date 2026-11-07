from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from py_clob_client.clob_types import OpenOrderParams

from .gamma import build_retry_session, iter_active_events_keyset
from .normalization import make_excel_safe, normalize_event_to_rows, rows_to_dataframe

DATA_API = "https://data-api.polymarket.com"


def fetch_active_markets_enriched(
    limit: int = 500,
    timeout: int = 30,
    max_pages: int = 10000,
    session: Optional[requests.Session] = None,
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    """Download active Polymarket events and return a market-level enriched table.

    Paginates the Gamma ``/events/keyset`` endpoint (active, not closed) with
    deduplication and the same stop conditions as the legacy implementation.
    Each returned row corresponds to one market (or one placeholder row if an
    event has no markets).

    The ``limit`` parameter is the maximum number of **events** to fetch (not the
    API page size). Requests use a fixed keyset page size of 100, e.g.
    ``limit=1000`` performs up to 10 pages of 100 events.

    Columns include category, ids, slugs, question, timestamps, maturity and
    its source, implied yes/no probabilities, days to maturity, CLOB
    ``yes_token_id`` / ``no_token_id`` when parsable from the market payload,
    volume, and a comma-separated tags field. Maturity prefers slug parsing,
    then API ``endDate``, then the event-level slug maturity fallback.

    You may pass an existing ``requests.Session`` for connection reuse; otherwise
    a session with retry middleware is created. ``sleep_seconds`` throttles
    between pages to reduce rate-limit pressure.
    """
    max_events = limit
    s = session or build_retry_session()
    now_utc = pd.Timestamp.now(tz="UTC")
    rows: List[Dict[str, Any]] = []
    for ev in iter_active_events_keyset(
        s,
        limit=100,
        timeout=timeout,
        max_pages=max_pages,
        max_events=max_events,
        sleep_seconds=sleep_seconds,
        rows_for_logging=rows,
    ):
        rows.extend(normalize_event_to_rows(ev, now_utc))
    return rows_to_dataframe(rows)


def get_my_positions_df(user_address: str) -> pd.DataFrame:
    rows = []
    limit = 500
    offset = 0

    while True:
        params = {
            "user": user_address,
            "status": "OPEN",
            "limit": limit,
            "offset": offset,
            "sortBy": "TOKENS",
            "sortDirection": "DESC",
        }

        r = requests.get(
            f"{DATA_API}/positions",
            params=params,
            timeout=20,
        )
        r.raise_for_status()

        data = r.json()

        if not data:
            break

        rows.extend(data)

        if len(data) < limit:
            break

        offset += limit

    if not rows:
        return pd.DataFrame(columns=[
            "token_id",
            "balance",
            "outcome",
            "market_slug",
            "title",
            "cur_price",
            "current_value",
            "cash_pnl",
        ])

    df = pd.DataFrame(rows)

    df = df.rename(columns={
        "asset": "token_id",
        "size": "balance",
        "slug": "market_slug",
        "curPrice": "cur_price",
        "currentValue": "current_value",
        "cashPnl": "cash_pnl",
        "percentPnl": "percent_pnl",
        "avgPrice": "avg_price",
    })

    keep_cols = [
        "token_id",
        "balance",
        "outcome",
        "market_slug",
        "title",
        "cur_price",
        "avg_price",
        "current_value",
        "cash_pnl",
        "percent_pnl",
        "endDate",
    ]

    keep_cols = [c for c in keep_cols if c in df.columns]

    return (
        df[keep_cols]
        .sort_values("balance", ascending=False)
        .reset_index(drop=True)
    )


def get_my_open_orders_df(client: Any) -> pd.DataFrame:
    orders = client.get_open_orders()

    if not orders:
        return pd.DataFrame(columns=[
            "order_id",
            "token_id",
            "market",
            "side",
            "price",
            "original_size",
            "size_matched",
            "remaining_size",
            "status",
            "created_at",
            "expiration",
        ])

    df = pd.DataFrame(orders)

    rename_map = {
        "id": "order_id",
        "asset_id": "token_id",
    }

    df = df.rename(columns=rename_map)

    for col in ["price", "original_size", "size_matched"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["token_id"] = df["token_id"].astype(str)
    df["side"] = df["side"].astype(str).str.upper()

    df["remaining_size"] = df["original_size"] - df["size_matched"]
    df["notional_remaining"] = df["remaining_size"] * df["price"]
    df["notional_original"] = df["original_size"] * df["price"]
    df["notional_matched"] = df["size_matched"] * df["price"]

    preferred_cols = [
        "order_id",
        "token_id",
        "market",
        "side",
        "price",
        "original_size",
        "size_matched",
        "remaining_size",
        "notional_original",
        "notional_matched",
        "notional_remaining",
        "status",
        "outcome",
        "created_at",
        "expiration",
        "order_type",
        "maker_address",
        "owner",
    ]

    existing = [c for c in preferred_cols if c in df.columns]
    other = [c for c in df.columns if c not in existing]

    return df[existing + other].reset_index(drop=True)



def _aggregate_orders_one_side(df_side: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Aggregate open orders for one side (buy_* or sell_* columns)."""
    if df_side.empty:
        return pd.DataFrame(columns=["token_id"])

    return (
        df_side.groupby("token_id", as_index=False)
        .agg(
            **{
                f"{prefix}_orders_count": ("token_id", "count"),
                f"{prefix}_total_original_size": ("original_size", "sum"),
                f"{prefix}_total_size_matched": ("size_matched", "sum"),
                f"{prefix}_total_remaining_size": ("remaining_size", "sum"),
                f"{prefix}_min_price": ("price", "min"),
                f"{prefix}_max_price": ("price", "max"),
            }
        )
    )


def aggregate_orders_by_token(df_orders: pd.DataFrame) -> pd.DataFrame:
    if df_orders is None or df_orders.empty:
        return pd.DataFrame(columns=_ORDER_AGG_COLS)

    df = df_orders.copy()

    df["token_id"] = df["token_id"].astype(str)
    df["side"] = df["side"].astype(str).str.upper()

    for col in ["price", "original_size", "size_matched", "remaining_size"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    buy_agg = _aggregate_orders_one_side(df[df["side"] == "BUY"], "buy")
    sell_agg = _aggregate_orders_one_side(df[df["side"] == "SELL"], "sell")

    result = pd.DataFrame({"token_id": df["token_id"].unique()})
    result = result.merge(buy_agg, on="token_id", how="left")
    result = result.merge(sell_agg, on="token_id", how="left")

    metric_cols = [c for c in _ORDER_AGG_COLS if c != "token_id"]
    for col in metric_cols:
        if col not in result.columns:
            result[col] = 0
        else:
            result[col] = result[col].fillna(0)

    return result[_ORDER_AGG_COLS]


_POSITION_JOIN_COLS = [
    "token_id",
    "balance",
    "outcome",
    "market_slug",
    "title",
    "cur_price",
    "avg_price",
    "current_value",
    "cash_pnl",
    "percent_pnl",
    "endDate",
]

_ORDER_AGG_COLS = [
    "token_id",
    "buy_orders_count",
    "buy_total_original_size",
    "buy_total_size_matched",
    "buy_total_remaining_size",
    "buy_min_price",
    "buy_max_price",
    "sell_orders_count",
    "sell_total_original_size",
    "sell_total_size_matched",
    "sell_total_remaining_size",
    "sell_min_price",
    "sell_max_price",
]


def merge_markets_with_positions_and_orders(
    df_markets: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_orders: pd.DataFrame,
) -> pd.DataFrame:
    out = df_markets.copy()

    pos = df_positions[
        [c for c in _POSITION_JOIN_COLS if c in df_positions.columns]
    ].copy()
    pos = pos.rename(columns={c: f"position_{c}" for c in pos.columns})
    if not pos.empty:
        out = out.merge(
            pos,
            left_on="yes_token_id",
            right_on="position_token_id",
            how="left",
        )
    else:
        for c in pos.columns:
            out[c] = pd.NA

    for base in _POSITION_JOIN_COLS:
        pc = f"position_{base}"
        if pc not in out.columns:
            out[pc] = pd.NA

    df_orders_agg = aggregate_orders_by_token(df_orders)
    ord_renamed = df_orders_agg.rename(
        columns={c: f"order_{c}" for c in df_orders_agg.columns}
    )
    if not ord_renamed.empty:
        out = out.merge(
            ord_renamed,
            left_on="yes_token_id",
            right_on="order_token_id",
            how="left",
        )
    else:
        for c in ord_renamed.columns:
            out[c] = pd.NA

    for base in _ORDER_AGG_COLS:
        oc = f"order_{base}"
        if oc not in out.columns:
            out[oc] = pd.NA

    for col in out.columns:
        if not (col.startswith("position_") or col.startswith("order_")):
            continue
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].fillna(0)

    return out


def fetch_active_markets_with_positions_and_orders_bundle(
    client: Any,
    user_address: str,
    limit: int = 2000000,
    save_csv: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return ``(df_full, df_orders)`` without storing raw order ids in ``df_full``."""
    df_markets = fetch_active_markets_enriched(limit=limit)
    df_positions = get_my_positions_df(user_address)
    df_orders = get_my_open_orders_df(client)
    df_final = merge_markets_with_positions_and_orders(
        df_markets, df_positions, df_orders
    )
    df_export = make_excel_safe(df_final)
    if save_csv:
        df_export.to_csv(Path("current_markets.csv"), index=False)
    return df_export, df_orders


def fetch_active_markets_with_positions_and_orders(
    client: Any,
    user_address: str,
    limit: int = 2000000,
) -> pd.DataFrame:
    df_full, _ = fetch_active_markets_with_positions_and_orders_bundle(
        client,
        user_address,
        limit=limit,
    )
    return df_full
