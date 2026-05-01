"""FastMCP HTTP application entry."""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response

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
    hmac_on = bool(
        (settings.api_consumer_key_id or "").strip()
        and (settings.api_consumer_secret or "").strip()
    )
    logger.info(
        "RideLogger MCP ready — SK_API_URL=%s consumer=%s HMAC_signing=%s",
        settings.sk_api_url,
        (settings.api_consumer_code or "mcp").strip() or "mcp",
        hmac_on,
    )
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
        "Authenticate through the MCP client's OAuth/Bearer flow and send Authorization: Bearer on HTTP requests — "
        "the server validates it via GET /api/auth/me. "
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
    settings = Settings()
    kid = (settings.api_consumer_key_id or "").strip()
    secret_on = bool((settings.api_consumer_secret or "").strip())
    key_id_configured = bool(kid)
    hmac_signing_configured = key_id_configured and secret_on
    code = (settings.api_consumer_code or "mcp").strip() or "mcp"
    key_hint = kid[:6] + "…" if len(kid) > 6 else kid
    return JSONResponse(
        {
            "ok": True,
            "service": "ridelogger-mcp",
            "version": __version__,
            "api_upstream": settings.sk_api_url,
            "api_consumer": {
                "code": code,
                "key_id_configured": key_id_configured,
                "key_id_hint": key_hint,
                "hmac_signing_configured": hmac_signing_configured,
            },
        },
    )


@mcp.custom_route("/.well-known/openai-apps-challenge", methods=["GET"])
async def openai_apps_challenge(_request: Request) -> Response:
    """Serve the OpenAI Apps domain-verification token as plain text.

    The token is copied from OpenAI Platform dashboard (MCP Server →
    Domain verification → Token) into the server `.env` as
    `OPENAI_APPS_CHALLENGE_TOKEN`. When unset, return 404 so the
    endpoint does not leak an empty placeholder.
    """
    settings = Settings()
    token = (settings.openai_apps_challenge_token or "").strip()
    if not token:
        return PlainTextResponse("Not Found", status_code=404)
    return PlainTextResponse(token, media_type="text/plain; charset=utf-8")


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
