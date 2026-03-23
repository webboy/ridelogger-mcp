"""Process-wide state set during MCP lifespan."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ridelogger_mcp.api_client import ApiClient
from ridelogger_mcp.config import Settings
from ridelogger_mcp.reference_cache import ReferenceCache


@dataclass
class AppState:
    settings: Settings
    client: ApiClient
    cache: ReferenceCache
    refresh_task: asyncio.Task[None] | None = None


app_state: AppState | None = None


def get_state() -> AppState:
    if app_state is None:
        raise RuntimeError("Application state is not initialized (lifespan not started).")
    return app_state
