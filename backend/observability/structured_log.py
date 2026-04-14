"""Logging estructurado mínimo (level, module, function)."""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping

_logger = logging.getLogger("synapse")


def structured_log(
    level: str,
    *,
    module: str,
    function: str,
    message: str,
    fields: Mapping[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "level": level.upper(),
        "module": module,
        "function": function,
        "message": message,
    }
    if fields:
        payload.update(dict(fields))
    line = json.dumps(payload, default=str)
    lvl = getattr(logging, level.upper(), logging.INFO)
    _logger.log(lvl, line)
