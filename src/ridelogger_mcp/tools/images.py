"""Vehicle gallery images."""

from __future__ import annotations

import base64
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
from ridelogger_mcp.tools.common import require_token, tool_error, tool_success


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="vehicle_images_list",
        annotations=get_annotations("vehicle_images_list"),
        exclude_args=["access_token"],
        description=(
            "[READ] List gallery images for a vehicle (GET /api/vehicles/{vehicle_id}/images). "
            "Requires OAuth/Bearer authorization."
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_images_get",
        annotations=get_annotations("vehicle_images_get"),
        exclude_args=["access_token"],
        description=(
            "[READ] Download one gallery image (GET /api/vehicles/{vehicle_id}/images/{image_id}). "
            "Requires OAuth/Bearer authorization. Returns JSON with base64, content_type, filename_hint."
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
        annotations=get_annotations("vehicle_images_create"),
        exclude_args=["access_token"],
        meta={"openai/fileParams": ["image"]},
        description=(
            "[WRITE] Upload a gallery image (POST /api/vehicles/{vehicle_id}/images). "
            "Requires OAuth/Bearer authorization. "
            "Exactly one file source: (1) ChatGPT attachment via the `image` file-reference object "
            "(OpenAI download_url + file_id), (2) RideLogger `chat_upload_id` UUID from ai_chat_uploaded_files "
            "(not an OpenAI file_id), or (3) file_base64 + file_name. "
            "Image files only, max 10 MB."
        ),
    )
    async def vehicle_images_create(
        vehicle_id: int,
        image: ChatGptFileReference | None = None,
        file_name: str | None = None,
        file_base64: str | None = None,
        chat_upload_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        downloaded = None
        try:
            token = require_token(access_token)
            st = get_state()
            files, upload_id, downloaded = await prepare_multipart_file(
                field_name="image",
                chatgpt_file=image,
                chat_upload_id=chat_upload_id,
                file_base64=file_base64,
                file_name=file_name,
                policy=FileInputPolicy.VEHICLE_IMAGE,
            )
            if upload_id:
                resp = await st.client.request(
                    "POST",
                    f"/vehicles/{vehicle_id}/images",
                    token=token,
                    data={"chat_upload_id": upload_id},
                )
            else:
                resp = await st.client.request(
                    "POST",
                    f"/vehicles/{vehicle_id}/images",
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

    @mcp.tool(
        name="vehicle_images_delete",
        annotations=get_annotations("vehicle_images_delete"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Delete gallery image (DELETE .../images/{image_id}). Requires OAuth/Bearer authorization."
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)
