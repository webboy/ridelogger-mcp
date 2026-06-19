"""Each FastMCP tool resolves and runs against a stub API client / cache (offline)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, cast

import httpx
import pytest
from unittest.mock import AsyncMock

from ridelogger_mcp.app import mcp
from ridelogger_mcp.tool_semantics import REGISTERED_TOOL_NAMES
import ridelogger_mcp.state as state_mod

_MIN_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/VOJ6cQAAAAASUVORK5CYII="


def _coerce_leaf(schema_fragment: dict[str, Any]) -> Any:
    if not isinstance(schema_fragment, dict):
        return None
    if schema_fragment.get("default") not in (None,):
        return schema_fragment.get("default")
    if "const" in schema_fragment:
        return schema_fragment["const"]
    if isinstance(schema_fragment.get("enum"), list) and schema_fragment["enum"]:
        return schema_fragment["enum"][0]
    opts = schema_fragment.get("anyOf")
    if isinstance(opts, list):
        for opt in opts:
            if isinstance(opt, dict):
                leaf = _coerce_leaf(cast(dict[str, Any], opt))
                if leaf is not None:
                    return leaf

    typ = schema_fragment.get("type")
    if typ == "string":
        ml = schema_fragment.get("minLength")
        if isinstance(ml, int) and ml >= 160:
            return "z" * min(ml + 10, 400)
        return "e2e"
    if typ == "integer":
        return int(schema_fragment.get("minimum", 1))
    if typ == "number":
        return float(schema_fragment.get("minimum", 1.0))
    if typ == "boolean":
        return False
    if typ == "array":
        return []
    if typ == "object":
        return {}
    return None


def _build_dummy_arguments(parameters: dict[str, Any]) -> dict[str, Any]:
    props = cast(dict[str, Any], parameters.get("properties") or {})
    required = set(parameters.get("required") or ())
    built: dict[str, Any] = {}

    for key in props:
        fragment = cast(dict[str, Any], props[key])

        val: Any | None = fragment.get("default", None)

        if val is None:
            val = _coerce_leaf(fragment)

        if key in {"access_token", "bearer"}:
            val = "__stub-token__"

        if val is None and key in required:
            ft = fragment.get("type")
            if ft == "string":
                val = "required-e2e"
            elif ft == "integer":
                val = 1

        # Optional missing → drop from dict (omit if still None nullable only param)
        if val is None and key not in required:
            continue

        built[key] = val

    return built


def finalize_tool_arguments(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Resolve mutually-exclusive parameter groups modeled in tool implementations."""
    stub = "__stub-token__"

    if tool_name == "vehicle_log_files_upload":
        return {
            "vehicle_id": int(args.get("vehicle_id", 1)),
            "vehicle_log_id": int(args.get("vehicle_log_id", 1)),
            "access_token": stub,
            "file_name": "e2e.bin",
            "file_base64": _MIN_PNG_B64,
        }

    if tool_name == "vehicle_log_files_upload_base64":
        return {
            "vehicle_id": int(args.get("vehicle_id", 1)),
            "vehicle_log_id": int(args.get("vehicle_log_id", 1)),
            "access_token": stub,
            "vehicle_log_file": _MIN_PNG_B64,
            "vehicle_log_file_name": "tiny.png",
        }

    if tool_name == "user_avatar_upload":
        return {
            "access_token": stub,
            "file_name": "avatar.png",
            "file_base64": _MIN_PNG_B64,
        }

    if tool_name == "vehicle_images_create":
        return {
            "vehicle_id": int(args.get("vehicle_id", 1)),
            "access_token": stub,
            "file_name": "img.png",
            "file_base64": _MIN_PNG_B64,
        }

    if tool_name == "vehicle_cabinet_create":
        return {
            "vehicle_id": int(args.get("vehicle_id", 1)),
            "title": str(args.get("title") or "E2E title"),
            "document_category": str(args.get("document_category") or "other"),
            "access_token": stub,
            "file_name": "doc.pdf",
            "file_base64": _MIN_PNG_B64,
        }

    if tool_name == "vehicle_cabinet_update":
        return {
            "vehicle_id": int(args.get("vehicle_id", 1)),
            "document_id": int(args.get("document_id", 1)),
            "access_token": stub,
            "title": "Updated title",
        }

    if tool_name != "reference_data_refresh":
        args.setdefault("access_token", stub)

    return args


@dataclass
class _UpstreamStubState:
    client: Any
    cache: Any
    settings: Any | None = None


@pytest.fixture(autouse=True)
def _stub_app_state() -> Any:
    class StubCache:
        async def refresh(self) -> None:
            return None

        def loaded_dataset_names(self) -> list[str]:
            return []

    async def json_ok(*_: Any, **__: Any) -> dict[str, Any]:
        return {"data": {}, "messages": {}, "pagination": {}}

    async def bytes_ok(*_: Any, **__: Any) -> tuple[bytes, httpx.Headers]:
        return (b"", httpx.Headers({}))

    async def raw_ok(*_: Any, **__: Any) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})

    client = AsyncMock()
    client.request_json.side_effect = json_ok
    client.request_bytes.side_effect = bytes_ok
    client.request.side_effect = raw_ok

    prev = getattr(state_mod, "app_state", None)
    state_mod.app_state = _UpstreamStubState(client=client, cache=StubCache())

    yield client

    state_mod.app_state = prev


@pytest.mark.parametrize("tool_name", sorted(REGISTERED_TOOL_NAMES))
def test_tool_call_with_stub_upstream(tool_name: str) -> None:
    async def _run() -> dict[str, Any]:
        tools = await mcp.list_tools()
        tmap = {t.name: t for t in tools}
        assert tool_name in tmap, f"missing tool {tool_name} in FastMCP registry"
        tool_def = tmap[tool_name]
        args = finalize_tool_arguments(
            tool_name,
            _build_dummy_arguments(tool_def.parameters),
        )

        payload = await mcp.call_tool(tool_name, arguments=args)
        if isinstance(payload, dict):
            sc = payload.get("structured_content")
            if isinstance(sc, dict):
                return cast(dict[str, Any], sc)
            return cast(dict[str, Any], payload)
        if hasattr(payload, "model_dump"):
            dumped = payload.model_dump()
            if isinstance(dumped, dict):
                sc = dumped.get("structured_content")
                if isinstance(sc, dict):
                    return cast(dict[str, Any], sc)
                return cast(dict[str, Any], dumped)
        raise AssertionError(f"{tool_name}: unexpected payload {payload!r}")

    result = asyncio.run(_run())

    assert isinstance(result, dict) and result.get("ok") is True, (
        f"{tool_name}: expected ok=True envelope got {result!r}"
    )
