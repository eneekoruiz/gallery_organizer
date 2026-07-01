def test_db_initialization(temp_db):
    """Verifica que las tablas básicas se creen correctamente."""
    with temp_db._read() as c:
        res = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='FileQueue'"
        ).fetchone()
        assert res is not None

        # Verificar versión de esquema
        res = c.execute("SELECT version FROM SchemaInfo").fetchone()
        assert res["version"] == 4


def test_file_upsert_and_fetch(temp_db):
    """Verifica el flujo de inserción y recuperación de archivos."""
    fid, _ = temp_db.upsert_file("test/path.jpg", "path.jpg", "image")
    assert fid is not None

    stats = temp_db.get_stats()
    assert stats["total"] == 1
    assert stats["pending"] == 1


def test_update_status(temp_db):
    """Verifica el cambio de estados en la cola."""
    fid, _ = temp_db.upsert_file("test.jpg", "test.jpg")
    temp_db.set_processing(fid)

    with temp_db._read() as c:
        row = c.execute("SELECT status FROM FileQueue WHERE id=?", (fid,)).fetchone()
        assert row["status"] == "PROCESSING"

    temp_db.update_done(fid, ["tag1"], "safe")

    stats = temp_db.get_stats()
    assert stats["done"] == 1
    assert stats["safe"] == 1


def test_retry_all_errors(temp_db):
    """Verifica que la herramienta de reintento funcione."""
    fid, _ = temp_db.upsert_file("error.jpg", "error.jpg")

    # Simular error
    with temp_db._write() as c:
        c.execute("UPDATE FileQueue SET status='ERROR', retries=3 WHERE id=?", (fid,))
        c.execute(
            "INSERT INTO ProcessingErrors (file_id, filepath, phase, exception) VALUES (?,?,?,?)",
            (fid, "error.jpg", "test", "dummy exception"),
        )

    stats = temp_db.get_stats()
    assert stats["errors"] == 1

    # Reintentar
    count = temp_db.retry_all_errors()
    assert count == 1

    stats = temp_db.get_stats()
    assert stats["errors"] == 0
    assert stats["pending"] == 1

    # Verificar que se limpió la tabla de errores
    with temp_db._read() as c:
        err = c.execute("SELECT COUNT(*) FROM ProcessingErrors").fetchone()[0]
        assert err == 0


def test_clean_stale_thumbnails(temp_db):
    """Verifica que la limpieza de caché huérfana no falle."""
    count = temp_db.clean_stale_thumbnails()
    assert count >= 0


def test_fuzzy_search(temp_db):
    """Verifica que la traducción de lenguaje natural a SQL y la búsqueda funcionen."""
    fid1, _ = temp_db.upsert_file("fotos/agosto/perro_playa.jpg", "perro_playa.jpg")
    temp_db.update_done(
        fid1,
        tags=["perro", "playa"],
        triage_tier="safe",
        best_datetime="2023-08-15T14:30:00Z",
        ocr_text="DNI de prueba",
    )

    fid2, _ = temp_db.upsert_file("fotos/diciembre/gato.jpg", "gato.jpg")
    temp_db.update_done(
        fid2,
        tags=["gato", "cocina"],
        triage_tier="safe",
        best_datetime="2023-12-25T10:00:00Z",
        ocr_text="Factura de gas",
    )

    # 1. Buscar "perro en la playa en agosto" -> Debería retornar perro_playa.jpg
    df1 = temp_db.search_files_fuzzy("perro en la playa en agosto")
    assert len(df1) == 1
    assert df1.iloc[0]["id"] == fid1

    # 2. Buscar "factura en diciembre" -> Debería retornar gato.jpg (por ocr y mes)
    df2 = temp_db.search_files_fuzzy("factura en diciembre")
    assert len(df2) == 1
    assert df2.iloc[0]["id"] == fid2

    # 3. Buscar "agosto" -> Debería retornar perro_playa.jpg
    df3 = temp_db.search_files_fuzzy("agosto")
    assert len(df3) == 1
    assert df3.iloc[0]["id"] == fid1

    # 4. Buscar "gato" -> Debería retornar gato.jpg
    df4 = temp_db.search_files_fuzzy("gato")
    assert len(df4) == 1
    assert df4.iloc[0]["id"] == fid2


def test_merge_identities(temp_db):
    """Verifica que la fusión de identidades conocidas reasigne las detecciones y recalcule el embedding promedio."""
    import numpy as np

    # Crear identidades conocidas iniciales
    # Embedding de Alice: [1, 1, 1, ..., 1]
    emb_alice = np.ones(512, dtype=np.float32)
    # Embedding de Bob: [3, 3, 3, ..., 3]
    emb_bob = np.ones(512, dtype=np.float32) * 3

    id_alice = temp_db.add_known_face("Alice", emb_alice, is_faceless=False)
    id_bob = temp_db.add_known_face("Bob", emb_bob, is_faceless=False)

    # Crear detecciones de Alice y Bob
    fid1, _ = temp_db.upsert_file("img1.jpg", "img1.jpg")
    fid2, _ = temp_db.upsert_file("img2.jpg", "img2.jpg")

    # Agregar detección de Alice (usando su embedding)
    temp_db.add_detection(
        file_id=fid1,
        embedding=emb_alice,
        bbox={"top": 0, "right": 10, "bottom": 10, "left": 0},
        assigned_name="Alice",
    )
    # Agregar detección de Bob (usando su embedding)
    temp_db.add_detection(
        file_id=fid2,
        embedding=emb_bob,
        bbox={"top": 0, "right": 10, "bottom": 10, "left": 0},
        assigned_name="Bob",
    )

    # También agregar relaciones en FileIdentities
    with temp_db._write() as c:
        c.execute(
            "INSERT OR IGNORE INTO FileIdentities (file_id, identity) VALUES (?,?)", (fid1, "Alice")
        )
        c.execute(
            "INSERT OR IGNORE INTO FileIdentities (file_id, identity) VALUES (?,?)", (fid2, "Bob")
        )

    # Verificar estado inicial
    faces = temp_db.get_known_faces_with_crops()
    names = [f["name"] for f in faces]
    assert "Alice" in names
    assert "Bob" in names

    # Fusionar Bob en Alice
    temp_db.merge_known_faces(id_alice, [id_bob])

    # 1. Bob debe ser eliminado de KnownFaces
    faces_post = temp_db.get_known_faces_with_crops()
    names_post = [f["name"] for f in faces_post]
    assert "Alice" in names_post
    assert "Bob" not in names_post

    # 2. Las detecciones de Bob deben haberse reasignado a Alice
    with temp_db._read() as c:
        rows = c.execute(
            "SELECT assigned_name, embedding FROM Detections WHERE file_id = ?", (fid2,)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["assigned_name"] == "Alice"

    # 3. El embedding promedio de Alice debe haberse recalculado
    # El promedio de [1,1,...] y [3,3,...] debería ser [2,2,...]
    names_db, embs_db = temp_db.load_known_faces()
    alice_idx = names_db.index("Alice")
    alice_emb = embs_db[alice_idx]

    expected_emb = np.ones(512, dtype=np.float32) * 2.0
    assert np.allclose(alice_emb, expected_emb)


def test_queue_priority_is_atomic_and_cleared(temp_db):
    """La cola debe respetar prioridad y limpiar estado temporal al completar."""
    first_id, _ = temp_db.upsert_file("first.jpg", "first.jpg")
    priority_id, _ = temp_db.upsert_file("priority.jpg", "priority.jpg")
    third_id, _ = temp_db.upsert_file("third.jpg", "third.jpg")

    temp_db.prioritize_file(priority_id)
    batch = temp_db.next_batch_pending(limit=2)

    assert [row["id"] for row in batch] == [priority_id, first_id]

    temp_db.update_done(priority_id, ["tag"], "safe")
    with temp_db._read() as c:
        done_row = c.execute(
            "SELECT priority, current_stage, failed_stage, error_message FROM FileQueue WHERE id=?",
            (priority_id,),
        ).fetchone()
        pending_row = c.execute("SELECT status FROM FileQueue WHERE id=?", (third_id,)).fetchone()

    assert done_row["priority"] == 0
    assert done_row["current_stage"] is None
    assert done_row["failed_stage"] is None
    assert done_row["error_message"] is None
    assert pending_row["status"] == "PENDING"


def test_prioritize_ignores_non_pending_files(temp_db):
    """Un archivo ya finalizado no debe saltar la cola por accidente."""
    file_id, _ = temp_db.upsert_file("done.jpg", "done.jpg")
    temp_db.update_done(file_id, ["tag"], "safe")

    temp_db.prioritize_file(file_id)

    with temp_db._read() as c:
        row = c.execute("SELECT priority FROM FileQueue WHERE id=?", (file_id,)).fetchone()
    assert row["priority"] == 0


def test_prepare_manual_processing_supports_reprocess(temp_db):
    """Procesar ahora debe ser una transición única desde la capa de persistencia."""
    file_id, _ = temp_db.upsert_file("manual.jpg", "manual.jpg")
    temp_db.update_done(file_id, ["old"], "safe")

    row = temp_db.prepare_manual_processing(file_id)

    assert row is not None
    assert row["id"] == file_id
    assert row["status"] == "PROCESSING"
    assert row["retries"] == 0
    assert row["priority"] == 0

    with temp_db._read() as c:
        db_row = c.execute(
            "SELECT status, retries, priority, failed_stage, error_message FROM FileQueue WHERE id=?",
            (file_id,),
        ).fetchone()

    assert db_row["status"] == "PROCESSING"
    assert db_row["retries"] == 0
    assert db_row["priority"] == 0
    assert db_row["failed_stage"] is None
    assert db_row["error_message"] is None

