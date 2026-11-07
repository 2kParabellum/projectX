"""Polymarket CLOB client factory (authenticated trading session)."""

from __future__ import annotations

import os
from dotenv import load_dotenv

from py_clob_client_v2 import ClobClient, SignatureTypeV2

from .config import CHAIN_ID, CLOB_HOST


def build_clob_client() -> ClobClient:
    load_dotenv()

    private_key = os.getenv("POLY_PRIVATE_KEY")
    funder = os.getenv("POLY_FUNDER_ADDRESS")

    if not private_key:
        raise ValueError("POLY_PRIVATE_KEY is not set")
    if not funder:
        raise ValueError("POLY_FUNDER_ADDRESS is not set")

    # 1. L1 auth: signer wallet only
    auth_client = ClobClient(
        host=CLOB_HOST,
        chain_id=CHAIN_ID,
        key=private_key,
        signature_type=SignatureTypeV2.POLY_1271,
    )

    creds = auth_client.derive_api_key()

    # 2. Trading client: same signer + funder/proxy wallet
    client = ClobClient(
        host=CLOB_HOST,
        chain_id=CHAIN_ID,
        key=private_key,
        creds=creds,
        signature_type=SignatureTypeV2.POLY_GNOSIS_SAFE,
        funder=funder,
    )

    return client
