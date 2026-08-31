"""Cached RideLogger reference datasets: refresh + ChatGPT-readable lookup."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP

from ridelogger_mcp.logging_setup import new_request_id
from ridelogger_mcp.reference_cache import row_matches_query
from ridelogger_mcp.reference_paths import REFERENCE_PATHS
from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import tool_error, tool_success

ReferenceDataset = Literal[
    "countries",
    "currencies",
    "vehicle_types",
    "vehicle_makes",
    "fuel_types",
    "fuel_units",
    "charge_types",
    "energy_units",
    "powertrain_types",
    "service_types",
    "expense_types",
    "mileage_units",
    "steering_sides",
    "fuel_consumption_units",
]

_DATASETS = ", ".join(sorted(REFERENCE_PATHS))
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="reference_data_get",
        annotations=get_annotations("reference_data_get"),
        description=(
            "[READ] Look up RideLogger catalog/reference rows from the MCP cache "
            f"(same datasets as ridelogger://reference/*). Valid dataset: {_DATASETS}. "
            "Use this to resolve integer IDs before create/update tools — especially "
            "`vehicle_make_id` for vehicles_create. Optional `q` filters name/label/slug/code "
            "(e.g. dataset=vehicle_makes, q=Claas). Optional `limit` (default 50, max 200). "
            "Does not require user authorization. Does not change any records. "
            "vehicle_models are not in this cache; agri types 4–7 use vehicle_model_label instead."
        ),
    )
    async def reference_data_get(
        dataset: ReferenceDataset,
        q: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        try:
            new_request_id()
            if dataset not in REFERENCE_PATHS:
                return tool_error(ValueError(f"Unknown dataset. Valid: {_DATASETS}"))
            cap = _DEFAULT_LIMIT if limit is None else max(1, min(int(limit), _MAX_LIMIT))
            st = get_state()
            rows = st.cache.rows(dataset)
            if q and str(q).strip():
                rows = [row for row in rows if row_matches_query(row, str(q))]
            total = len(rows)
            sliced = rows[:cap]
            return tool_success(
                {
                    "dataset": dataset,
                    "q": q,
                    "total_matched": total,
                    "returned": len(sliced),
                    "truncated": total > len(sliced),
                    "items": sliced,
                }
            )
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="reference_data_refresh",
        annotations=get_annotations("reference_data_refresh"),
        description=(
            "[WRITE] Reload the MCP server's cached reference datasets from the RideLogger API "
            "(countries, currencies, etc.). This changes only the server-side cache state — it never reads or "
            "modifies any user records. "
            "The `currencies` dataset is needed to convert monetary log rows (each has `currency_id`) to a single "
            "display currency — typically the user's `currency_id` from `auth_me`. "
            "Does not require user authorization. Use after TTL or when data seems stale. "
            "To read rows after refresh, call `reference_data_get`."
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
