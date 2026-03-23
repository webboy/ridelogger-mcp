"""Vehicle CRUD wrappers."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import parse_json_object, require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="vehicles_list",
        description=(
            "List vehicles the user can manage (GET /api/vehicles). "
            "Requires access_token or HTTP Bearer. "
            "Optional page for paginated responses if API supports it. "
            "Returns { data: [...] }."
        ),
    )
    async def vehicles_list(
        page: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            params: dict[str, Any] = {}
            if page is not None:
                params["page"] = page
            data = await st.client.request_json(
                "GET",
                "/vehicles",
                token=token,
                params=params or None,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicles_create",
        description=(
            "Create a vehicle (POST /api/vehicles). Requires access_token or HTTP Bearer. "
            "body_json: JSON object with required fields: vehicle_type_id, vehicle_make_id, "
            "vehicle_model_id, mileage, mileage_unit_id, fuel_type_id, label, production_year; "
            "optional: plate, valid_to, engine_displacement, engine_power_kw, engine_power_hp, country_id (for plate flow). "
            "See API docs for exact types."
        ),
    )
    async def vehicles_create(body_json: str, access_token: str | None = None) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = parse_json_object("body_json", body_json)
            st = get_state()
            data = await st.client.request_json(
                "POST",
                "/vehicles",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicles_get",
        description=(
            "Get one vehicle by id (GET /api/vehicles/{vehicle_id}). Requires access_token or HTTP Bearer."
        ),
    )
    async def vehicles_get(vehicle_id: int, access_token: str | None = None) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicles_update",
        description=(
            "Update vehicle (PUT /api/vehicles/{vehicle_id}). Requires access_token or HTTP Bearer. "
            "body_json: JSON object with fields to update (same family as create — see API docs)."
        ),
    )
    async def vehicles_update(
        vehicle_id: int,
        body_json: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = parse_json_object("body_json", body_json)
            st = get_state()
            data = await st.client.request_json(
                "PUT",
                f"/vehicles/{vehicle_id}",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
