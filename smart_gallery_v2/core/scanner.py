"""
core/scanner.py — Crawl del Sistema de Archivos
Descubre nuevos archivos y los añade a la cola de SQLite.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.database import DatabaseManager

from core.config import DIR_ENTRADA, EXT_TODAS, EXT_VIDEO

log = logging.getLogger(__name__)


def scan_directory(db: DatabaseManager, path: Path = DIR_ENTRADA) -> int:
    """
    Escanea recursivamente el directorio de entrada y añade archivos nuevos a la cola.
    Retorna el número de nuevos archivos encontrados.
    """
    log.info(f"Iniciando scan en: {path}")
    count = 0
    if not path.exists():
        log.warning(f"Ruta de scan no existe: {path}")
        return 0

    for p in path.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXT_TODAS:
            # Intentar añadir a la DB (INSERT OR IGNORE)
            media_type = "video" if p.suffix.lower() in EXT_VIDEO else "image"
            file_id = db.upsert_file(str(p.resolve()), p.name, media_type=media_type)
            if file_id:
                count += 1

    log.info(f"Scan finalizado. {count} archivos en cola.")
    return count
