"""
Shared constants: evidence status enum values, supported file types,
observation type identifiers, etc. Single source of truth to avoid magic
strings scattered across routers/services.
"""

import enum


class EvidenceStatus(str, enum.Enum):
    SUPPORTED = "SUPPORTED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTING = "CONFLICTING"
    UNSUPPORTED = "UNSUPPORTED"


class ObservationType(str, enum.Enum):
    LAB = "lab"
    MEDICATION = "medication"
    CONDITION = "condition"
    SYMPTOM = "symptom"
    VITAL = "vital"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


SUPPORTED_FILE_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
