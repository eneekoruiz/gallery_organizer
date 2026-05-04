"""
core/watchdog_engine.py — Motor de Vigilancia de Sistema de Archivos
Detección en tiempo real · Drag & Drop · Sincronización bidireccional DB ↔ disco
"""

from __future__ import annotations

import gc
import logging
import threading
from pathlib import Path
from queue import Queue
from typing import Callable, Optional

from watchdog.events import (
    FileCreatedEvent, FileDeletedEvent,
    FileMovedEvent, FileSystemEvent, FileSystemEventHandler,
)
from watchdog.observers import Observer

from core.config import DIR_ENTRADA, EXT_TODAS, EXT_VIDEO

log = logging.getLogger(__name__)

# Tipo del callback que recibe el DatabaseManager
DbCallback = Callable[[str, str, str], None]


# ──────────────────────────────────────────────────────────────────────────────
# Handler de Eventos del SO
# ──────────────────────────────────────────────────────────────────────────────
class _GalleryHandler(FileSystemEventHandler):
    def __init__(self, event_queue: Queue, db_callback: Optional[DbCallback] = None) -> None:
        super().__init__()
        self._q  = event_queue
        self._cb = db_callback

    def _is_media(self, path: str) -> bool:
        return Path(path).suffix.lower() in EXT_TODAS

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_media(event.src_path):
            self._emit("created", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_media(event.src_path):
            self._emit("deleted", event.src_path)

    def on_moved(self, event: FileMovedEvent) -> None:  # type: ignore[override]
        if not event.is_directory:
            src, dst = event.src_path, event.dest_path
            if self._is_media(src) or self._is_media(dst):
                self._emit("moved", src, dst)

    def _emit(self, etype: str, src: str, dest: str = "") -> None:
        self._q.put({"event": etype, "src": src, "dest": dest})
        log.debug("FsEvent %s | %s → %s", etype, src, dest)
        if self._cb:
            try:
                self._cb(etype, src, dest)
            except Exception as exc:
                log.warning("Watchdog callback error: %s", exc)


# ──────────────────────────────────────────────────────────────────────────────
# FileSystemWatcher — clase pública
# ──────────────────────────────────────────────────────────────────────────────
class FileSystemWatcher:
    """
    Wrapper sobre watchdog.Observer.
    Escucha DIR_ENTRADA (y opcionalmente otras carpetas) en tiempo real.
    Propaga eventos al motor de procesamiento sin polling.
    """

    def __init__(self, event_queue: Queue,
                 watch_path: Path = DIR_ENTRADA,
                 db_callback: Optional[DbCallback] = None,
                 recursive: bool = True) -> None:
        self._q          = event_queue
        self._watch_path = watch_path
        self._recursive  = recursive
        self._handler    = _GalleryHandler(event_queue, db_callback)
        self._observer: Optional[Observer] = None
        self._active     = threading.Event()

    def start(self) -> None:
        if self._active.is_set():
            return
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self._watch_path), recursive=self._recursive)
        self._observer.start()
        self._active.set()
        log.info("Watchdog activo → %s", self._watch_path)

    def stop(self) -> None:
        if not self._active.is_set():
            return
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self._active.clear()
        gc.collect()
        log.info("Watchdog detenido.")

    def is_running(self) -> bool:
        return self._active.is_set()

    def add_watch(self, path: Path) -> None:
        if self._observer and self._active.is_set():
            self._observer.schedule(self._handler, str(path), recursive=self._recursive)


# ──────────────────────────────────────────────────────────────────────────────
# Fábrica de callback DB
# ──────────────────────────────────────────────────────────────────────────────
def make_db_callback(db: "DatabaseManager") -> DbCallback:  # type: ignore[name-defined]
    """Conecta eventos del SO con la capa de DB."""
    def _cb(event_type: str, src: str, dest: str) -> None:
        db.log_fs_event(event_type, src, dest)
        if event_type == "created":
            p = Path(src)
            db.upsert_file(src, p.name,
                           media_type="video" if p.suffix.lower() in EXT_VIDEO else "image")
        elif event_type == "deleted":
            db.delete_by_path(src)
        elif event_type == "moved":
            if Path(dest).suffix.lower() in EXT_TODAS:
                db.move_filepath(src, dest)
            else:
                db.delete_by_path(src)
    return _cb
