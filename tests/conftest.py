import sys
from pathlib import Path

# Añadir el directorio de la app al path para que las importaciones relativas funcionen
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "smart_gallery_v2"))

import pytest
import sqlite3
import os
from smart_gallery_v2.core.database import DatabaseManager

@pytest.fixture
def temp_db(tmp_path):
    """Crea una instancia de DatabaseManager con una DB temporal."""
    db_file = tmp_path / "test_gallery.db"
    
    # Mockear la ruta en DatabaseManager antes de instanciar
    # Como es un singleton, tenemos que resetearlo si ya existe
    DatabaseManager._instance = None
    
    # Inyectar la ruta temporal
    db = DatabaseManager()
    db._db_path = db_file
    db._init_db()
    
    yield db
    
    # Limpieza
    DatabaseManager._instance = None
    if db_file.exists():
        os.remove(db_file)
