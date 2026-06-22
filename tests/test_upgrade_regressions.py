from __future__ import annotations

import pytest
from core.migrations.v5_identity_events import migrate
from core.worker import _gps_decimal


def test_gps_decimal_supports_exif_rationals_and_cardinal_signs() -> None:
    coordinates = ((43, 1), (15, 1), (30, 1))
    assert _gps_decimal(coordinates, "N") == pytest.approx(43.258333)
    assert _gps_decimal(((2, 1), (56, 1), (6, 1)), "W") == pytest.approx(-2.935)


def test_v5_migration_is_idempotent_and_imports_legacy_identities(temp_db) -> None:
    with temp_db._write() as cursor:
        cursor.execute("INSERT INTO KnownFaces(name,is_faceless) VALUES ('Legacy Person',1)")
    connection = temp_db._connect()
    try:
        migrate(connection)
        migrate(connection)
        count = connection.execute(
            "SELECT COUNT(*) FROM Identities WHERE display_name='Legacy Person' COLLATE NOCASE"
        ).fetchone()[0]
        versions = connection.execute(
            "SELECT COUNT(*) FROM AppSchemaMigrations WHERE version=5"
        ).fetchone()[0]
    finally:
        connection.close()
    assert count == 1
    assert versions == 1
