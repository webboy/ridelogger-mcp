"""Async HTTP client for RideLogger API (Bearer JWT)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ridelogger_mcp.config import Settings
from ridelogger_mcp.errors import raise_for_status
from ridelogger_mcp.logging_setup import get_request_id

logger = logging.getLogger(__name__)

_UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"
_SIG_VERSION = "v1"


def _request_target(url: httpx.URL) -> str:
    q = url.query.decode("ascii") if url.query else ""
    return url.path + (f"?{q}" if q else "")


def _canonical_string(
    method: str,
    request_target: str,
    timestamp: str,
    nonce: str,
    content_sha256: str,
) -> bytes:
    parts = [method.upper(), request_target, timestamp, nonce, content_sha256]
    return "\n".join(parts).encode("utf-8")


class ApiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.api_base,
            timeout=httpx.Timeout(settings.http_timeout_s),
            headers={"Accept": "application/json"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def _signing_enabled(self) -> bool:
        s = self._settings
        return bool(
            (s.api_consumer_secret or "").strip() and (s.api_consumer_key_id or "").strip()
        )

    def _headers(self, token: str | None) -> dict[str, str]:
        h: dict[str, str] = {}
        rid = get_request_id()
        if rid:
            h["X-Request-Id"] = rid
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _signing_headers(
        self,
        *,
        method: str,
        url: httpx.URL,
        content_sha256_for_sig: str,
    ) -> dict[str, str]:
        ts = str(int(time.time()))
        nonce = str(uuid.uuid4())
        request_target = _request_target(url)
        canonical = _canonical_string(
            method, request_target, ts, nonce, content_sha256_for_sig
        )
        secret = self._settings.api_consumer_secret.strip().encode("utf-8")
        sig_hex = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
        code = (self._settings.api_consumer_code or "").strip() or "mcp"
        kid = self._settings.api_consumer_key_id.strip()

        return {
            "X-Api-Consumer": code,
            "X-Api-Key-Id": kid,
            "X-Api-Timestamp": ts,
            "X-Api-Nonce": nonce,
            "X-Api-Content-SHA256": content_sha256_for_sig,
            "X-Api-Signature": f"{_SIG_VERSION}={sig_hex}",
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        base_headers = self._headers(token)
        req = self._client.build_request(
            method,
            path,
            headers=base_headers,
            params=params,
            json=json_body,
            files=files,
            data=data,
        )

        if self._signing_enabled:
            use_unsigned = bool(files)
            if use_unsigned:
                sha_for_sig = _UNSIGNED_PAYLOAD
            else:
                body = req.content or b""
                sha_for_sig256 = hashlib.sha256(body).hexdigest()
                sha_for_sig = sha_for_sig256.lower()

            for k, v in self._signing_headers(
                method=method,
                url=req.url,
                content_sha256_for_sig=sha_for_sig,
            ).items():
                req.headers[k] = v

        return await self._client.send(req)

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        resp = await self.request(
            method,
            path,
            token=token,
            params=params,
            json_body=json_body,
            files=files,
            data=data,
        )
        raise_for_status(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def request_bytes(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[bytes, httpx.Headers]:
        resp = await self.request(method, path, token=token, params=params)
        raise_for_status(resp)
        return resp.content, resp.headers

    async def get_public_json(self, path: str) -> Any:
        """GET without auth — used for reference data preload."""
        max_attempts = max(1, int(self._settings.http_max_retries) + 1)
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            reraise=True,
        ):
            with attempt:
                resp = await self.request("GET", path, token=None)
                raise_for_status(resp)
                return resp.json()
