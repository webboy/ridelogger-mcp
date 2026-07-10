"""ChatGPT-native file reference download, validation, and multipart preparation."""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from tempfile import SpooledTemporaryFile
from typing import BinaryIO
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field

MAX_FILE_BYTES = 10 * 1024 * 1024
DOWNLOAD_CONNECT_TIMEOUT = 5.0
DOWNLOAD_READ_TIMEOUT = 30.0
MAX_REDIRECTS = 5
SNIFF_BYTES = 16

GENERIC_CONTENT_TYPES = frozenset(
    {
        "application/octet-stream",
        "binary/octet-stream",
        "application/x-msdownload",
    }
)

IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "gif", "bmp", "webp", "svg"})
IMAGE_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        "image/webp",
        "image/svg+xml",
    }
)

CABINET_EXTENSIONS = frozenset(
    {
        "jpg",
        "jpeg",
        "png",
        "webp",
        "gif",
        "heic",
        "heif",
        "pdf",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "odt",
        "ods",
        "txt",
        "rtf",
        "csv",
    }
)


class ChatGptFileReference(BaseModel):
    """OpenAI Apps SDK file-reference object (top-level tool argument)."""

    model_config = ConfigDict(extra="forbid")

    download_url: str = Field(description="Temporary HTTPS URL authorized for this tool call.")
    file_id: str = Field(description="OpenAI file identifier (file_…), not RideLogger chat_upload_id.")
    mime_type: str | None = Field(default=None, description="Declared MIME type from ChatGPT attachment metadata.")
    file_name: str | None = Field(default=None, description="Original attachment filename when available.")


class FileInputPolicy(str, Enum):
    AVATAR_IMAGE = "avatar_image"
    VEHICLE_IMAGE = "vehicle_image"
    CABINET = "cabinet"
    LOG_ATTACHMENT = "log_attachment"


class FileSourceSelection(str, Enum):
    CHATGPT = "chatgpt"
    CHAT_UPLOAD_ID = "chat_upload_id"
    BASE64 = "base64"
    NONE = "none"


@dataclass(frozen=True)
class ResolvedFileType:
    mime_type: str
    extension: str


@dataclass
class DownloadedFile:
    file_name: str
    content_type: str
    spool: SpooledTemporaryFile
    size: int

    def multipart_tuple(self) -> tuple[str, BinaryIO, str]:
        self.spool.seek(0)
        return (self.file_name, self.spool, self.content_type)

    def close(self) -> None:
        self.spool.close()


class FileInputError(ValueError):
    """User-safe validation/download error for file inputs."""


def normalize_basename(file_name: str | None, *, fallback: str = "upload.bin") -> str:
    raw = (file_name or "").strip()
    if not raw:
        return fallback
    base = PurePosixPath(raw.replace("\\", "/")).name
    base = re.sub(r"[^\w.\- ]+", "_", base).strip(" .")
    if not base or base in {".", ".."}:
        return fallback
    return base[:255]


def extension_of(file_name: str) -> str:
    return PurePosixPath(file_name).suffix.lower().lstrip(".")


def _has_chatgpt_file(file_ref: ChatGptFileReference | None) -> bool:
    return file_ref is not None and bool(file_ref.download_url.strip() and file_ref.file_id.strip())


def _has_base64_source(file_base64: str | None, file_name: str | None) -> bool:
    return bool(file_base64 and file_base64.strip()) or bool(file_name and file_name.strip())


def select_file_source(
    *,
    chatgpt_file: ChatGptFileReference | None,
    chat_upload_id: str | None,
    file_base64: str | None,
    file_name: str | None,
    allow_no_file: bool = False,
) -> FileSourceSelection:
    has_chatgpt = _has_chatgpt_file(chatgpt_file)
    has_chat_upload = bool(chat_upload_id and chat_upload_id.strip())
    has_base64 = _has_base64_source(file_base64, file_name)

    active = sum((has_chatgpt, has_chat_upload, has_base64))
    if active > 1:
        raise FileInputError(
            "Provide exactly one file source: ChatGPT attachment, RideLogger chat_upload_id, "
            "or file_base64 + file_name."
        )
    if has_chatgpt:
        return FileSourceSelection.CHATGPT
    if has_chat_upload:
        return FileSourceSelection.CHAT_UPLOAD_ID
    if has_base64:
        if not (file_base64 and file_base64.strip() and file_name and file_name.strip()):
            raise FileInputError("file_base64 and file_name must both be provided together.")
        return FileSourceSelection.BASE64
    if allow_no_file:
        return FileSourceSelection.NONE
    raise FileInputError(
        "A file source is required: ChatGPT attachment, RideLogger chat_upload_id, "
        "or file_base64 + file_name."
    )


def _normalize_content_type(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.split(";", 1)[0].strip().lower()
    return value or None


def _mime_from_extension(ext: str) -> str | None:
    mapping = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "odt": "application/vnd.oasis.opendocument.text",
        "ods": "application/vnd.oasis.opendocument.spreadsheet",
        "txt": "text/plain",
        "rtf": "application/rtf",
        "csv": "text/csv",
        "heic": "image/heic",
        "heif": "image/heif",
    }
    return mapping.get(ext.lower())


def _sniff_file_type(header: bytes) -> ResolvedFileType | None:
    if header.startswith(b"%PDF"):
        return ResolvedFileType("application/pdf", "pdf")
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ResolvedFileType("image/png", "png")
    if header.startswith(b"\xff\xd8\xff"):
        return ResolvedFileType("image/jpeg", "jpg")
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return ResolvedFileType("image/gif", "gif")
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return ResolvedFileType("image/webp", "webp")
    if header.startswith(b"PK\x03\x04"):
        # ZIP container — docx/xlsx/odt/ods; extension disambiguation happens later.
        return ResolvedFileType("application/zip", "zip")
    if header.lstrip().startswith(b"<?xml") or header.lstrip().startswith(b"<svg"):
        return ResolvedFileType("image/svg+xml", "svg")
    return None


def _assert_policy_allows(resolved: ResolvedFileType, policy: FileInputPolicy) -> None:
    ext = resolved.extension
    mime = resolved.mime_type

    if policy in (FileInputPolicy.AVATAR_IMAGE, FileInputPolicy.VEHICLE_IMAGE):
        if ext not in IMAGE_EXTENSIONS and mime not in IMAGE_MIME_TYPES:
            raise FileInputError("Unsupported file type for image upload.")
        if ext == "zip":
            raise FileInputError("Unsupported file type for image upload.")
        return

    if policy == FileInputPolicy.CABINET:
        if ext == "zip":
            raise FileInputError(
                "Unsupported cabinet file type. Use a direct document or image extension."
            )
        if ext and ext not in CABINET_EXTENSIONS:
            raise FileInputError("Unsupported cabinet file extension.")
        return

    # LOG_ATTACHMENT — any file up to size limit.


def resolve_content_type(
    *,
    header_content_type: str | None,
    declared_mime: str | None,
    file_name: str,
    header_bytes: bytes,
    policy: FileInputPolicy,
) -> ResolvedFileType:
    header_mime = _normalize_content_type(header_content_type)
    declared = _normalize_content_type(declared_mime)
    ext = extension_of(file_name)
    ext_mime = _mime_from_extension(ext) if ext else None
    sniffed = _sniff_file_type(header_bytes[:SNIFF_BYTES])

    candidates: list[tuple[str, str, str]] = []

    if header_mime and header_mime not in GENERIC_CONTENT_TYPES:
        candidates.append(("header", header_mime, ext or (sniffed.extension if sniffed else "")))

    if declared and declared not in GENERIC_CONTENT_TYPES:
        candidates.append(("declared", declared, ext or (sniffed.extension if sniffed else "")))

    if ext_mime:
        candidates.append(("extension", ext_mime, ext))

    if sniffed:
        candidates.append(("sniff", sniffed.mime_type, sniffed.extension))

    if header_mime in GENERIC_CONTENT_TYPES and declared:
        candidates.append(("declared_generic", declared, ext or sniffed.extension if sniffed else ""))

    if not candidates:
        if header_mime:
            candidates.append(("header_generic", header_mime, ext or "bin"))
        elif ext_mime:
            candidates.append(("extension_only", ext_mime, ext))
        elif sniffed:
            candidates.append(("sniff_only", sniffed.mime_type, sniffed.extension))
        else:
            raise FileInputError("Unable to determine file type.")

    # Prefer concrete header, then declared, then extension, then sniff.
    priority = {"header": 0, "declared": 1, "extension": 2, "sniff": 3, "declared_generic": 4, "header_generic": 5, "extension_only": 6, "sniff_only": 7}
    candidates.sort(key=lambda item: priority.get(item[0], 99))
    _source, chosen_mime, chosen_ext = candidates[0]

    if sniffed and header_mime and header_mime not in GENERIC_CONTENT_TYPES:
        if _mime_family(header_mime) != _mime_family(sniffed.mime_type):
            raise FileInputError("Conflicting file type signals; upload rejected.")
    elif sniffed and chosen_mime not in GENERIC_CONTENT_TYPES:
        if _mime_family(chosen_mime) != _mime_family(sniffed.mime_type):
            raise FileInputError("File content does not match declared type.")

    if not chosen_ext:
        chosen_ext = sniffed.extension if sniffed else "bin"

    resolved = ResolvedFileType(chosen_mime, chosen_ext)
    _assert_policy_allows(resolved, policy)
    return resolved


def _mime_family(mime: str) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime == "application/pdf":
        return "pdf"
    if "word" in mime or mime.endswith("msword"):
        return "word"
    if "sheet" in mime or "excel" in mime:
        return "excel"
    if mime.startswith("text/"):
        return "text"
    return mime


def _is_blocked_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise FileInputError("File download URL must use HTTPS.")
    host = parsed.hostname
    if not host:
        raise FileInputError("Invalid file download URL.")
    try:
        literal = ipaddress.ip_address(host)
        if _is_blocked_ip(str(literal)):
            raise FileInputError("File download URL target is not allowed.")
        return
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FileInputError("File download URL host could not be resolved.") from exc

    if not infos:
        raise FileInputError("File download URL host could not be resolved.")

    for info in infos:
        addr = info[4][0]
        if _is_blocked_ip(addr):
            raise FileInputError("File download URL resolves to a disallowed address.")


def _safe_error_message(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    lowered = text.lower()
    for secret_marker in ("download_url", "file_id", "token", "sig=", "secret", "authorization"):
        if secret_marker in lowered:
            return "File download failed."
    if "https://" in lowered or "http://" in lowered:
        return "File download failed."
    return text


async def download_chatgpt_file(
    file_ref: ChatGptFileReference,
    *,
    policy: FileInputPolicy,
    max_bytes: int = MAX_FILE_BYTES,
) -> DownloadedFile:
    url = file_ref.download_url.strip()
    _validate_download_url(url)

    current_url = httpx.URL(url)
    spool = SpooledTemporaryFile(max_size=max_bytes + 1, mode="w+b")
    header_content_type: str | None = None
    total = 0

    timeout = httpx.Timeout(DOWNLOAD_CONNECT_TIMEOUT, read=DOWNLOAD_READ_TIMEOUT)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response: httpx.Response | None = None
        for _ in range(MAX_REDIRECTS + 1):
            _validate_download_url(str(current_url))
            req = client.build_request("GET", str(current_url))
            response = await client.send(req, stream=True)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                await response.aclose()
                if not location:
                    spool.close()
                    raise FileInputError("File download redirect missing target.")
                redirect_target = httpx.URL(location)
                current_url = redirect_target if redirect_target.host else current_url.join(location)
                response = None
                continue

            if response.status_code in (403, 404):
                await response.aclose()
                spool.close()
                raise FileInputError("File is unavailable or has expired.")
            if response.status_code >= 400:
                await response.aclose()
                spool.close()
                raise FileInputError("File download failed.")

            content_length = response.headers.get("content-length")
            if content_length is not None:
                try:
                    if int(content_length) > max_bytes:
                        await response.aclose()
                        spool.close()
                        raise FileInputError("File exceeds the maximum allowed size.")
                except ValueError:
                    pass

            header_content_type = response.headers.get("content-type")
            try:
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise FileInputError("File exceeds the maximum allowed size.")
                    spool.write(chunk)
            except httpx.TimeoutException as exc:
                raise FileInputError("File download timed out.") from exc
            finally:
                await response.aclose()
            break
        else:
            spool.close()
            raise FileInputError("Too many redirects while downloading file.")

    if response is None:
        spool.close()
        raise FileInputError("File download failed.")

    spool.seek(0)
    header_bytes = spool.read(SNIFF_BYTES)
    spool.seek(0)

    file_name = normalize_basename(
        file_ref.file_name,
        fallback=f"upload.{extension_of(file_ref.file_name or '') or 'bin'}",
    )
    resolved = resolve_content_type(
        header_content_type=header_content_type,
        declared_mime=file_ref.mime_type,
        file_name=file_name,
        header_bytes=header_bytes,
        policy=policy,
    )

    if not extension_of(file_name):
        stem = PurePosixPath(file_name).stem or "upload"
        file_name = f"{stem}.{resolved.extension}"

    return DownloadedFile(
        file_name=file_name,
        content_type=resolved.mime_type,
        spool=spool,
        size=total,
    )


async def prepare_multipart_file(
    *,
    field_name: str,
    chatgpt_file: ChatGptFileReference | None,
    chat_upload_id: str | None,
    file_base64: str | None,
    file_name: str | None,
    policy: FileInputPolicy,
    allow_no_file: bool = False,
) -> tuple[dict[str, tuple[str, BinaryIO, str]] | None, str | None, DownloadedFile | None]:
    """Return (multipart_files, chat_upload_id, downloaded) for upstream ApiClient.request."""
    import base64
    import io

    selection = select_file_source(
        chatgpt_file=chatgpt_file,
        chat_upload_id=chat_upload_id,
        file_base64=file_base64,
        file_name=file_name,
        allow_no_file=allow_no_file,
    )

    if selection == FileSourceSelection.NONE:
        return None, None, None
    if selection == FileSourceSelection.CHAT_UPLOAD_ID:
        return None, chat_upload_id.strip(), None
    if selection == FileSourceSelection.BASE64:
        raw = base64.b64decode(file_base64 or "")
        if len(raw) > MAX_FILE_BYTES:
            raise FileInputError("File exceeds the maximum allowed size.")
        fname = normalize_basename(file_name)
        ext = extension_of(fname)
        if policy == FileInputPolicy.CABINET and ext and ext not in CABINET_EXTENSIONS:
            raise FileInputError("Unsupported cabinet file extension.")
        spool = SpooledTemporaryFile(max_size=max_bytes_safe(len(raw)), mode="w+b")
        spool.write(raw)
        spool.seek(0)
        downloaded = DownloadedFile(
            file_name=fname,
            content_type="application/octet-stream",
            spool=spool,
            size=len(raw),
        )
        return {field_name: downloaded.multipart_tuple()}, None, downloaded

    downloaded = await download_chatgpt_file(chatgpt_file, policy=policy)
    return {field_name: downloaded.multipart_tuple()}, None, downloaded


def max_bytes_safe(size: int) -> int:
    return max(size, MAX_FILE_BYTES + 1)
