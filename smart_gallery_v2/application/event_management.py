"""Casos de uso de edición y consulta de eventos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.database import DatabaseManager


@dataclass(frozen=True, slots=True)
class EventMediaItem:
    path: Path
    filename: str
    membership_score: float


class EventManagementService:
    """Mantiene SQL de eventos fuera de la presentación Streamlit."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def rename(self, event_id: int, title: str, *, locked: bool) -> None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("El evento necesita un nombre")
        with self._db._write() as cursor:
            cursor.execute(
                "UPDATE Events SET title=?,title_source='human',manually_locked=?,"
                "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
                (clean_title, int(locked), event_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"Evento inexistente: {event_id}")

    def media(self, event_id: int) -> list[EventMediaItem]:
        with self._db._read() as cursor:
            rows = cursor.execute(
                "SELECT f.filepath,f.filename,em.membership_score FROM EventMedia em "
                "JOIN FileQueue f ON f.id=em.media_id WHERE em.event_id=? "
                "ORDER BY f.best_datetime",
                (event_id,),
            ).fetchall()
        return [
            EventMediaItem(Path(row["filepath"]), str(row["filename"]), float(row["membership_score"]))
            for row in rows
        ]
