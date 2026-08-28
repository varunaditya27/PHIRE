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


def validate_upload_size(size_bytes: int) -> None:
    max_size = get_settings().upload_max_size_bytes
    if size_bytes > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max upload size of {max_size} bytes.",
        )


def validate_date_range(start: date | None, end: date | None) -> None:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date.")
