"""Vehicle cabinet (private per-vehicle documents)."""

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
        name="vehicle_cabinet_list",
        annotations=get_annotations("vehicle_cabinet_list"),
        description=(
            "[READ] List cabinet documents for a vehicle "
            "(GET /api/vehicles/{vehicle_id}/cabinet-documents). Requires access_token or HTTP Bearer."
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
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_cabinet_get",
        annotations=get_annotations("vehicle_cabinet_get"),
        description=(
            "[READ] Show one cabinet document metadata "
            "(GET /api/vehicles/{vehicle_id}/cabinet-documents/{document_id}). Requires access_token or HTTP Bearer."
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
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_cabinet_download",
        annotations=get_annotations("vehicle_cabinet_download"),
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
        description=(
            "[WRITE] Upload a cabinet document (POST /api/vehicles/{vehicle_id}/cabinet-documents). "
            "Multipart: title, document_category, optional description/issued_at/expires_at, cabinet_file. "
            "Provide exactly one file source: chat_upload_id or file_base64 + file_name."
        ),
    )
    async def vehicle_cabinet_create(
        vehicle_id: int,
        title: str,
        document_category: str,
        description: str | None = None,
        issued_at: str | None = None,
        expires_at: str | None = None,
        chat_upload_id: str | None = None,
        file_name: str | None = None,
        file_base64: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            has_binary_source = bool(file_base64)
            if chat_upload_id and has_binary_source:
                raise ValueError("Use either chat_upload_id or file upload fields, not both.")

            files = None
            if chat_upload_id:
                fname = None
                raw = None
            elif file_base64 and file_name:
                raw = base64.b64decode(file_base64)
                fname = file_name
            else:
                raise ValueError("Provide chat_upload_id, or file_base64+file_name.")
            if raw is not None and fname is not None:
                files = {"cabinet_file": (fname, io.BytesIO(raw), "application/octet-stream")}
            data: dict[str, Any] = {
                "title": title,
                "document_category": document_category,
            }
            if chat_upload_id:
                data["chat_upload_id"] = chat_upload_id.strip()
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
            return {"ok": True, "data": out}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_cabinet_update",
        annotations=get_annotations("vehicle_cabinet_update"),
        description=(
            "[WRITE] Update cabinet document metadata and/or replace file "
            "(PUT /api/vehicles/{vehicle_id}/cabinet-documents/{document_id}). "
            "Optional file_base64 + file_name for cabinet_file."
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
        file_name: str | None = None,
        file_base64: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            raw = None
            fname = None
            if file_base64 and file_name:
                raw = base64.b64decode(file_base64)
                fname = file_name

            if raw is not None and fname is not None:
                files = {"cabinet_file": (fname, io.BytesIO(raw), "application/octet-stream")}
                data = {}
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
            return {"ok": True, "data": out}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_cabinet_delete",
        annotations=get_annotations("vehicle_cabinet_delete"),
        description=(
            "[WRITE] Delete cabinet document (DELETE .../cabinet-documents/{document_id}). "
            "Requires access_token or HTTP Bearer."
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
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)
