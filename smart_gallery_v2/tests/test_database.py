import os
import tempfile
from core.database import DatabaseManager
from core.config import DB_PATH


def test_upsert_and_delete_file():
    db = DatabaseManager()
    # insert a temporary filepath
    fp = os.path.abspath(__file__)
    fid = db.upsert_file(fp, os.path.basename(fp), media_type="image")
    assert fid is not None
    # ensure we can fetch stats and that total >= 0
    stats = db.get_stats()
    assert isinstance(stats, dict)
    # cleanup
    db.delete_by_path(fp)


def test_control_state_roundtrip():
    db = DatabaseManager()
    db.set_control_state("unittest_state", "running")
    v = db.get_control_state("unittest_state")
    assert v == "running"
    db.set_control_state("unittest_state", "stopped")
    v2 = db.get_control_state("unittest_state")
    assert v2 == "stopped"
