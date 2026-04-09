"""REST helpers para hilos de Cortex Agent (POST /api/v2/cortex/threads, GET describe)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.cortex_http import auth_headers, rest_base_url


def create_cortex_thread() -> int:
    """Crea un hilo nuevo; la API devuelve el thread id (JSON number o string)."""
    url = f"{rest_base_url()}/api/v2/cortex/threads"
    origin = os.getenv("CORTEX_ORIGIN_APPLICATION", "synapse").strip()[:16] or "synapse"
    payload: Dict[str, Any] = {"origin_application": origin}
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST", headers=auth_headers())
    timeout = int(os.getenv("CORTEX_THREAD_HTTP_TIMEOUT_SEC", "30"))
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"Cortex threads HTTP {e.code}: {err_body or e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Cortex threads red: {e.reason}") from e

    if isinstance(parsed, int):
        return parsed
    if isinstance(parsed, str) and parsed.strip().isdigit():
        return int(parsed.strip())
    raise RuntimeError(f"Respuesta inesperada al crear thread: {raw[:500]}")


def describe_thread(thread_id: int, page_size: int = 100) -> Dict[str, Any]:
    url = f"{rest_base_url()}/api/v2/cortex/threads/{thread_id}?page_size={page_size}"
    req = Request(url, method="GET", headers=auth_headers())
    timeout = int(os.getenv("CORTEX_THREAD_HTTP_TIMEOUT_SEC", "30"))
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"Cortex describe thread HTTP {e.code}: {err_body or e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Cortex describe thread red: {e.reason}") from e


def last_assistant_message_id(thread_id: int) -> Optional[int]:
    """Último message_id con role assistant en el hilo (para parent_message_id siguiente)."""
    data = describe_thread(thread_id)
    messages = data.get("messages") or []
    candidates: list[int] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        if str(m.get("role") or "").lower() != "assistant":
            continue
        mid = m.get("message_id")
        if isinstance(mid, int):
            candidates.append(mid)
    if not candidates:
        return None
    return max(candidates)
