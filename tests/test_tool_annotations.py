"""Tests: every registered MCP tool has explicit, correct FastMCP annotations.

Rules verified:
- All read tools (mutation=False) have readOnlyHint=True.
- All destructive tools (risk="high") have destructiveHint=True.
- No tool has openWorldHint=True (all operate on bounded user data).
- No tool is missing annotations entirely.
- validate_registry() stays in sync — REGISTERED_TOOL_NAMES == TOOL_SEMANTICS keys.
- get_annotations() raises KeyError for unknown tool names.
"""

from __future__ import annotations

import asyncio

import pytest

from ridelogger_mcp.tool_semantics import (
    MCP_DESTRUCTIVE_HINT_TOOLS,
    MCP_NON_READ_ONLY_TOOLS,
    REGISTERED_TOOL_NAMES,
    TOOL_SEMANTICS,
    get_annotations,
    validate_registry,
)


def test_registry_in_sync() -> None:
    """REGISTERED_TOOL_NAMES and TOOL_SEMANTICS must stay in sync."""
    validate_registry()


def test_get_annotations_unknown_tool_raises() -> None:
    with pytest.raises(KeyError, match="no_such_tool"):
        get_annotations("no_such_tool")


@pytest.mark.parametrize("tool_name", sorted(REGISTERED_TOOL_NAMES))
def test_annotations_not_none(tool_name: str) -> None:
    ann = get_annotations(tool_name)
    assert ann is not None, f"{tool_name}: annotations must not be None"


@pytest.mark.parametrize("tool_name", sorted(REGISTERED_TOOL_NAMES))
def test_open_world_hint_false(tool_name: str) -> None:
    """All tools operate on bounded user data — openWorldHint must be False."""
    ann = get_annotations(tool_name)
    assert ann.openWorldHint is False, f"{tool_name}: openWorldHint must be False"


@pytest.mark.parametrize(
    "tool_name",
    sorted(
        n
        for n, s in TOOL_SEMANTICS.items()
        if not s.get("mutation", False) and n not in MCP_NON_READ_ONLY_TOOLS
    ),
)
def test_read_only_hint_for_non_mutation_tools(tool_name: str) -> None:
    ann = get_annotations(tool_name)
    assert ann.readOnlyHint is True, f"{tool_name}: mutation=False but readOnlyHint is not True"


@pytest.mark.parametrize(
    "tool_name",
    sorted(
        n
        for n, s in TOOL_SEMANTICS.items()
        if s.get("mutation", False) or n in MCP_NON_READ_ONLY_TOOLS
    ),
)
def test_no_read_only_hint_for_state_changing_tools(tool_name: str) -> None:
    ann = get_annotations(tool_name)
    assert ann.readOnlyHint is False, f"{tool_name}: state-changing tool but readOnlyHint is True"


@pytest.mark.parametrize(
    "tool_name",
    sorted(
        n
        for n, s in TOOL_SEMANTICS.items()
        if s.get("risk") == "high" or n in MCP_DESTRUCTIVE_HINT_TOOLS
    ),
)
def test_destructive_hint_for_delete_or_overwrite_tools(tool_name: str) -> None:
    ann = get_annotations(tool_name)
    assert ann.destructiveHint is True, f"{tool_name}: destructive behavior but destructiveHint is not True"


@pytest.mark.parametrize(
    "tool_name",
    sorted(
        n
        for n, s in TOOL_SEMANTICS.items()
        if s.get("risk") != "high" and n not in MCP_DESTRUCTIVE_HINT_TOOLS
    ),
)
def test_no_destructive_hint_for_additive_or_read_tools(tool_name: str) -> None:
    ann = get_annotations(tool_name)
    assert ann.destructiveHint is False, f"{tool_name}: non-destructive tool but destructiveHint is True"


def test_fastmcp_list_tool_names_equal_registry() -> None:
    """Names returned by FastMCP must equal REGISTERED_TOOL_NAMES (guards decorator drift)."""
    from ridelogger_mcp.app import mcp

    tools = asyncio.run(mcp.list_tools())
    assert frozenset(t.name for t in tools) == REGISTERED_TOOL_NAMES


# --- Integration: verify annotations are visible via FastMCP list_tools ---


def test_list_tools_all_have_annotations() -> None:
    """list_tools() output must include annotations on every tool (smoke test)."""
    from ridelogger_mcp.app import mcp

    tools = asyncio.run(mcp.list_tools())
    assert len(tools) == len(REGISTERED_TOOL_NAMES), (
        f"Expected {len(REGISTERED_TOOL_NAMES)} tools, got {len(tools)}"
    )
    missing = [t.name for t in tools if t.annotations is None]
    assert not missing, f"Tools missing annotations in list_tools output: {missing}"


def test_list_tools_read_only_tools_correct() -> None:
    """Spot-check: known read-only tools must have readOnlyHint=True in list_tools output."""
    from ridelogger_mcp.app import mcp

    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}

    read_only_samples = ["vehicles_list", "auth_me", "fuel_logs_get", "reminder_show"]
    for name in read_only_samples:
        t = tool_map[name]
        assert t.annotations.readOnlyHint is True, f"{name}: expected readOnlyHint=True"

    assert tool_map["reference_data_refresh"].annotations.readOnlyHint is False


def test_list_tools_destructive_tools_correct() -> None:
    """Spot-check: known delete tools must have destructiveHint=True in list_tools output."""
    from ridelogger_mcp.app import mcp

    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}

    destructive_samples = [
        "fuel_logs_delete", "service_logs_delete", "reminder_delete",
        "vehicle_images_delete", "vehicle_plates_delete", "vehicles_update",
        "user_avatar_upload", "reminder_complete",
    ]
    for name in destructive_samples:
        t = tool_map[name]
        assert t.annotations.destructiveHint is True, f"{name}: expected destructiveHint=True"


def _tool_parameters(tool_name: str) -> dict:
    from ridelogger_mcp.app import mcp

    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}
    return tool_map[tool_name].parameters


def test_openai_schema_hardening_for_vehicle_plate_dates_and_uuid() -> None:
    """OpenAI review flags unconstrained plate date/uuid strings as unclear."""
    create_params = _tool_parameters("vehicle_plates_create")
    update_params = _tool_parameters("vehicle_plates_update")

    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    uuid_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

    for params in (create_params, update_params):
        props = params["properties"]
        assert props["valid_from"]["pattern"] == date_pattern
        assert props["valid_to"]["pattern"] == date_pattern

    assert create_params["properties"]["uuid"]["pattern"] == uuid_pattern


def test_openai_schema_hardening_for_charge_log_create() -> None:
    """Charge create must not describe required energy while leaving it optional."""
    params = _tool_parameters("charge_logs_create")

    assert "energy" in params["required"]
    assert params["properties"]["date"]["pattern"] == r"^\d{4}-\d{2}-\d{2}$"
    assert "pattern" in params["properties"]["uuid"]["anyOf"][0]


def test_openai_schema_hardening_for_reminder_filters_and_create() -> None:
    """Reminder status/alarm fields need explicit enum/date contract for OpenAI scan."""
    status_values = ["active", "passed", "canceled", "completed"]

    for tool_name in ("reminder_list", "reminder_list_user"):
        params = _tool_parameters(tool_name)
        assert params["properties"]["status"]["anyOf"][0]["enum"] == status_values

    params = _tool_parameters("reminder_create")
    props = params["properties"]
    assert props["alarm_type_id"]["enum"] == [1, 2, 3]
    assert props["reminder_slot_id"]["anyOf"][0]["enum"] == [1, 2, 3, 4, 5]
    assert props["interval_mileage_unit_id"]["anyOf"][0]["enum"] == [1, 2]
    assert props["target_date"]["anyOf"][0]["pattern"] == r"^\d{4}-\d{2}-\d{2}$"
