"""Conexión Snowflake para Cortex Analyst y repositorios (SQL ejecutado en Snowflake)."""
from __future__ import annotations

import os
from typing import Any, Dict

import snowflake.connector

# Defaults si no hay variables de entorno (ver `backend/.env.example`).
RAG_DB = "DB_BT_TERPEL_COMBS"
RAG_SCHEMA = "BT_TERPEL_COMBS_MART_ANALYTICS"


def build_snowflake_connection_params() -> Dict[str, Any]:
    """Parámetros de conexión (PAT o password); reutilizado por Cortex Analyst y repositorios."""
    token = os.getenv("SNOWFLAKE_TOKEN", "").strip()
    user = os.getenv("SNOWFLAKE_USER", "").strip().upper()
    account = os.getenv("SNOWFLAKE_ACCOUNT", "").strip().upper()
    role = os.getenv("SNOWFLAKE_ROLE", "SYNAPSE_APP_ROLE").strip().upper()
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "WH_BT_TERPEL_COMBS_BI").strip().upper()
    schema = os.getenv("SNOWFLAKE_SCHEMA", RAG_SCHEMA).strip().upper()

    login_timeout = int(os.getenv("SNOWFLAKE_LOGIN_TIMEOUT_SEC", "15"))
    network_timeout = int(os.getenv("SNOWFLAKE_NETWORK_TIMEOUT_SEC", "60"))
    statement_timeout = int(os.getenv("SNOWFLAKE_STATEMENT_TIMEOUT_SEC", "90"))

    conn_params: Dict[str, Any] = {
        "user": user,
        "account": account,
        "database": os.getenv("SNOWFLAKE_DATABASE", RAG_DB),
        "warehouse": warehouse,
        "schema": schema,
        "role": role,
        "client_prefetch_mfa_token": False,
        "client_request_mfa_token": False,
        "login_timeout": login_timeout,
        "network_timeout": network_timeout,
        "session_parameters": {
            "STATEMENT_TIMEOUT_IN_SECONDS": statement_timeout,
        },
    }

    if token:
        conn_params.pop("role", None)
        print(f"[Snowflake] Connecting via Token (User: {user}, Account: {account})")
        conn_params["authenticator"] = "PROGRAMMATIC_ACCESS_TOKEN"
        conn_params["token"] = token
    else:
        print("[Snowflake] Connecting via Password")
        conn_params["password"] = os.getenv("SNOWFLAKE_PASSWORD")

    return conn_params


def connect_snowflake():
    return snowflake.connector.connect(**build_snowflake_connection_params())
