"""Auth/account tools that do not collect credentials."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="auth_me",
        annotations=get_annotations("auth_me"),
        description=(
            "[READ] Current user profile and account settings (GET /api/auth/me). "
            "Requires access_token or HTTP Authorization: Bearer. "
            "Response includes `currency_id` — the user's preferred display/reporting currency — plus country, "
            "fuel consumption unit, name, email, etc. Use this together with monetary log tools: each log row can be "
            "in a different currency, so read `currency_id` from `auth_me`, fetch `ridelogger://reference/currencies`, "
            "convert row amounts to one currency, then aggregate. "
            "Errors: 401 if token missing/expired."
        ),
    )
    async def auth_me(access_token: str | None = None) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json("GET", "/auth/me", token=token)
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
