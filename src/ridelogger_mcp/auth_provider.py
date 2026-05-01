"""FastMCP OAuth resource-server integration."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastmcp.server.auth import AccessToken, RemoteAuthProvider, TokenVerifier

from ridelogger_mcp.api_client import ApiClient
from ridelogger_mcp.config import Settings
from ridelogger_mcp.state import get_state

logger = logging.getLogger(__name__)

OAUTH_SCOPES: list[str] = [
    "profile:read",
    "vehicles:read",
    "vehicles:write",
    "logs:read",
    "logs:write",
    "files:read",
    "files:write",
]


class RideLoggerTokenVerifier(TokenVerifier):
    """Validate OAuth bearer tokens against the RideLogger API."""

    @property
    def scopes_supported(self) -> list[str]:
        return OAUTH_SCOPES

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            data = await self._auth_me(token)
        except Exception as exc:
            logger.info("Bearer token rejected by /auth/me: %s", exc)
            return None

        user = data.get("data", data) if isinstance(data, dict) else {}
        user_id = user.get("id") if isinstance(user, dict) else None

        return AccessToken(
            token=token,
            client_id="ridelogger-oauth",
            scopes=OAUTH_SCOPES,
            claims={"user_id": user_id} if user_id is not None else {},
        )

    async def _auth_me(self, token: str) -> Any:
        try:
            st = get_state()
        except RuntimeError:
            settings = Settings()
            client = ApiClient(settings)
            try:
                return await client.request_json("GET", "/auth/me", token=token)
            finally:
                await client.aclose()

        return await st.client.request_json("GET", "/auth/me", token=token)


def create_auth_provider() -> RemoteAuthProvider:
    """Create FastMCP auth provider without requiring full app settings at import time."""

    authorization_server = os.getenv("OAUTH_AUTHORIZATION_SERVER", "https://api.ridelogger.com")
    resource_url = os.getenv("OAUTH_RESOURCE_URL", "https://mcp.ridelogger.com/mcp")
    base_url = resource_url.rsplit("/", 1)[0]

    verifier = RideLoggerTokenVerifier(base_url=base_url)

    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[authorization_server],
        base_url=base_url,
        resource_base_url=base_url,
        scopes_supported=OAUTH_SCOPES,
        resource_name="RideLogger MCP",
    )
