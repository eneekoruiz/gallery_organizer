import tempfile
from pathlib import Path
from uuid import uuid4

from core.config import DIR_RESULT
from core.database import DatabaseManager


def test_cleanup_missing_files_removes_orphaned_filequeue_rows():
    db = DatabaseManager()
    suffix = uuid4().hex[:8]
    path = Path(tempfile.gettempdir()) / f"missing_file_{suffix}.jpg"
    path.write_text("temp", encoding="utf-8")
    file_id = db.upsert_file(str(path), path.name, media_type="image")
    assert file_id is not None
    path.unlink(missing_ok=True)

    removed = db.cleanup_missing_files(limit=10)
    assert removed >= 1


def test_cleanup_broken_symlinks_removes_orphaned_fileidentities_rows():
    db = DatabaseManager()
    suffix = uuid4().hex[:8]
    fake_link = DIR_RESULT / f"PersonaRepair_{suffix}" / f"broken_{suffix}.jpg"
    fake_link.parent.mkdir(parents=True, exist_ok=True)

    source = Path(tempfile.gettempdir()) / f"repair_source_{suffix}.jpg"
    file_id = db.upsert_file(str(source), source.name, media_type="image")
    assert file_id is not None
    db.add_file_identity(
        file_id=file_id,
        identity=f"PersonaRepair_{suffix}",
        symlink_path=str(fake_link),
        is_faceless=False,
    )

    removed = db.cleanup_broken_symlinks(limit=10)
    assert removed >= 1

    db.delete_by_path(str(source))
