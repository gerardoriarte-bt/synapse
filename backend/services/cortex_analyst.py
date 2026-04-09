"""
Cliente Cortex Analyst (REST): NL → SQL + texto usando modelo semántico / vista semántica en Snowflake.

Documentación: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api
Auth (PAT): https://docs.snowflake.com/en/developer-guide/sql-api/authenticating
"""
from __future__ import annotations

import json
import os
import uuid
import calendar
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from models.synapse import DecisionMeta, SynapseResponse
from services.cortex_http import auth_headers, rest_base_url
from services.snowflake import connect_snowflake


def _cortex_api_mode() -> str:
    return os.getenv("CORTEX_API_MODE", "analyst").strip().lower()


def _endpoint_path() -> str:
    explicit = os.getenv("CORTEX_API_ENDPOINT", "").strip()
    if explicit:
        return explicit if explicit.startswith("/") else f"/{explicit}"
    if _cortex_api_mode() == "agent_run":
        return "/api/v2/cortex/agent:run"
    return "/api/v2/cortex/analyst/message"


def _build_messages(user_query: str, history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Cortex Analyst: prioriza pregunta actual y aplica guardrails de periodo explícito."""
    period_hint = _explicit_period_hint(user_query)
    strict = (
        "INSTRUCCIONES OBLIGATORIAS:\n"
        "- Responde exactamente la pregunta del usuario.\n"
        "- Idioma de salida: español (es-ES/es-LATAM), claro y profesional.\n"
        "- No uses introducciones en inglés ni frases de sistema (ej.: 'This is our interpretation...').\n"
        "- Si el usuario define periodo (mes/año/rango), filtra SOLO ese periodo.\n"
        "- No amplíes fechas ni agregues periodos adicionales.\n"
        "- Para periodos de campañas, aplica el filtro temporal sobre la columna de fecha del modelo.\n"
    )
    if period_hint:
        strict += f"- {period_hint}\n"

    include_history = os.getenv("CORTEX_INCLUDE_HISTORY", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if not include_history or not history:
        text = f"{strict}\nPREGUNTA ACTUAL:\n{user_query}"
        return [{"role": "user", "content": [{"type": "text", "text": text}]}]

    lines = []
    for h in history[-5:]:
        q = (h.get("q") or "")[:800]
        a = (h.get("a") or "")[:1200]
        lines.append(f"Usuario (antes): {q}\nAnalista (antes): {a}")
    block = "\n\n---\n\n".join(lines)
    text = (
        f"{strict}\nContexto de conversación reciente:\n{block}\n\n---\n\nPregunta actual:\n{user_query}"
    )
    return [{"role": "user", "content": [{"type": "text", "text": text}]}]


def _parse_date_token(token: str) -> Optional[date]:
    s = (token or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _month_name_map() -> Dict[str, int]:
    return {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }


def _month_bounds(year: int, month: int) -> Tuple[date, date]:
    end_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, end_day)


def _add_months(d: date, delta: int) -> date:
    month_idx = d.year * 12 + (d.month - 1) + delta
    y = month_idx // 12
    m = month_idx % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def _quarter_bounds(year: int, q: int) -> Tuple[date, date]:
    start_month = 1 + (q - 1) * 3
    start = date(year, start_month, 1)
    end_month = start_month + 2
    end_day = calendar.monthrange(year, end_month)[1]
    return start, date(year, end_month, end_day)


def _infer_period_bounds(query: str, today: Optional[date] = None) -> Optional[Tuple[date, date, str]]:
    q = (query or "").lower()
    now = today or datetime.utcnow().date()

    # 1) Rangos explícitos entre dos fechas
    date_pat = r"(20\d{2}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2}|20\d{2}/\d{2}/\d{2})"
    m = re.search(rf"{date_pat}.*?{date_pat}", q)
    if m:
        d1 = _parse_date_token(m.group(1))
        d2 = _parse_date_token(m.group(2))
        if d1 and d2:
            start, end = (d1, d2) if d1 <= d2 else (d2, d1)
            return start, end, f"rango explícito {start} a {end}"

    # 2) Mes + año (diciembre 2025 / 2025 diciembre)
    for name, month in _month_name_map().items():
        m1 = re.search(rf"\b{name}\b\s*(?:de\s*)?(20\d{{2}})\b", q)
        m2 = re.search(rf"\b(20\d{{2}})\b\s*(?:de\s*)?\b{name}\b", q)
        year = int(m1.group(1)) if m1 else (int(m2.group(1)) if m2 else None)
        if year:
            start, end = _month_bounds(year, month)
            return start, end, f"{name} {year}"

    # 3) Trimestre (Q1 2025 / trimestre 1 2025 / primer trimestre 2025)
    qm = re.search(r"\bq([1-4])\s*(20\d{2})\b", q)
    if not qm:
        qm = re.search(r"\btrimestre\s*([1-4])\s*(?:de\s*)?(20\d{2})\b", q)
    if not qm:
        ord_map = {"primer": 1, "primero": 1, "segundo": 2, "tercer": 3, "tercero": 3, "cuarto": 4}
        for k, v in ord_map.items():
            mo = re.search(rf"\b{k}\s+trimestre\s*(?:de\s*)?(20\d{{2}})\b", q)
            if mo:
                qm = (v, int(mo.group(1)))
                break
    if qm:
        if isinstance(qm, tuple):
            qn, year = qm
        else:
            qn, year = int(qm.group(1)), int(qm.group(2))
        start, end = _quarter_bounds(year, int(qn))
        return start, end, f"Q{qn} {year}"

    # 4) Semestre
    sm = re.search(r"\b(1|2)\s*semestre\s*(?:de\s*)?(20\d{2})\b", q)
    if sm:
        sem, year = int(sm.group(1)), int(sm.group(2))
        if sem == 1:
            return date(year, 1, 1), date(year, 6, 30), f"S1 {year}"
        return date(year, 7, 1), date(year, 12, 31), f"S2 {year}"
    if "primer semestre" in q or "1er semestre" in q:
        y = re.search(r"(20\d{2})", q)
        if y:
            year = int(y.group(1))
            return date(year, 1, 1), date(year, 6, 30), f"S1 {year}"
    if "segundo semestre" in q:
        y = re.search(r"(20\d{2})", q)
        if y:
            year = int(y.group(1))
            return date(year, 7, 1), date(year, 12, 31), f"S2 {year}"

    # 5) Relativos
    m = re.search(r"\b(?:ultim[oa]s?|last)\s+(\d{1,3})\s+(d[ií]as?|days?)\b", q)
    if m:
        n = max(1, int(m.group(1)))
        return now - timedelta(days=n - 1), now, f"últimos {n} días"
    m = re.search(r"\b(?:ultim[oa]s?|last)\s+(\d{1,3})\s+(semanas?|weeks?)\b", q)
    if m:
        n = max(1, int(m.group(1)))
        return now - timedelta(days=(7 * n) - 1), now, f"últimas {n} semanas"
    m = re.search(r"\b(?:ultim[oa]s?|last)\s+(\d{1,3})\s+(meses?|months?)\b", q)
    if m:
        n = max(1, int(m.group(1)))
        start = _add_months(date(now.year, now.month, 1), -(n - 1))
        return start, now, f"últimos {n} meses"

    # 6) Anclas comunes
    if "esta semana" in q or "this week" in q or "wtd" in q:
        start = now - timedelta(days=now.weekday())
        return start, now, "semana actual"
    if "semana pasada" in q or "last week" in q:
        this_start = now - timedelta(days=now.weekday())
        start = this_start - timedelta(days=7)
        end = this_start - timedelta(days=1)
        return start, end, "semana pasada"
    if "este mes" in q or "this month" in q or "mtd" in q:
        return date(now.year, now.month, 1), now, "mes actual"
    if "mes pasado" in q or "last month" in q:
        prev_anchor = _add_months(date(now.year, now.month, 1), -1)
        start, end = _month_bounds(prev_anchor.year, prev_anchor.month)
        return start, end, "mes pasado"
    if "este año" in q or "this year" in q or "ytd" in q:
        return date(now.year, 1, 1), now, "año actual"
    if "año pasado" in q or "last year" in q:
        y = now.year - 1
        return date(y, 1, 1), date(y, 12, 31), "año pasado"
    if "este trimestre" in q or "this quarter" in q or "qtd" in q:
        cq = ((now.month - 1) // 3) + 1
        start, _ = _quarter_bounds(now.year, cq)
        return start, now, "trimestre actual"
    if "trimestre pasado" in q or "last quarter" in q:
        cq = ((now.month - 1) // 3) + 1
        if cq == 1:
            y, qn = now.year - 1, 4
        else:
            y, qn = now.year, cq - 1
        start, end = _quarter_bounds(y, qn)
        return start, end, "trimestre pasado"

    # 7) Año puntual (en 2025 / año 2025)
    years = sorted({int(x) for x in re.findall(r"\b(20\d{2})\b", q)})
    if len(years) == 1 and any(k in q for k in ("en ", "año", "year", "durante")):
        y = years[0]
        return date(y, 1, 1), date(y, 12, 31), f"año {y}"
    if re.search(r"\b(20\d{2})\s*(?:a|to|-)\s*(20\d{2})\b", q):
        m = re.search(r"\b(20\d{2})\s*(?:a|to|-)\s*(20\d{2})\b", q)
        if m:
            y1, y2 = int(m.group(1)), int(m.group(2))
            start_y, end_y = (y1, y2) if y1 <= y2 else (y2, y1)
            return date(start_y, 1, 1), date(end_y, 12, 31), f"{start_y} a {end_y}"
    return None


def _explicit_period_hint(query: str) -> Optional[str]:
    inferred = _infer_period_bounds(query)
    if not inferred:
        return None
    start, end, label = inferred
    return (
        f"Periodo requerido detectado ({label}): {start} a {end}. "
        f"Aplica filtro temporal estricto en SQL: DATE >= '{start}' AND DATE <= '{end}'."
    )


def _merge_agent_run_config_extra() -> Dict[str, Any]:
    extra = os.getenv("CORTEX_AGENT_RUN_CONFIG_JSON", "").strip()
    if not extra:
        return {}
    try:
        parsed = json.loads(extra)
    except json.JSONDecodeError as e:
        raise ValueError(f"CORTEX_AGENT_RUN_CONFIG_JSON no es JSON válido: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError("CORTEX_AGENT_RUN_CONFIG_JSON debe ser un objeto JSON.")
    return parsed


def _agent_run_payload(
    user_query: str,
    history: List[Dict[str, str]],
    *,
    agent_thread_id: Optional[int] = None,
    agent_parent_message_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Con hilo Cortex (thread_id + parent_message_id): un solo mensaje usuario por request
    (el historial vive en Snowflake). Sin hilo: historial compactado en el texto.
    """
    extra_cfg = _merge_agent_run_config_extra()
    if agent_thread_id is not None and agent_parent_message_id is not None:
        payload: Dict[str, Any] = {**extra_cfg}
        payload["thread_id"] = agent_thread_id
        payload["parent_message_id"] = agent_parent_message_id
        payload["messages"] = [
            {"role": "user", "content": [{"type": "text", "text": user_query}]},
        ]
        payload["stream"] = False
        return payload

    payload = {
        **extra_cfg,
        "messages": _build_messages(user_query, history),
        "stream": False,
    }
    payload["messages"] = _build_messages(user_query, history)
    payload["stream"] = False
    thread_id = os.getenv("CORTEX_AGENT_THREAD_ID", "").strip()
    parent_message_id = os.getenv("CORTEX_AGENT_PARENT_MESSAGE_ID", "").strip()
    if thread_id and parent_message_id:
        payload["thread_id"] = int(thread_id)
        payload["parent_message_id"] = int(parent_message_id)
    return payload


def _extract_assistant_message_id_from_agent_response(body: Dict[str, Any]) -> Optional[int]:
    meta = body.get("metadata")
    if isinstance(meta, dict):
        mid = meta.get("message_id")
        if isinstance(mid, int):
            return mid
    mid = body.get("message_id")
    if isinstance(mid, int):
        return mid
    msg = body.get("message")
    if isinstance(msg, dict):
        mid = msg.get("message_id")
        if isinstance(mid, int):
            return mid
        nested = msg.get("metadata")
        if isinstance(nested, dict) and isinstance(nested.get("message_id"), int):
            return nested["message_id"]
    return None


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
            # En modo passthrough no inyectamos sugerencias al texto principal.
            pass

    narrative = "\n\n".join(p for p in narrative_parts if p).strip()
    narrative = _sanitize_english_preamble(narrative)
    narrative = _sanitize_brand_terms(narrative)
    warnings_list: List[str] = []
    for w in body.get("warnings") or []:
        if isinstance(w, dict) and w.get("message"):
            warnings_list.append(str(w["message"]))

    if body.get("semantic_model_selection") is not None:
        extra["semantic_model_selection"] = body["semantic_model_selection"]
    if body.get("response_metadata"):
        extra["response_metadata"] = body["response_metadata"]
    if body.get("request_id"):
        extra["request_id"] = body["request_id"]

    return narrative, sql_statement, warnings_list, extra


def _sanitize_english_preamble(text: str) -> str:
    """
    Algunas respuestas de Analyst incluyen una cabecera en inglés no solicitada.
    La removemos de forma conservadora para mantener salida en español.
    """
    if not text:
        return text
    cleaned = re.sub(
        r"^\s*this is our interpretation of your question:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Si quedó una línea en inglés tipo "Show ...", la mantenemos para no perder semántica,
    # pero eliminamos doble salto al inicio.
    return cleaned.lstrip()


def _sanitize_brand_terms(text: str) -> str:
    """Evita mencionar proveedores de datos; marca visible al cliente = Synapse."""
    if not text:
        return text
    out = re.sub(r"\bsnowflake\b", "Synapse", text, flags=re.IGNORECASE)
    return out


def _parse_agent_run_body(body: Dict[str, Any]) -> Tuple[str, Optional[str], List[str], Dict[str, Any]]:
    """
    Parser tolerante para Agent Run.
    La estructura exacta puede variar por versión/modelo, así que extraemos texto/SQL de forma flexible.
    """
    text_parts: List[str] = []
    sql_statement: Optional[str] = None
    warnings_list: List[str] = []
    extra: Dict[str, Any] = {}

    def walk(node: Any) -> None:
        nonlocal sql_statement
        if isinstance(node, dict):
            ntype = str(node.get("type") or "").lower()
            if ntype == "text" and node.get("text"):
                text_parts.append(str(node.get("text")))
            if ntype == "sql" and node.get("statement") and sql_statement is None:
                sql_statement = str(node.get("statement"))
            if node.get("warnings") and isinstance(node.get("warnings"), list):
                for w in node["warnings"]:
                    if isinstance(w, dict) and w.get("message"):
                        warnings_list.append(str(w["message"]))
            if "request_id" in node:
                extra["request_id"] = node.get("request_id")
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for i in node:
                walk(i)
        elif isinstance(node, str):
            pass

    walk(body)
    narrative = "\n\n".join([p.strip() for p in text_parts if p and p.strip()]).strip()
    if not narrative:
        # Fallback para respuestas donde el texto viene en campos alternos.
        for key in ("response", "answer", "output_text"):
            val = body.get(key)
            if isinstance(val, str) and val.strip():
                narrative = val.strip()
                break
    narrative = _sanitize_english_preamble(narrative)
    narrative = _sanitize_brand_terms(narrative)
    if body.get("response_metadata"):
        extra["response_metadata"] = body.get("response_metadata")
    if body.get("thread_id") is not None:
        extra["thread_id"] = body.get("thread_id")
    if body.get("parent_message_id") is not None:
        extra["parent_message_id"] = body.get("parent_message_id")
    return narrative, sql_statement, list(dict.fromkeys(warnings_list)), extra


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
            if max_rows and max_rows > 0:
                rows = cur.fetchmany(max_rows)
            else:
                rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, r)) for r in rows] if rows else []
        finally:
            cur.close()
    finally:
        conn.close()


def call_cortex_analyst_api(
    user_query: str,
    history: List[Dict[str, str]],
    *,
    agent_thread_id: Optional[int] = None,
    agent_parent_message_id: Optional[int] = None,
) -> Dict[str, Any]:
    mode = _cortex_api_mode()
    url = f"{rest_base_url()}{_endpoint_path()}"
    if mode == "agent_run":
        payload = _agent_run_payload(
            user_query,
            history,
            agent_thread_id=agent_thread_id,
            agent_parent_message_id=agent_parent_message_id,
        )
    else:
        payload = {
            "messages": _build_messages(user_query, history),
            **_semantic_payload(),
            "stream": False,
        }
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST", headers=auth_headers())
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
        rest = rest_base_url()
    except Exception as e:
        errors.append(f"URL REST: {e}")
    try:
        auth_headers()
    except Exception as e:
        errors.append(f"Token: {e}")
    mode = _cortex_api_mode()
    if mode == "agent_run":
        extra = os.getenv("CORTEX_AGENT_RUN_CONFIG_JSON", "").strip()
        if extra:
            try:
                parsed = json.loads(extra)
                if not isinstance(parsed, dict):
                    errors.append("CORTEX_AGENT_RUN_CONFIG_JSON debe ser objeto JSON.")
            except Exception as e:
                errors.append(f"Agent run config: {e}")
    else:
        try:
            _semantic_payload()
        except Exception as e:
            errors.append(f"Modelo semántico: {e}")
    return {
        "ok": not errors,
        "rest_base_url": rest,
        "mode": mode,
        "endpoint": _endpoint_path(),
        "errors": errors,
    }


def process_with_cortex_analyst(
    query: str,
    history: List[Dict[str, str]],
    *,
    agent_thread_id: Optional[int] = None,
    agent_parent_message_id: Optional[int] = None,
    conversation_id: Optional[str] = None,
) -> SynapseResponse:
    body = call_cortex_analyst_api(
        query,
        history,
        agent_thread_id=agent_thread_id,
        agent_parent_message_id=agent_parent_message_id,
    )
    mode = _cortex_api_mode()
    if mode == "agent_run":
        narrative, sql_statement, warnings, extra = _parse_agent_run_body(body)
    else:
        narrative, sql_statement, warnings, extra = _parse_analyst_body(body)

    if not narrative and not sql_statement:
        narrative = (
            "El endpoint de Cortex no devolvió texto ni SQL. "
            "Revisa configuración de Agent/Analyst y permisos."
        )

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
            # 0 = sin límite (traer todo lo que devuelva Snowflake para la consulta)
            max_rows = int(os.getenv("SYNAPSE_ANALYST_MAX_ROWS", "0"))
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
    if raw_data is not None:
        meta_extra["returned_rows"] = len(raw_data)

    if (
        mode == "agent_run"
        and agent_thread_id is not None
        and agent_parent_message_id is not None
    ):
        last_mid = _extract_assistant_message_id_from_agent_response(body)
        if last_mid is None:
            from services.cortex_threads import last_assistant_message_id

            last_mid = last_assistant_message_id(agent_thread_id)
        if last_mid is not None:
            meta_extra["last_assistant_message_id"] = last_mid

    decision_meta = DecisionMeta(
        intent="cortex_agent" if mode == "agent_run" else "cortex_analyst",
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
        conversation_id=conversation_id,
    )
