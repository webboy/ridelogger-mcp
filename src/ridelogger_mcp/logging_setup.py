"""Structured logging with request id (no token logging)."""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    rid = str(uuid.uuid4())
    request_id_ctx.set(rid)
    return rid


def get_request_id() -> str | None:
    return request_id_ctx.get()


def setup_logging(
    level: str = "INFO",
    *,
    verbose_mcp_library_logs: bool = False,
) -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s rid=%(request_id)s %(message)s",
            stream=sys.stdout,
        )
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = old_factory(*args, **kwargs)
            record.request_id = get_request_id() or "-"
            return record

        logging.setLogRecordFactory(record_factory)

    _apply_third_party_log_levels(verbose_mcp_library_logs)


def _apply_third_party_log_levels(verbose_mcp_library_logs: bool) -> None:
    """Reduce noise: Cursor repeatedly calls ListTools/ListPrompts/ListResources over HTTP."""
    noisy_level = logging.INFO if verbose_mcp_library_logs else logging.WARNING
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(noisy_level)
    logging.getLogger("mcp.server").setLevel(noisy_level)
    logging.getLogger("uvicorn.access").setLevel(noisy_level)
