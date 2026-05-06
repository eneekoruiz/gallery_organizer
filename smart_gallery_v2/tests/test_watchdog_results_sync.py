import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

from core.config import DB_PATH, DIR_RESULT
from core.database import DatabaseManager
from core.watchdog_engine import make_db_callback


def _cleanup_path(path: str) -> None:
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("DELETE FROM FileIdentities WHERE symlink_path=?", (path,))
            conn.execute("DELETE FROM FileQueue WHERE filepath=?", (path,))
            conn.commit()
    except Exception:
        pass


def test_results_delete_removes_identity_only():
    db = DatabaseManager()
    cb = make_db_callback(db)

    suffix = uuid4().hex[:8]
    original = Path(tempfile.gettempdir()) / f"watchdog_source_a_{suffix}.jpg"
    result_link = DIR_RESULT / "PersonaA" / f"watchdog_link_a_{suffix}.jpg"
    result_link.parent.mkdir(parents=True, exist_ok=True)

    file_id = db.upsert_file(str(original), original.name, media_type="image")
    assert file_id is not None
    db.add_file_identity(
        file_id=file_id, identity="PersonaA", symlink_path=str(result_link), is_faceless=False
    )

    cb("deleted", str(result_link), "")

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM FileIdentities WHERE symlink_path=?", (str(result_link),)
        ).fetchall()
        fq = conn.execute("SELECT * FROM FileQueue WHERE filepath=?", (str(original),)).fetchall()

    assert rows == []
    assert len(fq) == 1

    db.delete_by_path(str(original))


def test_results_move_updates_symlink_path():
    db = DatabaseManager()
    cb = make_db_callback(db)

    suffix = uuid4().hex[:8]
    original = Path(tempfile.gettempdir()) / f"watchdog_source_b_{suffix}.jpg"
    old_link = DIR_RESULT / "PersonaB" / f"watchdog_link_b_{suffix}.jpg"
    new_link = DIR_RESULT / "PersonaB" / f"watchdog_link_b_{suffix}_renamed.jpg"
    old_link.parent.mkdir(parents=True, exist_ok=True)

    file_id = db.upsert_file(str(original), original.name, media_type="image")
    assert file_id is not None
    db.add_file_identity(
        file_id=file_id, identity="PersonaB", symlink_path=str(old_link), is_faceless=False
    )

    cb("moved", str(old_link), str(new_link))

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        old_rows = conn.execute(
            "SELECT * FROM FileIdentities WHERE symlink_path=?", (str(old_link),)
        ).fetchall()
        new_rows = conn.execute(
            "SELECT * FROM FileIdentities WHERE symlink_path=?", (str(new_link),)
        ).fetchall()

    assert old_rows == []
    assert len(new_rows) == 1

    db.delete_by_path(str(original))
