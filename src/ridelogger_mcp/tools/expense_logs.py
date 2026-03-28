"""Expense log CRUD."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import (
    MONEY_LOGS_HINT,
    body_from_kwargs,
    require_token,
    tool_error,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="expense_logs_list",
        description=(
            "List expense logs for a vehicle (GET /api/vehicles/{vehicle_id}/expense_logs). "
            "Requires access_token or HTTP Bearer. Optional page. "
            + MONEY_LOGS_HINT
        ),
    )
    async def expense_logs_list(
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
                f"/vehicles/{vehicle_id}/expense_logs",
                token=token,
                params=params,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="expense_logs_create",
        description=(
            "Create expense log (POST .../expense_logs). Requires access_token or HTTP Bearer. "
            "ExpenseLogStoreRequest: amount, currency_id, mileage, expense_type_id, title; "
            "plus date (Y-m-d) for vehicle log; optional description, uuid. "
            + MONEY_LOGS_HINT
        ),
    )
    async def expense_logs_create(
        vehicle_id: int,
        amount: float,
        currency_id: int,
        mileage: int,
        expense_type_id: int,
        title: str,
        date: str,
        description: str | None = None,
        uuid: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                amount=amount,
                currency_id=currency_id,
                mileage=mileage,
                expense_type_id=expense_type_id,
                title=title,
                date=date,
                description=description,
                uuid=uuid,
            )
            st = get_state()
            data = await st.client.request_json(
                "POST",
                f"/vehicles/{vehicle_id}/expense_logs",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="expense_logs_get",
        description=(
            "Get one expense log (GET .../expense_logs/{expense_log_id}). Requires access_token or HTTP Bearer. "
            + MONEY_LOGS_HINT
        ),
    )
    async def expense_logs_get(
        vehicle_id: int,
        expense_log_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/expense_logs/{expense_log_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="expense_logs_update",
        description=(
            "Update expense log (PUT .../expense_logs/{expense_log_id}). Requires access_token or HTTP Bearer. "
            "Optional: amount, currency_id, mileage, expense_type_id (ExpenseLogUpdateRequest); "
            "optional title, description, date (controller merges vehicle log + expense row). "
            + MONEY_LOGS_HINT
        ),
    )
    async def expense_logs_update(
        vehicle_id: int,
        expense_log_id: int,
        amount: float | None = None,
        currency_id: int | None = None,
        mileage: int | None = None,
        expense_type_id: int | None = None,
        title: str | None = None,
        description: str | None = None,
        date: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                amount=amount,
                currency_id=currency_id,
                mileage=mileage,
                expense_type_id=expense_type_id,
                title=title,
                description=description,
                date=date,
            )
            if not body:
                raise ValueError("Provide at least one field to update.")
            st = get_state()
            data = await st.client.request_json(
                "PUT",
                f"/vehicles/{vehicle_id}/expense_logs/{expense_log_id}",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="expense_logs_delete",
        description=(
            "Delete expense log (DELETE .../expense_logs/{expense_log_id}). Requires access_token or HTTP Bearer."
        ),
    )
    async def expense_logs_delete(
        vehicle_id: int,
        expense_log_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/expense_logs/{expense_log_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
