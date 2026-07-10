"""Auth/account tools that do not collect credentials."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import tool_error, tool_success, ToolToken

# ChatGPT only needs account *settings* to work with vehicle data (currency,
# units, country/language, active vehicle). Profile identity fields (names,
# email, phone, address, account tier/status, pivots) are intentionally
# excluded — returning them was flagged as unnecessary personal identifiers
# during OpenAI app review.
_AUTH_ME_SETTINGS_FIELDS = (
    "country_id",
    "currency_id",
    "language_id",
    "fuel_consumption_unit_id",
    "fuel_consumption_unit",
    "quantity_unit_id",
    "quantity_unit",
    "vehicle_id",
    "instance",
)


def _settings_only(data: Any) -> Any:
    """Reduce the /auth/me payload to the settings allowlist."""
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return {**data, "data": _settings_only(data["data"])}
    if not isinstance(data, dict):
        return data
    return {k: data[k] for k in _AUTH_ME_SETTINGS_FIELDS if k in data}


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="auth_me",
        annotations=get_annotations("auth_me"),
        description=(
            "[READ] Current account settings (GET /api/auth/me). "
            "Requires OAuth/Bearer authorization. "
            "Returns only settings needed for vehicle workflows: `currency_id` — the user's preferred "
            "display/reporting currency — plus country, language, fuel consumption unit, quantity unit, "
            "and the currently selected `vehicle_id`. No profile identity fields are returned. "
            "Use this together with monetary log tools: each log row can be in a different currency, "
            "so read `currency_id` from `auth_me`, fetch `ridelogger://reference/currencies`, "
            "convert row amounts to one currency, then aggregate. "
            "Errors: 401 if token missing/expired."
        ),
    )
    async def auth_me(token: str = ToolToken) -> dict[str, Any]:
        try:
            st = get_state()
            data = await st.client.request_json("GET", "/auth/me", token=token)
            return tool_success(_settings_only(data))
        except Exception as e:
            return tool_error(e)
