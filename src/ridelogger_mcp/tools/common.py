"""Shared helpers for MCP tools."""

from __future__ import annotations

import json
from typing import Any

from ridelogger_mcp.bearer_auth import get_http_bearer_token
from ridelogger_mcp.errors import UpstreamApiError
from ridelogger_mcp.logging_setup import new_request_id


def require_token(access_token: str | None) -> str:
    new_request_id()
    bearer = get_http_bearer_token()
    if bearer:
        return bearer
    if not access_token or not str(access_token).strip():
        raise ValueError(
            "access_token is required (or send Authorization: Bearer on the MCP HTTP request). "
            "Call auth_login and pass access_token to tools, or configure the client with a Bearer token."
        )
    return str(access_token).strip()


def parse_json_object(label: str, raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        raise ValueError(f"{label} must be a non-empty JSON object string.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"{label} must be valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a JSON object at the top level.")
    return data


def parse_json_optional(label: str, raw: str | None) -> dict[str, Any] | None:
    if raw is None or not str(raw).strip():
        return None
    return parse_json_object(label, raw)


def tool_error(e: Exception) -> dict[str, Any]:
    if isinstance(e, UpstreamApiError):
        return {
            "ok": False,
            "error": {
                "type": "upstream_api",
                "status_code": e.status_code,
                "message": e.message,
            },
        }
    if isinstance(e, ValueError):
        return {"ok": False, "error": {"type": "validation", "message": str(e)}}
    return {
        "ok": False,
        "error": {"type": "internal", "message": str(e)},
    }

