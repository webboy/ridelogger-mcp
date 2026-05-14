"""MCP resources for cached reference datasets."""

from __future__ import annotations

import json

from fastmcp import FastMCP

from ridelogger_mcp.reference_paths import REFERENCE_PATHS
from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import POLICY_RESOURCE_URI, policy_resource_json


def register_resources(mcp: FastMCP) -> None:
    @mcp.resource(
        POLICY_RESOURCE_URI,
        mime_type="application/json",
        description=(
            "Tool policy semantics for RideLogger MCP tools: kind, category, mutation, confirmation, "
            "risk/risk_level, side_effect_scope, idempotency, requires, provides. "
            "Consumed by ridelogger-ai orchestrator."
        ),
    )
    async def _tool_policy_resource() -> str:
        return policy_resource_json()

    _tool_policy_resource.__doc__ = "RideLogger MCP tool policy (JSON)."

    for name in REFERENCE_PATHS:
        uri = f"ridelogger://reference/{name}"

        def factory(n: str = name, u: str = uri) -> None:
            @mcp.resource(
                u,
                mime_type="application/json",
                description=(
                    f"Cached '{n}' reference data from RideLogger API. "
                    "JSON envelope: data, fetched_at, ttl_seconds, source_endpoint."
                ),
            )
            async def _read() -> str:
                st = get_state()
                return json.dumps(st.cache.envelope(n), ensure_ascii=False)

            _read.__doc__ = f"Reference dataset: {n}"

        factory()
