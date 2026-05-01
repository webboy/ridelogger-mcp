"""Canonical RideLogger MCP tool policy semantics (orchestrator / agents read via MCP resource).

Contract version is bumped when JSON shape or required fields change.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastmcp.tools.tool import ToolAnnotations

# Bump when the policy envelope or meaning of fields changes.
POLICY_CONTRACT_VERSION = "2026-04-23.1"
POLICY_RESOURCE_URI = "ridelogger://policy/tool-semantics"

# Keep in sync with every @mcp.tool name in tools/*.py.
REGISTERED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "user_avatar_upload",
        "vehicles_list",
        "vehicles_create",
        "vehicles_get",
        "vehicles_update",
        "vehicle_plates_list",
        "vehicle_plates_create",
        "vehicle_plates_update",
        "vehicle_plates_delete",
        "vehicle_images_list",
        "vehicle_images_get",
        "vehicle_images_create",
        "vehicle_images_delete",
        "vehicle_cabinet_list",
        "vehicle_cabinet_get",
        "vehicle_cabinet_download",
        "vehicle_cabinet_create",
        "vehicle_cabinet_update",
        "vehicle_cabinet_delete",
        "fuel_logs_list",
        "fuel_logs_create",
        "fuel_logs_get",
        "fuel_logs_update",
        "fuel_logs_delete",
        "charge_logs_list",
        "charge_logs_create",
        "charge_logs_get",
        "charge_logs_update",
        "charge_logs_delete",
        "service_logs_list",
        "service_logs_create",
        "service_logs_get",
        "service_logs_update",
        "service_logs_delete",
        "expense_logs_list",
        "expense_logs_create",
        "expense_logs_get",
        "expense_logs_update",
        "expense_logs_delete",
        "generic_vehicle_logs_list",
        "generic_vehicle_logs_delete",
        "vehicle_log_files_list",
        "vehicle_log_files_upload",
        "vehicle_log_files_upload_base64",
        "vehicle_log_files_delete",
        "vehicle_log_files_download",
        "reference_data_refresh",
        "reminder_slots_list",
        "reminder_list",
        "reminder_list_user",
        "reminder_show",
        "reminder_create",
        "reminder_update",
        "reminder_delete",
        "reminder_complete",
    }
)


def _read(
    scope: str,
    *,
    risk: str = "low",
    idem: str = "idempotent",
    requires: list[str] | None = None,
    provides: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "mcp",
        "category": "acquisition",
        "mutation": False,
        "confirmation": "none",
        "risk": risk,
        "risk_level": risk,
        "side_effect_scope": scope,
        "idempotency": idem,
        "requires": list(requires or []),
        "provides": list(provides or []),
    }


def _write(
    scope: str,
    *,
    confirmation: str,
    risk: str = "medium",
    idem: str = "non_idempotent",
    requires: list[str] | None = None,
    provides: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "mcp",
        "category": "execution",
        "mutation": True,
        "confirmation": confirmation,
        "risk": risk,
        "risk_level": risk,
        "side_effect_scope": scope,
        "idempotency": idem,
        "requires": list(requires or []),
        "provides": list(provides or []),
    }


# Single source of truth: tool name -> policy (x-ridelogger-compatible shape).
TOOL_SEMANTICS: dict[str, dict[str, Any]] = {
    "user_avatar_upload": _write("account", confirmation="recommended", requires=["file"], provides=["user_profile"]),
    "reference_data_refresh": _read(
        "session",
        idem="unknown",
        provides=["reference_data"],
    ),
    # Vehicles
    "vehicles_list": _read("vehicle", provides=["vehicles"]),
    "vehicles_get": _read("vehicle", requires=["vehicle_id"], provides=["vehicle"]),
    "vehicles_create": _write("vehicle", confirmation="recommended", provides=["vehicle"]),
    "vehicles_update": _write("vehicle", confirmation="recommended", requires=["vehicle_id"], provides=["vehicle"]),
    # Plates
    "vehicle_plates_list": _read("vehicle", requires=["vehicle_id"], provides=["vehicle_plates"]),
    "vehicle_plates_create": _write("vehicle", confirmation="recommended", requires=["vehicle_id"], provides=["vehicle_plate"]),
    "vehicle_plates_update": _write("vehicle", confirmation="recommended", requires=["vehicle_id", "plate_id"], provides=["vehicle_plate"]),
    "vehicle_plates_delete": _write("vehicle", confirmation="required", risk="high", requires=["vehicle_id", "plate_id"]),
    # Gallery
    "vehicle_images_list": _read("vehicle", requires=["vehicle_id"], provides=["vehicle_images"]),
    "vehicle_images_get": _read("vehicle", requires=["vehicle_id", "image_id"], provides=["vehicle_image"]),
    "vehicle_images_create": _write("vehicle", confirmation="recommended", requires=["vehicle_id", "chat_upload_id"], provides=["vehicle_image"]),
    "vehicle_images_delete": _write("vehicle", confirmation="required", risk="high", requires=["vehicle_id", "image_id"]),
    # Vehicle cabinet (private documents)
    "vehicle_cabinet_list": _read("vehicle", requires=["vehicle_id"], provides=["vehicle_cabinet_documents"]),
    "vehicle_cabinet_get": _read("vehicle", requires=["vehicle_id", "document_id"], provides=["vehicle_cabinet_document"]),
    "vehicle_cabinet_download": _read("vehicle", requires=["vehicle_id", "document_id"], provides=["file_blob"]),
    "vehicle_cabinet_create": _write("vehicle", confirmation="recommended", requires=["vehicle_id"], provides=["vehicle_cabinet_document"]),
    "vehicle_cabinet_update": _write("vehicle", confirmation="recommended", requires=["vehicle_id", "document_id"], provides=["vehicle_cabinet_document"]),
    "vehicle_cabinet_delete": _write("vehicle", confirmation="required", risk="high", requires=["vehicle_id", "document_id"]),
    # Fuel
    "fuel_logs_list": _read("vehicle_log", requires=["vehicle_id"], provides=["fuel_logs"]),
    "fuel_logs_get": _read("vehicle_log", requires=["vehicle_id", "log_id"], provides=["fuel_log"]),
    "fuel_logs_create": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id"], provides=["fuel_log"]),
    "fuel_logs_update": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id", "log_id"], provides=["fuel_log"]),
    "fuel_logs_delete": _write("vehicle_log", confirmation="required", risk="high", requires=["vehicle_id", "log_id"]),
    # Charge
    "charge_logs_list": _read("vehicle_log", requires=["vehicle_id"], provides=["charge_logs"]),
    "charge_logs_get": _read("vehicle_log", requires=["vehicle_id", "log_id"], provides=["charge_log"]),
    "charge_logs_create": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id"], provides=["charge_log"]),
    "charge_logs_update": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id", "log_id"], provides=["charge_log"]),
    "charge_logs_delete": _write("vehicle_log", confirmation="required", risk="high", requires=["vehicle_id", "log_id"]),
    # Service
    "service_logs_list": _read("vehicle_log", requires=["vehicle_id"], provides=["service_logs"]),
    "service_logs_get": _read("vehicle_log", requires=["vehicle_id", "log_id"], provides=["service_log"]),
    "service_logs_create": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id"], provides=["service_log"]),
    "service_logs_update": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id", "log_id"], provides=["service_log"]),
    "service_logs_delete": _write("vehicle_log", confirmation="required", risk="high", requires=["vehicle_id", "log_id"]),
    # Expense
    "expense_logs_list": _read("vehicle_log", requires=["vehicle_id"], provides=["expense_logs"]),
    "expense_logs_get": _read("vehicle_log", requires=["vehicle_id", "log_id"], provides=["expense_log"]),
    "expense_logs_create": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id"], provides=["expense_log"]),
    "expense_logs_update": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id", "log_id"], provides=["expense_log"]),
    "expense_logs_delete": _write("vehicle_log", confirmation="required", risk="high", requires=["vehicle_id", "log_id"]),
    # Generic vehicle logs + files
    "generic_vehicle_logs_list": _read("vehicle_log", requires=["vehicle_id"], provides=["vehicle_logs"]),
    "generic_vehicle_logs_delete": _write("vehicle_log", confirmation="required", risk="high", requires=["vehicle_id", "log_id"]),
    "vehicle_log_files_list": _read("vehicle_log", requires=["vehicle_id", "vehicle_log_id"], provides=["vehicle_log_files"]),
    "vehicle_log_files_download": _read("vehicle_log", requires=["vehicle_id", "vehicle_log_id", "file_id"], provides=["file_blob"]),
    "vehicle_log_files_upload": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id", "vehicle_log_id"], provides=["vehicle_log_file"]),
    "vehicle_log_files_upload_base64": _write("vehicle_log", confirmation="recommended", requires=["vehicle_id", "vehicle_log_id"], provides=["vehicle_log_file"]),
    "vehicle_log_files_delete": _write("vehicle_log", confirmation="required", risk="high", requires=["vehicle_id", "vehicle_log_id", "file_id"]),
    # Reminders
    "reminder_slots_list": _read("session", provides=["reminder_slots"]),
    "reminder_list": _read("vehicle", requires=["vehicle_id"], provides=["reminders"]),
    "reminder_list_user": _read("account", provides=["reminders"]),
    "reminder_show": _read("vehicle", requires=["vehicle_id", "reminder_id"], provides=["reminder"]),
    "reminder_create": _write("vehicle", confirmation="recommended", requires=["vehicle_id"], provides=["reminder"]),
    "reminder_update": _write("vehicle", confirmation="recommended", requires=["vehicle_id", "reminder_id"], provides=["reminder"]),
    "reminder_delete": _write("vehicle", confirmation="required", risk="high", requires=["vehicle_id", "reminder_id"]),
    "reminder_complete": _write("vehicle", confirmation="recommended", requires=["vehicle_id", "reminder_id"], provides=["reminder"]),
}


def build_annotations(semantics: dict[str, Any]) -> "ToolAnnotations":
    """Convert a TOOL_SEMANTICS entry into a FastMCP ToolAnnotations instance.

    Mapping rules:
    - readOnlyHint=True  when mutation=False (no server-side user data changes)
    - destructiveHint=True when risk="high" (irreversible deletes)
    - idempotentHint=True when idempotency="idempotent" (read-only tools)
    - openWorldHint=False for all — RideLogger tools operate on bounded user data only
    """
    from fastmcp.tools.tool import ToolAnnotations

    return ToolAnnotations(
        readOnlyHint=not semantics.get("mutation", False),
        destructiveHint=semantics.get("risk", "low") == "high",
        idempotentHint=semantics.get("idempotency", "non_idempotent") == "idempotent",
        openWorldHint=False,
    )


def get_annotations(tool_name: str) -> "ToolAnnotations":
    """Return FastMCP ToolAnnotations for a registered tool. Fails fast if unknown."""
    try:
        return build_annotations(TOOL_SEMANTICS[tool_name])
    except KeyError:
        raise KeyError(f"No TOOL_SEMANTICS entry for tool '{tool_name}'. Add it before registering.")


def validate_registry() -> None:
    """Assert every registered MCP tool has semantics; fail fast in tests / CI."""
    missing = REGISTERED_TOOL_NAMES - set(TOOL_SEMANTICS)
    extra = set(TOOL_SEMANTICS) - REGISTERED_TOOL_NAMES
    if missing or extra:
        raise ValueError(f"tool_semantics out of sync: missing={sorted(missing)} extra={sorted(extra)}")


def policy_resource_json() -> str:
    """JSON string for MCP resource body (pretty for debugging; clients should parse generically)."""
    validate_registry()
    envelope: dict[str, Any] = {
        "ok": True,
        "contract_version": POLICY_CONTRACT_VERSION,
        "uri": POLICY_RESOURCE_URI,
        "x_ridelogger": {
            "description": (
                "Policy hints for RideLogger MCP tools. Orchestrator enforces; "
                "confirmation none|recommended|required; mutation indicates server-side user data changes."
            ),
        },
        "tools": TOOL_SEMANTICS,
    }
    return json.dumps(envelope, ensure_ascii=False)


__all__ = [
    "POLICY_CONTRACT_VERSION",
    "POLICY_RESOURCE_URI",
    "REGISTERED_TOOL_NAMES",
    "TOOL_SEMANTICS",
    "build_annotations",
    "get_annotations",
    "policy_resource_json",
    "validate_registry",
]
