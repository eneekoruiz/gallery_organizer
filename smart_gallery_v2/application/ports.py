"""Interfaces que mantienen el dominio ajeno a SQLite, Streamlit y OpenCV."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from domain.models import MediaLocation

from core.models_types import AIResult, DedupeResult, ExifResult, MediaRecord, ThumbnailResult


class PipelineSteps(Protocol):
    def thumbnail(self, filepath: str) -> ThumbnailResult: ...

    def exif(self, filepath: str) -> ExifResult: ...

    def dedupe(self, filepath: str, file_id: int) -> DedupeResult: ...

    def ai(self, filepath: str, file_id: int, media_type: str = "image") -> AIResult: ...

    def materialize_results(self, record: MediaRecord, ai: AIResult) -> None: ...

    def persist(
        self,
        record: MediaRecord,
        ai: AIResult,
        exif: ExifResult,
        thumb: str | None,
    ) -> None: ...

    def persist_duplicate(
        self, record: MediaRecord, dedupe: DedupeResult, thumb: str | None
    ) -> None: ...

    def check_stability(self, filepath: str) -> bool: ...


class JobRepository(Protocol):
    def update_error(self, file_id: int, stage: str, message: str) -> None: ...
    def update_stage(self, file_id: int, stage: str) -> None: ...


class MediaLocationRepository(Protocol):
    def search(self, query: str = "") -> Sequence[MediaLocation]: ...


class FolderOpener(Protocol):
    def open(self, path: Path) -> None: ...
