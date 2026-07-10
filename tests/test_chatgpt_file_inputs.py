"""Tests for ChatGPT-native file inputs: schema, download security, MIME, forwarding."""

from __future__ import annotations

import asyncio
import base64
import socket
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from ridelogger_mcp.app import mcp
from ridelogger_mcp.file_inputs import (
    MAX_FILE_BYTES,
    ChatGptFileReference,
    DownloadedFile,
    FileInputError,
    FileInputPolicy,
    _validate_download_url,
    download_chatgpt_file,
    normalize_basename,
    resolve_content_type,
    select_file_source,
)
from ridelogger_mcp.tools.common import tool_error

_MIN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/VOJ6cQAAAAASUVORK5CYII="
)
_MIN_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"

FILE_PARAM_TOOLS: dict[str, str] = {
    "user_avatar_upload": "avatar",
    "vehicle_images_create": "image",
    "vehicle_cabinet_create": "cabinet_file",
    "vehicle_cabinet_update": "cabinet_file",
    "vehicle_log_files_upload": "vehicle_log_file",
}


def _file_schema_fragment(tool_name: str) -> dict[str, Any]:
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == tool_name)
    param_name = FILE_PARAM_TOOLS[tool_name]
    fragment = tool.parameters["properties"][param_name]
    if "anyOf" in fragment:
        return next(item for item in fragment["anyOf"] if item.get("type") == "object")
    return fragment


@pytest.mark.parametrize("tool_name,param_name", list(FILE_PARAM_TOOLS.items()))
def test_openai_file_params_meta_and_schema(tool_name: str, param_name: str) -> None:
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == tool_name)
    assert tool.meta == {"openai/fileParams": [param_name]}

    schema = _file_schema_fragment(tool_name)
    props = schema["properties"]
    assert set(props) == {"download_url", "file_id", "mime_type", "file_name"}
    assert set(schema["required"]) == {"download_url", "file_id"}


def test_legacy_log_base64_tool_has_no_file_params_meta() -> None:
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "vehicle_log_files_upload_base64")
    assert tool.meta in (None, {})


def test_select_file_source_exactly_one() -> None:
    ref = ChatGptFileReference(
        download_url="https://files.example/doc",
        file_id="file_abc",
    )
    assert select_file_source(chatgpt_file=ref, chat_upload_id=None, file_base64=None, file_name=None) is not None
    with pytest.raises(FileInputError):
        select_file_source(
            chatgpt_file=ref,
            chat_upload_id="550e8400-e29b-41d4-a716-446655440000",
            file_base64=None,
            file_name=None,
        )
    with pytest.raises(FileInputError):
        select_file_source(chatgpt_file=None, chat_upload_id=None, file_base64="abc", file_name=None)
    with pytest.raises(FileInputError):
        select_file_source(chatgpt_file=None, chat_upload_id=None, file_base64=None, file_name=None)


def test_select_file_source_optional_for_cabinet_update() -> None:
    from ridelogger_mcp.file_inputs import FileSourceSelection

    assert (
        select_file_source(
            chatgpt_file=None,
            chat_upload_id=None,
            file_base64=None,
            file_name=None,
            allow_no_file=True,
        )
        == FileSourceSelection.NONE
    )


def test_normalize_basename_strips_unsafe() -> None:
    assert normalize_basename("../../evil.pdf") == "evil.pdf"
    assert normalize_basename("") == "upload.bin"


def test_resolve_content_type_prefers_concrete_header() -> None:
    resolved = resolve_content_type(
        header_content_type="application/pdf",
        declared_mime="image/png",
        file_name="doc.pdf",
        header_bytes=_MIN_PDF,
        policy=FileInputPolicy.CABINET,
    )
    assert resolved.mime_type == "application/pdf"
    assert resolved.extension == "pdf"


def test_resolve_content_type_octet_stream_uses_declared_and_sniff() -> None:
    resolved = resolve_content_type(
        header_content_type="application/octet-stream",
        declared_mime="image/png",
        file_name="photo.png",
        header_bytes=_MIN_PNG,
        policy=FileInputPolicy.VEHICLE_IMAGE,
    )
    assert resolved.mime_type == "image/png"


def test_resolve_content_type_rejects_conflicting_signals() -> None:
    with pytest.raises(FileInputError, match="Conflicting"):
        resolve_content_type(
            header_content_type="application/pdf",
            declared_mime="image/png",
            file_name="photo.png",
            header_bytes=_MIN_PNG,
            policy=FileInputPolicy.VEHICLE_IMAGE,
        )


def test_resolve_content_type_rejects_non_image_for_avatar() -> None:
    with pytest.raises(FileInputError, match="Unsupported"):
        resolve_content_type(
            header_content_type="application/pdf",
            declared_mime="application/pdf",
            file_name="doc.pdf",
            header_bytes=_MIN_PDF,
            policy=FileInputPolicy.AVATAR_IMAGE,
        )


def test_validate_download_url_rejects_http() -> None:
    with pytest.raises(FileInputError, match="HTTPS"):
        _validate_download_url("http://files.example/a")


def test_validate_download_url_rejects_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )
    with pytest.raises(FileInputError, match="disallowed"):
        _validate_download_url("https://files.example/a")


def test_validate_download_url_rejects_private_ip_literal() -> None:
    with pytest.raises(FileInputError, match="disallowed"):
        _validate_download_url("https://10.0.0.5/file")


def _run(coro):
    return asyncio.run(coro)


def test_download_chatgpt_file_happy_path_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )

    class FakeStreamResponse:
        status_code = 200
        headers = {"content-type": "application/pdf", "content-length": str(len(_MIN_PDF))}

        async def aiter_bytes(self):
            yield _MIN_PDF

        async def aclose(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def build_request(self, method: str, url: str):
            return httpx.Request(method, url)

        async def send(self, request, *, stream: bool = False):
            return FakeStreamResponse()

    monkeypatch.setattr("ridelogger_mcp.file_inputs.httpx.AsyncClient", FakeClient)

    ref = ChatGptFileReference(
        download_url="https://files.example/doc.pdf",
        file_id="file_test",
        mime_type="application/pdf",
        file_name="invoice.pdf",
    )
    downloaded = _run(download_chatgpt_file(ref, policy=FileInputPolicy.CABINET))
    try:
        assert downloaded.content_type == "application/pdf"
        assert downloaded.file_name == "invoice.pdf"
        assert downloaded.size == len(_MIN_PDF)
    finally:
        downloaded.close()


def test_download_rejects_oversized_stream_without_content_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )

    chunk = b"x" * 1024

    class FakeStreamResponse:
        status_code = 200
        headers = {"content-type": "application/octet-stream"}

        async def aiter_bytes(self):
            for _ in range((MAX_FILE_BYTES // len(chunk)) + 2):
                yield chunk

        async def aclose(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def build_request(self, method: str, url: str):
            return httpx.Request(method, url)

        async def send(self, request, *, stream: bool = False):
            return FakeStreamResponse()

    monkeypatch.setattr("ridelogger_mcp.file_inputs.httpx.AsyncClient", FakeClient)

    ref = ChatGptFileReference(
        download_url="https://files.example/big.bin",
        file_id="file_big",
        file_name="big.bin",
    )
    with pytest.raises(FileInputError, match="maximum"):
        _run(download_chatgpt_file(ref, policy=FileInputPolicy.LOG_ATTACHMENT))


def test_download_rejects_private_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake_getaddrinfo(host, *args, **kwargs):
        if host == "files.example":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        if host == "127.0.0.1":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
        raise socket.gaierror("unknown")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    class RedirectResponse:
        status_code = 302
        headers = {"location": "https://127.0.0.1/secret"}

        async def aclose(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def build_request(self, method: str, url: str):
            return httpx.Request(method, url)

        async def send(self, request, *, stream: bool = False):
            calls["n"] += 1
            return RedirectResponse()

    monkeypatch.setattr("ridelogger_mcp.file_inputs.httpx.AsyncClient", FakeClient)

    ref = ChatGptFileReference(
        download_url="https://files.example/start",
        file_id="file_redirect",
    )
    with pytest.raises(FileInputError, match="disallowed"):
        _run(download_chatgpt_file(ref, policy=FileInputPolicy.LOG_ATTACHMENT))


def test_tool_error_does_not_leak_download_url() -> None:
    err = tool_error(
        FileInputError("failed for https://files.example/x?token=secret and file_id=file_abc")
    )
    message = err["error"]["message"]
    assert "token=secret" not in message
    assert "files.example" not in message


def test_vehicle_cabinet_create_native_forwards_multipart(monkeypatch: pytest.MonkeyPatch) -> None:
    import ridelogger_mcp.state as state_mod

    monkeypatch.setattr(
        "ridelogger_mcp.bearer_auth.get_http_bearer_token",
        lambda: "__stub-token__",
    )

    downloaded = DownloadedFile(
        file_name="invoice.pdf",
        content_type="application/pdf",
        spool=__import__("tempfile").SpooledTemporaryFile(max_size=1024, mode="w+b"),
        size=len(_MIN_PDF),
    )
    downloaded.spool.write(_MIN_PDF)
    downloaded.spool.seek(0)

    async def fake_prepare(**kwargs):
        return {"cabinet_file": downloaded.multipart_tuple()}, None, downloaded

    captured: dict[str, Any] = {}

    async def fake_request(*args, **kwargs):
        captured.update(kwargs)
        return httpx.Response(201, json={"data": {"id": 1}})

    class StubCache:
        async def refresh(self) -> None:
            return None

    client = AsyncMock()
    client.request.side_effect = fake_request
    prev = getattr(state_mod, "app_state", None)
    state_mod.app_state = type("S", (), {"client": client, "cache": StubCache()})()

    monkeypatch.setattr("ridelogger_mcp.tools.vehicle_cabinet.prepare_multipart_file", fake_prepare)

    result = asyncio.run(
        mcp.call_tool(
            "vehicle_cabinet_create",
            arguments={
                "vehicle_id": 7,
                "title": "Registracija",
                "document_category": "Ostalo",
                "cabinet_file": {
                    "download_url": "https://files.example/invoice.pdf",
                    "file_id": "file_123",
                    "mime_type": "application/pdf",
                    "file_name": "invoice.pdf",
                },
            },
        )
    )
    state_mod.app_state = prev
    if isinstance(result, dict):
        payload = result
    elif hasattr(result, "structured_content"):
        payload = result.structured_content
    else:
        payload = result
    assert isinstance(payload, dict) and payload.get("ok") is True
    assert captured["files"] is not None
    assert "cabinet_file" in captured["files"]
    assert captured["data"]["title"] == "Registracija"
