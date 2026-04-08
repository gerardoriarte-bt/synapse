"""
Cliente Cortex Analyst (REST): NL → SQL + texto usando modelo semántico / vista semántica en Snowflake.

Documentación: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api
Auth (PAT): https://docs.snowflake.com/en/developer-guide/sql-api/authenticating
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import snowflake.connector

from models.synapse import DecisionMeta, SynapseResponse
from services.snowflake import connect_snowflake


def _rest_base_url() -> str:
    base = os.getenv("SNOWFLAKE_REST_BASE_URL", "").strip().rstrip("/")
    if base:
        return base
    acct = os.getenv("SNOWFLAKE_ACCOUNT", "").strip()
    if not acct:
        raise ValueError(
            "Define SNOWFLAKE_REST_BASE_URL (recomendado, ej. https://xyz.us-east-1.aws.snowflakecomputing.com) "
            "o SNOWFLAKE_ACCOUNT para derivar https://<cuenta>.snowflakecomputing.com"
        )
    return f"https://{acct.lower()}.snowflakecomputing.com"


def _auth_headers() -> Dict[str, str]:
    token = os.getenv("SNOWFLAKE_TOKEN", "").strip()
    if not token:
        raise ValueError("SNOWFLAKE_TOKEN es obligatorio para Cortex Analyst REST (PAT).")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
    }
    return headers


def _build_messages(user_query: str, history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Cortex Analyst acepta mensajes user; el historial se compacta en un solo turno si hace falta."""
    if not history:
        return [{"role": "user", "content": [{"type": "text", "text": user_query}]}]
    lines = []
    for h in history[-5:]:
        q = (h.get("q") or "")[:800]
        a = (h.get("a") or "")[:1200]
        lines.append(f"Usuario (antes): {q}\nAnalista (antes): {a}")
    block = "\n\n---\n\n".join(lines)
    text = (
        f"Contexto de conversación reciente:\n{block}\n\n---\n\nPregunta actual:\n{user_query}"
    )
    return [{"role": "user", "content": [{"type": "text", "text": text}]}]


def _semantic_payload() -> Dict[str, Any]:
    view = os.getenv("CORTEX_ANALYST_SEMANTIC_VIEW", "").strip()
    model_file = os.getenv("CORTEX_ANALYST_SEMANTIC_MODEL_FILE", "").strip()
    models_json = os.getenv("CORTEX_ANALYST_SEMANTIC_MODELS_JSON", "").strip()

    if models_json:
        try:
            arr = json.loads(models_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"CORTEX_ANALYST_SEMANTIC_MODELS_JSON no es JSON válido: {e}") from e
        if not isinstance(arr, list) or not arr:
            raise ValueError("CORTEX_ANALYST_SEMANTIC_MODELS_JSON debe ser un array no vacío.")
        return {"semantic_models": arr}

    if view:
        return {"semantic_view": view}

    if model_file:
        return {"semantic_model_file": model_file}

    raise ValueError(
        "Configura uno de: CORTEX_ANALYST_SEMANTIC_VIEW (ej. DB.SCHEMA.MI_VISTA_SEMANTICA), "
        "CORTEX_ANALYST_SEMANTIC_MODEL_FILE (ej. @DB.SCHEMA.STAGE/model.yaml), "
        "o CORTEX_ANALYST_SEMANTIC_MODELS_JSON (array de semantic_view / semantic_model_file)."
    )


def _parse_analyst_body(body: Dict[str, Any]) -> Tuple[str, Optional[str], List[str], Dict[str, Any]]:
    narrative_parts: List[str] = []
    sql_statement: Optional[str] = None
    extra: Dict[str, Any] = {}

    msg = body.get("message") or {}
    for c in msg.get("content") or []:
        if not isinstance(c, dict):
            continue
        ct = c.get("type")
        if ct == "text":
            narrative_parts.append(str(c.get("text") or ""))
        elif ct == "sql":
            sql_statement = c.get("statement")
            if c.get("confidence") is not None:
                extra["sql_confidence"] = c.get("confidence")
        elif ct == "suggestion":
            sug = c.get("suggestions")
            narrative_parts.append(f"Sugerencias del modelo: {sug}")

    narrative = "\n\n".join(p for p in narrative_parts if p).strip()
    warnings_list: List[str] = []
    for w in body.get("warnings") or []:
        if isinstance(w, dict) and w.get("message"):
            warnings_list.append(str(w["message"]))
    if warnings_list:
        narrative = (narrative + "\n\n---\nAvisos:\n" + "\n".join(f"- {x}" for x in warnings_list)).strip()

    if body.get("semantic_model_selection") is not None:
        extra["semantic_model_selection"] = body["semantic_model_selection"]
    if body.get("response_metadata"):
        extra["response_metadata"] = body["response_metadata"]
    if body.get("request_id"):
        extra["request_id"] = body["request_id"]

    return narrative, sql_statement, warnings_list, extra


def _sql_safe_readonly(sql: str) -> bool:
    s = sql.strip()
    if not s:
        return False
    if s.count(";") > 1 or (s.endswith(";") and s[:-1].count(";") > 0):
        return False
    s = s.rstrip(";").strip()
    u = s.upper()
    if u.startswith("WITH"):
        return True
    if u.startswith("SELECT"):
        forbidden = (
            " INSERT ",
            " UPDATE ",
            " DELETE ",
            " MERGE ",
            " DROP ",
            " CREATE ",
            " ALTER ",
            " TRUNCATE ",
            " GRANT ",
            " REVOKE ",
            " CALL ",
            " EXECUTE ",
        )
        padded = f" {u} "
        return not any(f in padded for f in forbidden)
    return False


def _execute_analyst_sql(sql: str, max_rows: int) -> List[Dict[str, Any]]:
    if not _sql_safe_readonly(sql):
        raise ValueError("SQL rechazado: solo se permiten consultas de lectura (SELECT/WITH).")
    conn = connect_snowflake()
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchmany(max_rows)
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, r)) for r in rows] if rows else []
        finally:
            cur.close()
    finally:
        conn.close()


def call_cortex_analyst_api(
    user_query: str,
    history: List[Dict[str, str]],
) -> Dict[str, Any]:
    url = f"{_rest_base_url()}/api/v2/cortex/analyst/message"
    payload: Dict[str, Any] = {
        "messages": _build_messages(user_query, history),
        **_semantic_payload(),
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST", headers=_auth_headers())
    try:
        with urlopen(req, timeout=int(os.getenv("CORTEX_ANALYST_TIMEOUT_SEC", "120"))) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"Cortex Analyst HTTP {e.code}: {err_body or e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Cortex Analyst red: {e.reason}") from e


def validate_cortex_analyst_config() -> Dict[str, Any]:
    """Comprueba variables mínimas sin llamar a la API (útil para /health)."""
    errors: List[str] = []
    rest = None
    try:
        rest = _rest_base_url()
    except Exception as e:
        errors.append(f"URL REST: {e}")
    try:
        _auth_headers()
    except Exception as e:
        errors.append(f"Token: {e}")
    try:
        _semantic_payload()
    except Exception as e:
        errors.append(f"Modelo semántico: {e}")
    return {"ok": not errors, "rest_base_url": rest, "errors": errors}


def process_with_cortex_analyst(
    query: str,
    history: List[Dict[str, str]],
) -> SynapseResponse:
    body = call_cortex_analyst_api(query, history)
    narrative, sql_statement, warnings, extra = _parse_analyst_body(body)

    if not narrative and not sql_statement:
        narrative = "Cortex Analyst no devolvió texto ni SQL. Revisa el modelo semántico y permisos."

    execute = os.getenv("SYNAPSE_ANALYST_EXECUTE_SQL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    raw_data: Optional[List[Dict[str, Any]]] = None
    render_type = "text"
    chart_config = None

    if execute and sql_statement:
        try:
            max_rows = int(os.getenv("SYNAPSE_ANALYST_MAX_ROWS", "500"))
            raw_data = _execute_analyst_sql(sql_statement, max_rows=max_rows)
            if raw_data:
                render_type = "table"
        except Exception as e:
            narrative = (
                f"{narrative}\n\n---\nNo se pudo ejecutar el SQL generado: {e}"
            ).strip()

    meta_extra = {**extra, "warnings": warnings}
    if sql_statement:
        meta_extra["generated_sql"] = sql_statement

    decision_meta = DecisionMeta(
        intent="cortex_analyst",
        confidence_score=0.75 if sql_statement else 0.4,
        data_freshness="unknown",
        guardrails=warnings or [],
        comparisons={
            "week_over_week": {"status": "unavailable", "reason": "Modo Cortex Analyst."},
            "vs_target": {"status": "unavailable", "reason": "Modo Cortex Analyst."},
            "vs_last_year": {"status": "unavailable", "reason": "Modo Cortex Analyst."},
        },
        actions=[],
    )

    return SynapseResponse(
        response_id=str(uuid.uuid4()),
        narrative=narrative,
        render_type=render_type,
        chart_config=chart_config,
        raw_data=raw_data,
        decision_meta=decision_meta,
        cortex_analyst=meta_extra,
    )
