"""Startup + TTL reference data cache (public GET endpoints)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from ridelogger_mcp.api_client import ApiClient
from ridelogger_mcp.config import Settings

logger = logging.getLogger(__name__)

# Relative to api base (includes /api)
REFERENCE_PATHS: dict[str, str] = {
    "countries": "/countries",
    "currencies": "/currencies",
    "vehicle_types": "/vehicle_types",
    "vehicle_makes": "/vehicle_makes",
    "fuel_types": "/fuel_types",
    "fuel_units": "/fuel_units",
    "service_types": "/service_types",
    "expense_types": "/expense_types",
    "mileage_units": "/mileage_units",
}


class ReferenceCache:
    def __init__(self, settings: Settings, client: ApiClient) -> None:
        self._settings = settings
        self._client = client
        self._data: dict[str, Any] = {}
        self._meta: dict[str, dict[str, Any]] = {}

    async def refresh(self) -> None:
        async def fetch_one(name: str, path: str) -> tuple[str, Any, dict[str, Any]]:
            data = await self._client.get_public_json(path)
            ep = f"{self._settings.api_base}{path}" if path.startswith("/") else f"{self._settings.api_base}/{path}"
            meta = {
                "fetched_at": datetime.now(UTC).isoformat(),
                "source_endpoint": ep,
            }
            return name, data, meta

        tasks = [fetch_one(n, p) for n, p in REFERENCE_PATHS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                logger.exception("Reference fetch failed: %s", res)
                continue
            name, data, meta = res
            self._data[name] = data
            self._meta[name] = meta
        logger.info("Reference cache loaded: %s datasets", len(self._data))

    def envelope(self, name: str) -> dict[str, Any]:
        if name not in REFERENCE_PATHS:
            raise KeyError(f"Unknown reference dataset: {name}")
        path = REFERENCE_PATHS[name]
        ep = f"{self._settings.api_base}{path}"
        return {
            "data": self._data.get(name),
            "fetched_at": self._meta.get(name, {}).get("fetched_at"),
            "ttl_seconds": self._settings.reference_cache_ttl_seconds,
            "source_endpoint": self._meta.get(name, {}).get("source_endpoint", ep),
        }

    def loaded_dataset_names(self) -> list[str]:
        return sorted(self._data.keys())

    async def refresh_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(
                    float(self._settings.reference_cache_ttl_seconds),
                )
                await self.refresh()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Periodic reference refresh failed")
