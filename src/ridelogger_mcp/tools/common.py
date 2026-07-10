"""Shared helpers for MCP tools."""

from __future__ import annotations

import json
from types import TracebackType
from typing import Any

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from uncalled_for import Dependency

from ridelogger_mcp.errors import UpstreamApiError
from ridelogger_mcp.logging_setup import new_request_id

_AUTH_REQUIRED_MSG = (
    "Authorization is required. Configure the MCP client OAuth/Bearer connection and retry."
)

# Appended to tool descriptions for endpoints that return monetary log rows (fuel, service, expense, …).
MONEY_LOGS_HINT = (
    "Money: logs are multi-currency — each row has its own `currency_id`, and `amount` / `total` are in that row's currency. "
    "Do not sum raw numbers across rows without converting. Call `auth_me` for the user's preferred `currency_id` "
    "(account settings), use MCP resource `ridelogger://reference/currencies` (or GET /api/currencies) for codes and "
    "exchange `value` fields, then normalize every row to one target currency before aggregating or comparing totals."
)

# Embedded reference objects in vehicle responses (API v1.3+).
VEHICLE_REFS_HINT = (
    "Each vehicle includes resolved reference objects alongside raw IDs: "
    "vehicle_type {id,name}, fuel_type {id,name}, mileage_unit {id,name,unit,ratio}, "
    "steering_side {id,name}, "
    "fuel_unit {id,name,unit,units,ratio}, vehicle_make_info {id,name}, vehicle_model_info {id,name}. "
    "Use these instead of cross-referencing IDs with ridelogger://reference/* resources."
)

# Embedded reference objects in log responses (API v1.3+).
LOG_REFS_HINT = (
    "Each log row includes resolved reference objects alongside raw IDs: "
    "fuel_type {id,name} (fuel logs), charge_type {id,name} (charge logs), service_type {id,name} (service logs), "
    "expense_type {id,name} (expense logs), unit_label (fuel unit name string), energy_unit_label (charge logs), "
    "currency_info {id,code,name,symbol}. Null when the field does not apply to the log type."
)

_MINIMIZED_KEY_NAMES = {
    "access_token",
    "address",
    "api_token",
    "avatar",
    "created_at",
    "created_by",
    "deleted_at",
    "device_id",
    "email",
    "first_name",
    "invited_by_user_id",
    "ip",
    "last_name",
    "marketing_consent",
    "owner_id",
    "password",
    "phone",
    "premium",
    "refresh_token",
    "request_id",
    "run_id",
    "secret",
    "session_id",
    "token",
    "trace_id",
    "unsubscribed_at",
    "updated_at",
    "updated_by",
    "user_agent",
    "user_id",
    "username",
    "uuid",
}

_MINIMIZED_KEY_SUFFIXES = (
    "_token",
    "_secret",
)


def require_token(access_token: str | None) -> str:
    new_request_id()
    from ridelogger_mcp import bearer_auth

    bearer = bearer_auth.get_http_bearer_token()
    if bearer:
        return bearer
    if not access_token or not str(access_token).strip():
        raise ValueError(_AUTH_REQUIRED_MSG)
    return str(access_token).strip()


class _RideLoggerToolToken(Dependency[str]):
    """Inject HTTP Bearer token validated by RideLoggerBearerMiddleware."""

    async def __aenter__(self) -> str:
        new_request_id()
        from ridelogger_mcp import bearer_auth

        bearer = bearer_auth.get_http_bearer_token()
        if bearer:
            return bearer
        raise ToolError(_AUTH_REQUIRED_MSG)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


ToolToken = Depends(_RideLoggerToolToken)


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


def body_from_kwargs(**kwargs: Any) -> dict[str, Any]:
    """Build JSON body for API calls: omit keys whose value is None (optional fields omitted)."""
    return {k: v for k, v in kwargs.items() if v is not None}


def compact_query_params(values: dict[str, Any]) -> dict[str, Any] | None:
    """Build GET query dict: drop None values; return None if empty (caller may pass through to HTTP client)."""
    out = {k: v for k, v in values.items() if v is not None}
    return out or None


def sanitize_tool_data(data: Any) -> Any:
    """Remove personal/internal identifiers from MCP tool responses.

    The API is broader than ChatGPT needs. MCP responses should keep useful
    domain fields and record ids needed for follow-up tool calls, while dropping
    user identifiers, auth/session/debug fields, sync UUIDs, and internal
    timestamps that are not necessary for answering user requests.
    """
    if isinstance(data, list):
        return [sanitize_tool_data(item) for item in data]
    if not isinstance(data, dict):
        return data

    out: dict[str, Any] = {}
    for key, value in data.items():
        normalized_key = str(key).lower()
        if normalized_key in _MINIMIZED_KEY_NAMES:
            continue
        if any(normalized_key.endswith(suffix) for suffix in _MINIMIZED_KEY_SUFFIXES):
            continue
        out[key] = sanitize_tool_data(value)
    return out


def tool_success(data: Any = None) -> dict[str, Any]:
    return {"ok": True, "data": sanitize_tool_data(data)}


def _redact_sensitive_error_message(message: str) -> str:
    lowered = message.lower()
    if any(
        marker in lowered
        for marker in ("download_url", "token=", "sig=", "file_id=file_")
    ):
        return "Invalid file source or file download failed."
    if "https://" in lowered or "http://" in lowered:
        return "Invalid file source or file download failed."
    return message


def tool_error(e: Exception) -> dict[str, Any]:
    if isinstance(e, UpstreamApiError):
        err_obj: dict[str, Any] = {
            "type": "upstream_api",
            "status_code": e.status_code,
            "message": e.message,
        }
        body = e.body
        if isinstance(body, dict):
            field_errors = body.get("errors")
            if isinstance(field_errors, dict) and field_errors:
                err_obj["errors"] = field_errors
        return {"ok": False, "error": err_obj}
    if isinstance(e, ValueError):
        return {
            "ok": False,
            "error": {
                "type": "validation",
                "message": _redact_sensitive_error_message(str(e)),
            },
        }
    return {
        "ok": False,
        "error": {"type": "internal", "message": str(e)},
    }
