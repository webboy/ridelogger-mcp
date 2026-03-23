"""Vehicle plates CRUD."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import parse_json_object, require_token, tool_error


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
            "body_json: plate, country_id, valid_from, valid_to, uuid (required per API)."
        ),
    )
    async def vehicle_plates_create(
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
            "body_json: fields to update per API."
        ),
    )
    async def vehicle_plates_update(
        vehicle_id: int,
        plate_id: int,
        body_json: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = parse_json_object("body_json", body_json)
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
