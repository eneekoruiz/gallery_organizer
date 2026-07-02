"""
tests/test_simulation_learning.py
Simulación del aprendizaje activo: cola de revisión, prototipos múltiples e idempotencia.
"""

import numpy as np

from core.database import DatabaseManager


def _embedding(value: float) -> np.ndarray:
    return np.full(512, value, dtype=np.float32)


def test_double_thresholds_logic(temp_db: DatabaseManager):
    """El refresco genera sugerencias fuertes y cola de confirmación humana."""
    f1, _ = temp_db.upsert_file("test1.jpg", "test1.jpg")
    f2, _ = temp_db.upsert_file("test2.jpg", "test2.jpg")

    emb_proto = _embedding(0.10)
    emb_close = _embedding(0.11)
    with temp_db._write() as c:
        c.execute(
            "INSERT INTO Detections(file_id, assigned_name, embedding, is_verified, "
            "triage_tier, is_false_positive, is_faceless) "
            "VALUES (?, 'Alice', ?, 1, 'safe', 0, 0)",
            (f1, emb_proto.tobytes()),
        )
        candidate_id = c.execute(
            "INSERT INTO Detections(file_id, assigned_name, embedding, is_verified, "
            "triage_tier, is_false_positive, is_faceless) "
            "VALUES (?, 'Desconocido', ?, 0, 'unclassified', 0, 0)",
            (f2, emb_close.tobytes()),
        ).lastrowid
        temp_db._refresh_identity_learning(c, {"Alice"}, set(), review_distance=1.5)

    with temp_db._read() as c:
        queue_rows = c.execute("SELECT * FROM IdentityRecheckQueue").fetchall()
        candidate = c.execute(
            "SELECT assigned_name, triage_tier, is_verified FROM Detections WHERE id=?",
            (candidate_id,),
        ).fetchone()

    assert len(queue_rows) == 1
    assert queue_rows[0]["affected_identity"] == "Alice"
    assert candidate["assigned_name"] == "Alice"
    assert candidate["triage_tier"] == "safe"
    assert candidate["is_verified"] == 0


def test_recheck_queue_is_idempotent(temp_db: DatabaseManager):
    """Recalcular el mismo aprendizaje no debe duplicar revisiones abiertas."""
    f1, _ = temp_db.upsert_file("proto.jpg", "proto.jpg")
    f2, _ = temp_db.upsert_file("candidate.jpg", "candidate.jpg")

    with temp_db._write() as c:
        c.execute(
            "INSERT INTO Detections(file_id, assigned_name, embedding, is_verified, "
            "is_false_positive, is_faceless) VALUES (?, 'Alice', ?, 1, 0, 0)",
            (f1, _embedding(0.10).tobytes()),
        )
        c.execute(
            "INSERT INTO Detections(file_id, assigned_name, embedding, is_verified, "
            "is_false_positive, is_faceless) VALUES (?, 'Desconocido', ?, 0, 0, 0)",
            (f2, _embedding(0.11).tobytes()),
        )
        temp_db._refresh_identity_learning(c, {"Alice"}, set(), review_distance=1.5)
        temp_db._refresh_identity_learning(c, {"Alice"}, set(), review_distance=1.5)

    with temp_db._read() as c:
        count = c.execute(
            "SELECT COUNT(*) FROM IdentityRecheckQueue WHERE resolved_at IS NULL"
        ).fetchone()[0]

    assert count == 1


def test_multiple_prototypes(temp_db: DatabaseManager):
    """Valida la indexación múltiple y creación de IdentityPrototypes."""
    file_ids = [temp_db.upsert_file(f"bob_{i}.jpg", f"bob_{i}.jpg")[0] for i in range(3)]

    with temp_db._write() as c:
        for i, file_id in enumerate(file_ids):
            emb = _embedding(float(i) / 10)
            c.execute(
                "INSERT INTO Detections(file_id, assigned_name, embedding, is_verified, "
                "is_false_positive, is_faceless) VALUES (?, 'Bob', ?, 1, 0, 0)",
                (file_id, emb.tobytes()),
            )
        temp_db._refresh_identity_learning(c, {"Bob"}, set())

    names, embs = temp_db.load_known_faces()
    bob_embs = [embs[i] for i, name in enumerate(names) if name == "Bob"]

    assert len(bob_embs) == 3
    assert any(np.allclose(emb, _embedding(0.0)) for emb in bob_embs)
    assert any(np.allclose(emb, _embedding(0.1)) for emb in bob_embs)
    assert any(np.allclose(emb, _embedding(0.2)) for emb in bob_embs)
