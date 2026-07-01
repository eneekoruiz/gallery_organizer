"""
core/database.py — Capa de Persistencia Enterprise
WAL · Thread-Safe · Triage · Faceless Tags · Group Symlinks · Undo/Redo
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import re
import sqlite3
import threading
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

import numpy as np
import pandas as pd

from core.config import ARCFACE_DIM, DB_PATH

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# DDL
# ──────────────────────────────────────────────────────────────────────────────
_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;  -- 64MB cache
PRAGMA mmap_size=268435456; -- 256MB mmap
PRAGMA temp_store=MEMORY;
PRAGMA foreign_keys=ON;
PRAGMA page_size=4096;

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
    status       TEXT    NOT NULL DEFAULT 'PENDING', -- PENDING|PROCESSING|AUTO_CLASSIFIED|NEEDS_REVIEW|VERIFIED|ERROR|IGNORED
    triage_tier  TEXT    NOT NULL DEFAULT 'unclassified',
    -- 'safe'(>85%) | 'review'(40-85%) | 'unclassified'(<40%)
    retries      INTEGER NOT NULL DEFAULT 0,
    tags         TEXT,                               -- JSON array de strings
    phash        TEXT,                               -- perceptual hash hex
    exif_date    TEXT,
    gps_lat      REAL,
    gps_lon      REAL,
    hash_sha256  TEXT,
    camera_model TEXT,
    lens_model   TEXT,
    iso          INTEGER,
    f_number     REAL,
    exposure     TEXT,
    quality_score REAL    NOT NULL DEFAULT 0.0,
    exif_datetime TEXT,
    filename_datetime TEXT,
    folder_datetime TEXT,
    filesystem_datetime TEXT,
    best_datetime TEXT,
    date_source  TEXT,
    date_confidence TEXT,
    review_required BOOLEAN NOT NULL DEFAULT 0,
    review_reasons TEXT,
    confidence_score REAL NOT NULL DEFAULT 1.0,
    failed_stage TEXT,
    error_message TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    current_stage TEXT,
    last_updated TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_fq_status  ON FileQueue(status);
CREATE INDEX IF NOT EXISTS idx_fq_triage  ON FileQueue(triage_tier);
CREATE INDEX IF NOT EXISTS idx_fq_date    ON FileQueue(exif_date);
CREATE INDEX IF NOT EXISTS idx_fq_updated ON FileQueue(last_updated);
CREATE INDEX IF NOT EXISTS idx_fq_media   ON FileQueue(media_type);
CREATE INDEX IF NOT EXISTS idx_fq_best_datetime ON FileQueue(best_datetime);
CREATE INDEX IF NOT EXISTS idx_fq_review_required ON FileQueue(review_required);
CREATE INDEX IF NOT EXISTS idx_fq_pending_priority ON FileQueue(status, priority DESC, id);

-- ── DETECCIONES (HITL) ────────────────────────────────────────────────────────
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
    is_high_quality  BOOLEAN NOT NULL DEFAULT 1,
    cluster_id       INTEGER,
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_det_file     ON Detections(file_id);
CREATE INDEX IF NOT EXISTS idx_det_triage   ON Detections(triage_tier, is_verified);
CREATE INDEX IF NOT EXISTS idx_det_name     ON Detections(assigned_name);
CREATE INDEX IF NOT EXISTS idx_det_verified ON Detections(is_verified);

-- ── RELACIONES ARCHIVO ↔ IDENTIDAD (MULTI-TAG GRUPOS) ────────────────────────
CREATE TABLE IF NOT EXISTS FileIdentities (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id      INTEGER NOT NULL REFERENCES FileQueue(id) ON DELETE CASCADE,
    identity     TEXT    NOT NULL,
    symlink_path TEXT,
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
    action  TEXT    NOT NULL,
    payload TEXT    NOT NULL,
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

-- ── CONTROL / ESTADO ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ControlState (
    key_name TEXT PRIMARY KEY,
    value    TEXT,
    last_updated TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- ── CACHÉ DE THUMBNAILS ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ThumbnailCache (
    file_id    INTEGER PRIMARY KEY REFERENCES FileQueue(id) ON DELETE CASCADE,
    thumb_path TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_tc_path ON ThumbnailCache(thumb_path);

-- ── ERRORES PROCESABLES ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ProcessingErrors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id     INTEGER REFERENCES FileQueue(id) ON DELETE CASCADE,
    filepath    TEXT    NOT NULL,
    phase       TEXT    NOT NULL,
    exception   TEXT    NOT NULL,
    retries     INTEGER DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_retry  TEXT
);
CREATE INDEX IF NOT EXISTS idx_pe_file ON ProcessingErrors(file_id);

-- ── VERSIONADO ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS SchemaInfo (
    version INTEGER PRIMARY KEY,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
INSERT OR IGNORE INTO SchemaInfo (version) VALUES (1);
"""


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS DE BÚSQUEDA Y NORMALIZACIÓN
# ──────────────────────────────────────────────────────────────────────────────
def normalize_text(text: str) -> str:
    if not text:
        return ""
    # Convertir a minúsculas
    text = text.lower()
    # Eliminar acentos y diacríticos
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return text


MONTHS_MAP = {
    "enero": "01",
    "january": "01",
    "jan": "01",
    "ene": "01",
    "febrero": "02",
    "february": "02",
    "feb": "02",
    "marzo": "03",
    "march": "03",
    "mar": "03",
    "abril": "04",
    "april": "04",
    "apr": "04",
    "abr": "04",
    "mayo": "05",
    "may": "05",
    "junio": "06",
    "june": "06",
    "jun": "06",
    "julio": "07",
    "july": "07",
    "jul": "07",
    "agosto": "08",
    "august": "08",
    "ago": "08",
    "aug": "08",
    "septiembre": "09",
    "september": "09",
    "sep": "09",
    "sept": "09",
    "octubre": "10",
    "october": "10",
    "oct": "10",
    "noviembre": "11",
    "november": "11",
    "nov": "11",
    "diciembre": "12",
    "december": "12",
    "dec": "12",
    "dic": "12",
}

STOP_WORDS = {
    "en",
    "la",
    "el",
    "de",
    "con",
    "y",
    "o",
    "un",
    "una",
    "unos",
    "unas",
    "para",
    "por",
    "al",
    "del",
    "in",
    "on",
    "at",
    "with",
    "a",
    "the",
    "of",
    "and",
    "or",
    "los",
    "las",
    "sobre",
    "bajo",
    "delante",
    "detras",
}


# ──────────────────────────────────────────────────────────────────────────────
# DatabaseManager — Singleton Thread-Safe
# ──────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None
    _cls_lock: threading.Lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> "DatabaseManager":
        with cls._cls_lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._initialized = False
                cls._instance = obj
            return cls._instance

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        if self._initialized:
            return
        self._write_lock = threading.Lock()
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._init_db()
        self._initialized = True

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_DDL)
            # Para las migraciones sí usamos el cursor con transacciones manuales si es necesario,
            # pero aquí las manejaremos dentro de la función.
            self._run_migrations(conn.cursor())
            from core.migrations.v5_identity_events import migrate

            migrate(conn)
        finally:
            conn.close()

    @property
    def schema_version(self) -> int:
        """Retorna la versión actual del esquema de la base de datos."""
        with self._read() as c:
            try:
                c.execute("SELECT version FROM SchemaInfo")
                row = c.fetchone()
                return row["version"] if row else 1
            except sqlite3.OperationalError:
                return 1

    def _run_migrations(self, cursor: sqlite3.Cursor) -> None:
        """Migraciones idempotentes."""
        try:
            cursor.execute("SELECT version FROM SchemaInfo")
            row = cursor.fetchone()
            version = row["version"] if row else 1
        except sqlite3.OperationalError:
            version = 1

        # Obtener columnas existentes en FileQueue
        cursor.execute("PRAGMA table_info(FileQueue)")
        cols = [r[1] for r in cursor.fetchall()]

        # Asegurar columna phash (Legacy upgrade)
        if "phash" not in cols:
            log.info("Migration: Adding phash column to FileQueue.")
            cursor.execute("ALTER TABLE FileQueue ADD COLUMN phash TEXT")

        # Asegurar columna gps_lon si falta
        if "gps_lon" not in cols:
            log.info("Migration: Adding gps_lon column to FileQueue.")
            cursor.execute("ALTER TABLE FileQueue ADD COLUMN gps_lon REAL")

        # Migración Phase 5 & 6 & Version 4: Nuevas columnas EXIF, Calidad, Triage, Fechas y OCR
        new_fq_cols = {
            "camera_model": "TEXT",
            "lens_model": "TEXT",
            "iso": "INTEGER",
            "f_number": "REAL",
            "exposure": "TEXT",
            "quality_score": "REAL NOT NULL DEFAULT 0.0",
            "best_datetime": "TEXT",
            "date_source": "TEXT",
            "date_confidence": "TEXT",
            "exif_datetime": "TEXT",
            "filename_datetime": "TEXT",
            "folder_datetime": "TEXT",
            "filesystem_datetime": "TEXT",
            "review_required": "BOOLEAN NOT NULL DEFAULT 0",
            "review_reasons": "TEXT",
            "confidence_score": "REAL NOT NULL DEFAULT 1.0",
            "failed_stage": "TEXT",
            "error_message": "TEXT",
            "ocr_text": "TEXT",
            "priority": "INTEGER DEFAULT 0",
            "current_stage": "TEXT",
        }
        for col, ctype in new_fq_cols.items():
            if col not in cols:
                log.info(f"Migration: Adding {col} to FileQueue.")
                cursor.execute(f"ALTER TABLE FileQueue ADD COLUMN {col} {ctype}")

        cursor.execute("PRAGMA table_info(Detections)")
        d_cols = [r[1] for r in cursor.fetchall()]
        if "cluster_id" not in d_cols:
            log.info("Migration: Adding cluster_id to Detections.")
            cursor.execute("ALTER TABLE Detections ADD COLUMN cluster_id INTEGER")
        if "gaze_direction" not in d_cols:
            log.info("Migration: Adding gaze_direction to Detections.")
            cursor.execute("ALTER TABLE Detections ADD COLUMN gaze_direction TEXT")
        if "eye_contact" not in d_cols:
            log.info("Migration: Adding eye_contact to Detections.")
            cursor.execute("ALTER TABLE Detections ADD COLUMN eye_contact BOOLEAN DEFAULT 1")
        if "landmarks_json" not in d_cols:
            log.info("Migration: Adding landmarks_json to Detections.")
            cursor.execute("ALTER TABLE Detections ADD COLUMN landmarks_json TEXT")

        # Crear los nuevos índices si no existen
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fq_best_datetime ON FileQueue(best_datetime);"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fq_status ON FileQueue(status);")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fq_review_required ON FileQueue(review_required);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fq_pending_priority ON FileQueue(status, priority DESC, id);"
        )

        # Migrar DONE a AUTO_CLASSIFIED / NEEDS_REVIEW si hay datos legacy
        cursor.execute(
            "UPDATE FileQueue SET status='AUTO_CLASSIFIED' WHERE status='DONE' AND triage_tier='safe'"
        )
        cursor.execute(
            "UPDATE FileQueue SET status='NEEDS_REVIEW' WHERE status='DONE' AND triage_tier!='safe'"
        )

        # Incrementar version a 4 si es menor
        if version < 4:
            log.info("Migration: Upgrading database schema version to 4.")
            cursor.execute("UPDATE SchemaInfo SET version = 4")
            if cursor.rowcount == 0:
                cursor.execute("INSERT OR IGNORE INTO SchemaInfo (version) VALUES (4)")
            version = 4

        log.info(f"Database schema version: {version}")

    # ── Conexión ──────────────────────────────────────────────────────────
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
            timeout=60.0,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row
        # Registrar funciones personalizadas para búsquedas insensibles a acentos
        conn.create_function("NORMALIZE_TXT", 1, normalize_text)
        # Optimización extrema para app local
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
        conn.execute("PRAGMA mmap_size=268435456;")  # 256MB memory mapping
        conn.execute("PRAGMA temp_store=MEMORY;")
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
                log.exception("Write transaction failed; rolling back.")
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

    # ── FileQueue ─────────────────────────────────────────────────────────
    def delete_file_record(self, file_id: int):
        """Elimina un archivo y todos sus datos asociados (Cascading)."""
        with self._write() as c:
            # Gracias a ON DELETE CASCADE en el esquema, esto limpia Detections, Thumbs, etc.
            c.execute("DELETE FROM FileQueue WHERE id=?", (file_id,))

    def upsert_file(
        self,
        filepath: str,
        filename: str,
        media_type: str = "image",
        phash: Optional[str] = None,
    ) -> tuple[Optional[int], bool]:
        # Issue 11: Calcular SHA256 para deduplicación real
        sha256 = ""
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            sha256 = h.hexdigest()
        except Exception as e:
            log.debug(f"SHA256 calculation skipped for {filepath}: {e}")

        try:
            with self._write() as c:
                # Si ya existe por SHA256 y filepath, ignorar.
                c.execute(
                    "INSERT OR IGNORE INTO FileQueue (filepath,filename,media_type,phash,hash_sha256,last_updated) "
                    "VALUES (?,?,?,?,?,?)",
                    (filepath, filename, media_type, phash, sha256, _now()),
                )
                if c.lastrowid:
                    return c.lastrowid, True

                c.execute("SELECT id FROM FileQueue WHERE filepath=?", (filepath,))
                row = c.fetchone()
                return (row["id"] if row else None), False
        except sqlite3.Error:
            return None, False

    def set_processing(self, file_id: int) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE FileQueue SET status='PROCESSING', current_stage=NULL, last_updated=? WHERE id=?",
                (_now(), file_id),
            )

    def update_done(
        self,
        file_id: int,
        tags: list[str],
        triage_tier: str,
        exif_date: Optional[str] = None,
        gps: Optional[tuple[float, float]] = None,
        thumb_path: Optional[str] = None,
        phash: Optional[str] = None,
        camera_model: Optional[str] = None,
        lens_model: Optional[str] = None,
        iso: Optional[int] = None,
        f_number: Optional[float] = None,
        exposure: Optional[str] = None,
        quality_score: float = 0.0,
        exif_datetime: Optional[str] = None,
        filename_datetime: Optional[str] = None,
        folder_datetime: Optional[str] = None,
        filesystem_datetime: Optional[str] = None,
        best_datetime: Optional[str] = None,
        date_source: Optional[str] = None,
        date_confidence: Optional[str] = None,
        review_required: bool = False,
        review_reasons: Optional[list[str]] = None,
        confidence_score: float = 1.0,
        status: str = "AUTO_CLASSIFIED",
        ocr_text: Optional[str] = None,
        detections_payload: Optional[list[dict]] = None,
        clip_embedding: Optional[bytes] = None,
    ) -> None:
        reasons_json = json.dumps(review_reasons or [], ensure_ascii=False)
        with self._write() as c:
            # 1. Update FileQueue
            c.execute(
                "UPDATE FileQueue SET status=?, triage_tier=?, tags=?, "
                "exif_date=?, gps_lat=?, gps_lon=?, phash=?, "
                "camera_model=?, lens_model=?, iso=?, f_number=?, exposure=?, "
                "quality_score=?, exif_datetime=?, filename_datetime=?, folder_datetime=?, "
                "filesystem_datetime=?, best_datetime=?, date_source=?, date_confidence=?, "
                "review_required=?, review_reasons=?, confidence_score=?, ocr_text=?, priority=0, current_stage=NULL, failed_stage=NULL, error_message=NULL, last_updated=? WHERE id=?",
                (
                    status,
                    triage_tier,
                    json.dumps(tags, ensure_ascii=False),
                    exif_date,
                    gps[0] if gps else None,
                    gps[1] if gps else None,
                    phash,
                    camera_model,
                    lens_model,
                    iso,
                    f_number,
                    exposure,
                    quality_score,
                    exif_datetime,
                    filename_datetime,
                    folder_datetime,
                    filesystem_datetime,
                    best_datetime,
                    date_source,
                    date_confidence,
                    1 if review_required else 0,
                    reasons_json,
                    confidence_score,
                    ocr_text,
                    _now(),
                    file_id,
                ),
            )
            # 2. Update Thumbnail Cache
            if thumb_path:
                c.execute(
                    "INSERT OR REPLACE INTO ThumbnailCache (file_id, thumb_path) VALUES (?,?)",
                    (file_id, thumb_path),
                )
            # 3. SRE Phase 4: Atomic insertion of Detections
            if detections_payload:
                c.execute("DELETE FROM Detections WHERE file_id=? AND is_faceless=0", (file_id,))
                for det in detections_payload:
                    c.execute(
                        "INSERT INTO Detections (file_id, embedding, bbox_json, face_crop_path, "
                        "confidence, assigned_name, triage_tier, is_high_quality, gaze_direction, eye_contact, landmarks_json) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            file_id,
                            det.get("embedding"),
                            json.dumps(det.get("bbox", {})),
                            det.get("face_crop_path"),
                            det.get("confidence", 0.0),
                            det.get("assigned_name", "Desconocido"),
                            det.get("triage_tier", "unclassified"),
                            1 if det.get("is_high_quality", True) else 0,
                            det.get("gaze_direction"),
                            1 if det.get("eye_contact", True) else 0,
                            json.dumps(det.get("landmarks", [])) if det.get("landmarks") else None,
                        ),
                    )
            # 4. SRE Phase 4: Atomic insertion of CLIP Embeddings
            if clip_embedding:
                c.execute(
                    "INSERT OR REPLACE INTO ClipEmbeddings (id, embedding) VALUES (?, ?)",
                    (file_id, clip_embedding),
                )

    def update_error(self, file_id: int, stage: str = "unknown", message: str = "") -> None:
        filepath = ""
        with self._write() as c:
            # Recuperar filepath para el log de errores
            row = c.execute("SELECT filepath FROM FileQueue WHERE id=?", (file_id,)).fetchone()
            if row:
                filepath = row["filepath"]

            # Incrementar retries
            c.execute(
                "UPDATE FileQueue SET retries=retries+1, last_updated=? WHERE id=?",
                (_now(), file_id),
            )

            # Obtener retries actualizados
            row_retries = c.execute(
                "SELECT retries FROM FileQueue WHERE id=?", (file_id,)
            ).fetchone()
            current_retries = row_retries["retries"] if row_retries else 0

            # Decidir si pasar a ERROR final o dejar en PENDING para reintento automático
            status = "ERROR" if current_retries >= 3 else "PENDING"
            c.execute(
                "UPDATE FileQueue SET status=?, failed_stage=?, error_message=?, priority=0, current_stage=NULL, last_updated=? WHERE id=?",
                (status, stage, message, _now(), file_id),
            )

            # Registrar en la tabla de errores detallados
            c.execute(
                "INSERT INTO ProcessingErrors (file_id, filepath, phase, exception, retries) "
                "VALUES (?, ?, ?, ?, ?)",
                (file_id, filepath, stage, message, current_retries),
            )

    def update_stage(self, file_id: int, stage: str) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE FileQueue SET current_stage=?, last_updated=? WHERE id=?",
                (stage, _now(), file_id),
            )

    def prioritize_file(self, file_id: int) -> None:
        with self._write() as c:
            pending = c.execute(
                "SELECT 1 FROM FileQueue WHERE id=? AND status='PENDING'",
                (file_id,),
            ).fetchone()
            if not pending:
                return
            row = c.execute("SELECT MAX(priority) FROM FileQueue WHERE status='PENDING'").fetchone()
            max_p = row[0] if row and row[0] is not None else 0
            c.execute(
                "UPDATE FileQueue SET priority=?, last_updated=? WHERE id=?",
                (max_p + 1, _now(), file_id),
            )

    def prepare_manual_processing(self, file_id: int) -> Optional[dict[str, Any]]:
        """Move a queue item into PROCESSING for immediate manual execution."""
        with self._write() as c:
            row = c.execute(
                "SELECT * FROM FileQueue WHERE id=? AND status NOT IN ('PROCESSING', 'IGNORED')",
                (file_id,),
            ).fetchone()
            if not row:
                return None
            c.execute(
                "UPDATE FileQueue SET status='PROCESSING', retries=0, priority=0, "
                "current_stage=NULL, failed_stage=NULL, error_message=NULL, last_updated=? "
                "WHERE id=?",
                (_now(), file_id),
            )
            result = dict(row)
            result["status"] = "PROCESSING"
            result["retries"] = 0
            result["priority"] = 0
            result["current_stage"] = None
            result["failed_stage"] = None
            result["error_message"] = None
            return result

    def retry_all_errors(self) -> int:
        """Reinicia todos los archivos con estado ERROR a PENDING y resetea retries."""
        with self._write() as c:
            c.execute(
                "UPDATE FileQueue SET status='PENDING', retries=0, priority=0, current_stage=NULL, failed_stage=NULL, error_message=NULL, last_updated=? WHERE status='ERROR'",
                (_now(),),
            )
            count = c.rowcount
            # Limpiar tabla de errores descriptivos
            c.execute("DELETE FROM ProcessingErrors")
            return count

    def clean_stale_thumbnails(self) -> int:
        """Elimina entradas de caché que ya no existen en FileQueue."""
        with self._write() as c:
            c.execute("DELETE FROM ThumbnailCache WHERE file_id NOT IN (SELECT id FROM FileQueue)")
            return c.rowcount

    def move_filepath(self, old: str, new: str) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE FileQueue SET filepath=?, filename=?, last_updated=? WHERE filepath=?",
                (new, Path(new).name, _now(), old),
            )

    def delete_by_path(self, filepath: str) -> None:
        with self._write() as c:
            c.execute("DELETE FROM FileQueue WHERE filepath=?", (filepath,))

    def get_missing_filequeue_records(self, limit: int = 200) -> list[dict[str, Any]]:
        """Return FileQueue rows whose source file no longer exists on disk."""
        with self._read() as c:
            c.execute(
                "SELECT id, filepath, filename, status, triage_tier FROM FileQueue ORDER BY id DESC"
            )
            rows = c.fetchall()

        missing: list[dict[str, Any]] = []
        for row in rows:
            path = row["filepath"]
            if not Path(path).exists():
                missing.append(dict(row))
                if len(missing) >= limit:
                    break
        return missing

    def get_broken_symlink_records(self, limit: int = 200) -> list[dict[str, Any]]:
        """Return FileIdentities rows with broken or missing symlink paths."""
        with self._read() as c:
            c.execute(
                "SELECT id, file_id, identity, symlink_path, is_faceless FROM FileIdentities ORDER BY id DESC"
            )
            rows = c.fetchall()

        broken: list[dict[str, Any]] = []
        for row in rows:
            link = row["symlink_path"]
            if not link:
                broken.append(dict(row))
            else:
                p = Path(link)
                if not p.exists() or not p.is_symlink():
                    broken.append(dict(row))
            if len(broken) >= limit:
                break
        return broken

    def cleanup_broken_symlinks(self, limit: int = 200) -> int:
        """Remove broken FileIdentities entries and any dangling link file on disk."""
        broken = self.get_broken_symlink_records(limit=limit)
        removed = 0
        for row in broken:
            link = row.get("symlink_path") or ""
            if link:
                p = Path(link)
                try:
                    if p.exists() or p.is_symlink():
                        p.unlink()
                except Exception as e:
                    log.error("Could not unlink broken symlink %s: %s", link, e)
            try:
                with self._write() as c:
                    c.execute("DELETE FROM FileIdentities WHERE id=?", (row["id"],))
                removed += 1
            except Exception:
                log.exception("Failed to delete broken FileIdentities row %s", row.get("id"))
        return removed

    def cleanup_missing_files(self, limit: int = 200) -> int:
        """Remove FileQueue rows whose files disappeared from disk."""
        missing = self.get_missing_filequeue_records(limit=limit)
        removed = 0
        for row in missing:
            try:
                self.delete_by_path(row["filepath"])
                removed += 1
            except Exception:
                log.exception("Failed to delete missing file row %s", row.get("filepath"))
        return removed

    def next_pending(self) -> Optional[dict[str, Any]]:
        batch = self.next_batch_pending(limit=1)
        return batch[0] if batch else None

    def next_batch_pending(self, limit: int = 1) -> list[dict[str, Any]]:
        with self._write() as c:
            c.execute(
                "SELECT * FROM FileQueue WHERE status='PENDING' ORDER BY priority DESC, id LIMIT ?",
                (limit,),
            )
            rows = c.fetchall()
            if not rows:
                return []

            ids = [row["id"] for row in rows]
            placeholders = ",".join("?" * len(ids))
            c.execute(
                f"UPDATE FileQueue SET status='PROCESSING', last_updated=? WHERE id IN ({placeholders})",
                [_now()] + ids,
            )

            results = []
            for row in rows:
                res = dict(row)
                res["status"] = "PROCESSING"
                results.append(res)
            return results

    def get_stats(self) -> dict[str, int]:
        with self._read() as c:
            c.execute("""SELECT
                COUNT(*) total,
                SUM(status IN ('DONE', 'AUTO_CLASSIFIED', 'NEEDS_REVIEW', 'VERIFIED')) done,
                SUM(status='PENDING')     pending,
                SUM(status='PROCESSING')  processing,
                SUM(status='ERROR')       errors,
                SUM(triage_tier='safe' AND status IN ('DONE', 'AUTO_CLASSIFIED', 'NEEDS_REVIEW', 'VERIFIED')) safe,
                SUM(triage_tier='review' AND status IN ('DONE', 'AUTO_CLASSIFIED', 'NEEDS_REVIEW', 'VERIFIED')) review,
                SUM(triage_tier='unclassified' AND status IN ('DONE', 'AUTO_CLASSIFIED', 'NEEDS_REVIEW', 'VERIFIED')) unclassified
              FROM FileQueue""")
            row = c.fetchone()
            return {k: (v or 0) for k, v in dict(row).items()} if row else {}

    def get_file_by_path(self, filepath: str) -> Optional[dict]:
        with self._read() as c:
            c.execute("SELECT * FROM FileQueue WHERE filepath=?", (filepath,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_file_record(self, file_id: int) -> Optional[dict]:
        with self._read() as c:
            c.execute("SELECT * FROM FileQueue WHERE id=?", (file_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_detections_for_file(self, file_id: int) -> list[dict]:
        with self._read() as c:
            c.execute(
                "SELECT * FROM Detections WHERE file_id=? AND is_false_positive=0",
                (file_id,),
            )
            return [dict(r) for r in c.fetchall()]

    def update_detection_gaze(
        self, detection_id: int, eye_contact: bool, gaze_direction: str
    ) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE Detections SET eye_contact=?, gaze_direction=? WHERE id=?",
                (1 if eye_contact else 0, gaze_direction, detection_id),
            )

    def update_detection_gaze_full(
        self, detection_id: int, eye_contact: bool, gaze_direction: str, landmarks: list
    ) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE Detections SET eye_contact=?, gaze_direction=?, landmarks_json=? WHERE id=?",
                (
                    1 if eye_contact else 0,
                    gaze_direction,
                    json.dumps(landmarks) if landmarks else None,
                    detection_id,
                ),
            )

    def get_symlink_paths_for_file(self, file_id: int) -> list[str]:
        with self._read() as c:
            c.execute("SELECT symlink_path FROM FileIdentities WHERE file_id=?", (file_id,))
            return [r["symlink_path"] for r in c.fetchall() if r["symlink_path"]]

    def get_detection_ids_for_files(self, file_ids: list[int]) -> list[int]:
        if not file_ids:
            return []
        with self._read() as c:
            ph = ",".join("?" * len(file_ids))
            c.execute(f"SELECT id FROM Detections WHERE file_id IN ({ph})", file_ids)
            return [r["id"] for r in c.fetchall()]

    def get_files_by_ids_with_thumbs(self, file_ids: list[int]) -> pd.DataFrame:
        if not file_ids:
            return pd.DataFrame()
        ph = ",".join("?" * len(file_ids))
        sql = f"""
            SELECT f.*, t.thumb_path as cached_thumb 
            FROM FileQueue f 
            LEFT JOIN ThumbnailCache t ON f.id = t.file_id
            WHERE f.id IN ({ph})
        """
        conn = self._connect()
        df = pd.read_sql_query(sql, conn, params=file_ids)
        conn.close()
        # Reordenar para preservar el orden de file_ids (importante para search ranking)
        df["id"] = df["id"].astype(int)
        df.set_index("id", inplace=True, drop=False)
        return df.reindex(file_ids).dropna(subset=["id"])

    def get_files_df(
        self,
        status: Optional[str] = None,
        triage: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> pd.DataFrame:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            if status == "DONE":
                clauses.append("status IN ('AUTO_CLASSIFIED', 'NEEDS_REVIEW', 'VERIFIED')")
            else:
                clauses.append("status=?")
                params.append(status)
        if triage:
            clauses.append("triage_tier=?")
            params.append(triage)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT * FROM FileQueue {where} ORDER BY exif_date DESC, id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        conn = self._connect()
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df

    def get_queue_files_df(self, limit: int = 50) -> pd.DataFrame:
        sql = """
            SELECT id, filepath, filename, media_type, status, priority, current_stage, failed_stage, error_message, last_updated 
            FROM FileQueue 
            ORDER BY 
              CASE status 
                WHEN 'PROCESSING' THEN 1 
                WHEN 'PENDING' THEN 2 
                WHEN 'ERROR' THEN 3 
                ELSE 4 
              END, 
              priority DESC, 
              id DESC 
            LIMIT ?
        """
        conn = self._connect()
        df = pd.read_sql_query(sql, conn, params=(limit,))
        conn.close()
        return df

    def get_files_count(
        self,
        status: Optional[str] = None,
        triage: Optional[str] = None,
        camera: Optional[str] = None,
        lens: Optional[str] = None,
    ) -> int:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            if status == "DONE":
                clauses.append("status IN ('AUTO_CLASSIFIED', 'NEEDS_REVIEW', 'VERIFIED')")
            else:
                clauses.append("status=?")
                params.append(status)
        if triage:
            clauses.append("triage_tier=?")
            params.append(triage)
        if camera:
            clauses.append("camera_model=?")
            params.append(camera)
        if lens:
            clauses.append("lens_model=?")
            params.append(lens)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT COUNT(*) FROM FileQueue {where}"
        with self._read() as c:
            return c.execute(sql, params).fetchone()[0]

    def get_files_with_thumbs_df(
        self,
        status: Optional[str] = None,
        triage: Optional[str] = None,
        camera: Optional[str] = None,
        lens: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> pd.DataFrame:
        """Versión optimizada que incluye el path de la miniatura cacheada."""
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            if status == "DONE":
                clauses.append("f.status IN ('AUTO_CLASSIFIED', 'NEEDS_REVIEW', 'VERIFIED')")
            else:
                clauses.append("f.status=?")
                params.append(status)
        if triage:
            clauses.append("f.triage_tier=?")
            params.append(triage)
        if camera:
            clauses.append("f.camera_model=?")
            params.append(camera)
        if lens:
            clauses.append("f.lens_model=?")
            params.append(lens)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"""
            SELECT f.*, t.thumb_path as cached_thumb 
            FROM FileQueue f 
            LEFT JOIN ThumbnailCache t ON f.id = t.file_id
            {where} 
            ORDER BY f.exif_date DESC, f.id DESC 
            LIMIT ? OFFSET ?
        """
        params += [limit, offset]
        conn = self._connect()
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df

    def get_unique_metadata(self) -> dict[str, list[str]]:
        """Retorna valores únicos para filtros (Cámaras, Lentes)."""
        with self._read() as c:
            cameras = c.execute(
                "SELECT DISTINCT camera_model FROM FileQueue WHERE camera_model IS NOT NULL"
            ).fetchall()
            lenses = c.execute(
                "SELECT DISTINCT lens_model FROM FileQueue WHERE lens_model IS NOT NULL"
            ).fetchall()
            return {
                "cameras": [r[0] for r in cameras],
                "lenses": [r[0] for r in lenses],
            }

    def get_duplicate_groups(self) -> list[pd.DataFrame]:
        """Agrupa archivos que tienen el mismo phash."""
        sql = """
            SELECT phash, COUNT(*) as cnt 
            FROM FileQueue 
            WHERE phash IS NOT NULL AND phash != ''
            GROUP BY phash 
            HAVING cnt > 1
        """
        with self._read() as c:
            hashes = [r["phash"] for r in c.execute(sql).fetchall()]

        groups = []
        for h in hashes:
            sql_group = """
                SELECT f.*, t.thumb_path as cached_thumb
                FROM FileQueue f
                LEFT JOIN ThumbnailCache t ON f.id = t.file_id
                WHERE f.phash = ?
            """
            conn = self._connect()
            df = pd.read_sql_query(sql_group, conn, params=(h,))
            conn.close()
            if not df.empty:
                groups.append(df)
        return groups

    def get_burst_groups(self, window_seconds: int = 3) -> list[pd.DataFrame]:
        """Agrupa archivos tomados en ráfaga (ventana de tiempo pequeña)."""
        sql = (
            "SELECT id, exif_date FROM FileQueue WHERE exif_date IS NOT NULL ORDER BY exif_date ASC"
        )
        with self._read() as c:
            rows = [dict(r) for r in c.execute(sql).fetchall()]

        if not rows:
            return []

        from datetime import datetime

        groups_ids = []
        current_group = [rows[0]["id"]]
        try:
            last_date = datetime.fromisoformat(rows[0]["exif_date"])
        except ValueError:
            return []  # O manejar fechas mal formadas

        for i in range(1, len(rows)):
            try:
                curr_date = datetime.fromisoformat(rows[i]["exif_date"])
            except ValueError:
                continue

            diff = (curr_date - last_date).total_seconds()

            if diff <= window_seconds:
                current_group.append(rows[i]["id"])
            else:
                if len(current_group) > 1:
                    groups_ids.append(current_group)
                current_group = [rows[i]["id"]]
            last_date = curr_date

        if len(current_group) > 1:
            groups_ids.append(current_group)

        # Convertir IDs a DataFrames
        results = []
        for ids in groups_ids:
            results.append(self.get_files_by_ids_with_thumbs(ids))
        return results

    def get_geo_points(self) -> pd.DataFrame:
        conn = self._connect()
        df = pd.read_sql_query(
            "SELECT filename,filepath,exif_date,gps_lat lat,gps_lon lon "
            "FROM FileQueue WHERE gps_lat IS NOT NULL",
            conn,
        )
        conn.close()
        return df

    def get_timeline_df(self) -> pd.DataFrame:
        conn = self._connect()
        df = pd.read_sql_query(
            "SELECT substr(exif_date,1,10) exif_date, COUNT(*) count "
            "FROM FileQueue WHERE exif_date IS NOT NULL GROUP BY 1 ORDER BY 1",
            conn,
        )
        conn.close()
        return df

    def get_files_by_date_range(
        self, d_from: str, d_to: str, limit: int = 100, offset: int = 0
    ) -> pd.DataFrame:
        sql = """
            SELECT f.*, t.thumb_path as cached_thumb 
            FROM FileQueue f
            LEFT JOIN ThumbnailCache t ON f.id = t.file_id
            WHERE substr(f.exif_date,1,10) >= ? AND substr(f.exif_date,1,10) <= ?
            ORDER BY f.exif_date DESC, f.id DESC
            LIMIT ? OFFSET ?
        """
        conn = self._connect()
        df = pd.read_sql_query(sql, conn, params=[d_from, d_to, limit, offset])
        conn.close()
        return df

    # ── KnownFaces ────────────────────────────────────────────────────────
    def add_known_face(
        self,
        name: str,
        embedding: Optional[np.ndarray] = None,
        is_faceless: bool = False,
        source_img: str = "",
    ) -> int:
        emb_bytes = embedding.astype(np.float32).tobytes() if embedding is not None else None
        with self._write() as c:
            c.execute(
                "INSERT INTO KnownFaces (name,embedding,is_faceless,source_img) VALUES (?,?,?,?)",
                (name, emb_bytes, int(is_faceless), source_img),
            )
            return c.lastrowid  # type: ignore[return-value]

    def load_known_faces(self) -> tuple[list[str], np.ndarray]:
        with self._read() as c:
            c.execute("SELECT name,embedding FROM KnownFaces WHERE embedding IS NOT NULL")
            rows = c.fetchall()
        if not rows:
            return [], np.empty((0, ARCFACE_DIM), dtype=np.float32)
        names = [r["name"] for r in rows]
        embs = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
        return names, embs

    def get_all_identity_names(self) -> list[str]:
        with self._read() as c:
            c.execute("SELECT DISTINCT name FROM KnownFaces ORDER BY name")
            return [r["name"] for r in c.fetchall()]

    # ── Detections ────────────────────────────────────────────────────────
    def add_detection(
        self,
        file_id: int,
        embedding: Optional[np.ndarray],
        bbox: dict[str, int],
        face_crop_path: str = "",
        confidence: float = 0.0,
        assigned_name: str = "Desconocido",
        triage_tier: str = "unclassified",
        is_faceless: bool = False,
        is_high_quality: bool = True,
    ) -> int:
        emb_bytes = embedding.astype(np.float32).tobytes() if embedding is not None else None
        with self._write() as c:
            c.execute(
                "INSERT INTO Detections "
                "(file_id,face_crop_path,bbox_json,assigned_name,confidence,"
                "triage_tier,embedding,is_faceless,is_high_quality) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    file_id,
                    face_crop_path,
                    json.dumps(bbox),
                    assigned_name,
                    confidence,
                    triage_tier,
                    emb_bytes,
                    int(is_faceless),
                    int(is_high_quality),
                ),
            )
            return c.lastrowid  # type: ignore[return-value]

    def get_triage_count(self, tier: str) -> int:
        with self._read() as c:
            return c.execute(
                "SELECT COUNT(*) FROM Detections "
                "WHERE triage_tier=? AND is_verified=0 AND is_false_positive=0",
                (tier,),
            ).fetchone()[0]

    def get_triage_detections(self, tier: str, limit: int = 48, offset: int = 0) -> pd.DataFrame:
        conn = self._connect()
        df = pd.read_sql_query(
            "SELECT d.*,f.filepath,f.filename FROM Detections d "
            "JOIN FileQueue f ON d.file_id=f.id "
            "WHERE d.triage_tier=? AND d.is_verified=0 AND d.is_false_positive=0 "
            "ORDER BY d.confidence DESC LIMIT ? OFFSET ?",
            conn,
            params=[tier, limit, offset],
        )
        conn.close()
        return df

    def get_unverified_detections(self, limit: int = 48, offset: int = 0) -> pd.DataFrame:
        conn = self._connect()
        df = pd.read_sql_query(
            "SELECT d.*,f.filepath,f.filename FROM Detections d "
            "JOIN FileQueue f ON d.file_id=f.id "
            "WHERE d.is_verified=0 AND d.is_false_positive=0 "
            "AND d.assigned_name='Desconocido' ORDER BY d.id DESC LIMIT ? OFFSET ?",
            conn,
            params=[limit, offset],
        )
        conn.close()
        return df

    def verify_detection(self, det_id: int, name: str) -> None:
        _before = self._snap_detections([det_id])
        emb_bytes: Optional[bytes] = None
        file_id: int = 0
        is_high_q: bool = True
        with self._read() as c:
            row = c.execute(
                "SELECT embedding, file_id, is_high_quality FROM Detections WHERE id=?",
                (det_id,),
            ).fetchone()
            if row:
                emb_bytes = row["embedding"]
                file_id = row["file_id"]
                is_high_q = bool(row["is_high_quality"])

        identity_id = None
        with self._write() as c:
            c.execute(
                "UPDATE Detections SET assigned_name=?,is_verified=1,triage_tier='safe' WHERE id=?",
                (name, det_id),
            )
            # Issue 3 & 19: Deduplicación + Filtro de Calidad
            # Solo "enseñamos" a la IA si la cara es nítida (is_high_q)
            if emb_bytes and is_high_q:
                count = c.execute(
                    "SELECT COUNT(*) FROM KnownFaces WHERE name=?", (name,)
                ).fetchone()[0]
                if count < 10:
                    c.execute(
                        "INSERT INTO KnownFaces (name,embedding) VALUES (?,?)",
                        (name, emb_bytes),
                    )
                    identity_id = c.lastrowid

            # Issue 8: Actualizar symlinks en disco (vía FileIdentities)
            c.execute(
                "INSERT OR IGNORE INTO FileIdentities (file_id, identity) VALUES (?,?)",
                (file_id, name),
            )

        # Issue 4: Guardamos el ID de la identidad creada para el deshacer
        self._record_tx("VERIFY", _before, {"name": name, "identity_id": identity_id})

    def mark_false_positive(self, det_id: int) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE Detections SET is_false_positive=1,is_verified=1 WHERE id=?",
                (det_id,),
            )

    def bulk_verify(self, det_ids: list[int], name: str) -> None:
        _before = self._snap_detections(det_ids)
        with self._write() as c:
            c.executemany(
                "UPDATE Detections SET assigned_name=?,is_verified=1,triage_tier='safe' WHERE id=?",
                [(name, did) for did in det_ids],
            )
            # enseñar primer embedding (Upsert identity)
            c.execute(
                "SELECT embedding FROM Detections WHERE id=? AND embedding IS NOT NULL LIMIT 1",
                (det_ids[0],),
            )
            row = c.fetchone()
            if row and row["embedding"]:
                # Guardamos el ID de la identidad creada para el deshacer
                c.execute(
                    "INSERT INTO KnownFaces (name,embedding) VALUES (?,?)",
                    (name, row["embedding"]),
                )
                identity_id = c.lastrowid
                self._record_tx(
                    "RENAME",
                    _before,
                    {"name": name, "ids": det_ids, "identity_id": identity_id},
                )
            else:
                self._record_tx("RENAME", _before, {"name": name, "ids": det_ids})

    def bulk_false_positive(self, det_ids: list[int]) -> None:
        with self._write() as c:
            c.executemany(
                "UPDATE Detections SET is_false_positive=1,is_verified=1 WHERE id=?",
                [(did,) for did in det_ids],
            )

    # ── Etiquetado Faceless ───────────────────────────────────────────────
    def add_faceless_tag(
        self, file_id: int, name: str, bbox: Optional[dict[str, int]] = None
    ) -> int:
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
        with self._write() as c:
            c.execute("UPDATE Detections SET is_verified=1 WHERE id=?", (det_id,))
        # Asegurar que la identidad existe en KnownFaces
        with self._read() as c:
            c.execute(
                "SELECT id FROM KnownFaces WHERE name=? AND is_faceless=1 LIMIT 1",
                (name,),
            )
            row = c.fetchone()
        if not row:
            self.add_known_face(name, embedding=None, is_faceless=True)
        self._record_tx("FACELESS", _before, {"file_id": file_id, "name": name})
        return det_id

    # ── FileIdentities (Grupos / Symlinks) ────────────────────────────────
    def add_file_identity(
        self,
        file_id: int,
        identity: str,
        symlink_path: str = "",
        is_faceless: bool = False,
    ) -> None:
        with self._write() as c:
            c.execute(
                "INSERT OR IGNORE INTO FileIdentities (file_id,identity,symlink_path,is_faceless) "
                "VALUES (?,?,?,?)",
                (file_id, identity, _norm_path(symlink_path), int(is_faceless)),
            )

    def get_identities_for_file(self, file_id: int) -> list[str]:
        with self._read() as c:
            c.execute("SELECT identity FROM FileIdentities WHERE file_id=?", (file_id,))
            return [r["identity"] for r in c.fetchall()]

    def update_symlink_path(self, file_id: int, identity: str, symlink_path: str) -> None:
        with self._write() as c:
            c.execute(
                "UPDATE FileIdentities SET symlink_path=? WHERE file_id=? AND identity=?",
                (_norm_path(symlink_path), file_id, identity),
            )

    def get_file_identity_by_symlink_path(self, symlink_path: str) -> Optional[dict[str, Any]]:
        with self._read() as c:
            c.execute(
                "SELECT id, file_id, identity, symlink_path, is_faceless FROM FileIdentities WHERE symlink_path=? LIMIT 1",
                (_norm_path(symlink_path),),
            )
            row = c.fetchone()
            return dict(row) if row else None

    def update_symlink_path_by_path(self, old_path: str, new_path: str) -> bool:
        with self._write() as c:
            c.execute(
                "UPDATE FileIdentities SET symlink_path=? WHERE symlink_path=?",
                (_norm_path(new_path), _norm_path(old_path)),
            )
            return c.rowcount > 0

    def delete_file_identity_by_symlink_path(self, symlink_path: str) -> bool:
        with self._write() as c:
            c.execute(
                "DELETE FROM FileIdentities WHERE symlink_path=?",
                (_norm_path(symlink_path),),
            )
            return c.rowcount > 0

    # ── CLIP Embeddings ───────────────────────────────────────────────────
    def upsert_clip(self, file_id: int, emb: np.ndarray) -> None:
        with self._write() as c:
            c.execute(
                "INSERT OR REPLACE INTO ClipEmbeddings (id,embedding) VALUES (?,?)",
                (file_id, emb.astype(np.float32).tobytes()),
            )

    def load_clip(self) -> tuple[list[int], np.ndarray]:
        with self._read() as c:
            c.execute("SELECT id,embedding FROM ClipEmbeddings")
            rows = c.fetchall()
        if not rows:
            return [], np.empty((0, 512), dtype=np.float32)
        ids = [r["id"] for r in rows]
        embs = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
        return ids, embs

    # ── Undo/Redo ─────────────────────────────────────────────────────────
    def _record_tx(self, action: str, before: Any, after: Any) -> None:
        with self._write() as c:
            c.execute(
                "INSERT INTO TxHistory (action,payload) VALUES (?,?)",
                (
                    action,
                    json.dumps({"before": before, "after": after}, ensure_ascii=False),
                ),
            )

    def _snap_detections(self, det_ids: list[int]) -> list[dict]:
        with self._read() as c:
            ph = ",".join("?" * len(det_ids))
            c.execute(
                f"SELECT id,assigned_name,triage_tier FROM Detections WHERE id IN ({ph})",
                det_ids,
            )
            return [dict(r) for r in c.fetchall()]

    def undo_last(self) -> Optional[str]:
        # Issue 16: Hacer atómico el proceso de deshacer
        with self._write() as c:
            c.execute("SELECT * FROM TxHistory WHERE undone=0 ORDER BY id DESC LIMIT 1")
            row = c.fetchone()
            if not row:
                return None

            payload = json.loads(row["payload"])
            action = row["action"]
            if action in ("RENAME", "VERIFY"):
                before: list[dict] = payload.get("before", [])
                after: dict = payload.get("after", {})
                identity_id = after.get("identity_id")

                for item in before:
                    c.execute(
                        "UPDATE Detections SET assigned_name=?,triage_tier=?,is_verified=0 WHERE id=?",
                        (item["assigned_name"], item["triage_tier"], item["id"]),
                    )
                # Limpiar polución de identidades
                if identity_id:
                    c.execute("DELETE FROM KnownFaces WHERE id=?", (identity_id,))

                c.execute("UPDATE TxHistory SET undone=1 WHERE id=?", (row["id"],))
                return f"Undo '{action}' → {len(before)} detecciones revertidas"
        return None

    def get_last_tx(self) -> Optional[dict[str, Any]]:
        with self._read() as c:
            c.execute(
                "SELECT id, ts, action, payload, undone FROM TxHistory ORDER BY id DESC LIMIT 1"
            )
            row = c.fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            payload = json.loads(data.get("payload") or "{}")
        except Exception:
            payload = {}
        before = payload.get("before", [])
        after = payload.get("after", {})
        data["before_count"] = len(before) if isinstance(before, list) else 0
        data["after"] = after if isinstance(after, dict) else {}
        return data

    def has_pending_maintenance(self) -> bool:
        return bool(
            self.get_missing_filequeue_records(limit=1) or self.get_broken_symlink_records(limit=1)
        )

    # ── Watchdog ──────────────────────────────────────────────────────────
    def log_fs_event(self, event: str, src: str, dest: str = "") -> None:
        with self._write() as c:
            c.execute(
                "INSERT INTO FsEvents (event,src_path,dest_path) VALUES (?,?,?)",
                (event, src, dest or None),
            )

    # ── Control State ───────────────────────────────────────────────────
    def set_control_state(self, key: str, value: str) -> None:
        with self._write() as c:
            c.execute(
                "INSERT OR REPLACE INTO ControlState (key_name,value,last_updated) VALUES (?,?,?)",
                (key, value, _now()),
            )

    def get_control_state(self, key: str) -> Optional[str]:
        with self._read() as c:
            c.execute("SELECT value FROM ControlState WHERE key_name=?", (key,))
            row = c.fetchone()
            return row["value"] if row else None

    # ── Phash / Dedupe helpers ──────────────────────────────────────────
    def get_all_phashes(self) -> list[tuple[int, str]]:
        """Recupera todos los hashes para búsqueda vectorizada en memoria."""
        with self._read() as c:
            c.execute("SELECT id, phash FROM FileQueue WHERE phash IS NOT NULL")
            return [(r["id"], r["phash"]) for r in c.fetchall()]

    def find_similar_phash(self, phash_hex: str, max_hamming: int = 8) -> list[dict]:
        """Busca archivos con phash cercano. Retorna lista de dict rows con distance."""
        if not phash_hex:
            return []
        try:
            with self._read() as c:
                c.execute(
                    "SELECT id,filepath,filename,phash,exif_date FROM FileQueue WHERE phash IS NOT NULL"
                )
                rows = c.fetchall()
        except Exception:
            log.exception("Failed to load similar phashes")
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
                rec = {
                    k: r[idx]
                    for idx, k in enumerate(["id", "filepath", "filename", "phash", "exif_date"])
                }
                rec["hamming"] = d
                out.append(rec)
        return out

    # ── Mantenimiento Avanzado ────────────────────────────────────────────
    def rename_identity(self, old_name: str, new_name: str) -> bool:
        """Issue 17: Renombrado global de una identidad."""
        if not old_name or not new_name or old_name == new_name:
            return False

        with self._write() as c:
            # 1. Actualizar identidades conocidas
            c.execute("UPDATE KnownFaces SET name=? WHERE name=?", (new_name, old_name))
            # 2. Actualizar todas las detecciones históricas
            c.execute(
                "UPDATE Detections SET assigned_name=? WHERE assigned_name=?",
                (new_name, old_name),
            )
            # 3. Actualizar relaciones de archivos (para symlinks)
            c.execute(
                "UPDATE FileIdentities SET identity=? WHERE identity=?",
                (new_name, old_name),
            )
            return c.rowcount > 0

    def cleanup_db(self) -> dict[str, int]:
        """Issue 20: Eliminar huérfanos y optimizar DB."""
        removed_files = 0
        with self._read() as c:
            c.execute("SELECT id, filepath FROM FileQueue")
            rows = c.fetchall()

        to_delete = []
        for r in rows:
            if not Path(r["filepath"]).exists():
                to_delete.append(r["id"])

        if to_delete:
            with self._write() as c:
                ph = ",".join("?" * len(to_delete))
                c.execute(f"DELETE FROM FileQueue WHERE id IN ({ph})", to_delete)
                removed_files = c.rowcount

        # Optimizar espacio
        with self._write() as c:
            c.execute("VACUUM")

        return {"removed_files": removed_files}

    def get_similar_files(self, file_id: int, limit: int = 24) -> pd.DataFrame:
        """Encuentra archivos visualmente similares usando CLIP embeddings."""
        with self._read() as c:
            row = c.execute(
                "SELECT embedding FROM ClipEmbeddings WHERE id=?", (file_id,)
            ).fetchone()
            if not row:
                return pd.DataFrame()
            query_emb = np.frombuffer(row["embedding"], dtype=np.float32)

        # Cargar todos para búsqueda bruta
        ids, embs = self.load_clip()
        if len(ids) == 0:
            return pd.DataFrame()

        # Similitud coseno
        scores = embs @ query_emb

        # Ordenar y filtrar
        sorted_indices = np.argsort(scores)[::-1]
        sorted_ids = [ids[i] for i in sorted_indices if ids[i] != file_id]

        return self.get_files_by_ids_with_thumbs(sorted_ids[:limit])

    def get_unlabeled_face_embeddings(self) -> list[tuple[int, bytes]]:
        """Obtiene IDs y embeddings de caras que no han sido verificadas ni etiquetadas."""
        with self._read() as c:
            c.execute(
                "SELECT id, embedding FROM Detections "
                "WHERE assigned_name = 'Desconocido' AND is_verified = 0 AND embedding IS NOT NULL"
            )
            return [(r["id"], r["embedding"]) for r in c.fetchall()]

    def get_clusters_with_samples(self, limit_per_cluster: int = 5) -> list[dict]:
        """Agrupa las detecciones por cluster_id y devuelve ejemplos."""
        with self._read() as c:
            c.execute(
                "SELECT cluster_id, COUNT(*) as count "
                "FROM Detections WHERE cluster_id IS NOT NULL "
                "GROUP BY cluster_id HAVING count >= 2 ORDER BY count DESC"
            )
            clusters = c.fetchall()

            results = []
            for cl in clusters:
                cid = cl["cluster_id"]
                # Obtener muestras
                c.execute(
                    "SELECT d.id, d.face_crop_path, f.filepath "
                    "FROM Detections d JOIN FileQueue f ON d.file_id = f.id "
                    "WHERE d.cluster_id = ? LIMIT ?",
                    (cid, limit_per_cluster),
                )
                samples = c.fetchall()
                results.append(
                    {
                        "cluster_id": cid,
                        "count": cl["count"],
                        "samples": [dict(s) for s in samples],
                    }
                )
            return results

    def verify_cluster(self, cluster_id: int, name: str) -> None:
        """Asigna un nombre verificado a todo un cluster de una vez."""
        with self._write() as c:
            c.execute(
                "UPDATE Detections SET assigned_name = ?, is_verified = 1, cluster_id = NULL "
                "WHERE cluster_id = ?",
                (name, cluster_id),
            )

    def search_semantic(self, query: str, threshold: float = 0.2, limit: int = 50) -> pd.DataFrame:
        """
        [Fast-Path] Búsqueda semántica ultrarrápida (Vector Search).
        Usa la caché LRU de CLIP para el texto y producto punto (Cosine Similarity) vía NumPy
        sobre los embeddings cargados de SQLite.
        """
        from core.ai_engines import CLIPEngine

        # 1. Obtener embedding de texto cacheado O(1) si ya se buscó antes
        engine = CLIPEngine()
        txt_emb = engine.embed_text(query)
        if txt_emb is None:
            return pd.DataFrame()

        # 2. Cargar todos los blobs de ClipEmbeddings
        conn = self._connect()
        df_clip = pd.read_sql("SELECT id, embedding FROM ClipEmbeddings", conn)
        conn.close()

        if df_clip.empty:
            return pd.DataFrame()

        # 3. Deserializar blobs a NumPy
        # Convertir list de bytes a matriz 2D
        embeddings_list = [np.frombuffer(b, dtype=np.float32) for b in df_clip["embedding"]]
        if not embeddings_list:
            return pd.DataFrame()

        img_embs = np.stack(embeddings_list)

        # 4. Multiplicación de matrices súper rápida (Cosine Similarity)
        # txt_emb ya está normalizado (forma: (dim,))
        # img_embs ya están normalizados (forma: (N, dim))
        similarities = img_embs @ txt_emb

        # 5. Filtrar y ordenar
        df_clip["similarity"] = similarities
        df_matched = df_clip[df_clip["similarity"] >= threshold].copy()
        df_matched.sort_values("similarity", ascending=False, inplace=True)
        df_matched = df_matched.head(limit)

        if df_matched.empty:
            return pd.DataFrame()

        # 6. Hacer JOIN con FileQueue para obtener los detalles
        ids = df_matched["id"].tolist()
        df_info = self.get_files_by_ids(ids)

        # Mantener el orden de similitud
        df_final = pd.merge(df_matched, df_info, on="id", how="left")
        return df_final

    def search_files_fuzzy(self, query: str, limit: int = 100) -> pd.DataFrame:
        """Búsqueda difusa de lenguaje natural traducido a SQL compleja."""
        query_clean = normalize_text(query).strip()
        # Eliminar puntuación común
        query_clean = re.sub(r"[^\w\s]", "", query_clean)
        words = query_clean.split()

        matched_months = []
        filtered_words = []
        for word in words:
            if word in MONTHS_MAP:
                matched_months.append(MONTHS_MAP[word])
            else:
                filtered_words.append(word)

        # Quitar stop words de los tokens de búsqueda
        search_tokens = [w for w in filtered_words if w not in STOP_WORDS]

        # Obtener columnas disponibles en la tabla FileQueue
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(FileQueue)")
        available_cols = [row["name"] for row in cursor.fetchall()]
        conn.close()

        where_clauses = []
        where_params = []

        # 1. Filtro por mes (si se especifica)
        if matched_months:
            month_conditions = []
            for m in matched_months:
                month_conditions.append(
                    "(strftime('%m', IFNULL(f.best_datetime, f.exif_date)) = ?)"
                )
                where_params.append(m)
            where_clauses.append("(" + " OR ".join(month_conditions) + ")")

        # 2. Filtro por tokens de texto cruzando columnas
        if search_tokens:
            # Columnas de texto a cruzar
            text_cols = ["tags", "filepath", "filename"]
            if "ocr_text" in available_cols:
                text_cols.append("ocr_text")
            if "camera_model" in available_cols:
                text_cols.append("camera_model")
            if "lens_model" in available_cols:
                text_cols.append("lens_model")

            token_clauses = []
            for token in search_tokens:
                col_clauses = []
                for col in text_cols:
                    col_clauses.append(f"NORMALIZE_TXT(f.{col}) LIKE ?")
                    where_params.append(f"%{token}%")
                token_clauses.append("(" + " OR ".join(col_clauses) + ")")

            # Intersección (AND) de tokens
            where_clauses.append("(" + " AND ".join(token_clauses) + ")")

        # Unir cláusulas WHERE
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # 3. Puntuación de relevancia (scoring) en SQL
        score_terms = []
        score_params = []
        if search_tokens:
            for token in search_tokens:
                # Más peso a tags y ocr_text, menos a filepath/filename
                if "tags" in available_cols:
                    score_terms.append("CASE WHEN NORMALIZE_TXT(f.tags) LIKE ? THEN 4 ELSE 0 END")
                    score_params.append(f"%{token}%")
                if "ocr_text" in available_cols:
                    score_terms.append(
                        "CASE WHEN NORMALIZE_TXT(f.ocr_text) LIKE ? THEN 3 ELSE 0 END"
                    )
                    score_params.append(f"%{token}%")
                if "filepath" in available_cols:
                    score_terms.append(
                        "CASE WHEN NORMALIZE_TXT(f.filepath) LIKE ? THEN 1 ELSE 0 END"
                    )
                    score_params.append(f"%{token}%")
                if "filename" in available_cols:
                    score_terms.append(
                        "CASE WHEN NORMALIZE_TXT(f.filename) LIKE ? THEN 1 ELSE 0 END"
                    )
                    score_params.append(f"%{token}%")
                if "camera_model" in available_cols:
                    score_terms.append(
                        "CASE WHEN NORMALIZE_TXT(f.camera_model) LIKE ? THEN 2 ELSE 0 END"
                    )
                    score_params.append(f"%{token}%")

        score_sql = " + ".join(score_terms) if score_terms else "1"

        sql = f"""
            SELECT f.*, t.thumb_path as cached_thumb,
                   ({score_sql}) as relevance_score
            FROM FileQueue f
            LEFT JOIN ThumbnailCache t ON f.id = t.file_id
            {where_sql}
            ORDER BY relevance_score DESC, IFNULL(f.best_datetime, f.exif_date) DESC
            LIMIT ?
        """
        # Combinar en el orden secuencial en el que aparecen los placeholders en la consulta:
        # 1. SELECT clause (score_sql) -> score_params
        # 2. WHERE clause (where_sql) -> where_params
        # 3. LIMIT clause -> limit
        params = score_params + where_params + [limit]

        conn = self._connect()
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df

    def get_known_faces_with_crops(self) -> list[dict[str, Any]]:
        """
        Retorna todas las identidades conocidas de KnownFaces con su ID, nombre,
        y una ruta a una miniatura (face crop) representativa desde Detections.
        """
        with self._read() as c:
            c.execute("SELECT id, name, is_faceless, source_img FROM KnownFaces ORDER BY name")
            rows = c.fetchall()

            results = []
            for r in rows:
                name = r["name"]
                crop_row = c.execute(
                    "SELECT face_crop_path FROM Detections "
                    "WHERE assigned_name = ? AND face_crop_path IS NOT NULL AND face_crop_path != '' LIMIT 1",
                    (name,),
                ).fetchone()

                crop_path = crop_row["face_crop_path"] if crop_row else None
                results.append(
                    {
                        "id": r["id"],
                        "name": name,
                        "is_faceless": bool(r["is_faceless"]),
                        "source_img": r["source_img"],
                        "face_crop_path": crop_path,
                    }
                )
            return results

    def merge_known_faces(self, target_id: int, source_ids: list[int]) -> None:
        """
        Fusiona una o más identidades de origen (source_ids) en una identidad destino (target_id).
        Reasigna las fotos (Detections y FileIdentities), recalcula el embedding promedio,
        y elimina las identidades origen.
        """
        if not source_ids:
            return

        with self._write() as c:
            # 1. Obtener nombre de la identidad destino
            target = c.execute("SELECT name FROM KnownFaces WHERE id = ?", (target_id,)).fetchone()
            if not target:
                log.error(
                    f"Error al fusionar: No se encontró la identidad destino con ID {target_id}"
                )
                return
            target_name = target["name"]

            # 2. Obtener nombres de las identidades origen
            source_names = []
            for s_id in source_ids:
                row = c.execute("SELECT name FROM KnownFaces WHERE id = ?", (s_id,)).fetchone()
                if row:
                    source_names.append(row["name"])

            if not source_names:
                return

            # 3. Reasignar en Detections
            placeholders = ",".join("?" for _ in source_names)
            c.execute(
                f"UPDATE Detections SET assigned_name = ?, triage_tier='safe', is_verified=1 WHERE assigned_name IN ({placeholders})",
                [target_name] + source_names,
            )

            # 4. Reasignar en FileIdentities (evitando conflictos de unicidad)
            file_ids_with_target = {
                row["file_id"]
                for row in c.execute(
                    "SELECT file_id FROM FileIdentities WHERE identity = ?", (target_name,)
                ).fetchall()
            }

            for s_name in source_names:
                source_links = c.execute(
                    "SELECT id, file_id FROM FileIdentities WHERE identity = ?", (s_name,)
                ).fetchall()
                for link_id, file_id in source_links:
                    if file_id in file_ids_with_target:
                        c.execute("DELETE FROM FileIdentities WHERE id = ?", (link_id,))
                    else:
                        c.execute(
                            "UPDATE FileIdentities SET identity = ? WHERE id = ?",
                            (target_name, link_id),
                        )
                        file_ids_with_target.add(file_id)

            # 5. Recalcular el embedding promedio para la identidad destino
            rows = c.execute(
                "SELECT embedding FROM Detections WHERE assigned_name = ? AND embedding IS NOT NULL",
                (target_name,),
            ).fetchall()

            if rows:
                embs = [np.frombuffer(r["embedding"], dtype=np.float32) for r in rows]
                mean_emb = np.mean(embs, axis=0)
                mean_emb_bytes = mean_emb.astype(np.float32).tobytes()
                c.execute(
                    "UPDATE KnownFaces SET embedding = ? WHERE id = ?", (mean_emb_bytes, target_id)
                )

            # 6. Eliminar las identidades origen de KnownFaces
            c.execute(f"DELETE FROM KnownFaces WHERE id IN ({placeholders})", source_ids)

        log.info(
            f"Identidades {source_names} fusionadas con éxito en '{target_name}' (ID {target_id})"
        )

    def merge_dbscan_clusters(self, target_cluster_id: int, source_cluster_ids: list[int]) -> None:
        """
        Fusiona múltiples clústeres DBSCAN de origen (source_cluster_ids) en un clúster destino (target_cluster_id).
        Reasigna todas las detecciones de origen al clúster destino.
        """
        if not source_cluster_ids:
            return

        with self._write() as c:
            placeholders = ",".join("?" for _ in source_cluster_ids)
            c.execute(
                f"UPDATE Detections SET cluster_id = ? WHERE cluster_id IN ({placeholders})",
                [target_cluster_id] + source_cluster_ids,
            )

        log.info(
            f"Clústeres {source_cluster_ids} fusionados con éxito en el clúster #{target_cluster_id}"
        )


# ── Helper ────────────────────────────────────────────────────────────────────
def _now() -> str:
    from datetime import timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _norm_path(path_str: str) -> str:
    try:
        return str(Path(path_str).resolve(strict=False))
    except Exception:
        log.debug("Path normalization failed for %s", path_str)
        return path_str
