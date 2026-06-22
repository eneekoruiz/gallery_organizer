from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from application.identity_corrections import CorrectIdentity, IdentityRegion
from application.media_pipeline import MediaPipeline
from core.event_engine import EventEngine, EventSettings, haversine_km
from core.models_types import AIResult, DedupeResult, ExifResult, MediaRecord, ThumbnailResult
from domain.models import BoundingBox, GeoPoint, IdentityName, RegionKind
from infrastructure.sqlite.identity_repository import SqliteIdentityCorrectionRepository
from infrastructure.sqlite.location_repository import SqliteMediaLocationRepository


def test_value_objects_reject_invalid_data() -> None:
    assert str(IdentityName("  Ada   Lovelace ")) == "Ada Lovelace"
    with pytest.raises(ValueError):
        GeoPoint(91, 0)
    with pytest.raises(ValueError):
        BoundingBox(top=1, right=0, bottom=0, left=1)


def test_v5_schema_and_human_evidence(temp_db) -> None:
    media_id, _ = temp_db.upsert_file("photo.jpg", "photo.jpg")
    service = CorrectIdentity(SqliteIdentityCorrectionRepository(temp_db))
    evidence_id = service.execute(
        media_id,
        "Ane",
        IdentityRegion(
            kind=RegionKind.RECTANGLE,
            x=0.1,
            y=0.2,
            width=0.3,
            height=0.4,
        ),
        hard_case="back_view",
    )
    assert evidence_id > 0
    evidence = service.list_for_media(media_id)
    assert evidence[0]["display_name"] == "Ane"
    with temp_db._read() as cursor:
        assert cursor.execute("SELECT hard_case FROM TrainingExamples").fetchone()[0] == "back_view"
        assert (
            cursor.execute("SELECT operation FROM FilesystemOutbox").fetchone()[0]
            == "rebuild_identity_projection"
        )


def test_location_repository_returns_original_and_results(temp_db, tmp_path: Path) -> None:
    original = tmp_path / "original" / "photo.jpg"
    original.parent.mkdir()
    original.write_bytes(b"image")
    media_id, _ = temp_db.upsert_file(str(original), original.name)
    result = tmp_path / "results" / "Ane" / "photo.jpg"
    temp_db.add_file_identity(media_id, "Ane", str(result))
    location = SqliteMediaLocationRepository(temp_db).search("Ane")[0]
    assert location.original_folder == original.parent
    assert location.result_folders == (result.parent,)


def test_event_engine_groups_close_media(temp_db) -> None:
    embedding = np.zeros(512, dtype=np.float32)
    embedding[0] = 1.0
    for index, hour in enumerate((10, 11, 12), start=1):
        media_id, _ = temp_db.upsert_file(f"bilbao_{index}.jpg", f"bilbao_{index}.jpg")
        temp_db.update_done(
            media_id,
            tags=["montaña"],
            triage_tier="safe",
            best_datetime=f"2025-05-10T{hour:02d}:00:00",
            gps=(43.263 + index * 0.001, -2.935),
            clip_embedding=embedding.tobytes(),
        )
    count = EventEngine(
        temp_db, EventSettings(radius_km=5, time_window_hours=3, min_media=2)
    ).rebuild()
    assert count == 1
    assert EventEngine(temp_db).list_events()[0]["media_count"] == 3
    assert haversine_km(43.263, -2.935, 43.273, -2.935) == pytest.approx(1.11, rel=0.05)


def test_pipeline_orchestrator_has_single_error_boundary() -> None:
    steps = MagicMock()
    jobs = MagicMock()
    steps.check_stability.return_value = True
    steps.thumbnail.return_value = ThumbnailResult(thumb_path="thumb.webp")
    steps.exif.return_value = ExifResult()
    steps.dedupe.return_value = DedupeResult()
    steps.ai.return_value = AIResult(tags=["test"], triage_tier="safe")
    result = MediaPipeline(steps, jobs).execute(MediaRecord(1, "photo.jpg"))
    assert result.status == "DONE"
    steps.persist.assert_called_once()
    jobs.update_error.assert_not_called()
