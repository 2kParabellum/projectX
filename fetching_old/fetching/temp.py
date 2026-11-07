import os
import requests
from dotenv import load_dotenv
import json
import math
import pandas as pd
import csv
import time
from datetime import datetime

from py_clob_client.clob_types import (
    OrderArgs,
    OrderType,
    OpenOrderParams,
    BalanceAllowanceParams,
    AssetType,
)
from py_clob_client.order_builder.constants import BUY, SELL

from py_clob_client.clob_types import OrderArgs, OrderType, ApiCreds, MarketOrderArgs
from py_clob_client.order_builder.constants import BUY

from .clob_client import build_clob_client

CLOB_BASE = "https://clob.polymarket.com"

load_dotenv()

GAMMA_BASE = "https://gamma-api.polymarket.com"

YES_TOKEN_CACHE = {}

GLOBAL_BUY_LIMIT_USD = 10.0     # общий лимит на все покупки в этой сессии
GLOBAL_BUY_SPENT_USD = 0.0      # сколько уже потрачено этой сессией


DATA_API = "https://data-api.polymarket.com"


def get_my_positions_df(user_address: str):
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


def get_my_open_orders_df(client):
    orders = client.get_orders(OpenOrderParams())

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


def aggregate_orders_by_token(df_orders: pd.DataFrame) -> pd.DataFrame:
    if df_orders is None or df_orders.empty:
        return pd.DataFrame(columns=[
            "token_id",
            "orders_count",
            "total_original_size",
            "total_size_matched",
            "total_remaining_size",
            "min_price",
            "max_price",
        ])

    df = df_orders.copy()

    df["token_id"] = df["token_id"].astype(str)

    for col in ["price", "original_size", "size_matched", "remaining_size"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    agg = (
        df.groupby("token_id")
        .agg(
            orders_count=("token_id", "count"),
            total_original_size=("original_size", "sum"),
            total_size_matched=("size_matched", "sum"),
            total_remaining_size=("remaining_size", "sum"),
            min_price=("price", "min"),
            max_price=("price", "max"),
        )
        .reset_index()
    )

    return agg
