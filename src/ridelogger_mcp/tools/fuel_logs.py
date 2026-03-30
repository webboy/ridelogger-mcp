"""Fuel log CRUD."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import (
    MONEY_LOGS_HINT,
    body_from_kwargs,
    compact_query_params,
    require_token,
    tool_error,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="fuel_logs_list",
        description=(
            "List fuel logs for a vehicle (GET /api/vehicles/{vehicle_id}/fuel_logs). "
            "Requires access_token or HTTP Bearer. Optional page for pagination. "
            "Filters (passed as query params to the API, combined with AND): date_from -> `from`, date_to -> `to` (Y-m-d, inclusive bounds), "
            "currency_id, fuel_type_id. "
            + MONEY_LOGS_HINT
        ),
    )
    async def fuel_logs_list(
        vehicle_id: int,
        page: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        currency_id: int | None = None,
        fuel_type_id: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            params = compact_query_params(
                {
                    "page": page,
                    "from": date_from,
                    "to": date_to,
                    "currency_id": currency_id,
                    "fuel_type_id": fuel_type_id,
                }
            )
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
            "Validated fields include FuelLogStoreRequest (amount, currency_id, unit, mileage, unit_id, fuel_type_id) "
            "plus date (Y-m-d) for the vehicle log row; optional unit_price, uuid. "
            + MONEY_LOGS_HINT
        ),
    )
    async def fuel_logs_create(
        vehicle_id: int,
        amount: float,
        currency_id: int,
        unit: float,
        mileage: int,
        unit_id: int,
        fuel_type_id: int,
        date: str,
        unit_price: float | None = None,
        uuid: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                amount=amount,
                currency_id=currency_id,
                unit=unit,
                mileage=mileage,
                unit_id=unit_id,
                fuel_type_id=fuel_type_id,
                date=date,
                unit_price=unit_price,
                uuid=uuid,
            )
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
            "Optional fields per FuelLogUpdateRequest (fuel row) plus vehicle log fields amount, currency_id, "
            "mileage, date. "
            + MONEY_LOGS_HINT
        ),
    )
    async def fuel_logs_update(
        vehicle_id: int,
        fuel_log_id: int,
        amount: float | None = None,
        currency_id: int | None = None,
        unit: float | None = None,
        mileage: int | None = None,
        unit_id: int | None = None,
        fuel_type_id: int | None = None,
        date: str | None = None,
        unit_price: float | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                amount=amount,
                currency_id=currency_id,
                unit=unit,
                mileage=mileage,
                unit_id=unit_id,
                fuel_type_id=fuel_type_id,
                date=date,
                unit_price=unit_price,
            )
            if not body:
                raise ValueError("Provide at least one field to update.")
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
