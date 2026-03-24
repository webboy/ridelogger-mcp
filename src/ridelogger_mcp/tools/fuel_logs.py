"""Fuel log CRUD."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import (
    MONEY_LOGS_HINT,
    parse_json_object,
    require_token,
    tool_error,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="fuel_logs_list",
        description=(
            "List fuel logs for a vehicle (GET /api/vehicles/{vehicle_id}/fuel_logs). "
            "Requires access_token or HTTP Bearer. Optional page for pagination. "
            + MONEY_LOGS_HINT
        ),
    )
    async def fuel_logs_list(
        vehicle_id: int,
        page: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            params = {"page": page} if page is not None else None
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/fuel_logs",
                token=token,
                params=params,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="fuel_logs_create",
        description=(
            "Create fuel log (POST .../fuel_logs). Requires access_token or HTTP Bearer. "
            "body_json: amount, currency_id, unit, unit_id, fuel_type_id, mileage, date (Y-m-d); "
            "optional unit_price, uuid. "
            "Monetary fields use the currency from `currency_id`. For totals across mixed-currency fills, use "
            "`auth_me` + reference currencies — see fuel_logs_list hint."
        ),
    )
    async def fuel_logs_create(
        vehicle_id: int,
        body_json: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = parse_json_object("body_json", body_json)
            st = get_state()
            data = await st.client.request_json(
                "POST",
                f"/vehicles/{vehicle_id}/fuel_logs",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="fuel_logs_get",
        description=(
            "Get one fuel log (GET .../fuel_logs/{fuel_log_id}). Requires access_token or HTTP Bearer. "
            + MONEY_LOGS_HINT
        ),
    )
    async def fuel_logs_get(
        vehicle_id: int,
        fuel_log_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/fuel_logs/{fuel_log_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="fuel_logs_update",
        description=(
            "Update fuel log (PUT .../fuel_logs/{fuel_log_id}). Requires access_token or HTTP Bearer. "
            "body_json: fields per API FuelLogUpdateRequest (including `currency_id` when changing currency). "
            "See fuel_logs_list for multi-currency aggregation."
        ),
    )
    async def fuel_logs_update(
        vehicle_id: int,
        fuel_log_id: int,
        body_json: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = parse_json_object("body_json", body_json)
            st = get_state()
            data = await st.client.request_json(
                "PUT",
                f"/vehicles/{vehicle_id}/fuel_logs/{fuel_log_id}",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="fuel_logs_delete",
        description=(
            "Delete fuel log (DELETE .../fuel_logs/{fuel_log_id}). Requires access_token or HTTP Bearer."
        ),
    )
    async def fuel_logs_delete(
        vehicle_id: int,
        fuel_log_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/fuel_logs/{fuel_log_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
