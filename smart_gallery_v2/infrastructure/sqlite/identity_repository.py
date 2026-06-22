"""Persistencia atómica de correcciones de identidad y dataset humano."""

from __future__ import annotations

import json

from application.identity_corrections import IdentityCorrection
from core.database import DatabaseManager
from domain.models import RegionKind


class SqliteIdentityCorrectionRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def save(self, correction: IdentityCorrection) -> int:
        name = str(correction.identity)
        region = correction.region
        with self._db._write() as cursor:
            cursor.execute("INSERT OR IGNORE INTO Identities(display_name) VALUES (?)", (name,))
            identity_id = int(
                cursor.execute(
                    "SELECT id FROM Identities WHERE display_name=? COLLATE NOCASE", (name,)
                ).fetchone()[0]
            )
            cursor.execute(
                "INSERT INTO RegionAnnotations "
                "(media_id,region_type,x,y,width,height,polygon_json) VALUES (?,?,?,?,?,?,?)",
                (
                    correction.media_id,
                    region.kind.value,
                    region.x,
                    region.y,
                    region.width,
                    region.height,
                    json.dumps(region.polygon) if region.polygon else None,
                ),
            )
            region_id = int(cursor.lastrowid)
            cursor.execute(
                "INSERT INTO IdentityEvidence "
                "(media_id,identity_id,region_id,source,decision,confidence,metadata_json) "
                "VALUES (?,?,?,'human','present',1.0,?)",
                (
                    correction.media_id,
                    identity_id,
                    region_id,
                    json.dumps({"hard_case": correction.hard_case}),
                ),
            )
            evidence_id = int(cursor.lastrowid)
            self._write_legacy_projection(cursor, correction)
            if correction.hard_case and correction.hard_case != "other":
                cursor.execute(
                    "INSERT OR IGNORE INTO TrainingExamples(evidence_id,hard_case) VALUES (?,?)",
                    (evidence_id, correction.hard_case),
                )
            cursor.execute(
                "INSERT INTO FilesystemOutbox(operation,payload_json) VALUES "
                "('rebuild_identity_projection',?)",
                (json.dumps({"media_id": correction.media_id, "identity": name}),),
            )
            return evidence_id

    def list_for_media(self, media_id: int) -> list[dict[str, object]]:
        with self._db._read() as cursor:
            rows = cursor.execute(
                "SELECT p.*,r.region_type,r.x,r.y,r.width,r.height,r.polygon_json "
                "FROM ResolvedIdentityPresence p "
                "LEFT JOIN RegionAnnotations r ON r.id=p.region_id "
                "WHERE p.media_id=? ORDER BY p.display_name",
                (media_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _write_legacy_projection(cursor, correction: IdentityCorrection) -> None:
        name = str(correction.identity)
        cursor.execute("INSERT OR IGNORE INTO KnownFaces(name,is_faceless) VALUES (?,1)", (name,))
        cursor.execute(
            "INSERT OR IGNORE INTO FileIdentities(file_id,identity,is_faceless) VALUES (?,?,1)",
            (correction.media_id, name),
        )
        region = correction.region
        bbox: dict[str, float | bool] = {"top": 0, "right": 0, "bottom": 0, "left": 0}
        if region.kind is RegionKind.RECTANGLE:
            assert region.x is not None and region.y is not None
            assert region.width is not None and region.height is not None
            bbox = {
                "top": region.y,
                "left": region.x,
                "right": region.x + region.width,
                "bottom": region.y + region.height,
                "normalized": True,
            }
        cursor.execute(
            "INSERT INTO Detections "
            "(file_id,bbox_json,assigned_name,confidence,triage_tier,is_faceless,is_verified) "
            "VALUES (?,?,?,1.0,'safe',1,1)",
            (correction.media_id, json.dumps(bbox), name),
        )
