"""HTTP Authorization: Bearer — validated against RideLogger GET /api/auth/me."""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult
import mcp.types as mt

from ridelogger_mcp.errors import UpstreamApiError
from ridelogger_mcp.state import get_state

logger = logging.getLogger(__name__)

# JWT from validated Authorization: Bearer on the current MCP HTTP request.
_http_bearer_token: ContextVar[str | None] = ContextVar("ridelogger_http_bearer_token", default=None)


def get_http_bearer_token() -> str | None:
    return _http_bearer_token.get()


def _parse_bearer_authorization(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    if not s.lower().startswith("bearer "):
        return None
    token = s[7:].strip()
    return token or None


def _bearer_validation_error_result(exc: Exception) -> ToolResult:
    if isinstance(exc, UpstreamApiError):
        return ToolResult(
            structured_content={
                "ok": False,
                "error": {
                    "type": "bearer_auth",
                    "status_code": exc.status_code,
                    "message": exc.message,
                },
            }
        )
    return ToolResult(
        structured_content={
            "ok": False,
            "error": {
                "type": "bearer_auth",
                "message": f"Authorization Bearer validation failed: {exc}",
            },
        }
    )


class RideLoggerBearerMiddleware(Middleware):
    """When the HTTP client sends Authorization: Bearer, validate via GET /auth/me."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        reset: Token[str | None] = _http_bearer_token.set(None)
        try:
            try:
                from fastmcp.server.dependencies import get_http_request

                request = get_http_request()
            except RuntimeError:
                return await call_next(context)

            bearer = _parse_bearer_authorization(request.headers.get("authorization"))
            if bearer is None:
                return await call_next(context)

            st = get_state()
            try:
                await st.client.request_json("GET", "/auth/me", token=bearer)
            except Exception as e:
                logger.info("Bearer token rejected by /auth/me: %s", e)
                return _bearer_validation_error_result(e)

            reset = _http_bearer_token.set(bearer)
            return await call_next(context)
        finally:
            _http_bearer_token.reset(reset)
