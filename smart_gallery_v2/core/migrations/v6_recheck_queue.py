"""Esquema v6: Cola de Reevaluación (Recheck Queue)."""

from __future__ import annotations

import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS IdentityRecheckQueue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES FileQueue(id) ON DELETE CASCADE,
    detection_id INTEGER NOT NULL REFERENCES Detections(id) ON DELETE CASCADE,
    affected_identity TEXT NOT NULL,
    old_name TEXT,
    suggested_name TEXT,
    distance REAL,
    confidence REAL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    resolved_at TEXT
);

DELETE FROM IdentityRecheckQueue
WHERE resolved_at IS NULL
  AND id NOT IN (
      SELECT MIN(id)
      FROM IdentityRecheckQueue
      WHERE resolved_at IS NULL
      GROUP BY detection_id, affected_identity, IFNULL(suggested_name, '')
  );

CREATE INDEX IF NOT EXISTS idx_recheck_file ON IdentityRecheckQueue(file_id);
CREATE INDEX IF NOT EXISTS idx_recheck_detection ON IdentityRecheckQueue(detection_id);
CREATE INDEX IF NOT EXISTS idx_recheck_unresolved ON IdentityRecheckQueue(resolved_at);
CREATE INDEX IF NOT EXISTS idx_recheck_distance ON IdentityRecheckQueue(distance);
CREATE UNIQUE INDEX IF NOT EXISTS uq_recheck_open_detection_suggestion
ON IdentityRecheckQueue(detection_id, affected_identity, IFNULL(suggested_name, ''))
WHERE resolved_at IS NULL;
"""

def migrate(conn: sqlite3.Connection) -> None:
    """Aplica v6: Cola de revisión de identidad."""
    conn.executescript(DDL)
    conn.execute(
        "INSERT OR IGNORE INTO AppSchemaMigrations(version,name) VALUES "
        "(6,'identity_recheck_queue')"
    )
