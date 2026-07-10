"""User profile tools: avatar upload."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.file_inputs import (
    ChatGptFileReference,
    FileInputPolicy,
    prepare_multipart_file,
)
from ridelogger_mcp.state import get_state
from ridelogger_mcp.errors import raise_for_status
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import tool_error, tool_success, ToolToken

_FILE_SOURCE_HELP = (
    "Exactly one file source: (1) ChatGPT attachment via the `avatar` file-reference object "
    "(OpenAI download_url + file_id), (2) RideLogger `chat_upload_id` UUID from ai_chat_uploaded_files "
    "(AI/PWA pipeline — not an OpenAI file_id), or (3) file_base64 + file_name for other MCP clients."
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="user_avatar_upload",
        annotations=get_annotations("user_avatar_upload"),
        meta={"openai/fileParams": ["avatar"]},
        description=(
            "[WRITE] Upload or replace the authenticated user's profile avatar "
            "(POST /api/user/avatar). "
            "Requires OAuth/Bearer authorization. "
            + _FILE_SOURCE_HELP
            + " Image files only, max 10 MB. "
            "Returns the updated user profile on success."
        ),
    )
    async def user_avatar_upload(
        avatar: ChatGptFileReference | None = None,
        file_name: str | None = None,
        file_base64: str | None = None,
        chat_upload_id: str | None = None,
        token: str = ToolToken,
    ) -> dict[str, Any]:
        downloaded = None
        try:
            st = get_state()

            files, upload_id, downloaded = await prepare_multipart_file(
                field_name="avatar",
                chatgpt_file=avatar,
                chat_upload_id=chat_upload_id,
                file_base64=file_base64,
                file_name=file_name,
                policy=FileInputPolicy.AVATAR_IMAGE,
            )

            if upload_id:
                resp = await st.client.request(
                    "POST",
                    "/user/avatar",
                    token=token,
                    data={"chat_upload_id": upload_id},
                )
            else:
                resp = await st.client.request(
                    "POST",
                    "/user/avatar",
                    token=token,
                    files=files,
                )

            raise_for_status(resp)
            data = resp.json() if resp.content else None
            return tool_success(data)
        except Exception as e:
            return tool_error(e)
        finally:
            if downloaded is not None:
                downloaded.close()
