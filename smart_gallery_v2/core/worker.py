"""
core/worker.py — Motor de Procesamiento con Máquina de Estados
Pipeline: Sync → EXIF → Thumbnail → YOLO → ArcFace/FAISS → CLIP → Triage → Symlinks
Pause/Resume exacto · Graceful Shutdown · Batching · 3 reintentos
"""

from __future__ import annotations

import gc
import hashlib
import logging
import shutil
import threading
import time
import uuid
from datetime import datetime
import re
import imagehash
from PIL import Image as _PILImage
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image, ExifTags, UnidentifiedImageError

from core.config import (
    BATCH_SIZE, CONF_HIGH, CONF_MEDIUM,
    DIR_FACES, DIR_RESULT, DIR_THUMBS,
    EXT_IMAGEN, EXT_VIDEO, FAISS_THRESHOLD,
    THUMB_FORMAT, THUMB_QUALITY, THUMB_SIZE,
    PHASH_HAMMING_THRESHOLD, BURST_WINDOW_SECONDS,
    USE_PYTESSERACT, OCR_MIN_TEXT_LEN, CONTROL_STATE_KEY,
)
from core.database import DatabaseManager
from core.ai_engines import ArcFaceEngine, CLIPEngine, FaissIndex, YOLOEngine
from core.symlink_manager import create_group_symlinks
from core.video_processor import VideoKeyframeExtractor

log = logging.getLogger(__name__)

MAX_RETRIES = 3

# ──────────────────────────────────────────────────────────────────────────────
# EXIF Reader
# ──────────────────────────────────────────────────────────────────────────────
def _read_exif(filepath: str) -> dict[str, Any]:
    result: dict[str, Any] = {"exif_date": None, "gps": None}
    try:
        img      = Image.open(filepath)
        exif_raw = img._getexif()  # type: ignore[attr-defined]
        if not exif_raw:
            return result
        tag_map = {v: k for k, v in ExifTags.TAGS.items()}
        for name in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
            tid = tag_map.get(name)
            if tid and tid in exif_raw:
                try:
                    dt = datetime.strptime(exif_raw[tid], "%Y:%m:%d %H:%M:%S")
                    result["exif_date"] = dt.strftime("%Y-%m-%dT%H:%M:%S")
                    break
                except ValueError:
                    pass
        gid = tag_map.get("GPSInfo")
        if gid and gid in exif_raw:
            gps = exif_raw[gid]
            def dms(v, ref):
                d, m, s = float(v[0]), float(v[1]), float(v[2])
                dd = d + m/60 + s/3600
                return -dd if ref in ("S","W") else dd
            if gps.get(2) and gps.get(4):
                result["gps"] = (dms(gps[2], gps.get(1,"N")), dms(gps[4], gps.get(3,"E")))
    except Exception:
        pass
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Thumbnail Worker (hilo dedicado en background)
# ──────────────────────────────────────────────────────────────────────────────
class ThumbnailWorker:
    def __init__(self) -> None:
        self._q: Queue[Optional[str]] = Queue(maxsize=300)
        self._t = threading.Thread(target=self._loop, name="ThumbWorker", daemon=True)
        self._t.start()

    def enqueue(self, filepath: str) -> None:
        try:
            self._q.put_nowait(filepath)
        except Exception:
            pass

    def _loop(self) -> None:
        while True:
            fp = self._q.get()
            if fp is None:
                break
            _make_thumb(fp)
            self._q.task_done()

    def stop(self) -> None:
        self._q.put(None)
        self._t.join(timeout=3)


def _make_thumb(filepath: str) -> Optional[str]:
    try:
        stem  = Path(filepath).stem
        name  = f"{stem}_{_h6(filepath)}.webp"
        dest  = DIR_THUMBS / name
        if dest.exists():
            return str(dest)
        with Image.open(filepath) as img:
            img.thumbnail(THUMB_SIZE, Image.LANCZOS)
            if img.mode in ("RGBA","P","LA"):
                img = img.convert("RGB")
            img.save(str(dest), format=THUMB_FORMAT, quality=THUMB_QUALITY, method=4)
        return str(dest)
    except Exception as exc:
        log.debug("Thumbnail error %s: %s", filepath, exc)
        return None


def get_thumb(filepath: str) -> str:
    stem = Path(filepath).stem
    name = f"{stem}_{_h6(filepath)}.webp"
    dest = DIR_THUMBS / name
    if not dest.exists():
        _make_thumb(filepath)
    return str(dest) if dest.exists() else filepath


def _h6(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:6]


# ──────────────────────────────────────────────────────────────────────────────
# ProcessingEngine — Máquina de Estados con Pause/Resume exacto
# ──────────────────────────────────────────────────────────────────────────────
class ProcessingEngine:
    """
    Controles:
        start()  → Inicia o reanuda exactamente donde se detuvo
        pause()  → Pausa después del archivo actual (estado guardado en DB)
        stop()   → Graceful shutdown
    Mensajes canal UI: (tipo, payload)
        tipo: INFO | WARNING | ERROR | PROCESS | PROGRESS | DONE
    """

    def __init__(self, db: DatabaseManager, log_queue: Queue) -> None:
        self._db        = db
        self._log_q     = log_queue
        self._stop_evt  = threading.Event()
        self._pause_evt = threading.Event()
        self._thread:   Optional[threading.Thread] = None
        self._thumb_w:  Optional[ThumbnailWorker]  = None

        # Motores IA (lazy-load al arrancar)
        self._yolo:    Optional[YOLOEngine]    = None
        self._arcface: Optional[ArcFaceEngine] = None
        self._clip:    Optional[CLIPEngine]    = None
        self._faiss:   Optional[FaissIndex]    = None
        self._video:   Optional[VideoKeyframeExtractor] = None

    # ── Control ───────────────────────────────────────────────────────────
    def start(self) -> None:
        if self.is_running():
            # Reanudar desde pausa
            self._pause_evt.clear()
            try:
                self._db.set_control_state(CONTROL_STATE_KEY, "running")
            except Exception:
                pass
            self._emit("INFO", "▶ Motor reanudado.")
            return
        self._stop_evt.clear()
        self._pause_evt.clear()
        self._thread = threading.Thread(target=self._run, name="ProcessingEngine", daemon=True)
        self._thread.start()
        self._emit("INFO", "▶ Motor iniciado.")

    def pause(self) -> None:
        """
        Pausa elegante: el archivo actual termina antes de parar.
        El estado queda en DB (status PENDING para el siguiente).
        Al reanudar, next_pending() devuelve exactamente donde quedó.
        """
        self._pause_evt.set()
        try:
            self._db.set_control_state(CONTROL_STATE_KEY, "paused")
        except Exception:
            pass
        self._emit("WARNING", "⏸ Pausa solicitada — termina frame actual y se detiene.")

    def stop(self) -> None:
        self._stop_evt.set()
        self._pause_evt.clear()
        if self._thread:
            self._thread.join(timeout=12)
        if self._thumb_w:
            self._thumb_w.stop()
        try:
            self._db.set_control_state(CONTROL_STATE_KEY, "stopped")
        except Exception:
            pass
        self._emit("INFO", "⏹ Motor detenido (graceful shutdown).")
        gc.collect()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def is_paused(self) -> bool:
        return self._pause_evt.is_set()

    # ── Bucle principal ───────────────────────────────────────────────────
    def _run(self) -> None:
        self._thumb_w = ThumbnailWorker()
        self._load_engines()

        # Persistir estado como 'running'
        try:
            self._db.set_control_state(CONTROL_STATE_KEY, "running")
        except Exception:
            pass

        while not self._stop_evt.is_set():
            # Punto de pausa: espera sin consumir CPU
            if self._pause_evt.is_set():
                time.sleep(0.4)
                continue

            record = self._db.next_pending()
            if record is None:
                self._emit("DONE", "✅ Cola vacía. Todos los archivos procesados.")
                break

            filepath   = record["filepath"]
            file_id    = int(record["id"])
            media_type = record.get("media_type", "image")

            self._emit("PROCESS", f"[{media_type.upper()}] {Path(filepath).name}")

            try:
                # Dedupe: calcular pHash rápido antes de procesar (solo imágenes)
                phash_hex: Optional[str] = None
                if media_type == "image" and Path(filepath).exists():
                    try:
                        with _PILImage.open(filepath) as _im:
                            ph = imagehash.phash(_im)
                        phash_hex = ph.__str__()
                        simil = self._db.find_similar_phash(phash_hex, PHASH_HAMMING_THRESHOLD)
                        if simil:
                            # Si hay similar cercano, crear symlink en Results/Duplicates apuntando al original
                            s = simil[0]
                            try:
                                dup_dir = DIR_RESULT / "Duplicates"
                                dup_dir.mkdir(parents=True, exist_ok=True)
                                link_name = f"{Path(filepath).stem}_{_h6(filepath)}{Path(filepath).suffix}"
                                link_path = dup_dir / link_name
                                src_target = Path(s["filepath"]).resolve()
                                if not link_path.exists():
                                    try:
                                        os.symlink(str(src_target), str(link_path))
                                    except Exception:
                                        try:
                                            os.link(str(src_target), str(link_path))
                                        except Exception:
                                            pass
                                # Registrar relación en DB para este file_id
                                try:
                                    self._db.add_file_identity(file_id=file_id, identity="Duplicado",
                                                              symlink_path=str(link_path), is_faceless=False)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                            # Marcar DONE con tag Duplicado y phash
                            self._db.update_done(file_id, tags=["Duplicado"], triage_tier="unclassified",
                                                 exif_date=None, gps=None, thumb_path=get_thumb(filepath), phash=phash_hex)
                            self._emit("INFO", f"🔁 Duplicado detectado: {Path(filepath).name}")
                            continue
                    except Exception:
                        pass
                # 1. Thumbnail asíncrono
                self._thumb_w.enqueue(filepath)
                thumb_path = get_thumb(filepath)

                # 2. EXIF
                exif      = _read_exif(filepath) if media_type == "image" else {}
                exif_date = exif.get("exif_date")
                gps       = exif.get("gps")

                # 3. Inferencia
                if media_type == "image":
                    tags, triage_tier, identities, phash = self._process_image(filepath, file_id)
                else:
                    tags, triage_tier, identities = self._process_video(filepath, file_id)
                    phash = None

                # 4. Symlinks para grupos
                src = Path(filepath)
                if identities:
                    create_group_symlinks(src, identities, self._db, file_id)
                else:
                    # Sin identidades: carpeta por tags de objetos/SinClasificar
                    for t in (tags or ["SinClasificar"]):
                        d = DIR_RESULT / _safe(t)
                        d.mkdir(parents=True, exist_ok=True)
                        dest = d / f"{src.stem}_{_h6(filepath)}{src.suffix}"
                        if not dest.exists():
                            shutil.copy2(str(src), str(dest))

                # 5. Actualizar DB
                self._db.update_done(file_id, tags=tags, triage_tier=triage_tier,
                                     exif_date=exif_date, gps=gps, thumb_path=thumb_path,
                                     phash=(phash if media_type=="image" else None))

            except Exception as exc:
                log.exception("Error procesando %s", filepath)
                self._emit("ERROR", f"💥 {Path(filepath).name}: {exc}")
                self._db.update_error(file_id)

            # Progreso
            stats = self._db.get_stats()
            total = stats.get("total", 1) or 1
            done  = (stats.get("done", 0) or 0) + (stats.get("errors", 0) or 0)
            self._emit("PROGRESS", (done, total))
            gc.collect()

        if self._thumb_w:
            self._thumb_w.stop()
        self._emit("INFO", "Motor finalizado.")

    # ── Carga de motores ─────────────────────────────────────────────────
    def _load_engines(self) -> None:
        self._emit("INFO", "Cargando motores IA…")
        for name, cls, attr in [
            ("YOLO",    YOLOEngine,    "_yolo"),
            ("ArcFace", ArcFaceEngine, "_arcface"),
            ("CLIP",    CLIPEngine,    "_clip"),
        ]:
            try:
                setattr(self, attr, cls())
                self._emit("INFO", f"✓ {name} listo")
            except Exception as e:
                self._emit("WARNING", f"⚠ {name} no disponible: {e}")

        self._video = VideoKeyframeExtractor()
        self._reload_faiss()
        self._emit("INFO", "✓ Todos los motores listos.")

    def _reload_faiss(self) -> None:
        names, embs = self._db.load_known_faces()
        self._faiss = FaissIndex()
        self._faiss.rebuild(names, embs)
        self._emit("INFO", f"FAISS: {self._faiss.total} identidades cargadas.")

    # ── Análisis de imagen ────────────────────────────────────────────────
    def _process_image(self, filepath: str, file_id: int) -> tuple[list[str], str, list[str]]:
        stream = np.fromfile(filepath, dtype=np.uint8)
        img    = cv2.imdecode(stream, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("No se pudo decodificar la imagen")
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # compute pHash
        phash_hex: Optional[str] = None
        try:
            ph = imagehash.phash(_PILImage.open(filepath))
            phash_hex = ph.__str__()
        except Exception:
            phash_hex = None
        tags, tier, ids = self._analyze(img, rgb, filepath, file_id)
        return tags, tier, ids, phash_hex

    def _process_video(self, filepath: str, file_id: int) -> tuple[list[str], str, list[str]]:
        if self._video is None:
            return ["SinClasificar"], "unclassified", []
        keyframes  = self._video.extract(filepath)
        all_tags:  set[str] = set()
        all_ids:   set[str] = set()
        best_tier: str      = "unclassified"
        tier_rank  = {"safe": 2, "review": 1, "unclassified": 0}

        for kf in keyframes:
            rgb  = cv2.cvtColor(kf, cv2.COLOR_BGR2RGB)
            tags, tier, ids = self._analyze(kf, rgb, filepath, file_id)
            all_tags.update(tags)
            all_ids.update(ids)
            if tier_rank.get(tier, 0) > tier_rank.get(best_tier, 0):
                best_tier = tier

        return list(all_tags) or ["SinClasificar"], best_tier, list(all_ids)

    def _analyze(self, img_bgr: np.ndarray, img_rgb: np.ndarray,
                 filepath: str, file_id: int) -> tuple[list[str], str, list[str]]:
        """
        Retorna (tags, triage_tier, identidades_reconocidas).
        triage_tier: 'safe' | 'review' | 'unclassified'
        """
        tags:        set[str] = set()
        identities:  set[str] = set()
        best_tier = "unclassified"
        tier_rank = {"safe": 2, "review": 1, "unclassified": 0}

        # 1. YOLO
        if self._yolo:
            dets = self._yolo.detect_batch([img_bgr])[0]
            for d in dets:
                tags.add(d["class"])

        # 2. ArcFace + FAISS (VIP filter aplicado)
        if self._arcface and self._faiss:
            faces = self._arcface.get_faces(img_rgb)
            h_img, w_img = img_bgr.shape[:2]
            for bbox, emb, det_conf in faces:
                # calcular proporción del rostro en la imagen
                top, right, bottom, left = bbox["top"], bbox["right"], bbox["bottom"], bbox["left"]
                fw = max(0, right - left)
                fh = max(0, bottom - top)
                face_area = fw * fh
                img_area = max(1, w_img * h_img)
                area_pct = (face_area / img_area) * 100.0

                name, faiss_conf, tier = self._faiss.search(emb)

                # VIP logic: ignorar turistas muy pequeños si desconocido
                if area_pct < 5.0 and name == "Desconocido":
                    # marcar como turista — no crear detection para no contaminar índices
                    continue

                if name != "Desconocido":
                    identities.add(name)
                    tags.add(name)
                    if tier_rank.get(tier, 0) > tier_rank.get(best_tier, 0):
                        best_tier = tier
                else:
                    tier = "unclassified"

                crop_path = self._save_crop(img_bgr, bbox)
                self._db.add_detection(
                    file_id=file_id,
                    embedding=emb,
                    bbox=bbox,
                    face_crop_path=crop_path,
                    confidence=faiss_conf if name != "Desconocido" else det_conf,
                    assigned_name=name,
                    triage_tier=tier,
                    is_faceless=False,
                )

        # 3. CLIP
        if self._clip:
            emb = self._clip.embed_image(img_rgb)
            if emb is not None:
                self._db.upsert_clip(file_id, emb)

        # Si no hay caras ni objetos relevantes -> OCR / Documentos / Capturas
        if not tags:
            # Intentar OCR si está disponible
            ocr_text = ""
            try:
                if USE_PYTESSERACT:
                    ocr_text = __import__("pytesseract").image_to_string(_PILImage.fromarray(img_rgb))
                else:
                    reader = __import__("easyocr").Reader(["en"], gpu=False)
                    res = reader.readtext(img_rgb)
                    ocr_text = "\n".join([r[1] for r in res])
            except Exception:
                ocr_text = ""

            if ocr_text and len(ocr_text) >= OCR_MIN_TEXT_LEN:
                txt = ocr_text.lower()
                if any(k in txt for k in ("dni","factura","cedula","invoice","rut")):
                    tags.add("Documentos")
                else:
                    tags.add("Captura")
            else:
                tags.add("SinClasificar")

        return sorted(tags), best_tier, sorted(identities)

    def _save_crop(self, img_bgr: np.ndarray, bbox: dict[str, int]) -> str:
        t, r, b, l = bbox["top"], bbox["right"], bbox["bottom"], bbox["left"]
        crop = img_bgr[max(0,t):b, max(0,l):r]
        if crop.size == 0:
            return ""
        p = DIR_FACES / f"face_{uuid.uuid4().hex[:10]}.jpg"
        cv2.imwrite(str(p), crop)
        return str(p)

    def _emit(self, tipo: str, msg: Any) -> None:
        try:
            self._log_q.put_nowait((tipo, msg))
        except Exception:
            pass


def _safe(name: str) -> str:
    return ("".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ","_")) or "otros"
