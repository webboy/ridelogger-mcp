"""Vehicle gallery images."""

from __future__ import annotations

import base64
import io
from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.state import get_state
from ridelogger_mcp.errors import raise_for_status
from ridelogger_mcp.tools.common import require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="vehicle_images_list",
        description=(
            "[READ] List gallery images for a vehicle (GET /api/vehicles/{vehicle_id}/images). "
            "Requires access_token or HTTP Bearer."
        ),
    )
    async def vehicle_images_list(
        vehicle_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/images",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_images_get",
        description=(
            "[READ] Download one gallery image (GET /api/vehicles/{vehicle_id}/images/{image_id}). "
            "Requires access_token or HTTP Bearer. Returns JSON with base64, content_type, filename_hint."
        ),
    )
    async def vehicle_images_get(
        vehicle_id: int,
        image_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            raw, headers = await st.client.request_bytes(
                "GET",
                f"/vehicles/{vehicle_id}/images/{image_id}",
                token=token,
            )
            ct = headers.get("content-type", "application/octet-stream")
            cd = headers.get("content-disposition", "")
            name = None
            if "filename=" in cd:
                name = cd.split("filename=")[-1].strip('"')
            return {
                "ok": True,
                "data": {
                    "encoding": "base64",
                    "content": base64.b64encode(raw).decode("ascii"),
                    "content_type": ct,
                    "filename_hint": name,
                },
            }
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_images_create",
        description=(
            "[WRITE] Upload a gallery image (POST /api/vehicles/{vehicle_id}/images). "
            "Requires access_token or HTTP Bearer. "
            "Exactly one of: (1) chat_upload_id — UUID from AI chat attachment (ai_chat_uploaded_files), "
            "(2) file_base64 + file_name, (3) file_path on the MCP host. "
            "When using chat_upload_id, send form field chat_upload_id only (no binary)."
        ),
    )
    async def vehicle_images_create(
        vehicle_id: int,
        file_name: str | None = None,
        file_base64: str | None = None,
        file_path: str | None = None,
        chat_upload_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            if chat_upload_id and (file_path or file_base64 or file_name):
                raise ValueError("Use either chat_upload_id or file upload fields, not both.")
            if chat_upload_id:
                resp = await st.client.request(
                    "POST",
                    f"/vehicles/{vehicle_id}/images",
                    token=token,
                    data={"chat_upload_id": chat_upload_id.strip()},
                )
            else:
                if file_path:
                    with open(file_path, "rb") as f:
                        raw = f.read()
                elif file_base64 and file_name:
                    raw = base64.b64decode(file_base64)
                else:
                    raise ValueError("Provide chat_upload_id, or file_base64+file_name, or file_path.")
                fname = file_name or "upload.bin"
                files = {
                    "image": (fname, io.BytesIO(raw), "application/octet-stream"),
                }
                resp = await st.client.request(
                    "POST",
                    f"/vehicles/{vehicle_id}/images",
                    token=token,
                    files=files,
                )
            raise_for_status(resp)
            data = resp.json() if resp.content else None
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_images_delete",
        description=(
            "[WRITE] Delete gallery image (DELETE .../images/{image_id}). Requires access_token or HTTP Bearer."
        ),
    )
    async def vehicle_images_delete(
        vehicle_id: int,
        image_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/images/{image_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
