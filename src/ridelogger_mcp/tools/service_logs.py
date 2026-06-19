"""Service log CRUD."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import (
    LOG_REFS_HINT,
    MONEY_LOGS_HINT,
    body_from_kwargs,
    compact_query_params,
    require_token,
    tool_error,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="service_logs_list",
        annotations=get_annotations("service_logs_list"),
        exclude_args=["access_token"],
        description=(
            "[READ] List service logs for a vehicle (GET /api/vehicles/{vehicle_id}/service_logs). "
            "Requires OAuth/Bearer authorization. Optional page. "
            "Filters: date_from -> `from`, date_to -> `to` (Y-m-d, inclusive), currency_id, service_type_id. "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def service_logs_list(
        vehicle_id: int,
        page: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        currency_id: int | None = None,
        service_type_id: int | None = None,
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
                    "service_type_id": service_type_id,
                }
            )
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/service_logs",
                token=token,
                params=params,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="service_logs_create",
        annotations=get_annotations("service_logs_create"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Create service log (POST .../service_logs). Requires OAuth/Bearer authorization. "
            "ServiceLogStoreRequest: amount, currency_id, mileage, service_type_id, title; "
            "plus date (Y-m-d) for vehicle log; optional description, uuid. "
            "Optional geolocation: business_name, business_address, latitude, longitude; rating (1-5 stars, optional). "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def service_logs_create(
        vehicle_id: int,
        amount: float,
        currency_id: int,
        mileage: int,
        service_type_id: int,
        title: str,
        date: str,
        description: str | None = None,
        uuid: str | None = None,
        business_name: str | None = None,
        business_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        rating: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                amount=amount,
                currency_id=currency_id,
                mileage=mileage,
                service_type_id=service_type_id,
                title=title,
                date=date,
                description=description,
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
                f"/vehicles/{vehicle_id}/service_logs",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="service_logs_get",
        annotations=get_annotations("service_logs_get"),
        exclude_args=["access_token"],
        description=(
            "[READ] Get one service log (GET .../service_logs/{service_log_id}). Requires OAuth/Bearer authorization. "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def service_logs_get(
        vehicle_id: int,
        service_log_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/service_logs/{service_log_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="service_logs_update",
        annotations=get_annotations("service_logs_update"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Update service log (PUT .../service_logs/{service_log_id}). Requires OAuth/Bearer authorization. "
            "Optional: amount, currency_id, mileage, service_type_id, title, description, date (per API controller). "
            "Optional geolocation: business_name, business_address, latitude, longitude; rating (1-5 stars, optional). "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def service_logs_update(
        vehicle_id: int,
        service_log_id: int,
        amount: float | None = None,
        currency_id: int | None = None,
        mileage: int | None = None,
        service_type_id: int | None = None,
        title: str | None = None,
        description: str | None = None,
        date: str | None = None,
        business_name: str | None = None,
        business_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        rating: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                amount=amount,
                currency_id=currency_id,
                mileage=mileage,
                service_type_id=service_type_id,
                title=title,
                description=description,
                date=date,
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
                f"/vehicles/{vehicle_id}/service_logs/{service_log_id}",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="service_logs_delete",
        annotations=get_annotations("service_logs_delete"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Delete service log (DELETE .../service_logs/{service_log_id}). Requires OAuth/Bearer authorization."
        ),
    )
    async def service_logs_delete(
        vehicle_id: int,
        service_log_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/service_logs/{service_log_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
