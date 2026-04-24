"""Tests for /.well-known/openai-apps-challenge domain-verification endpoint.

Endpoint serves the OpenAI Apps domain-verification token (copied from the
OpenAI Platform dashboard) as plain text when OPENAI_APPS_CHALLENGE_TOKEN
is set, and 404 when it is not.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest
from starlette.testclient import TestClient


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
