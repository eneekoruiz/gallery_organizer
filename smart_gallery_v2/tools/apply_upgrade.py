"""Crea un backup y aplica en orden el esquema completo y sus migraciones.

Uso desde el directorio raíz::

    python smart_gallery_v2/tools/apply_upgrade.py
    python smart_gallery_v2/tools/apply_upgrade.py --db D:/Galeria/gallery.db
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core.config import DB_PATH  # noqa: E402
from core.database import DatabaseManager  # noqa: E402

log = logging.getLogger(__name__)


def apply(db_path: Path) -> Path:
    """Aplica todas las migraciones que conoce DatabaseManager."""
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base de datos: {db_path}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_suffix(f".before_upgrade_{stamp}.bak")
    shutil.copy2(db_path, backup)
    DatabaseManager._instance = None
    try:
        DatabaseManager(db_path)
    except Exception:
        log.exception("La migración falló; la base original permanece respaldada en %s", backup)
        raise
    finally:
        DatabaseManager._instance = None
    return backup


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Actualizar todo el esquema de Smart AI Gallery")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    backup = apply(args.db.resolve())
    log.info("Migraciones completadas. Backup: %s", backup)


if __name__ == "__main__":
    main()
