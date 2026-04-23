"""User profile tools: avatar upload."""

from __future__ import annotations

import base64
import io
from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.errors import raise_for_status
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="user_avatar_upload",
        annotations=get_annotations("user_avatar_upload"),
        description=(
            "[WRITE] Upload or replace the authenticated user's profile avatar "
            "(POST /api/avatar). "
            "Requires access_token or HTTP Bearer. "
            "Exactly one of: (1) chat_upload_id — UUID from AI chat attachment "
            "(ai_chat_uploaded_files), (2) file_base64 + file_name. "
            "When using chat_upload_id, the image is taken from the chat upload — "
            "no binary data needed. "
            "Returns the updated user profile on success."
        ),
    )
    async def user_avatar_upload(
        file_name: str | None = None,
        file_base64: str | None = None,
        chat_upload_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()

            if chat_upload_id and (file_base64 or file_name):
                raise ValueError("Use either chat_upload_id or file_base64+file_name, not both.")

            if chat_upload_id:
                resp = await st.client.request(
                    "POST",
                    "/user/avatar",
                    token=token,
                    data={"chat_upload_id": chat_upload_id.strip()},
                )
            elif file_base64 and file_name:
                raw = base64.b64decode(file_base64)
                files = {
                    "avatar": (file_name, io.BytesIO(raw), "application/octet-stream"),
                }
                resp = await st.client.request(
                    "POST",
                    "/user/avatar",
                    token=token,
                    files=files,
                )
            else:
                raise ValueError("Provide chat_upload_id, or file_base64 + file_name.")

            raise_for_status(resp)
            data = resp.json() if resp.content else None
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
