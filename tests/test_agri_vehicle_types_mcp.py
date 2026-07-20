"""Agri vehicle type (4–7) and HOUR unit MCP contract tests."""

from __future__ import annotations

import asyncio

from ridelogger_mcp.reference_paths import REFERENCE_PATHS
from ridelogger_mcp.tools.common import VEHICLE_REFS_HINT
from tests.test_tool_annotations import _tool_parameters


def _tool_description(tool_name: str) -> str:
    from ridelogger_mcp.app import mcp

    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}
    return tool_map[tool_name].description or ""


def test_reference_paths_include_vehicle_types_and_mileage_units() -> None:
    assert REFERENCE_PATHS["vehicle_types"] == "/vehicle_types"
    assert REFERENCE_PATHS["mileage_units"] == "/mileage_units"


def test_vehicle_refs_hint_documents_agri_types_and_hour_unit() -> None:
    assert "vehicle_type_id 4=tractor" in VEHICLE_REFS_HINT
    assert "3=hour" in VEHICLE_REFS_HINT
    assert "vehicle_model_label" in VEHICLE_REFS_HINT


def test_vehicles_create_tool_documents_agri_and_model_label() -> None:
    description = _tool_description("vehicles_create")
    params = _tool_parameters("vehicles_create")

    assert "vehicle_model_label" in description
    assert "mileage_unit_id=3" in description
    assert "vehicle_model_label" in params["properties"]
