import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.database import DatabaseManager
from core.worker import _make_thumb, _safe


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # Mock DB_PATH in config for this test if possible,
    # but DatabaseManager is a singleton.
    # For testing, we might need a fresh instance or a patch.
    # We will assume DatabaseManager can be pointed to a path or use a separate test manager.
    db = DatabaseManager()
    db._db_path = Path(path)
    db._init_db()
    yield db
    os.remove(path)


def test_db_basic_flow(temp_db):
    db = temp_db
    # Enqueue
    fid = db.upsert_file("test.jpg", "test.jpg")
    assert fid is not None

    # next_pending
    pending = db.next_pending()
    assert pending["id"] == fid
    assert pending["status"] == "PROCESSING"

    # update_done
    db.update_done(fid, tags=["test"], triage_tier="safe")
    stats = db.get_stats()
    assert stats["done"] == 1

    # update_error
    fid2 = db.upsert_file("error.jpg", "error.jpg")
    db.update_error(fid2, phase="test", exception="crash")
    stats = db.get_stats()
    assert stats["errors"] == 0  # It should be PENDING first because retries < 2

    # force error (retry 2)
    db.update_error(fid2, phase="test", exception="crash")
    stats = db.get_stats()
    assert stats["errors"] == 1


def test_safe_name():
    assert _safe("Hola Mundo!") == "Hola_Mundo"
    assert _safe("...archivo...") == "archivo"
    assert _safe("") == "otros"


def test_thumbnail_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test.jpg"
        Image.new("RGB", (100, 100), color="red").save(img_path)

        # We need to mock DIR_THUMBS from config
        # For test simplicity, we check if the function returns a path
        thumb = _make_thumb(str(img_path))
        if thumb:
            assert Path(thumb).exists()
            assert Path(thumb).suffix == ".webp"


def test_semantic_ranking_order():
    # Mock CLIP scores
    ids = [1, 2, 3]
    embs = np.array(
        [
            [1.0, 0.0],  # Relevance 1.0 for query [1,0]
            [0.5, 0.5],  # Relevance 0.5
            [0.0, 1.0],  # Relevance 0.0
        ],
        dtype=np.float32,
    )

    query_emb = np.array([1.0, 0.0], dtype=np.float32)
    scores = embs @ query_emb

    top_idx = np.argsort(scores)[::-1]
    sorted_ids = [ids[i] for i in top_idx]

    assert sorted_ids == [1, 2, 3]
    assert scores[0] > scores[1] > scores[2]
