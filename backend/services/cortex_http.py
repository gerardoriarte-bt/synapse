"""Utilidades HTTP compartidas para APIs REST de Snowflake Cortex (PAT)."""
from __future__ import annotations

import os
from typing import Dict


def rest_base_url() -> str:
    base = os.getenv("SNOWFLAKE_REST_BASE_URL", "").strip().rstrip("/")
    if base:
        return base
    acct = os.getenv("SNOWFLAKE_ACCOUNT", "").strip()
    if not acct:
        raise ValueError(
            "Define SNOWFLAKE_REST_BASE_URL (recomendado) "
            "o SNOWFLAKE_ACCOUNT para derivar https://<cuenta>.snowflakecomputing.com"
        )
    return f"https://{acct.lower()}.snowflakecomputing.com"


def auth_headers() -> Dict[str, str]:
    token = os.getenv("SNOWFLAKE_TOKEN", "").strip()
    if not token:
        raise ValueError("SNOWFLAKE_TOKEN es obligatorio para Cortex REST (PAT).")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
    }
