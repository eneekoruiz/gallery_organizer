"""Repositorio optimizado de ubicaciones; una consulta evita el N+1 de UI."""

from __future__ import annotations

from pathlib import Path

from core.database import DatabaseManager
from domain.models import GeoPoint, MediaLocation


class SqliteMediaLocationRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def search(self, query: str = "") -> list[MediaLocation]:
        needle = query.casefold().strip()
        with self._db._read() as cursor:
            rows = cursor.execute(
                "SELECT f.id,f.filename,f.filepath,f.gps_lat,f.gps_lon,"
                "GROUP_CONCAT(DISTINCT fi.symlink_path) result_paths,"
                "GROUP_CONCAT(DISTINCT fi.identity) identities "
                "FROM FileQueue f LEFT JOIN FileIdentities fi ON fi.file_id=f.id "
                "GROUP BY f.id ORDER BY COALESCE(f.best_datetime,f.exif_date) DESC"
            ).fetchall()

        locations: list[MediaLocation] = []
        for row in rows:
            results = tuple(Path(p) for p in (row["result_paths"] or "").split(",") if p)
            identities = tuple(i for i in (row["identities"] or "").split(",") if i)
            gps = (
                GeoPoint(float(row["gps_lat"]), float(row["gps_lon"]))
                if row["gps_lat"] is not None and row["gps_lon"] is not None
                else None
            )
            location = MediaLocation(
                media_id=int(row["id"]),
                filename=str(row["filename"]),
                original_path=Path(row["filepath"]),
                result_paths=results,
                identities=identities,
                gps=gps,
            )
            haystack = " ".join(
                [
                    location.filename,
                    str(location.original_folder),
                    *location.identities,
                    *(str(folder) for folder in location.result_folders),
                ]
            ).casefold()
            if not needle or needle in haystack:
                locations.append(location)
        return locations
