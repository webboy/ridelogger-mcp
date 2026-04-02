"""FastMCP HTTP application entry."""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from starlette.requests import Request
from starlette.responses import JSONResponse

from ridelogger_mcp import __version__
from ridelogger_mcp.api_client import ApiClient
from ridelogger_mcp.bearer_auth import RideLoggerBearerMiddleware
from ridelogger_mcp.config import Settings
from ridelogger_mcp.logging_setup import setup_logging
from ridelogger_mcp.reference_cache import ReferenceCache
from ridelogger_mcp.resources import register_resources
from ridelogger_mcp import state as state_mod
from ridelogger_mcp.state import AppState
from ridelogger_mcp.tools import register_all

logger = logging.getLogger(__name__)


@lifespan
async def lifespan_fn(server: FastMCP) -> None:
    settings = Settings()
    setup_logging(
        settings.log_level,
        verbose_mcp_library_logs=settings.mcp_verbose_logs,
    )
    client = ApiClient(settings)
    cache = ReferenceCache(settings, client)
    await cache.refresh()
    refresh_task = asyncio.create_task(cache.refresh_loop())
    state_mod.app_state = AppState(
        settings=settings,
        client=client,
        cache=cache,
        refresh_task=refresh_task,
    )
    logger.info("RideLogger MCP ready (reference cache loaded)")
    yield {}
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass
    await client.aclose()
    state_mod.app_state = None
    logger.info("RideLogger MCP shutdown complete")


mcp = FastMCP(
    "RideLogger MCP",
    lifespan=lifespan_fn,
    instructions=(
        "Thin MCP wrapper over the RideLogger REST API (vehicle maintenance logbook). "
        "Authenticate with auth_login (email/password) and pass access_token to tools, "
        "or send Authorization: Bearer <JWT> on HTTP requests — the server validates it via GET /api/auth/me. "
        "Call auth_me to read user settings including preferred currency_id. "
        "Expense, fuel, and service logs are multi-currency (each row has currency_id); use reference currencies "
        "to convert amounts to one currency before summing — see tool descriptions on those endpoints. "
        "Reference data (countries, currencies, …) is available as MCP resources ridelogger://reference/*. "
        "Write tools use typed parameters aligned with ridelogger-api FormRequest validation (see each tool's schema)."
    ),
)

mcp.add_middleware(RideLoggerBearerMiddleware())

register_all(mcp)
register_resources(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    return JSONResponse(
        {"ok": True, "service": "ridelogger-mcp", "version": __version__},
    )


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def oauth_protected_resource(_request: Request) -> JSONResponse:
    settings = Settings()
    return JSONResponse({
        "resource": settings.oauth_resource_url,
        "authorization_servers": [settings.oauth_authorization_server],
        "scopes_supported": [
            "profile:read",
            "vehicles:read",
            "vehicles:write",
            "logs:read",
            "logs:write",
            "files:read",
            "files:write",
        ],
        "bearer_methods_supported": ["header"],
    })


def run_server() -> None:
    settings = Settings()
    setup_logging(
        settings.log_level,
        verbose_mcp_library_logs=settings.mcp_verbose_logs,
    )
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
    )
