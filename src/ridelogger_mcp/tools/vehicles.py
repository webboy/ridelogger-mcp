"""Vehicle CRUD wrappers."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import VEHICLE_REFS_HINT, body_from_kwargs, require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="vehicles_list",
        annotations=get_annotations("vehicles_list"),
        exclude_args=["access_token"],
        description=(
            "[READ] List vehicles the user can manage (GET /api/vehicles). "
            "Requires OAuth/Bearer authorization. "
            "Optional filters: vehicle_make_id, vehicle_model_id, production_year (query params). "
            "Optional page for paginated responses if API supports it. "
            "Returns { data: [...] }. "
            + VEHICLE_REFS_HINT
        ),
    )
    async def vehicles_list(
        page: int | None = None,
        vehicle_make_id: int | None = None,
        vehicle_model_id: int | None = None,
        production_year: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            params: dict[str, Any] = {}
            if page is not None:
                params["page"] = page
            if vehicle_make_id is not None:
                params["vehicle_make_id"] = vehicle_make_id
            if vehicle_model_id is not None:
                params["vehicle_model_id"] = vehicle_model_id
            if production_year is not None:
                params["production_year"] = production_year
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
        annotations=get_annotations("vehicles_create"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Create a vehicle (POST /api/vehicles). Requires OAuth/Bearer authorization. "
            "Body matches VehicleStoreRequest in ridelogger-api: vehicle_type_id, vehicle_make_id, mileage, "
            "fuel_type_id, label, production_year are required; vehicle_model_id is required "
            "when vehicle_type_id is 1 (car). Optional: mileage_unit_id (defaults from owner country), "
            "steering_side_id (`GET /api/steering_sides`, defaults from owner country). "
            "Optional: plate, valid_to, engine_displacement, engine_power_kw, "
            "engine_power_hp. "
            "Response includes the created vehicle. " + VEHICLE_REFS_HINT
        ),
    )
    async def vehicles_create(
        vehicle_type_id: int,
        vehicle_make_id: int,
        mileage: int,
        fuel_type_id: int,
        label: str,
        production_year: int,
        mileage_unit_id: int | None = None,
        steering_side_id: int | None = None,
        vehicle_model_id: int | None = None,
        plate: str | None = None,
        valid_to: str | None = None,
        engine_displacement: int | None = None,
        engine_power_kw: int | None = None,
        engine_power_hp: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                vehicle_type_id=vehicle_type_id,
                vehicle_make_id=vehicle_make_id,
                vehicle_model_id=vehicle_model_id,
                mileage=mileage,
                mileage_unit_id=mileage_unit_id,
                steering_side_id=steering_side_id,
                fuel_type_id=fuel_type_id,
                label=label,
                production_year=production_year,
                plate=plate,
                valid_to=valid_to,
                engine_displacement=engine_displacement,
                engine_power_kw=engine_power_kw,
                engine_power_hp=engine_power_hp,
            )
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
        annotations=get_annotations("vehicles_get"),
        exclude_args=["access_token"],
        description=(
            "[READ] Get one vehicle by id (GET /api/vehicles/{vehicle_id}). Requires OAuth/Bearer authorization. "
            + VEHICLE_REFS_HINT
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
        annotations=get_annotations("vehicles_update"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Partial update vehicle (PUT /api/vehicles/{vehicle_id}). Requires OAuth/Bearer authorization. "
            "Only **vehicle_id** is required; include **only fields that change** (API merges with existing row). "
            "Omitted parameters are not sent. **mileage_unit_id** cannot be changed after create — omit it on update. "
            "For **cars** (vehicle_type_id=1), set **vehicle_make_id** and "
            "**vehicle_model_id** from reference data when you change identity; omit **vehicle_model_id** for "
            "motorcycles/trucks. Do not send null for unknown IDs — omit the key instead. "
            "Optional: steering_side_id (`GET /api/steering_sides`), powertrain_id, plate, valid_to, country_id "
            "(with plate), engine_*. "
            + VEHICLE_REFS_HINT
        ),
    )
    async def vehicles_update(
        vehicle_id: int,
        vehicle_type_id: int | None = None,
        vehicle_make_id: int | None = None,
        vehicle_model_id: int | None = None,
        mileage: int | None = None,
        steering_side_id: int | None = None,
        fuel_type_id: int | None = None,
        label: str | None = None,
        production_year: int | None = None,
        powertrain_id: int | None = None,
        plate: str | None = None,
        valid_to: str | None = None,
        country_id: int | None = None,
        engine_displacement: int | None = None,
        engine_power_kw: int | None = None,
        engine_power_hp: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = body_from_kwargs(
                vehicle_type_id=vehicle_type_id,
                vehicle_make_id=vehicle_make_id,
                vehicle_model_id=vehicle_model_id,
                mileage=mileage,
                steering_side_id=steering_side_id,
                fuel_type_id=fuel_type_id,
                label=label,
                production_year=production_year,
                powertrain_id=powertrain_id,
                plate=plate,
                valid_to=valid_to,
                country_id=country_id,
                engine_displacement=engine_displacement,
                engine_power_kw=engine_power_kw,
                engine_power_hp=engine_power_hp,
            )
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
