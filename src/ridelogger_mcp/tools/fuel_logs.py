"""Fuel log CRUD."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import (
    LOG_REFS_HINT,
    MONEY_LOGS_HINT,
    ToolToken,
    body_from_kwargs,
    compact_query_params,
    tool_error,
    tool_success,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="fuel_logs_list",
        annotations=get_annotations("fuel_logs_list"),
        description=(
            "[READ] List fuel logs for a vehicle (GET /api/vehicles/{vehicle_id}/fuel_logs). "
            "Requires OAuth/Bearer authorization. Optional page for pagination. "
            "Filters (passed as query params to the API, combined with AND): date_from -> `from`, date_to -> `to` (Y-m-d, inclusive bounds), "
            "currency_id, fuel_type_id. "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def fuel_logs_list(
        vehicle_id: int,
        page: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        currency_id: int | None = None,
        fuel_type_id: int | None = None,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="fuel_logs_create",
        annotations=get_annotations("fuel_logs_create"),
        description=(
            "[WRITE] Create fuel log (POST .../fuel_logs). Requires OAuth/Bearer authorization. "
            "Validated fields include FuelLogStoreRequest (amount, currency_id, unit, mileage, fuel_type_id) "
            "plus date (Y-m-d) for the vehicle log row; optional unit_price, uuid. "
            "Optional unit_id (fuel quantity unit — `GET /api/fuel_units`): when omitted, API defaults from the "
            "user's quantity preference then vehicle fuel unit. "
            "Optional geolocation: business_name, business_address, latitude, longitude; rating (1-5 stars, optional). "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def fuel_logs_create(
        vehicle_id: int,
        amount: float,
        currency_id: int,
        unit: float,
        mileage: int,
        fuel_type_id: int,
        date: str,
        unit_id: int | None = None,
        unit_price: float | None = None,
        uuid: str | None = None,
        business_name: str | None = None,
        business_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        rating: int | None = None,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
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
                business_name=business_name,
                business_address=business_address,
                latitude=latitude,
                longitude=longitude,
                rating=rating,
            )
            st = get_state()
            data = await st.client.request_json(
                "POST",
                f"/vehicles/{vehicle_id}/fuel_logs",
                token=token,
                json_body=body,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="fuel_logs_get",
        annotations=get_annotations("fuel_logs_get"),
        description=(
            "[READ] Get one fuel log (GET .../fuel_logs/{fuel_log_id}). Requires OAuth/Bearer authorization. "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def fuel_logs_get(
        vehicle_id: int,
        fuel_log_id: int,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/fuel_logs/{fuel_log_id}",
                token=token,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="fuel_logs_update",
        annotations=get_annotations("fuel_logs_update"),
        description=(
            "[WRITE] Update fuel log (PUT .../fuel_logs/{fuel_log_id}). Requires OAuth/Bearer authorization. "
            "Optional fields per FuelLogUpdateRequest (fuel row) plus vehicle log fields amount, currency_id, "
            "mileage, date. "
            "Optional geolocation: business_name, business_address, latitude, longitude; rating (1-5 stars, optional). "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
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
        business_name: str | None = None,
        business_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        rating: int | None = None,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
            body = body_from_kwargs(
                amount=amount,
                currency_id=currency_id,
                unit=unit,
                mileage=mileage,
                unit_id=unit_id,
                fuel_type_id=fuel_type_id,
                date=date,
                unit_price=unit_price,
                business_name=business_name,
                business_address=business_address,
                latitude=latitude,
                longitude=longitude,
                rating=rating,
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="fuel_logs_delete",
        annotations=get_annotations("fuel_logs_delete"),
        description=(
            "[WRITE] Delete fuel log (DELETE .../fuel_logs/{fuel_log_id}). Requires OAuth/Bearer authorization."
        ),
    )
    async def fuel_logs_delete(
        vehicle_id: int,
        fuel_log_id: int,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/fuel_logs/{fuel_log_id}",
                token=token,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)
