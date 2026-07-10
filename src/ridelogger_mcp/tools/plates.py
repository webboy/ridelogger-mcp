"""Vehicle plates CRUD."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import body_from_kwargs, tool_error, tool_success, ToolToken

PlateDate = Annotated[
    str,
    Field(
        description="Plate validity date in YYYY-MM-DD format, e.g. 2026-12-31.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
]

PlateUuid = Annotated[
    str,
    Field(
        description=(
            "Client-supplied stable unique identifier for the plate record. "
            "Use a UUID string such as 550e8400-e29b-41d4-a716-446655440000."
        ),
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    ),
]


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="vehicle_plates_list",
        annotations=get_annotations("vehicle_plates_list"),
        description=(
            "[READ] List plates for a vehicle (GET /api/vehicles/{vehicle_id}/vehicle_plates). "
            "Requires OAuth/Bearer authorization."
        ),
    )
    async def vehicle_plates_list(
        vehicle_id: int,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/vehicle_plates",
                token=token,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_plates_create",
        annotations=get_annotations("vehicle_plates_create"),
        description=(
            "[WRITE] Create plate (POST .../vehicle_plates). Requires OAuth/Bearer authorization. "
            "Fields match VehiclePlateStoreRequest: plate, country_id, valid_from, valid_to, uuid. "
            "Use YYYY-MM-DD for valid_from and valid_to; uuid must be a UUID string."
        ),
    )
    async def vehicle_plates_create(
        vehicle_id: int,
        plate: str,
        country_id: int,
        valid_from: PlateDate,
        valid_to: PlateDate,
        uuid: PlateUuid,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
            body = body_from_kwargs(
                plate=plate,
                country_id=country_id,
                valid_from=valid_from,
                valid_to=valid_to,
                uuid=uuid,
            )
            st = get_state()
            data = await st.client.request_json(
                "POST",
                f"/vehicles/{vehicle_id}/vehicle_plates",
                token=token,
                json_body=body,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_plates_update",
        annotations=get_annotations("vehicle_plates_update"),
        description=(
            "[WRITE] Update plate (PUT .../vehicle_plates/{plate_id}). Requires OAuth/Bearer authorization. "
            "Fields match VehiclePlateUpdateRequest: plate, country_id, valid_from, valid_to. "
            "Use YYYY-MM-DD for valid_from and valid_to."
        ),
    )
    async def vehicle_plates_update(
        vehicle_id: int,
        plate_id: int,
        plate: str,
        country_id: int,
        valid_from: PlateDate,
        valid_to: PlateDate,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
            body = body_from_kwargs(
                plate=plate,
                country_id=country_id,
                valid_from=valid_from,
                valid_to=valid_to,
            )
            st = get_state()
            data = await st.client.request_json(
                "PUT",
                f"/vehicles/{vehicle_id}/vehicle_plates/{plate_id}",
                token=token,
                json_body=body,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_plates_delete",
        annotations=get_annotations("vehicle_plates_delete"),
        description=(
            "[WRITE] Delete plate (DELETE .../vehicle_plates/{plate_id}). Requires OAuth/Bearer authorization."
        ),
    )
    async def vehicle_plates_delete(
        vehicle_id: int,
        plate_id: int,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        try:
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/vehicle_plates/{plate_id}",
                token=token,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)
