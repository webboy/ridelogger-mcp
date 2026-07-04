"""Reminder CRUD and reminder slots (API v2)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import body_from_kwargs, compact_query_params, require_token, tool_error, tool_success

ReminderStatus = Literal["active", "passed", "canceled", "completed"]
AlarmTypeId = Literal[1, 2, 3]
ReminderSlotId = Literal[1, 2, 3, 4, 5]
MileageUnitId = Literal[1, 2]

ReminderDate = Annotated[
    str,
    Field(
        description="Reminder target date in YYYY-MM-DD format.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
]


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="reminder_slots_list",
        annotations=get_annotations("reminder_slots_list"),
        exclude_args=["access_token"],
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_list",
        annotations=get_annotations("reminder_list"),
        exclude_args=["access_token"],
        description=(
            "[READ] List reminders for a vehicle (GET /api/vehicles/{vehicle_id}/reminders). "
            "Optional status filter must be one of: active, passed, canceled, completed. Requires OAuth/Bearer authorization."
        ),
    )
    async def reminder_list(
        vehicle_id: int,
        status: ReminderStatus | None = None,
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_list_user",
        annotations=get_annotations("reminder_list_user"),
        exclude_args=["access_token"],
        description=(
            "[READ] List reminders for the authenticated user across vehicles "
            "(GET /api/user/reminders). Optional status filter must be one of: active, passed, canceled, completed."
        ),
    )
    async def reminder_list_user(
        status: ReminderStatus | None = None,
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_show",
        annotations=get_annotations("reminder_show"),
        exclude_args=["access_token"],
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reminder_create",
        annotations=get_annotations("reminder_create"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Create reminder (POST /api/vehicles/{vehicle_id}/reminders). "
            "Built-in slots (reminder_slot_id): 1=Technical inspection, 2=Oil change, "
            "3=Tire swap (summer), 4=Tire swap (winter), 5=Brake check. "
            "ALWAYS use a matching slot when the user's request fits one of these 5 categories. "
            "Custom reminders may not be available for every account; if unavailable, the API returns a permission error. "
            "alarm_type_id: 1=DATE requires target_date, 2=MILEAGE requires target_mileage, "
            "3=ANY requires both target_date and target_mileage. "
            "Optional interval_* for recurring."
        ),
    )
    async def reminder_create(
        vehicle_id: int,
        alarm_type_id: Annotated[
            AlarmTypeId,
            Field(description="1=DATE, 2=MILEAGE, 3=ANY. Controls which target fields are required."),
        ],
        reminder_slot_id: ReminderSlotId | None = None,
        target_date: ReminderDate | None = None,
        target_mileage: int | None = None,
        interval_distance_value: int | None = None,
        interval_mileage_unit_id: MileageUnitId | None = None,
        interval_days: int | None = None,
        name: str | None = None,
        description: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            _validate_reminder_create(
                alarm_type_id=alarm_type_id,
                reminder_slot_id=reminder_slot_id,
                target_date=target_date,
                target_mileage=target_mileage,
                name=name,
            )
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)
    @mcp.tool(
        name="reminder_update",
        annotations=get_annotations("reminder_update"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Update custom reminder name/description only "
            "(PUT /api/vehicles/{vehicle_id}/reminders/{reminder_id})."
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)
    @mcp.tool(
        name="reminder_delete",
        annotations=get_annotations("reminder_delete"),
        exclude_args=["access_token"],
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)
    @mcp.tool(
        name="reminder_complete",
        annotations=get_annotations("reminder_complete"),
        exclude_args=["access_token"],
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)


def _validate_reminder_create(
    *,
    alarm_type_id: int,
    reminder_slot_id: int | None,
    target_date: str | None,
    target_mileage: int | None,
    name: str | None,
) -> None:
    if alarm_type_id == 1 and not target_date:
        raise ValueError("alarm_type_id=1 (DATE) requires target_date in YYYY-MM-DD format.")
    if alarm_type_id == 2 and target_mileage is None:
        raise ValueError("alarm_type_id=2 (MILEAGE) requires target_mileage.")
    if alarm_type_id == 3 and (not target_date or target_mileage is None):
        raise ValueError("alarm_type_id=3 (ANY) requires both target_date and target_mileage.")
    if reminder_slot_id is None and not (name or "").strip():
        raise ValueError("Custom reminders without reminder_slot_id require a name.")
