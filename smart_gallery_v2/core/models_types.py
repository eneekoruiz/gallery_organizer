from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class MediaRecord:
    id: int
    filepath: str
    media_type: str = "image"
    retries: int = 0


@dataclass(frozen=True)
class ThumbnailResult:
    thumb_path: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class ExifResult:
    exif_date: Optional[str] = None
    gps: Optional[tuple[float, float]] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    iso: Optional[int] = None
    f_number: Optional[float] = None
    exposure: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class AIResult:
    tags: list[str] = field(default_factory=list)
    triage_tier: str = "unclassified"
    identities: list[str] = field(default_factory=list)
    phash: Optional[str] = None
    quality_score: float = 0.0
    error: Optional[str] = None


@dataclass(frozen=True)
class DedupeResult:
    is_duplicate: bool = False
    original_id: Optional[int] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class ProcessResult:
    file_id: int
    status: str  # DONE, ERROR
    phase: str
    message: str = ""
    exception: Optional[str] = None
