"""Tests for /.well-known/openai-apps-challenge domain-verification endpoint.

Endpoint serves the OpenAI Apps domain-verification token (copied from the
OpenAI Platform dashboard) as plain text when OPENAI_APPS_CHALLENGE_TOKEN
is set, and 404 when it is not.
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest import mock

import pytest
from starlette.testclient import TestClient


async def _sleeping_refresh_loop(_self):
    await asyncio.sleep(3600)


def _initialize_mcp_session(client: TestClient) -> dict[str, str]:
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
    }
    response = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        },
    )
    assert response.status_code == 200
    session_id = response.headers.get("mcp-session-id")
    assert session_id
    return {**headers, "mcp-session-id": session_id}


@pytest.fixture()
def client_with_token():
    """Build a TestClient with the challenge token set via env."""
    with mock.patch.dict(
        os.environ,
        {
            "SK_API_URL": "https://api.servisna-knjizica.com",
            "OPENAI_APPS_CHALLENGE_TOKEN": "test-challenge-token-abc123",
        },
        clear=False,
    ):
        from ridelogger_mcp.app import mcp

        app = mcp.http_app()
        with TestClient(app) as c:
            yield c


@pytest.fixture()
def client_without_token():
    """Build a TestClient with no challenge token (empty string)."""
    with mock.patch.dict(
        os.environ,
        {
            "SK_API_URL": "https://api.servisna-knjizica.com",
            "OPENAI_APPS_CHALLENGE_TOKEN": "",
        },
        clear=False,
    ):
        from ridelogger_mcp.app import mcp

        app = mcp.http_app()
        with TestClient(app) as c:
            yield c


def test_challenge_returns_token_as_plain_text(client_with_token):
    r = client_with_token.get("/.well-known/openai-apps-challenge")
    assert r.status_code == 200
    assert r.text == "test-challenge-token-abc123"
    assert r.headers["content-type"].startswith("text/plain")


def test_challenge_returns_404_when_token_unset(client_without_token):
    r = client_without_token.get("/.well-known/openai-apps-challenge")
    assert r.status_code == 404


def test_mcp_discovery_is_public_for_openai_platform_scan():
    with mock.patch.dict(os.environ, {"SK_API_URL": "https://api.ridelogger.com"}, clear=False):
        from ridelogger_mcp.app import mcp
        from ridelogger_mcp.reference_cache import ReferenceCache

        with (
            mock.patch.object(ReferenceCache, "refresh", new=mock.AsyncMock()),
            mock.patch.object(ReferenceCache, "refresh_loop", new=_sleeping_refresh_loop),
        ):
            app = mcp.http_app()
            with TestClient(app) as client:
                headers = _initialize_mcp_session(client)
                response = client.post(
                    "/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                )

    assert response.status_code == 200
    assert "auth_me" in response.text
    assert "vehicle_cabinet_list" in response.text
    assert "auth_login" not in response.text


def test_mcp_discovery_accepts_octet_stream_json_for_openai_platform_scan():
    with mock.patch.dict(os.environ, {"SK_API_URL": "https://api.ridelogger.com"}, clear=False):
        from ridelogger_mcp.app import http_middleware, mcp
        from ridelogger_mcp.reference_cache import ReferenceCache

        with (
            mock.patch.object(ReferenceCache, "refresh", new=mock.AsyncMock()),
            mock.patch.object(ReferenceCache, "refresh_loop", new=_sleeping_refresh_loop),
        ):
            app = mcp.http_app(middleware=http_middleware())
            with TestClient(app) as client:
                headers = {
                    "accept": "*/*",
                    "content-type": "application/octet-stream",
                }
                initialize_response = client.post(
                    "/mcp",
                    headers=headers,
                    content=json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2025-03-26",
                                "capabilities": {},
                                "clientInfo": {"name": "platform-scan", "version": "1.0"},
                            },
                        }
                    ),
                )
                headers["mcp-session-id"] = initialize_response.headers["mcp-session-id"]
                response = client.post(
                    "/mcp",
                    headers=headers,
                    content=json.dumps(
                        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
                    ),
                )

    assert initialize_response.status_code == 200
    assert response.status_code == 200
    assert "vehicle_cabinet_list" in response.text
    assert "auth_login" not in response.text


def test_empty_mcp_post_returns_oauth_challenge_for_platform_probe():
    with mock.patch.dict(os.environ, {"SK_API_URL": "https://api.ridelogger.com"}, clear=False):
        from ridelogger_mcp.app import http_middleware, mcp
        from ridelogger_mcp.reference_cache import ReferenceCache

        with (
            mock.patch.object(ReferenceCache, "refresh", new=mock.AsyncMock()),
            mock.patch.object(ReferenceCache, "refresh_loop", new=_sleeping_refresh_loop),
        ):
            app = mcp.http_app(middleware=http_middleware())
            with TestClient(app) as client:
                response = client.post(
                    "/mcp",
                    headers={"accept": "*/*", "content-type": "application/octet-stream"},
                    content=b"",
                )

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"
    assert "resource_metadata=" in response.headers["www-authenticate"]


def test_oauth_protected_resource_aliases_for_platform_discovery():
    with mock.patch.dict(os.environ, {"SK_API_URL": "https://api.ridelogger.com"}, clear=False):
        from ridelogger_mcp.app import mcp
        from ridelogger_mcp.reference_cache import ReferenceCache

        with (
            mock.patch.object(ReferenceCache, "refresh", new=mock.AsyncMock()),
            mock.patch.object(ReferenceCache, "refresh_loop", new=_sleeping_refresh_loop),
        ):
            app = mcp.http_app()
            with TestClient(app) as client:
                responses = [
                    client.get("/.well-known/oauth-protected-resource"),
                    client.get("/.well-known/oauth-protected-resource/mcp"),
                    client.get("/mcp/.well-known/oauth-protected-resource"),
                ]

    assert all(response.status_code == 200 for response in responses)
    assert {response.json()["resource"] for response in responses} == {"https://mcp.ridelogger.com/mcp"}


def test_user_data_tool_call_without_bearer_returns_auth_error():
    with mock.patch.dict(os.environ, {"SK_API_URL": "https://api.ridelogger.com"}, clear=False):
        from ridelogger_mcp.app import mcp
        from ridelogger_mcp.reference_cache import ReferenceCache

        with (
            mock.patch.object(ReferenceCache, "refresh", new=mock.AsyncMock()),
            mock.patch.object(ReferenceCache, "refresh_loop", new=_sleeping_refresh_loop),
        ):
            app = mcp.http_app()
            with TestClient(app) as client:
                headers = _initialize_mcp_session(client)
                response = client.post(
                    "/mcp",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "auth_me", "arguments": {}},
                    },
                )

    assert response.status_code == 200
    assert "Authorization is required" in response.text
