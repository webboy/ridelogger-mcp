"""Generic vehicle logs (aggregated) and attachments."""

from __future__ import annotations

import base64
import io
from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.errors import raise_for_status
from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import (
    LOG_REFS_HINT,
    MONEY_LOGS_HINT,
    body_from_kwargs,
    require_token,
    tool_error,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="generic_vehicle_logs_list",
        description=(
            "List all vehicle log entries for a vehicle (fuel, service, expense) — "
            "GET /api/vehicles/{vehicle_id}/vehicle_logs. Requires access_token or HTTP Bearer. "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def generic_vehicle_logs_list(
        vehicle_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/vehicle_logs",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="generic_vehicle_logs_delete",
        description=(
            "Delete a generic vehicle log row (DELETE /api/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}). "
            "Requires access_token or HTTP Bearer. Returns 202 on success."
        ),
    )
    async def generic_vehicle_logs_delete(
        vehicle_id: int,
        vehicle_log_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_list",
        description=(
            "List file attachments on a vehicle log (GET .../vehicle_logs/{vehicle_log_id}/get_files). "
            "Requires access_token or HTTP Bearer."
        ),
    )
    async def vehicle_log_files_list(
        vehicle_id: int,
        vehicle_log_id: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}/get_files",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_upload",
        description=(
            "Upload attachment via multipart (POST .../put_files). Field name vehicle_log_file for binary. "
            "Requires access_token or HTTP Bearer. Exactly one of: chat_upload_id (AI chat attachment UUID), "
            "or file_base64 + file_name, or file_path. "
            "Non-premium users: at most one attachment per vehicle log; if one already exists, API returns 403 "
            "(remove it with vehicle_log_files_delete or use a premium account). Premium: multiple attachments allowed."
        ),
    )
    async def vehicle_log_files_upload(
        vehicle_id: int,
        vehicle_log_id: int,
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
                raise ValueError("Use either chat_upload_id or file fields, not both.")
            if chat_upload_id:
                resp = await st.client.request(
                    "POST",
                    f"/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}/put_files",
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
                    "vehicle_log_file": (fname, io.BytesIO(raw), "application/octet-stream"),
                }
                resp = await st.client.request(
                    "POST",
                    f"/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}/put_files",
                    token=token,
                    files=files,
                )
            raise_for_status(resp)
            data = resp.json() if resp.content else None
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_upload_base64",
        description=(
            "Upload attachment via JSON body (POST .../put_files_cordova). "
            "Requires access_token or HTTP Bearer. "
            "Either chat_upload_id (AI chat attachment UUID), or vehicle_log_file (base64) + vehicle_log_file_name — "
            "mutually exclusive. "
            "Non-premium: max one file per log (403 if a file is already attached; delete first or upgrade). "
            "Premium: multiple allowed."
        ),
    )
    async def vehicle_log_files_upload_base64(
        vehicle_id: int,
        vehicle_log_id: int,
        chat_upload_id: str | None = None,
        vehicle_log_file: str | None = None,
        vehicle_log_file_name: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            if chat_upload_id and (vehicle_log_file or vehicle_log_file_name):
                raise ValueError("Use either chat_upload_id or base64 file fields, not both.")
            if chat_upload_id:
                body: dict[str, Any] = {"chat_upload_id": chat_upload_id.strip()}
            else:
                if not vehicle_log_file or not vehicle_log_file_name:
                    raise ValueError("Provide chat_upload_id, or both vehicle_log_file and vehicle_log_file_name.")
                body = body_from_kwargs(
                    vehicle_log_file=vehicle_log_file,
                    vehicle_log_file_name=vehicle_log_file_name,
                )
            st = get_state()
            data = await st.client.request_json(
                "POST",
                f"/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}/put_files_cordova",
                token=token,
                json_body=body,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_delete",
        description=(
            "Delete one attachment by media uuid (DELETE .../delete_files/{uuid}). Requires access_token or HTTP Bearer."
        ),
    )
    async def vehicle_log_files_delete(
        vehicle_id: int,
        vehicle_log_id: int,
        uuid: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            data = await st.client.request_json(
                "DELETE",
                f"/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}/delete_files/{uuid}",
                token=token,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_download",
        description=(
            "Download attachment bytes as base64 (GET .../download_files/{uuid}). Requires access_token or HTTP Bearer."
        ),
    )
    async def vehicle_log_files_download(
        vehicle_id: int,
        vehicle_log_id: int,
        uuid: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            raw, headers = await st.client.request_bytes(
                "GET",
                f"/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}/download_files/{uuid}",
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
