"""Async HTTP client for RideLogger API (Bearer JWT)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ridelogger_mcp.config import Settings
from ridelogger_mcp.errors import raise_for_status
from ridelogger_mcp.logging_setup import get_request_id

logger = logging.getLogger(__name__)


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

    def _headers(self, token: str | None) -> dict[str, str]:
        h: dict[str, str] = {}
        rid = get_request_id()
        if rid:
            h["X-Request-Id"] = rid
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

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
        return await self._client.request(
            method,
            path,
            headers=self._headers(token),
            params=params,
            json=json_body,
            files=files,
            data=data,
        )

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

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def get_public_json(self, path: str) -> Any:
        """GET without auth — used for reference data preload."""
        resp = await self._client.get(path, headers=self._headers(None))
        raise_for_status(resp)
        return resp.json()
