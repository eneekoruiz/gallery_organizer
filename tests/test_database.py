import pytest
from smart_gallery_v2.core.database import DatabaseManager

def test_db_initialization(temp_db):
    """Verifica que las tablas básicas se creen correctamente."""
    with temp_db._read() as c:
        res = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='FileQueue'").fetchone()
        assert res is not None
        
        # Verificar versión de esquema
        res = c.execute("SELECT version FROM SchemaInfo").fetchone()
        assert res["version"] == 1

def test_file_upsert_and_fetch(temp_db):
    """Verifica el flujo de inserción y recuperación de archivos."""
    fid = temp_db.upsert_file("test/path.jpg", "path.jpg", "image")
    assert fid is not None
    
    stats = temp_db.get_stats()
    assert stats["total"] == 1
    assert stats["pending"] == 1

def test_update_status(temp_db):
    """Verifica el cambio de estados en la cola."""
    fid = temp_db.upsert_file("test.jpg", "test.jpg")
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
    fid = temp_db.upsert_file("error.jpg", "error.jpg")
    
    # Simular error
    with temp_db._write() as c:
        c.execute("UPDATE FileQueue SET status='ERROR', retries=3 WHERE id=?", (fid,))
        c.execute("INSERT INTO ProcessingErrors (file_id, filepath, phase, exception) VALUES (?,?,?,?)", 
                  (fid, "error.jpg", "test", "dummy exception"))
    
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
