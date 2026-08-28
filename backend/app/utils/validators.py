"""
Shared input validation helpers (file types, size limits, date ranges, etc.).
"""

from datetime import date

from fastapi import HTTPException, UploadFile

from app.config import get_settings
from app.utils.constants import SUPPORTED_FILE_TYPES


def validate_upload(file: UploadFile) -> None:
    if file.content_type not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. "
            f"Supported: {sorted(SUPPORTED_FILE_TYPES)}",
        )


_UPLOAD_READ_CHUNK_BYTES = 1024 * 1024


async def read_upload_within_limit(file: UploadFile) -> bytes:
    """Read an upload's contents in chunks, rejecting as soon as the size cap
    is exceeded -- reading the whole file first (via file.read()) then
    checking its length defeats the cap's purpose as a memory-exhaustion
    guard, since the oversized file is already fully buffered by then."""
    max_size = get_settings().upload_max_size_bytes
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_UPLOAD_READ_CHUNK_BYTES):
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds max upload size of {max_size} bytes.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def validate_date_range(start: date | None, end: date | None) -> None:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date.")
