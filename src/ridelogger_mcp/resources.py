"""MCP resources for cached reference datasets."""

from __future__ import annotations

import json

from fastmcp import FastMCP

from ridelogger_mcp.reference_cache import REFERENCE_PATHS
from ridelogger_mcp.state import get_state


def register_resources(mcp: FastMCP) -> None:
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
