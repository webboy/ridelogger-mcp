"""Vehicle plates CRUD."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import body_from_kwargs, require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="vehicle_plates_list",
        description=(
            "List plates for a vehicle (GET /api/vehicles/{vehicle_id}/vehicle_plates). "
            "Requires access_token or HTTP Bearer."
        ),
    )
    async def vehicle_plates_list(
        vehicle_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/vehicle_plates",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_plates_create",
        description=(
            "Create plate (POST .../vehicle_plates). Requires access_token or HTTP Bearer. "
            "Fields match VehiclePlateStoreRequest: plate, country_id, valid_from, valid_to, uuid."
        ),
    )
    async def vehicle_plates_create(
        vehicle_id: int,
        plate: str,
        country_id: int,
        valid_from: str,
        valid_to: str,
        uuid: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
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
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_plates_update",
        description=(
            "Update plate (PUT .../vehicle_plates/{plate_id}). Requires access_token or HTTP Bearer. "
            "Fields match VehiclePlateUpdateRequest: plate, country_id, valid_from, valid_to."
        ),
    )
    async def vehicle_plates_update(
        vehicle_id: int,
        plate_id: int,
        plate: str,
        country_id: int,
        valid_from: str,
        valid_to: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
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
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_plates_delete",
        description=(
            "Delete plate (DELETE .../vehicle_plates/{plate_id}). Requires access_token or HTTP Bearer."
        ),
    )
    async def vehicle_plates_delete(
        vehicle_id: int,
        plate_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/vehicle_plates/{plate_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
