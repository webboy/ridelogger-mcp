"""Map upstream HTTP errors to actionable messages."""

from __future__ import annotations

import json
from typing import Any

import httpx


class UpstreamApiError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        body: Any = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.body = body
        super().__init__(message)


def _extract_message(body: Any) -> str | None:
    if isinstance(body, dict):
        if "message" in body and isinstance(body["message"], str):
            return body["message"]
        err = body.get("errors")
        if isinstance(err, dict) and err:
            parts = []
            for k, v in err.items():
                if isinstance(v, list):
                    parts.append(f"{k}: {', '.join(str(x) for x in v)}")
                else:
                    parts.append(f"{k}: {v}")
            if parts:
                return "; ".join(parts)
    return None


def raise_for_status(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    body: Any = None
    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = resp.text[:2000] if resp.text else None
    msg = _extract_message(body) if isinstance(body, dict) else None
    if not msg:
        msg = resp.reason_phrase or f"HTTP {resp.status_code}"
    hint = ""
    if resp.status_code == 401:
        hint = " Token may be expired or invalid; reconnect or reauthorize the MCP client."
    elif resp.status_code == 402:
        hint = " Premium plan required for this action."
    elif resp.status_code == 403:
        hint = " You may lack permission for this vehicle or action."
    elif resp.status_code == 404:
        hint = " Resource not found; check vehicle_id and related ids."
    elif resp.status_code == 422:
        hint = " Validation failed; fix body fields and retry."
    elif resp.status_code == 429:
        hint = " Rate limited; wait and retry."
    elif resp.status_code >= 500:
        hint = " Upstream server error; retry later."

    raise UpstreamApiError(
        resp.status_code,
        f"{msg}{hint}",
        body=body,
    )
