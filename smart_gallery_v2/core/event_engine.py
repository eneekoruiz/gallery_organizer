"""Construcción determinista de eventos espaciotemporales y semánticos."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.database import DatabaseManager


@dataclass(frozen=True)
class EventSettings:
    radius_km: float = 5.0
    time_window_hours: float = 3.0
    max_event_hours: float = 18.0
    semantic_threshold: float = 0.48
    min_media: int = 2


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0088 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class EventEngine:
    VERSION = "spacetime-semantic-v1"

    def __init__(self, db: DatabaseManager, settings: EventSettings = EventSettings()) -> None:
        self.db = db
        self.settings = settings

    def rebuild(self) -> int:
        media = self._load_media()
        if media.empty:
            return 0
        groups = self._cluster(media)
        with self.db._write() as cursor:
            unlocked = cursor.execute("SELECT id FROM Events WHERE manually_locked=0").fetchall()
            unlocked_ids = [row[0] for row in unlocked]
            if unlocked_ids:
                marks = ",".join("?" for _ in unlocked_ids)
                cursor.execute(f"DELETE FROM Events WHERE id IN ({marks})", unlocked_ids)
            for group in groups:
                self._persist(cursor, group)
        return len(groups)

    def _load_media(self) -> pd.DataFrame:
        connection = self.db._connect()
        try:
            return pd.read_sql_query(
                "SELECT f.id,f.filepath,f.filename,COALESCE(f.best_datetime,f.exif_date) captured_at,"
                "f.gps_lat,f.gps_lon,f.tags,c.embedding "
                "FROM FileQueue f LEFT JOIN ClipEmbeddings c ON c.id=f.id "
                "WHERE COALESCE(f.best_datetime,f.exif_date) IS NOT NULL "
                "AND f.status IN ('AUTO_CLASSIFIED','NEEDS_REVIEW','VERIFIED','DONE') "
                "ORDER BY captured_at",
                connection,
            )
        finally:
            connection.close()

    def _cluster(self, frame: pd.DataFrame) -> list[pd.DataFrame]:
        frame = frame.copy()
        frame["dt"] = pd.to_datetime(frame["captured_at"], errors="coerce", utc=True)
        frame = frame.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)
        if frame.empty:
            return []

        groups: list[list[int]] = [[0]]
        for index in range(1, len(frame)):
            previous = frame.iloc[groups[-1][-1]]
            current = frame.iloc[index]
            first = frame.iloc[groups[-1][0]]
            gap_h = (current["dt"] - previous["dt"]).total_seconds() / 3600
            span_h = (current["dt"] - first["dt"]).total_seconds() / 3600
            close_time = gap_h <= self.settings.time_window_hours
            within_span = span_h <= self.settings.max_event_hours
            close_space = self._spatially_close(previous, current)
            semantic = self._semantic_similarity(previous.embedding, current.embedding)
            # Sin GPS exigimos continuidad semántica; con GPS aplicamos el radio duro.
            has_both_gps = pd.notna(previous.gps_lat) and pd.notna(current.gps_lat)
            compatible = (
                close_space if has_both_gps else semantic >= self.settings.semantic_threshold
            )
            if close_time and within_span and compatible:
                groups[-1].append(index)
            else:
                groups.append([index])
        return [
            frame.iloc[indexes].copy()
            for indexes in groups
            if len(indexes) >= self.settings.min_media
        ]

    def _spatially_close(self, left, right) -> bool:
        values = (left.gps_lat, left.gps_lon, right.gps_lat, right.gps_lon)
        if any(pd.isna(value) for value in values):
            return True
        return haversine_km(*map(float, values)) <= self.settings.radius_km

    @staticmethod
    def _semantic_similarity(left, right) -> float:
        if left is None or right is None:
            return 0.5
        a = np.frombuffer(left, dtype=np.float32)
        b = np.frombuffer(right, dtype=np.float32)
        if a.shape != b.shape or not len(a):
            return 0.0
        return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8))

    def _persist(self, cursor, group: pd.DataFrame) -> None:
        tags: list[str] = []
        for raw in group.tags.dropna():
            try:
                tags.extend(json.loads(raw))
            except (TypeError, json.JSONDecodeError):
                continue
        common_tag = max(set(tags), key=tags.count) if tags else "Recuerdos"
        parent = pd.Series([str(__import__("pathlib").Path(p).parent.name) for p in group.filepath])
        folder = parent.mode().iloc[0] if not parent.empty else ""
        title = f"{common_tag} · {folder}" if folder else common_tag
        located = group.dropna(subset=["gps_lat", "gps_lon"])
        lat = float(located.gps_lat.mean()) if not located.empty else None
        lon = float(located.gps_lon.mean()) if not located.empty else None
        start = group.dt.min().isoformat()
        end = group.dt.max().isoformat()
        confidence = min(0.98, 0.55 + 0.05 * len(group) + (0.15 if lat is not None else 0))
        cursor.execute(
            "INSERT INTO Events(title,title_source,starts_at,ends_at,centroid_lat,centroid_lon,"
            "semantic_label,confidence,algorithm_version,cover_media_id) VALUES "
            "(?,'algorithm',?,?,?,?,?,?,?,?)",
            (
                title,
                start,
                end,
                lat,
                lon,
                common_tag,
                confidence,
                self.VERSION,
                int(group.iloc[0].id),
            ),
        )
        event_id = cursor.lastrowid
        for row in group.itertuples():
            cursor.execute(
                "INSERT INTO EventMedia(event_id,media_id,membership_score,reason_json) VALUES (?,?,?,?)",
                (
                    event_id,
                    int(row.id),
                    confidence,
                    json.dumps({"time": row.captured_at, "gps": [row.gps_lat, row.gps_lon]}),
                ),
            )

    def list_events(self) -> list[dict]:
        with self.db._read() as cursor:
            rows = cursor.execute(
                "SELECT e.*,COUNT(em.media_id) media_count,f.filepath cover_path "
                "FROM Events e LEFT JOIN EventMedia em ON em.event_id=e.id "
                "LEFT JOIN FileQueue f ON f.id=e.cover_media_id "
                "GROUP BY e.id ORDER BY e.starts_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]
