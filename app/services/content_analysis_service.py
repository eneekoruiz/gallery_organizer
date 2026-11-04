"""Persistent, location-independent face detections. Labels remain path-specific."""
import hashlib
import json
import os
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from app.services.vector_index import get_db_connection


def content_sha256(path):
    """Hash every byte, including changes after a shared prefix."""
    with open(path, "rb") as file:
        before = os.fstat(file.fileno())
        digest = hashlib.file_digest(file, "sha256").hexdigest()
        after = os.fstat(file.fileno())
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise OSError(f"File changed during hashing: {path}")
    return digest


@lru_cache(maxsize=16)
def _model_digest(files):
    return hashlib.sha256("".join(content_sha256(path) for path, _, _ in files).encode()).hexdigest()


def model_version(root):
    files = tuple((str(path), path.stat().st_size, path.stat().st_mtime_ns)
                  for path in (Path(root) / "models/face_detection_yunet.onnx",
                               Path(root) / "models/face_recognition_sface.onnx"))
    return _model_digest(files)


def _prepare(connection):
    connection.execute("""CREATE TABLE IF NOT EXISTS content_face_analysis (
        sha256 TEXT NOT NULL, profile TEXT NOT NULL, payload TEXT NOT NULL,
        PRIMARY KEY (sha256, profile))""")
    connection.execute("""CREATE TABLE IF NOT EXISTS content_locations (
        path TEXT PRIMARY KEY, sha256 TEXT NOT NULL)""")
    connection.execute("CREATE INDEX IF NOT EXISTS content_locations_hash ON content_locations(sha256)")


def load_analysis(path, sha256, profile):
    with closing(get_db_connection()) as connection, connection:
        _prepare(connection)
        connection.execute("INSERT OR REPLACE INTO content_locations(path,sha256) VALUES (?,?)",
                           (str(path), sha256))
        row = connection.execute(
            "SELECT payload FROM content_face_analysis WHERE sha256=? AND profile=?",
            (sha256, profile)).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(row[0])
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("faces"), list):
        return None
    return payload


def save_analysis(sha256, profile, payload):
    encoded = json.dumps(payload, allow_nan=False, separators=(",", ":"))
    with closing(get_db_connection()) as connection, connection:
        _prepare(connection)
        connection.execute("""INSERT OR REPLACE INTO content_face_analysis
            (sha256, profile, payload) VALUES (?,?,?)""", (sha256, profile, encoded))


def find_content_duplicates():
    with closing(get_db_connection()) as connection, connection:
        _prepare(connection)
        rows = connection.execute("""SELECT sha256, path FROM content_locations
            WHERE sha256 IN (SELECT sha256 FROM content_locations GROUP BY sha256 HAVING COUNT(*)>1)
            ORDER BY sha256, path""").fetchall()
    result = {}
    for digest, path in rows:
        result.setdefault(digest, []).append(path)
    return result
