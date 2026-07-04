"""Generic vehicle logs (aggregated) and attachments."""

from __future__ import annotations

import base64
import io
from typing import Any

from fastmcp import FastMCP

from ridelogger_mcp.errors import raise_for_status
from ridelogger_mcp.state import get_state
from ridelogger_mcp.tool_semantics import get_annotations
from ridelogger_mcp.tools.common import (
    LOG_REFS_HINT,
    MONEY_LOGS_HINT,
    body_from_kwargs,
    compact_query_params,
    require_token,
    tool_error,
    tool_success,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="generic_vehicle_logs_list",
        annotations=get_annotations("generic_vehicle_logs_list"),
        exclude_args=["access_token"],
        description=(
            "[READ] List all vehicle log entries for a vehicle (fuel, service, expense) — "
            "GET /api/vehicles/{vehicle_id}/vehicle_logs. Requires OAuth/Bearer authorization. "
            "Filters (passed as query params, combined with AND): date_from -> `from`, date_to -> `to` "
            "(Y-m-d, inclusive bounds), currency_id. "
            + MONEY_LOGS_HINT + " " + LOG_REFS_HINT
        ),
    )
    async def generic_vehicle_logs_list(
        vehicle_id: int,
        date_from: str | None = None,
        date_to: str | None = None,
        currency_id: int | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            params = compact_query_params(
                {
                    "from": date_from,
                    "to": date_to,
                    "currency_id": currency_id,
                }
            )
            data = await st.client.request_json(
                "GET",
                f"/vehicles/{vehicle_id}/vehicle_logs",
                token=token,
                params=params,
            )
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="generic_vehicle_logs_delete",
        annotations=get_annotations("generic_vehicle_logs_delete"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Delete a generic vehicle log row (DELETE /api/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}). "
            "Requires OAuth/Bearer authorization. Returns 202 on success."
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_list",
        annotations=get_annotations("vehicle_log_files_list"),
        exclude_args=["access_token"],
        description=(
            "[READ] List file attachments on a vehicle log (GET .../vehicle_logs/{vehicle_log_id}/get_files). "
            "Requires OAuth/Bearer authorization."
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_upload",
        annotations=get_annotations("vehicle_log_files_upload"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Upload attachment via multipart (POST .../put_files). Field name vehicle_log_file for binary. "
            "Requires OAuth/Bearer authorization. Exactly one of: chat_upload_id (AI chat attachment UUID), "
            "or file_base64 + file_name. "
            "Some accounts allow a limited number of attachments per vehicle log; if the limit is reached, "
            "the API returns 403. Remove an existing attachment before retrying."
        ),
    )
    async def vehicle_log_files_upload(
        vehicle_id: int,
        vehicle_log_id: int,
        file_name: str | None = None,
        file_base64: str | None = None,
        chat_upload_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            token = require_token(access_token)
            st = get_state()
            if chat_upload_id and (file_base64 or file_name):
                raise ValueError("Use either chat_upload_id or file fields, not both.")
            if chat_upload_id:
                resp = await st.client.request(
                    "POST",
                    f"/vehicles/{vehicle_id}/vehicle_logs/{vehicle_log_id}/put_files",
                    token=token,
                    data={"chat_upload_id": chat_upload_id.strip()},
                )
            else:
                if file_base64 and file_name:
                    raw = base64.b64decode(file_base64)
                else:
                    raise ValueError("Provide chat_upload_id, or file_base64+file_name.")
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_upload_base64",
        annotations=get_annotations("vehicle_log_files_upload_base64"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Upload attachment via JSON body (POST .../put_files_cordova). "
            "Requires OAuth/Bearer authorization. "
            "Either chat_upload_id (AI chat attachment UUID), or vehicle_log_file (base64) + vehicle_log_file_name — "
            "mutually exclusive. "
            "Some accounts allow a limited number of attachments per log; if the limit is reached, "
            "delete an existing attachment before retrying."
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_delete",
        annotations=get_annotations("vehicle_log_files_delete"),
        exclude_args=["access_token"],
        description=(
            "[WRITE] Delete one attachment by media uuid (DELETE .../delete_files/{uuid}). Requires OAuth/Bearer authorization."
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
            return tool_success(data)
        except Exception as e:
            return tool_error(e)

    @mcp.tool(
        name="vehicle_log_files_download",
        annotations=get_annotations("vehicle_log_files_download"),
        exclude_args=["access_token"],
        description=(
            "[READ] Download attachment bytes as base64 (GET .../download_files/{uuid}). Requires OAuth/Bearer authorization."
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
