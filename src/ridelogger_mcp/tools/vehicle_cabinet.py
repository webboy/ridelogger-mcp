"""Vehicle cabinet (private per-vehicle documents)."""

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
        name="vehicle_cabinet_list",
        annotations=get_annotations("vehicle_cabinet_list"),
        exclude_args=["access_token"],
        description=(
            "[READ] List cabinet documents for a vehicle "
            "(GET /api/vehicles/{vehicle_id}/cabinet-documents). Requires OAuth/Bearer authorization."
        ),
    )
    async def vehicle_cabinet_list(
        vehicle_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/cabinet-documents",
                token=token,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_cabinet_get",
        annotations=get_annotations("vehicle_cabinet_get"),
        exclude_args=["access_token"],
        description=(
            "[READ] Show one cabinet document metadata "
            "(GET /api/vehicles/{vehicle_id}/cabinet-documents/{document_id}). Requires OAuth/Bearer authorization."
        ),
    )
    async def vehicle_cabinet_get(
        vehicle_id: int,
        document_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/cabinet-documents/{document_id}",
                token=token,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_cabinet_download",
        annotations=get_annotations("vehicle_cabinet_download"),
        exclude_args=["access_token"],
        description=(
            "[READ] Download cabinet file bytes "
            "(GET /api/vehicles/{vehicle_id}/cabinet-documents/{document_id}/download). "
            "Returns JSON with base64, content_type, filename_hint."
        ),
    )
    async def vehicle_cabinet_download(
        vehicle_id: int,
        document_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            raw, headers = await st.client.request_bytes(
                "GET",
                f"/vehicles/{vehicle_id}/cabinet-documents/{document_id}/download",
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
        name="vehicle_cabinet_create",
        annotations=get_annotations("vehicle_cabinet_create"),
        exclude_args=["access_token"],
        meta={"openai/fileParams": ["cabinet_file"]},
        description=(
            "[WRITE] Upload a cabinet document (POST /api/vehicles/{vehicle_id}/cabinet-documents). "
            "Multipart: title, document_category, optional description/issued_at/expires_at, cabinet_file. "
            "Exactly one file source: (1) ChatGPT attachment via `cabinet_file` file-reference object "
            "(OpenAI download_url + file_id), (2) RideLogger `chat_upload_id` UUID from ai_chat_uploaded_files "
            "(not an OpenAI file_id), or (3) file_base64 + file_name. Max 10 MB; allowed extensions match API allowlist."
        ),
    )
    async def vehicle_cabinet_create(
        vehicle_id: int,
        title: str,
        document_category: str,
        description: str | None = None,
        issued_at: str | None = None,
        expires_at: str | None = None,
        cabinet_file: ChatGptFileReference | None = None,
        chat_upload_id: str | None = None,
        file_name: str | None = None,
        file_base64: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        downloaded = None
        try:
            token = require_token(access_token)
            st = get_state()
            files, upload_id, downloaded = await prepare_multipart_file(
                field_name="cabinet_file",
                chatgpt_file=cabinet_file,
                chat_upload_id=chat_upload_id,
                file_base64=file_base64,
                file_name=file_name,
                policy=FileInputPolicy.CABINET,
            )
            data: dict[str, Any] = {
                "title": title,
                "document_category": document_category,
            }
            if upload_id:
                data["chat_upload_id"] = upload_id
            if description:
                data["description"] = description
            if issued_at:
                data["issued_at"] = issued_at
            if expires_at:
                data["expires_at"] = expires_at
            resp = await st.client.request(
                "POST",
                f"/vehicles/{vehicle_id}/cabinet-documents",
                token=token,
                files=files,
                data=data,
            )
            raise_for_status(resp)
            out = resp.json() if resp.content else None
            return tool_success(out)
        except Exception as e:
            return tool_error(e)
        finally:
            if downloaded is not None:
                downloaded.close()

    @mcp.tool(
        name="vehicle_cabinet_update",
        annotations=get_annotations("vehicle_cabinet_update"),
        exclude_args=["access_token"],
        meta={"openai/fileParams": ["cabinet_file"]},
        description=(
            "[WRITE] Update cabinet document metadata and/or replace file "
            "(PUT /api/vehicles/{vehicle_id}/cabinet-documents/{document_id}). "
            "Optional file replacement via ChatGPT `cabinet_file` attachment, or file_base64 + file_name. "
            "Metadata-only update when no file source is provided. "
            "RideLogger chat_upload_id is not supported on update."
        ),
    )
    async def vehicle_cabinet_update(
        vehicle_id: int,
        document_id: int,
        title: str | None = None,
        document_category: str | None = None,
        description: str | None = None,
        issued_at: str | None = None,
        expires_at: str | None = None,
        cabinet_file: ChatGptFileReference | None = None,
        file_name: str | None = None,
        file_base64: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        downloaded = None
        try:
            token = require_token(access_token)
            st = get_state()
            files, _upload_id, downloaded = await prepare_multipart_file(
                field_name="cabinet_file",
                chatgpt_file=cabinet_file,
                chat_upload_id=None,
                file_base64=file_base64,
                file_name=file_name,
                policy=FileInputPolicy.CABINET,
                allow_no_file=True,
            )

            if files is not None:
                data: dict[str, Any] = {}
                if title is not None:
                    data["title"] = title
                if document_category is not None:
                    data["document_category"] = document_category
                if description is not None:
                    data["description"] = description
                if issued_at is not None:
                    data["issued_at"] = issued_at
                if expires_at is not None:
                    data["expires_at"] = expires_at
                resp = await st.client.request(
                    "PUT",
                    f"/vehicles/{vehicle_id}/cabinet-documents/{document_id}",
                    token=token,
                    files=files,
                    data=data,
                )
            else:
                body: dict[str, Any] = {}
                if title is not None:
                    body["title"] = title
                if document_category is not None:
                    body["document_category"] = document_category
                if description is not None:
                    body["description"] = description
                if issued_at is not None:
                    body["issued_at"] = issued_at
                if expires_at is not None:
                    body["expires_at"] = expires_at
                resp = await st.client.request(
                    "PUT",
                    f"/vehicles/{vehicle_id}/cabinet-documents/{document_id}",
                    token=token,
                    json_body=body,
                )
            raise_for_status(resp)
            out = resp.json() if resp.content else None
            return tool_success(out)
        except Exception as e:
            return tool_error(e)
        finally:
            if downloaded is not None:
                downloaded.close()

    @mcp.tool(
        name="vehicle_cabinet_delete",
        annotations=get_annotations("vehicle_cabinet_delete"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Delete cabinet document (DELETE .../cabinet-documents/{document_id}). "
            "Requires OAuth/Bearer authorization."
        ),
    )
    async def vehicle_cabinet_delete(
        vehicle_id: int,
        document_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            resp = await st.client.request(
                "DELETE",
                f"/vehicles/{vehicle_id}/cabinet-documents/{document_id}",
                token=token,
            )
            raise_for_status(resp)
            data = resp.json() if resp.content else None
            return tool_success(data)
        except Exception as e:
            return tool_error(e)
