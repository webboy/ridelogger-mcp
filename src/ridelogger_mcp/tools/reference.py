"""Manual refresh of cached reference data."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.logging_setup import new_request_id
from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="reference_data_refresh",
        annotations=get_annotations("reference_data_refresh"),
        description=(
            "[READ] Reload all cached reference datasets from the API (countries, currencies, etc.). "
            "The `currencies` dataset is needed to convert monetary log rows (each has `currency_id`) to a single "
            "display currency — typically the user's `currency_id` from `auth_me`. "
            "Does not require user authorization. Use after TTL or when data seems stale."
        ),
    )
    async def reference_data_refresh() -> dict[str, Any]:
        try:
            new_request_id()
            st = get_state()
            await st.cache.refresh()
            return {
                "ok": True,
                "data": {"refreshed": True, "datasets": st.cache.loaded_dataset_names()},
            }
        except Exception as e:
            return tool_error(e)
