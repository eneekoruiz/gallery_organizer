from unittest.mock import MagicMock, patch

import pytest

from core.models_types import (
    AIResult,
    DedupeResult,
    ExifResult,
    MediaRecord,
    ThumbnailResult,
)
from core.worker import ProcessingEngine


@pytest.fixture
def mock_engine(temp_db):
    log_q = MagicMock()
    engine = ProcessingEngine(temp_db, log_q)
    return engine


def test_pipeline_step_dispatch(mock_engine, temp_db):
    """Verifica que el motor llame a los pasos correctos del pipeline."""
    fid, _ = temp_db.upsert_file("mock.jpg", "mock.jpg")
    record = MediaRecord(id=fid, filepath="mock.jpg")

    # Mockear todos los pasos internos con objetos concretos de retorno, no MagicMocks para campos de datos
    mock_engine.thumbnail = MagicMock(return_value=ThumbnailResult(thumb_path="thumb.webp"))
    mock_engine.exif = MagicMock(return_value=ExifResult(exif_date="2023-01-01"))
    mock_engine.dedupe = MagicMock(return_value=DedupeResult(is_duplicate=False))
    mock_engine.ai = MagicMock(return_value=AIResult(tags=["test"], triage_tier="safe"))
    mock_engine.persist = MagicMock()
    mock_engine.materialize_results = MagicMock()

    # Ejecutar proceso para un archivo
    with (
        patch("core.worker.Path.exists", return_value=True),
        patch("core.worker.Path.stat") as mock_stat,
        patch("builtins.open", MagicMock()),
    ):
        mock_stat.return_value.st_size = 100
        res = mock_engine.process_one(record)

    assert res.status == "DONE"
    mock_engine.thumbnail.assert_called_once()
    mock_engine.ai.assert_called_once()
    mock_engine.persist.assert_called_once()


def test_error_handling_in_pipeline(mock_engine, temp_db):
    """Verifica que un error en un paso marque el archivo como ERROR."""
    fid, _ = temp_db.upsert_file("fail.jpg", "fail.jpg")
    record = MediaRecord(id=fid, filepath="fail.jpg")

    # Forzar error en el primer paso
    mock_engine.thumbnail = MagicMock(side_effect=Exception("Disk full"))

    with (
        patch("core.worker.Path.exists", return_value=True),
        patch("core.worker.Path.stat") as mock_stat,
        patch("builtins.open", MagicMock()),
    ):
        mock_stat.return_value.st_size = 100
        res = mock_engine.process_one(record)

    assert res.status == "ERROR"
    # Verificar que el error se guardó como string
    assert res.exception == "Disk full"


def test_worker_reloads_faiss_when_learning_revision_changes(mock_engine, temp_db):
    mock_engine._faiss_count = 0
    mock_engine._faiss_revision = 0
    mock_engine._reload_faiss = MagicMock()
    temp_db.set_control_state("identity_learning_revision", "1")

    mock_engine._check_reload_faiss()

    mock_engine._reload_faiss.assert_called_once()
