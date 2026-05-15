"""
core/symlink_manager.py — Gestión de Symlinks para Fotos Grupales
Windows (junction/mklink) · macOS/Linux (os.symlink)
Garantiza que una foto con N personas aparezca en N carpetas sin duplicar disco.
"""

from __future__ import annotations

import gc
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.database import DatabaseManager

from core.config import DIR_RESULT

log = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"


# ──────────────────────────────────────────────────────────────────────────────
# Creación de Symlinks
# ──────────────────────────────────────────────────────────────────────────────


def _sanitize(name: str) -> str:
    """Sanea un string para usarlo como nombre de carpeta/symlink."""
    safe = "".join(c for c in name if c.isalnum() or c in " _-()")
    return safe.strip().replace(" ", "_") or "sin_nombre"


def create_symlink(src_file: Path, identity: str) -> Optional[Path]:
    """
    Crea un symlink de src_file en DIR_RESULT/<identity>/<filename>.
    En Windows usa mklink (requiere permisos de administrador o modo Developer).
    En Unix usa os.symlink estándar.

    Devuelve la ruta del symlink creado o None si falla.
    """
    dest_dir = DIR_RESULT / _sanitize(identity)
    dest_dir.mkdir(parents=True, exist_ok=True)

    import hashlib
    h6 = hashlib.sha256(str(src_file.resolve()).encode()).hexdigest()[:6]
    link_path = dest_dir / f"{src_file.stem}_{h6}{src_file.suffix}"

    # Evitar duplicados: si ya existe y apunta al mismo origen, ok
    if link_path.exists() or link_path.is_symlink():
        try:
            if link_path.resolve() == src_file.resolve():
                return link_path  # ya correcto
            # Diferente destino: eliminar y recrear
            link_path.unlink()
        except Exception as exc:
            log.warning("No se pudo evaluar symlink existente %s: %s", link_path, exc)
            return None

    try:
        if _IS_WINDOWS:
            return _create_symlink_windows(src_file, link_path)
        else:
            os.symlink(str(src_file.resolve()), str(link_path))
            return link_path
    except Exception as exc:
        log.error("Error creando symlink %s → %s: %s", link_path, src_file, exc)
        # Fallback: copia dura si symlinks no están disponibles
        return _fallback_hardlink(src_file, link_path)


def _create_symlink_windows(src: Path, link: Path) -> Optional[Path]:
    """
    En Windows, intenta os.symlink (requiere privilegios o Developer Mode).
    Fallback: crea un junction point o un hardlink.
    """
    try:
        # Archivos → symlink de archivo
        os.symlink(str(src.resolve()), str(link), target_is_directory=False)
        return link
    except (OSError, NotImplementedError) as e:
        log.debug("os.symlink not supported on Windows without elevated privileges: %s", e)

    # Intento con mklink vía subprocess (requiere admin)
    try:
        result = subprocess.run(
            ["cmd", "/c", "mklink", str(link), str(src.resolve())],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return link
    except Exception as e:
        log.debug("mklink via subprocess failed: %s", e)

    return _fallback_hardlink(src, link)


def _fallback_hardlink(src: Path, link: Path) -> Optional[Path]:
    """
    Hard link como último recurso (mismo volumen requerido).
    No duplica contenido en disco en la mayoría de sistemas de archivos.
    """
    try:
        os.link(str(src.resolve()), str(link))
        log.info("Hardlink creado (fallback): %s", link)
        return link
    except Exception as exc:
        log.error("Hardlink también falló para %s: %s", link, exc)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Gestión de grupos (multi-tag)
# ──────────────────────────────────────────────────────────────────────────────


def create_group_symlinks(
    src_file: Path,
    identities: list[str],
    db: "DatabaseManager",  # type: ignore[name-defined]
    file_id: int,
) -> list[Path]:
    """
    Para una foto grupal con N identidades, crea N symlinks (uno por persona).
    Issue 18: Eliminar symlinks previos si estamos corrigiendo una identidad.
    """
    created: list[Path] = []
    
    # 1. Obtener symlinks actuales de este archivo en la DB
    current_links = db.get_symlink_paths_for_file(file_id)
    
    # 2. Crear los nuevos
    for identity in identities:
        link_path = create_symlink(src_file, identity)
        if link_path:
            created.append(link_path)
            # Registrar si es nuevo
            db.add_file_identity(
                file_id=file_id,
                identity=identity,
                symlink_path=str(link_path),
                is_faceless=False,
            )
            # Issue 18: Eliminar de la lista de "limpieza" los que acabamos de (re)crear
            if str(link_path) in current_links:
                current_links.remove(str(link_path))
            log.info("Symlink: %s → Resultados/%s/", src_file.name, _sanitize(identity))
        else:
            db.add_file_identity(file_id=file_id, identity=identity)

    # 3. Eliminar los symlinks huérfanos (los que estaban antes pero ya no en esta lista)
    for old_sp in current_links:
        if old_sp:
            p = Path(old_sp)
            if p.is_symlink() or p.exists():
                try:
                    p.unlink()
                    # Limpiar de la DB
                    db.delete_file_identity_by_symlink_path(old_sp)
                    log.info("Symlink huérfano eliminado: %s", p)
                except Exception:
                    pass

    gc.collect()
    return created


def create_faceless_symlink(
    src_file: Path,
    identity: str,
    db: "DatabaseManager",  # type: ignore[name-defined]
    file_id: int,
) -> Optional[Path]:
    """
    Crea un symlink para identidad faceless (persona de espaldas, silueta, etc.)
    y lo registra en FileIdentities con is_faceless=True.
    """
    link_path = create_symlink(src_file, identity)
    db.add_file_identity(
        file_id=file_id,
        identity=identity,
        symlink_path=str(link_path) if link_path else "",
        is_faceless=True,
    )
    return link_path


def rename_identity_folders(old_name: str, new_name: str, db: "DatabaseManager") -> bool:
    """
    Issue 17: Mueve físicamente la carpeta de una identidad en Resultados.
    Actualiza los registros de symlinks en la base de datos.
    """
    old_dir = DIR_RESULT / _sanitize(old_name)
    new_dir = DIR_RESULT / _sanitize(new_name)
    
    if not old_dir.exists():
        return False
    
    try:
        # Si la carpeta destino ya existe, moveremos el contenido uno a uno
        if new_dir.exists():
            for f in old_dir.iterdir():
                dest = new_dir / f.name
                if dest.exists():
                    dest.unlink()
                f.rename(dest)
                db.update_symlink_path_by_path(str(f.resolve()), str(dest.resolve()))
            old_dir.rmdir()
        else:
            # Renombrar carpeta completa
            old_dir.rename(new_dir)
            # Actualizar DB (todas las rutas que empezaran por old_dir)
            # Como los symlinks tienen la ruta completa, usamos un update parcial o iterativo
            # Para simplificar, buscamos todos los links de esta identidad
            with db._write() as c:
                c.execute("SELECT id, symlink_path FROM FileIdentities WHERE identity=?", (new_name,))
                rows = c.fetchall()
                for r in rows:
                    if r["symlink_path"]:
                        old_p = Path(r["symlink_path"])
                        new_p = new_dir / old_p.name
                        c.execute("UPDATE FileIdentities SET symlink_path=? WHERE id=?", (str(new_p), r["id"]))
        return True
    except Exception as e:
        log.error("Error renombrando carpeta de identidad %s -> %s: %s", old_name, new_name, e)
        return False


def remove_symlinks_for_file(file_id: int, db: "DatabaseManager") -> None:  # type: ignore[name-defined]
    """Elimina todos los symlinks de un archivo (e.g., al borrar de la DB)."""
    paths = db.get_symlink_paths_for_file(file_id)

    for sp in paths:
        if sp:
            p = Path(sp)
            if p.is_symlink() or (p.exists() and not p.is_dir()):
                try:
                    p.unlink()
                    log.info("Symlink eliminado: %s", p)
                except Exception as exc:
                    log.warning("No se pudo eliminar symlink %s: %s", p, exc)
