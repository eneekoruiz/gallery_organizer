"""Esquema v5: evidencia humana, regiones, eventos y efectos de filesystem."""

from __future__ import annotations

import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS AppSchemaMigrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS Identities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    canonical_id INTEGER REFERENCES Identities(id),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS RegionAnnotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL REFERENCES FileQueue(id) ON DELETE CASCADE,
    region_type TEXT NOT NULL CHECK(region_type IN ('whole_image','rectangle','polygon')),
    x REAL CHECK(x IS NULL OR x BETWEEN 0 AND 1),
    y REAL CHECK(y IS NULL OR y BETWEEN 0 AND 1),
    width REAL CHECK(width IS NULL OR width BETWEEN 0 AND 1),
    height REAL CHECK(height IS NULL OR height BETWEEN 0 AND 1),
    polygon_json TEXT,
    coordinate_space TEXT NOT NULL DEFAULT 'exif_normalized',
    image_width INTEGER,
    image_height INTEGER,
    legacy_detection_id INTEGER UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK(region_type = 'whole_image'
       OR (region_type = 'rectangle' AND x IS NOT NULL AND y IS NOT NULL
           AND width IS NOT NULL AND height IS NOT NULL)
       OR (region_type = 'polygon' AND polygon_json IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_region_media ON RegionAnnotations(media_id);

CREATE TABLE IF NOT EXISTS IdentityEvidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL REFERENCES FileQueue(id) ON DELETE CASCADE,
    identity_id INTEGER NOT NULL REFERENCES Identities(id),
    region_id INTEGER REFERENCES RegionAnnotations(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK(source IN
        ('human','face_model','body_model','event_propagation','legacy','import')),
    decision TEXT NOT NULL CHECK(decision IN ('present','not_present','uncertain')),
    confidence REAL CHECK(confidence IS NULL OR confidence BETWEEN 0 AND 1),
    model_name TEXT,
    model_version TEXT,
    supersedes_id INTEGER REFERENCES IdentityEvidence(id),
    revision INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_evidence_media ON IdentityEvidence(media_id, is_active);
CREATE INDEX IF NOT EXISTS idx_evidence_identity ON IdentityEvidence(identity_id, is_active);
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_human_evidence
ON IdentityEvidence(media_id, identity_id, IFNULL(region_id, -1), decision)
WHERE source='human' AND is_active=1;

CREATE TABLE IF NOT EXISTS IdentityPrototypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identity_id INTEGER NOT NULL REFERENCES Identities(id) ON DELETE CASCADE,
    modality TEXT NOT NULL CHECK(modality IN ('face','body','clothing')),
    embedding BLOB NOT NULL,
    embedding_dim INTEGER NOT NULL,
    quality_score REAL NOT NULL CHECK(quality_score BETWEEN 0 AND 1),
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    source_evidence_id INTEGER REFERENCES IdentityEvidence(id),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS Events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    title_source TEXT NOT NULL CHECK(title_source IN ('algorithm','human')),
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    centroid_lat REAL,
    centroid_lon REAL,
    semantic_label TEXT,
    confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
    algorithm_version TEXT NOT NULL,
    manually_locked INTEGER NOT NULL DEFAULT 0 CHECK(manually_locked IN (0,1)),
    cover_media_id INTEGER REFERENCES FileQueue(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK(ends_at >= starts_at)
);
CREATE INDEX IF NOT EXISTS idx_events_time ON Events(starts_at, ends_at);

CREATE TABLE IF NOT EXISTS EventMedia (
    event_id INTEGER NOT NULL REFERENCES Events(id) ON DELETE CASCADE,
    media_id INTEGER NOT NULL REFERENCES FileQueue(id) ON DELETE CASCADE,
    membership_score REAL NOT NULL CHECK(membership_score BETWEEN 0 AND 1),
    reason_json TEXT NOT NULL DEFAULT '{}',
    manually_set INTEGER NOT NULL DEFAULT 0 CHECK(manually_set IN (0,1)),
    PRIMARY KEY(event_id, media_id)
);
CREATE INDEX IF NOT EXISTS idx_event_media_media ON EventMedia(media_id);

CREATE TABLE IF NOT EXISTS LocationCache (
    geohash TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    locality TEXT,
    region TEXT,
    country TEXT,
    resolved_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS FilesystemOutbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','processing','completed','failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    processed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON FilesystemOutbox(status, created_at);

CREATE TABLE IF NOT EXISTS TrainingExamples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id INTEGER NOT NULL UNIQUE REFERENCES IdentityEvidence(id) ON DELETE CASCADE,
    split TEXT CHECK(split IN ('train','validation','test')),
    hard_case TEXT CHECK(hard_case IN
        ('occluded','back_view','helmet','small_region','low_light','other')),
    export_status TEXT NOT NULL DEFAULT 'pending'
        CHECK(export_status IN ('pending','exported','rejected')),
    exported_at TEXT
);

CREATE VIEW IF NOT EXISTS ResolvedIdentityPresence AS
WITH ranked AS (
    SELECT e.*,
        ROW_NUMBER() OVER (
            PARTITION BY e.media_id, e.identity_id, IFNULL(e.region_id, -1)
            ORDER BY CASE e.source
                WHEN 'human' THEN 100 WHEN 'import' THEN 80
                WHEN 'event_propagation' THEN 50 WHEN 'body_model' THEN 30
                WHEN 'face_model' THEN 25 ELSE 10 END DESC,
                e.revision DESC, e.id DESC
        ) AS rank_no
    FROM IdentityEvidence e WHERE e.is_active=1
)
SELECT r.media_id, r.identity_id, i.display_name, r.region_id,
       r.source, r.decision, r.confidence, r.created_at
FROM ranked r JOIN Identities i ON i.id=r.identity_id
WHERE r.rank_no=1 AND r.decision='present';
"""


def migrate(conn: sqlite3.Connection) -> None:
    """Aplica v5 y migra nombres legacy sin destruir las tablas anteriores."""
    conn.executescript(DDL)
    conn.execute(
        "INSERT OR IGNORE INTO Identities(display_name) "
        "SELECT DISTINCT trim(name) FROM KnownFaces WHERE trim(name) != ''"
    )
    conn.execute(
        "INSERT OR IGNORE INTO Identities(display_name) "
        "SELECT DISTINCT trim(assigned_name) FROM Detections "
        "WHERE assigned_name NOT IN ('', 'Desconocido')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO Identities(display_name) "
        "SELECT DISTINCT trim(identity) FROM FileIdentities WHERE trim(identity) != ''"
    )
    conn.execute(
        "INSERT OR IGNORE INTO AppSchemaMigrations(version,name) VALUES "
        "(5,'identity_evidence_events_outbox_active_learning')"
    )
    conn.execute(
        "UPDATE FileQueue SET status='PENDING', retries=retries+1, "
        "failed_stage='lease_recovery', error_message='Recovered stale PROCESSING lease' "
        "WHERE status='PROCESSING' AND datetime(last_updated) < datetime('now','-20 minutes')"
    )
