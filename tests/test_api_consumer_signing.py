"""HMAC request signing for API consumer (must match Laravel ApiConsumerSignerVerifier)."""

from __future__ import annotations

import hashlib
import hmac

import httpx

from ridelogger_mcp.api_client import (
    _UNSIGNED_PAYLOAD,
    _canonical_string,
    _request_target,
)


def test_request_target_get_without_query():
    u = httpx.URL("https://example.com/api/currencies")
    assert _request_target(u) == "/api/currencies"


def test_request_target_get_with_query():
    u = httpx.URL("https://example.com/api/foo?a=1&b=two")
    assert _request_target(u) == "/api/foo?a=1&b=two"


def test_canonical_json_post_matches_server_shape():
    method = "POST"
    request_target = "/api/auth/login"
    ts = "1700000000"
    nonce = "550e8400-e29b-41d4-a716-446655440000"
    raw = b'{"email":"a@b.com","password":"x"}'
    content_sha = hashlib.sha256(raw).hexdigest()
    assert content_sha == content_sha.lower()
    c = _canonical_string(method, request_target, ts, nonce, content_sha)
    assert (
        c.decode("utf-8")
        == f"POST\n{request_target}\n{ts}\n{nonce}\n{content_sha}"
    )


def test_canonical_get_empty_body():
    method = "GET"
    request_target = "/api/currencies"
    ts = "1700000001"
    nonce = "n1"
    content_sha = hashlib.sha256(b"").hexdigest()
    c = _canonical_string(method, request_target, ts, nonce, content_sha)
    lines = c.decode("utf-8").split("\n")
    assert lines[0] == "GET"
    assert lines[4] == content_sha


def test_canonical_multipart_unsigned_payload():
    c = _canonical_string(
        "POST", "/api/upload", "1700000002", "n2", _UNSIGNED_PAYLOAD
    )
    assert c.decode("utf-8").endswith(_UNSIGNED_PAYLOAD)


def test_hmac_format_v1_hex():
    secret = b"test-secret-key-for-hmac-32bytes!!"
    canonical = _canonical_string(
        "GET", "/api/x", "1", "u", hashlib.sha256(b"").hexdigest()
    )
    sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
    assert len(sig) == 64
    assert sig == sig.lower()
