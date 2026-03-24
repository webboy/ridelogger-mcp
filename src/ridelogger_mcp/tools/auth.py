"""Auth tools: login (no token), me (token)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.logging_setup import new_request_id
from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="auth_login",
        description=(
            "Authenticate with email and password against RideLogger API. "
            "Does NOT require access_token. "
            "Returns JSON with access_token, refresh_token, expires_in — use access_token for all other tools. "
            "After login, call `auth_me` to read user settings (including preferred `currency_id` for interpreting "
            "multi-currency expense/fuel/service logs). "
            "On failure: 422 invalid credentials, 400 validation errors."
        ),
    )
    async def auth_login(
        email: str,
        password: str,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            new_request_id()
            st = get_state()
            body: dict[str, Any] = {"email": email, "password": password}
            if device_id:
                body["device_id"] = device_id
            data = await st.client.request_json(
                "POST",
                "/auth/login",
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="auth_me",
        description=(
            "Current user profile and account settings (GET /api/auth/me). "
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
