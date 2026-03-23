"""Generic vehicle logs (aggregated) and attachments."""

from __future__ import annotations

import base64
import io
from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.errors import raise_for_status
from ridelogger_mcp.state import get_state
from ridelogger_mcp.tools.common import parse_json_object, require_token, tool_error


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="generic_vehicle_logs_list",
        description=(
            "List all vehicle log entries for a vehicle (fuel, service, expense) — "
            "GET /api/vehicles/{vehicle_id}/vehicle_logs. Requires access_token or HTTP Bearer."
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
            "Upload attachment via multipart (POST .../put_files). Field name must be vehicle_log_file. "
            "Requires access_token or HTTP Bearer. Provide file_name + file_base64 OR file_path."
        ),
    )
    async def vehicle_log_files_upload(
        vehicle_id: int,
        vehicle_log_id: int,
        file_name: str,
        file_base64: str | None = None,
        file_path: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            if file_path:
                with open(file_path, "rb") as f:
                    raw = f.read()
            elif file_base64:
                raw = base64.b64decode(file_base64)
            else:
                raise ValueError("Provide file_base64 or file_path.")
            files = {
                "vehicle_log_file": (file_name, io.BytesIO(raw), "application/octet-stream"),
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
            "Requires access_token or HTTP Bearer. body_json must include vehicle_log_file (base64 string) and "
            "vehicle_log_file_name."
        ),
    )
    async def vehicle_log_files_upload_base64(
        vehicle_id: int,
        vehicle_log_id: int,
        body_json: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            body = parse_json_object("body_json", body_json)
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
