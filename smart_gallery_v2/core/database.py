"""
core/database.py — Capa de Persistencia Enterprise
WAL · Thread-Safe · Triage · Faceless Tags · Group Symlinks · Undo/Redo
"""

from __future__ import annotations

import gc
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

import numpy as np
import pandas as pd

from core.config import ARCFACE_DIM, DB_PATH


# ──────────────────────────────────────────────────────────────────────────────
# DDL
# ──────────────────────────────────────────────────────────────────────────────
_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-32000;
PRAGMA temp_store=MEMORY;
PRAGMA foreign_keys=ON;

-- ── IDENTIDADES VERIFICADAS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS KnownFaces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    embedding   BLOB,                       -- NULL para identidades "faceless"
    is_faceless BOOLEAN NOT NULL DEFAULT 0, -- etiquetado manual sin cara
    source_img  TEXT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_kf_name ON KnownFaces(name);

-- ── COLA DE TRABAJO (MÁQUINA DE ESTADOS) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS FileQueue (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath     TEXT    NOT NULL UNIQUE,
    filename     TEXT    NOT NULL,
    media_type   TEXT    NOT NULL DEFAULT 'image',   -- 'image' | 'video'
    status       TEXT    NOT NULL DEFAULT 'PENDING', -- PENDING|PROCESSING|DONE|ERROR|SKIPPED
    triage_tier  TEXT    NOT NULL DEFAULT 'unclassified',
    -- 'safe'(>85%) | 'review'(40-85%) | 'unclassified'(<40%)
    retries      INTEGER NOT NULL DEFAULT 0,
    tags         TEXT,                               -- JSON array de strings
    phash        TEXT,                               -- perceptual hash hex
    exif_date    TEXT,
    gps_lat      REAL,
    gps_lon      REAL,
    thumb_path   TEXT,
    hash_sha256  TEXT,
    last_updated TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_fq_status  ON FileQueue(status);
CREATE INDEX IF NOT EXISTS idx_fq_triage  ON FileQueue(triage_tier);
CREATE INDEX IF NOT EXISTS idx_fq_date    ON FileQueue(exif_date);

-- ── DETECCIONES (HITL) ────────────────────────────────────────────────────────
-- Una fila por CARA detectada (o zona faceless dibujada manualmente).
CREATE TABLE IF NOT EXISTS Detections (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id          INTEGER NOT NULL REFERENCES FileQueue(id) ON DELETE CASCADE,
    face_crop_path   TEXT,
    bbox_json        TEXT,                -- {"top","right","bottom","left"}
    assigned_name    TEXT    NOT NULL DEFAULT 'Desconocido',
    confidence       REAL    NOT NULL DEFAULT 0.0,
    triage_tier      TEXT    NOT NULL DEFAULT 'unclassified',
    embedding        BLOB,               -- NULL para detecciones faceless
    is_faceless      BOOLEAN NOT NULL DEFAULT 0,
    is_false_positive BOOLEAN NOT NULL DEFAULT 0,
    is_verified      BOOLEAN NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_det_file   ON Detections(file_id);
CREATE INDEX IF NOT EXISTS idx_det_triage ON Detections(triage_tier, is_verified);
CREATE INDEX IF NOT EXISTS idx_det_name   ON Detections(assigned_name);

-- ── RELACIONES ARCHIVO ↔ IDENTIDAD (MULTI-TAG GRUPOS) ────────────────────────
-- Una foto grupal con N personas tiene N filas aquí.
-- Los symlinks se crean desde esta tabla.
CREATE TABLE IF NOT EXISTS FileIdentities (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id      INTEGER NOT NULL REFERENCES FileQueue(id) ON DELETE CASCADE,
    identity     TEXT    NOT NULL,
    symlink_path TEXT,                   -- ruta del symlink ya creado
    is_faceless  BOOLEAN NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(file_id, identity)
);
CREATE INDEX IF NOT EXISTS idx_fi_identity ON FileIdentities(identity);
CREATE INDEX IF NOT EXISTS idx_fi_file     ON FileIdentities(file_id);

-- ── CLIP EMBEDDINGS ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ClipEmbeddings (
    id        INTEGER PRIMARY KEY REFERENCES FileQueue(id) ON DELETE CASCADE,
    embedding BLOB NOT NULL
);

-- ── HISTORIAL DE TRANSACCIONES (UNDO/REDO) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS TxHistory (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    action  TEXT    NOT NULL,           -- 'RENAME'|'VERIFY'|'DELETE'|'FACELESS'
    payload TEXT    NOT NULL,           -- JSON {before:[...], after:{...}}
    undone  BOOLEAN NOT NULL DEFAULT 0
);

-- ── WATCHDOG FILE EVENTS ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS FsEvents (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    event     TEXT NOT NULL,
    src_path  TEXT NOT NULL,
    dest_path TEXT
);

-- ── CONTROL / ESTADO (persistencia de controles maestro) ────────────────
CREATE TABLE IF NOT EXISTS ControlState (
    key_name TEXT PRIMARY KEY,
    value    TEXT,
    last_updated TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
"""


# ──────────────────────────────────────────────────────────────────────────────
# DatabaseManager — Singleton Thread-Safe
# ──────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None
    _cls_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "DatabaseManager":
        with cls._cls_lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._initialized = False
                cls._instance = obj
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._write_lock = threading.Lock()
        self._db_path    = DB_PATH
        self._init_schema()
        self._initialized = True

    # ── Conexión ──────────────────────────────────────────────────────────
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False,
                               timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA cache_size=-32000;")
        return conn

    @contextmanager
    def _write(self) -> Generator[sqlite3.Cursor, None, None]:
        with self._write_lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                cur = conn.cursor()
                yield cur
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()
                gc.collect()

    @contextmanager
    def _read(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._connect()
        try:
            yield conn.cursor()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._write_lock:
            conn = self._connect()
            conn.executescript(_DDL)
            # Migrate existing schema: asegurar columna phash en FileQueue
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(FileQueue)")
            cols = [r[1] for r in cur.fetchall()]
            if 'phash' not in cols:
                try:
                    cur.execute("ALTER TABLE FileQueue ADD COLUMN phash TEXT")
                except Exception:
                    pass
            conn.commit()
            conn.close()

    # ── FileQueue ─────────────────────────────────────────────────────────
    def upsert_file(self, filepath: str, filename: str,
                    media_type: str = "image", phash: Optional[str] = None) -> Optional[int]:
        try:
            with self._write() as c:
                c.execute(
                    "INSERT OR IGNORE INTO FileQueue (filepath,filename,media_type,phash,last_updated) "
                    "VALUES (?,?,?,?,?)", (filepath, filename, media_type, phash, _now()))
                if c.lastrowid:
                    return c.lastrowid
                c.execute("SELECT id FROM FileQueue WHERE filepath=?", (filepath,))
                row = c.fetchone()
                return row["id"] if row else None
        except sqlite3.Error:
            return None

    def set_processing(self, file_id: int) -> None:
        with self._write() as c:
            c.execute("UPDATE FileQueue SET status='PROCESSING', last_updated=? WHERE id=?",
                      (_now(), file_id))

    def update_done(self, file_id: int, tags: list[str], triage_tier: str,
                    exif_date: Optional[str] = None,
                    gps: Optional[tuple[float, float]] = None,
                    thumb_path: Optional[str] = None,
                    phash: Optional[str] = None) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE FileQueue SET status='DONE', triage_tier=?, tags=?, "
                "exif_date=?, gps_lat=?, gps_lon=?, thumb_path=?, phash=?, last_updated=? WHERE id=?",
                (triage_tier, json.dumps(tags, ensure_ascii=False),
                 exif_date, gps[0] if gps else None, gps[1] if gps else None,
                 thumb_path, phash, _now(), file_id))

    def update_error(self, file_id: int) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE FileQueue SET retries=retries+1, last_updated=?, "
                "status=CASE WHEN retries>=2 THEN 'ERROR' ELSE 'PENDING' END WHERE id=?",
                (_now(), file_id))

    def move_filepath(self, old: str, new: str) -> None:
        with self._write() as c:
            c.execute("UPDATE FileQueue SET filepath=?, filename=?, last_updated=? WHERE filepath=?",
                      (new, Path(new).name, _now(), old))

    def delete_by_path(self, filepath: str) -> None:
        with self._write() as c:
            c.execute("DELETE FROM FileQueue WHERE filepath=?", (filepath,))

    def next_pending(self) -> Optional[dict[str, Any]]:
        with self._write() as c:
            c.execute("SELECT * FROM FileQueue WHERE status='PENDING' ORDER BY id LIMIT 1")
            row = c.fetchone()
            if row:
                c.execute("UPDATE FileQueue SET status='PROCESSING', last_updated=? WHERE id=?",
                          (_now(), row["id"]))
                return dict(row)
        return None

    def get_stats(self) -> dict[str, int]:
        with self._read() as c:
            c.execute("""SELECT
                COUNT(*) total,
                SUM(status='DONE')        done,
                SUM(status='PENDING')     pending,
                SUM(status='PROCESSING')  processing,
                SUM(status='ERROR')       errors,
                SUM(triage_tier='safe' AND status='DONE')          safe,
                SUM(triage_tier='review' AND status='DONE')        review,
                SUM(triage_tier='unclassified' AND status='DONE')  unclassified
              FROM FileQueue""")
            row = c.fetchone()
            return {k: (v or 0) for k, v in dict(row).items()} if row else {}

    def get_files_df(self, status: Optional[str] = None,
                     triage: Optional[str] = None,
                     limit: int = 200, offset: int = 0) -> pd.DataFrame:
        clauses: list[str] = []
        params:  list[Any] = []
        if status:
            clauses.append("status=?"); params.append(status)
        if triage:
            clauses.append("triage_tier=?"); params.append(triage)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql   = f"SELECT * FROM FileQueue {where} ORDER BY exif_date DESC, id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        conn = self._connect()
        df   = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df

    def get_geo_points(self) -> pd.DataFrame:
        conn = self._connect()
        df = pd.read_sql_query(
            "SELECT filename,filepath,exif_date,gps_lat lat,gps_lon lon "
            "FROM FileQueue WHERE gps_lat IS NOT NULL", conn)
        conn.close()
        return df

    def get_timeline_df(self) -> pd.DataFrame:
        conn = self._connect()
        df = pd.read_sql_query(
            "SELECT substr(exif_date,1,10) exif_date, COUNT(*) count "
            "FROM FileQueue WHERE exif_date IS NOT NULL GROUP BY 1 ORDER BY 1", conn)
        conn.close()
        return df

    # ── KnownFaces ────────────────────────────────────────────────────────
    def add_known_face(self, name: str, embedding: Optional[np.ndarray] = None,
                       is_faceless: bool = False, source_img: str = "") -> int:
        emb_bytes = embedding.astype(np.float32).tobytes() if embedding is not None else None
        with self._write() as c:
            c.execute(
                "INSERT INTO KnownFaces (name,embedding,is_faceless,source_img) VALUES (?,?,?,?)",
                (name, emb_bytes, int(is_faceless), source_img))
            return c.lastrowid  # type: ignore[return-value]

    def load_known_faces(self) -> tuple[list[str], np.ndarray]:
        with self._read() as c:
            c.execute("SELECT name,embedding FROM KnownFaces WHERE embedding IS NOT NULL")
            rows = c.fetchall()
        if not rows:
            return [], np.empty((0, ARCFACE_DIM), dtype=np.float32)
        names = [r["name"] for r in rows]
        embs  = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
        return names, embs

    def get_all_identity_names(self) -> list[str]:
        with self._read() as c:
            c.execute("SELECT DISTINCT name FROM KnownFaces ORDER BY name")
            return [r["name"] for r in c.fetchall()]

    # ── Detections ────────────────────────────────────────────────────────
    def add_detection(self, file_id: int, embedding: Optional[np.ndarray],
                      bbox: dict[str, int], face_crop_path: str = "",
                      confidence: float = 0.0, assigned_name: str = "Desconocido",
                      triage_tier: str = "unclassified",
                      is_faceless: bool = False) -> int:
        emb_bytes = embedding.astype(np.float32).tobytes() if embedding is not None else None
        with self._write() as c:
            c.execute(
                "INSERT INTO Detections "
                "(file_id,face_crop_path,bbox_json,assigned_name,confidence,"
                "triage_tier,embedding,is_faceless) VALUES (?,?,?,?,?,?,?,?)",
                (file_id, face_crop_path, json.dumps(bbox), assigned_name,
                 confidence, triage_tier, emb_bytes, int(is_faceless)))
            return c.lastrowid  # type: ignore[return-value]

    def get_triage_detections(self, tier: str, limit: int = 48) -> pd.DataFrame:
        conn = self._connect()
        df = pd.read_sql_query(
            "SELECT d.*,f.filepath,f.filename FROM Detections d "
            "JOIN FileQueue f ON d.file_id=f.id "
            "WHERE d.triage_tier=? AND d.is_verified=0 AND d.is_false_positive=0 "
            "ORDER BY d.confidence DESC LIMIT ?",
            conn, params=[tier, limit])
        conn.close()
        return df

    def get_unverified_detections(self, limit: int = 48) -> pd.DataFrame:
        conn = self._connect()
        df = pd.read_sql_query(
            "SELECT d.*,f.filepath,f.filename FROM Detections d "
            "JOIN FileQueue f ON d.file_id=f.id "
            "WHERE d.is_verified=0 AND d.is_false_positive=0 "
            "AND d.assigned_name='Desconocido' ORDER BY d.id DESC LIMIT ?",
            conn, params=[limit])
        conn.close()
        return df

    def verify_detection(self, det_id: int, name: str) -> None:
        _before = self._snap_detections([det_id])
        emb_bytes: Optional[bytes] = None
        with self._read() as c:
            c.execute("SELECT embedding FROM Detections WHERE id=?", (det_id,))
            row = c.fetchone()
            if row:
                emb_bytes = row["embedding"]
        with self._write() as c:
            c.execute("UPDATE Detections SET assigned_name=?,is_verified=1,triage_tier='safe' WHERE id=?",
                      (name, det_id))
            # enseñar a KnownFaces si hay embedding
            if emb_bytes:
                c.execute("INSERT INTO KnownFaces (name,embedding) VALUES (?,?)", (name, emb_bytes))
        self._record_tx("VERIFY", _before, {"name": name})

    def mark_false_positive(self, det_id: int) -> None:
        with self._write() as c:
            c.execute("UPDATE Detections SET is_false_positive=1,is_verified=1 WHERE id=?", (det_id,))

    def bulk_verify(self, det_ids: list[int], name: str) -> None:
        _before = self._snap_detections(det_ids)
        with self._write() as c:
            c.executemany(
                "UPDATE Detections SET assigned_name=?,is_verified=1,triage_tier='safe' WHERE id=?",
                [(name, did) for did in det_ids])
            # enseñar primer embedding
            c.execute("SELECT embedding FROM Detections WHERE id=? AND embedding IS NOT NULL LIMIT 1",
                      (det_ids[0],))
            row = c.fetchone()
            if row and row["embedding"]:
                c.execute("INSERT INTO KnownFaces (name,embedding) VALUES (?,?)", (name, row["embedding"]))
        self._record_tx("RENAME", _before, {"name": name, "ids": det_ids})

    def bulk_false_positive(self, det_ids: list[int]) -> None:
        with self._write() as c:
            c.executemany("UPDATE Detections SET is_false_positive=1,is_verified=1 WHERE id=?",
                          [(did,) for did in det_ids])

    # ── Etiquetado Faceless ───────────────────────────────────────────────
    def add_faceless_tag(self, file_id: int, name: str,
                         bbox: Optional[dict[str, int]] = None) -> int:
        """
        Etiqueta manual de identidad SIN embedding facial.
        Permite taggear personas de espaldas, siluetas, etc.
        """
        _before: list[dict] = []
        det_id = self.add_detection(
            file_id=file_id,
            embedding=None,
            bbox=bbox or {"top": 0, "right": 0, "bottom": 0, "left": 0},
            assigned_name=name,
            confidence=1.0,
            triage_tier="safe",
            is_faceless=True,
        )
        # Asegurar que la identidad existe en KnownFaces
        with self._read() as c:
            c.execute("SELECT id FROM KnownFaces WHERE name=? AND is_faceless=1 LIMIT 1", (name,))
            row = c.fetchone()
        if not row:
            self.add_known_face(name, embedding=None, is_faceless=True)
        self._record_tx("FACELESS", _before, {"file_id": file_id, "name": name})
        return det_id

    # ── FileIdentities (Grupos / Symlinks) ────────────────────────────────
    def add_file_identity(self, file_id: int, identity: str,
                          symlink_path: str = "", is_faceless: bool = False) -> None:
        with self._write() as c:
            c.execute(
                "INSERT OR IGNORE INTO FileIdentities (file_id,identity,symlink_path,is_faceless) "
                "VALUES (?,?,?,?)",
                (file_id, identity, symlink_path, int(is_faceless)))

    def get_identities_for_file(self, file_id: int) -> list[str]:
        with self._read() as c:
            c.execute("SELECT identity FROM FileIdentities WHERE file_id=?", (file_id,))
            return [r["identity"] for r in c.fetchall()]

    def update_symlink_path(self, file_id: int, identity: str, symlink_path: str) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE FileIdentities SET symlink_path=? WHERE file_id=? AND identity=?",
                (symlink_path, file_id, identity))

    # ── CLIP Embeddings ───────────────────────────────────────────────────
    def upsert_clip(self, file_id: int, emb: np.ndarray) -> None:
        with self._write() as c:
            c.execute("INSERT OR REPLACE INTO ClipEmbeddings (id,embedding) VALUES (?,?)",
                      (file_id, emb.astype(np.float32).tobytes()))

    def load_clip(self) -> tuple[list[int], np.ndarray]:
        with self._read() as c:
            c.execute("SELECT id,embedding FROM ClipEmbeddings")
            rows = c.fetchall()
        if not rows:
            return [], np.empty((0, 512), dtype=np.float32)
        ids  = [r["id"] for r in rows]
        embs = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
        return ids, embs

    # ── Undo/Redo ─────────────────────────────────────────────────────────
    def _record_tx(self, action: str, before: Any, after: Any) -> None:
        with self._write() as c:
            c.execute("INSERT INTO TxHistory (action,payload) VALUES (?,?)",
                      (action, json.dumps({"before": before, "after": after}, ensure_ascii=False)))

    def _snap_detections(self, det_ids: list[int]) -> list[dict]:
        with self._read() as c:
            ph = ",".join("?" * len(det_ids))
            c.execute(f"SELECT id,assigned_name,triage_tier FROM Detections WHERE id IN ({ph})", det_ids)
            return [dict(r) for r in c.fetchall()]

    def undo_last(self) -> Optional[str]:
        with self._read() as c:
            c.execute("SELECT * FROM TxHistory WHERE undone=0 ORDER BY id DESC LIMIT 1")
            row = c.fetchone()
        if not row:
            return None
        payload = json.loads(row["payload"])
        action  = row["action"]
        if action in ("RENAME", "VERIFY"):
            before: list[dict] = payload.get("before", [])
            with self._write() as c:
                for item in before:
                    c.execute(
                        "UPDATE Detections SET assigned_name=?,triage_tier=? WHERE id=?",
                        (item["assigned_name"], item["triage_tier"], item["id"]))
                c.execute("UPDATE TxHistory SET undone=1 WHERE id=?", (row["id"],))
            return f"Undo '{action}' → {len(before)} detecciones revertidas"
        return None

    # ── Watchdog ──────────────────────────────────────────────────────────
    def log_fs_event(self, event: str, src: str, dest: str = "") -> None:
        with self._write() as c:
            c.execute("INSERT INTO FsEvents (event,src_path,dest_path) VALUES (?,?,?)",
                      (event, src, dest or None))

    # ── Control State ───────────────────────────────────────────────────
    def set_control_state(self, key: str, value: str) -> None:
        with self._write() as c:
            c.execute("INSERT OR REPLACE INTO ControlState (key_name,value,last_updated) VALUES (?,?,?)",
                      (key, value, _now()))

    def get_control_state(self, key: str) -> Optional[str]:
        with self._read() as c:
            c.execute("SELECT value FROM ControlState WHERE key_name=?", (key,))
            row = c.fetchone()
            return row["value"] if row else None

    # ── Phash / Dedupe helpers ──────────────────────────────────────────
    def find_similar_phash(self, phash_hex: str, max_hamming: int = 8) -> list[dict]:
        """Busca archivos con phash cercano. Retorna lista de dict rows con distance."""
        if not phash_hex:
            return []
        try:
            with self._read() as c:
                c.execute("SELECT id,filepath,filename,phash,exif_date FROM FileQueue WHERE phash IS NOT NULL")
                rows = c.fetchall()
        except Exception:
            return []

        def _hamming(a: str, b: str) -> int:
            try:
                ai = int(a, 16)
                bi = int(b, 16)
                return (ai ^ bi).bit_count()
            except Exception:
                return 999

        out: list[dict] = []
        for r in rows:
            ph = r[3]
            if not ph:
                continue
            d = _hamming(phash_hex, ph)
            if d <= max_hamming:
                rec = {k: r[idx] for idx, k in enumerate(["id","filepath","filename","phash","exif_date"]) }
                rec["hamming"] = d
                out.append(rec)
        return out

# ── Helper ────────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
