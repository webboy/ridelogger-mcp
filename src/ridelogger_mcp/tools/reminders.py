"""Reminder CRUD and reminder slots (API v2)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import body_from_kwargs, compact_query_params, require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="reminder_slots_list",
        description=(
            "[READ] List built-in reminder slots (GET /api/reminder_slots). "
            "Public reference data: slug, default alarm type, default intervals."
        ),
    )
    async def reminder_slots_list(
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                "/reminder_slots",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_list",
        description=(
            "[READ] List reminders for a vehicle (GET /api/vehicles/{vehicle_id}/reminders). "
            "Optional status: comma-separated active,passed,canceled,completed. Requires access_token."
        ),
    )
    async def reminder_list(
        vehicle_id: int,
        status: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            params = compact_query_params({"status": status})
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/reminders",
                token=token,
                params=params,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_list_user",
        description=(
            "[READ] List reminders for the authenticated user across vehicles "
            "(GET /api/user/reminders). Optional status filter."
        ),
    )
    async def reminder_list_user(
        status: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            params = compact_query_params({"status": status})
            data = await st.client.request_json(
                "GET",
                "/user/reminders",
                token=token,
                params=params,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_show",
        description="[READ] Get one reminder (GET /api/vehicles/{vehicle_id}/reminders/{reminder_id}).",
    )
    async def reminder_show(
        vehicle_id: int,
        reminder_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/reminders/{reminder_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_create",
        description=(
            "[WRITE] Create reminder (POST /api/vehicles/{vehicle_id}/reminders). "
            "Slot-based: reminder_slot_id 1–5, name auto. Custom (premium): omit reminder_slot_id and set name. "
            "alarm_type_id: 1=DATE, 2=MILEAGE, 3=ANY. target_date / target_mileage per type. "
            "Optional interval_* for recurring."
        ),
    )
    async def reminder_create(
        vehicle_id: int,
        alarm_type_id: int,
        reminder_slot_id: int | None = None,
        target_date: str | None = None,
        target_mileage: int | None = None,
        interval_distance_value: int | None = None,
        interval_mileage_unit_id: int | None = None,
        interval_days: int | None = None,
        name: str | None = None,
        description: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                alarm_type_id=alarm_type_id,
                reminder_slot_id=reminder_slot_id,
                target_date=target_date,
                target_mileage=target_mileage,
                interval_distance_value=interval_distance_value,
                interval_mileage_unit_id=interval_mileage_unit_id,
                interval_days=interval_days,
                name=name,
                description=description,
            )
            st = get_state()
            data = await st.client.request_json(
                "POST",
                f"/vehicles/{vehicle_id}/reminders",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_update",
        description=(
            "[WRITE] Update custom reminder name/description only "
            "(PUT /api/vehicles/{vehicle_id}/reminders/{reminder_id}). Premium custom reminders."
        ),
    )
    async def reminder_update(
        vehicle_id: int,
        reminder_id: int,
        name: str | None = None,
        description: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(name=name, description=description)
            st = get_state()
            data = await st.client.request_json(
                "PUT",
                f"/vehicles/{vehicle_id}/reminders/{reminder_id}",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_delete",
        description="[WRITE] Delete reminder (DELETE .../reminders/{reminder_id}). Confirmation recommended.",
    )
    async def reminder_delete(
        vehicle_id: int,
        reminder_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/reminders/{reminder_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_complete",
        description=(
            "[WRITE] Mark reminder complete; recurring creates next (POST .../reminders/{reminder_id}/complete)."
        ),
    )
    async def reminder_complete(
        vehicle_id: int,
        reminder_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "POST",
                f"/vehicles/{vehicle_id}/reminders/{reminder_id}/complete",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
