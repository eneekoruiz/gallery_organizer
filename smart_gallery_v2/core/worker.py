"""
core/worker.py — Motor de Procesamiento Local Robusto
Refactor Phase 3: Flujo explícito scan → enqueue → process_one → steps
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any, Optional

import cv2
import imagehash
import numpy as np
from PIL import ExifTags, Image
from PIL import Image as _PILImage

from core.ai_engines import ArcFaceEngine, CLIPEngine, DedupeEngine, FaissIndex, YOLOEngine
from core.config import (
    CONTROL_STATE_KEY,
    DIR_FACES,
    DIR_RESULT,
    DIR_THUMBS,
    OCR_MIN_TEXT_LEN,
    PHASH_HAMMING_THRESHOLD,
    THUMB_SIZE,
    USE_PYTESSERACT,
)
from core.database import DatabaseManager
from core.models_types import (
    AIResult,
    DedupeResult,
    ExifResult,
    MediaRecord,
    ProcessResult,
    ThumbnailResult,
)
from core.symlink_manager import create_group_symlinks
from core.video_processor import VideoKeyframeExtractor

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# OCR Singleton
# ──────────────────────────────────────────────────────────────────────────────
class OCREngine:
    _instance: Optional[OCREngine] = None

    def __new__(cls) -> OCREngine:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._reader = None
        return cls._instance

    def get_reader(self) -> Any:
        if self._reader is None:
            try:
                import easyocr

                self._reader = easyocr.Reader(["en", "es"], gpu=False)
                log.info("OCR Engine: EasyOCR loaded.")
            except Exception as e:
                log.error(f"OCR Engine load failed: {e}")
        return self._reader


ocr_engine = OCREngine()


# ──────────────────────────────────────────────────────────────────────────────
# ProcessingEngine
# ──────────────────────────────────────────────────────────────────────────────
class ProcessingEngine:
    def __init__(self, db: DatabaseManager, log_queue: Queue) -> None:
        self._db = db
        self._log_q = log_queue
        self._stop_evt = threading.Event()
        self._pause_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Motores
        self._yolo: Optional[YOLOEngine] = None
        self._arcface: Optional[ArcFaceEngine] = None
        self._clip: Optional[CLIPEngine] = None
        self._faiss: Optional[FaissIndex] = None
        self._video: Optional[VideoKeyframeExtractor] = None

    def start(self) -> None:
        if self.is_running():
            self._pause_evt.clear()
            self._db.set_control_state(CONTROL_STATE_KEY, "running")
            self._emit("INFO", "▶ Motor reanudado.")
            return
        self._stop_evt.clear()
        self._pause_evt.clear()
        self._thread = threading.Thread(target=self._run, name="ProcessingEngine", daemon=True)
        self._thread.start()
        self._emit("INFO", "▶ Motor iniciado.")

    def pause(self) -> None:
        self._pause_evt.set()
        self._db.set_control_state(CONTROL_STATE_KEY, "paused")
        self._emit("WARNING", "⏸ Pausa solicitada.")

    def stop(self) -> None:
        self._stop_evt.set()
        self._pause_evt.clear()
        if self._thread:
            self._thread.join(timeout=5)
        self._db.set_control_state(CONTROL_STATE_KEY, "stopped")
        self._emit("INFO", "⏹ Motor detenido.")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def is_paused(self) -> bool:
        return self._pause_evt.is_set()

    def _run(self) -> None:
        self._load_engines()
        log.info("Pipeline started.")

        while not self._stop_evt.is_set():
            if self._pause_evt.is_set():
                time.sleep(0.5)
                continue

            row = self._db.next_pending()
            if not row:
                self._emit("DONE", "✅ Cola vacía.")
                break

            record = MediaRecord(
                id=int(row["id"]),
                filepath=row["filepath"],
                media_type=row.get("media_type", "image"),
                retries=int(row.get("retries", 0)),
            )

            res = self.process_one(record)

            if res.status == "ERROR":
                self._emit("ERROR", f"💥 {Path(record.filepath).name}: {res.message}")

            # Progress update
            stats = self._db.get_stats()
            self._emit("PROGRESS", (stats.get("done", 0), stats.get("total", 1)))

        log.info("Pipeline loop finished.")

    def process_one(self, record: MediaRecord) -> ProcessResult:
        """Flujo explícito por fases."""
        fp = record.filepath
        file_id = record.id

        try:
            # 0. Estabilidad (Phase 4)
            if not self._check_stability(fp):
                return ProcessResult(
                    file_id, "ERROR", "stability", "Archivo inestable o no encontrado."
                )

            # 1. Thumbnail
            thumb_res = self._step_thumb(fp)
            if thumb_res.error:
                log.warning(f"Thumb error for {fp}: {thumb_res.error}")

            # 2. EXIF (solo imágenes)
            exif_res = ExifResult()
            if record.media_type == "image":
                exif_res = self._step_exif(fp)

            # 3. Dedupe (solo imágenes)
            if record.media_type == "image":
                dedupe_res = self._step_dedupe(fp, file_id)
                if dedupe_res.is_duplicate:
                    self._step_persist_duplicate(record, dedupe_res, thumb_res.thumb_path)
                    return ProcessResult(
                        file_id, "DONE", "dedupe", "Duplicado detectado y vinculado."
                    )

            # 4. AI (YOLO, Face, CLIP)
            ai_res = AIResult()
            if record.media_type == "image":
                ai_res = self._step_ai_image(fp, file_id)
            else:
                ai_res = self._step_ai_video(fp, file_id)

            if ai_res.error:
                return ProcessResult(file_id, "ERROR", "ai", ai_res.error)

            # 5. Materialize & Persist
            try:
                self._step_materialize(record, ai_res)
                self._step_persist_final(record, ai_res, exif_res, thumb_res.thumb_path)
            except Exception as e:
                return ProcessResult(
                    file_id, "ERROR", "materialize", f"Fallo al mover/copiar archivos: {e}"
                )

            return ProcessResult(file_id, "DONE", "persist", "Procesado correctamente.")

        except Exception as e:
            err_msg = str(e)
            log.exception(f"Unexpected error in process_one for {fp}")
            self._db.update_error(file_id, phase="process_one", exception=err_msg)
            return ProcessResult(file_id, "ERROR", "exception", err_msg, exception=err_msg)

    # ── Steps ─────────────────────────────────────────────────────────────

    def _check_stability(self, filepath: str) -> bool:
        p = Path(filepath)
        if not p.exists():
            return False
        # Check size stability over 100ms
        s1 = p.stat().st_size
        time.sleep(0.1)
        s2 = p.stat().st_size
        return s1 == s2

    def _step_thumb(self, filepath: str) -> ThumbnailResult:
        try:
            path = _make_thumb(filepath)
            return ThumbnailResult(thumb_path=path)
        except Exception as e:
            return ThumbnailResult(error=str(e))

    def _step_exif(self, filepath: str) -> ExifResult:
        try:
            data = _read_exif(filepath)
            return ExifResult(exif_date=data["exif_date"], gps=data["gps"])
        except Exception as e:
            return ExifResult(error=str(e))

    def _step_dedupe(self, filepath: str, file_id: int) -> DedupeResult:
        try:
            with _PILImage.open(filepath) as im:
                ph = imagehash.phash(im)
            ph_hex = str(ph)
            all_hashes = self._db.get_all_phashes()
            matches = DedupeEngine.find_similar(ph_hex, all_hashes, PHASH_HAMMING_THRESHOLD)
            matches = [m for m in matches if m != file_id]
            if matches:
                return DedupeResult(is_duplicate=True, original_id=matches[0])
            return DedupeResult(is_duplicate=False)
        except Exception as e:
            return DedupeResult(error=str(e))

    def _step_ai_image(self, filepath: str, file_id: int) -> AIResult:
        try:
            stream = np.fromfile(filepath, dtype=np.uint8)
            img = cv2.imdecode(stream, cv2.IMREAD_COLOR)
            if img is None:
                return AIResult(error="Decodificación fallida.")
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # phash para persistencia
            with _PILImage.open(filepath) as im:
                ph = str(imagehash.phash(im))

            tags, tier, ids, err = self._process_image(img, rgb, filepath, file_id)
            if err:
                return AIResult(error=err)
            return AIResult(tags=tags, triage_tier=tier, identities=ids, phash=ph)
        except Exception as e:
            log.exception(f"Fallo en _step_ai_image: {e}")
            return AIResult(error=str(e))

    def _step_ai_video(self, filepath: str, file_id: int) -> AIResult:
        if not self._video:
            return AIResult(tags=["SinClasificar"])
        try:
            keyframes = self._video.extract(filepath)
            all_tags, all_ids = set(), set()
            best_tier = "unclassified"
            tier_rank = {"safe": 2, "review": 1, "unclassified": 0}

            for kf in keyframes:
                rgb = cv2.cvtColor(kf, cv2.COLOR_BGR2RGB)
                tags, tier, ids, err = self._process_image(kf, rgb, filepath, file_id)
                if err:
                    continue
                all_tags.update(tags)
                all_ids.update(ids)
                if tier_rank.get(tier, 0) > tier_rank.get(best_tier, 0):
                    best_tier = tier
            return AIResult(tags=list(all_tags), triage_tier=best_tier, identities=list(all_ids))
        except Exception as e:
            log.exception(f"Fallo en _step_ai_video: {e}")
            return AIResult(error=str(e))

    def _step_persist_final(
        self, record: MediaRecord, ai: AIResult, exif: ExifResult, thumb: Optional[str]
    ):
        self._db.update_done(
            record.id,
            tags=ai.tags,
            triage_tier=ai.triage_tier,
            exif_date=exif.exif_date,
            gps=exif.gps,
            thumb_path=thumb,
            phash=ai.phash,
        )

    def _step_persist_duplicate(
        self, record: MediaRecord, dedupe: DedupeResult, thumb: Optional[str]
    ):
        self._db.update_done(
            record.id, tags=["Duplicado"], triage_tier="unclassified", thumb_path=thumb
        )

    def _step_materialize(self, record: MediaRecord, ai: AIResult):
        src = Path(record.filepath)
        if ai.identities:
            create_group_symlinks(src, ai.identities, self._db, record.id)
        else:
            for t in ai.tags or ["SinClasificar"]:
                d = DIR_RESULT / _safe(t)
                d.mkdir(parents=True, exist_ok=True)
                dest = d / f"{src.stem}_{_h6(str(src))}{src.suffix}"
                if not dest.exists():
                    try:
                        shutil.copy2(str(src), str(dest))
                    except Exception as e:
                        log.warning(f"Materialize copy fail: {e}")

    # ── IA Logic ──────────────────────────────────────────────────────────

    def _load_engines(self) -> None:
        self._emit("INFO", "Cargando motores IA...")
        self._yolo = YOLOEngine()
        self._arcface = ArcFaceEngine()
        self._clip = CLIPEngine()
        self._video = VideoKeyframeExtractor()
        self._reload_faiss()
        self._emit("INFO", "✓ Motores listos.")

    def _reload_faiss(self) -> None:
        names, embs = self._db.load_known_faces()
        self._faiss = FaissIndex()
        self._faiss.rebuild(names, embs)

    def _process_image(
        self, img_bgr: np.ndarray, img_rgb: np.ndarray, filepath: str, file_id: int
    ) -> tuple[list[str], str, list[str], Optional[str]]:
        """
        Analiza una imagen devolviendo: (tags, tier, identities, error_msg)
        """
        tags, identities = set(), set()
        best_tier = "unclassified"
        tier_rank = {"safe": 2, "review": 1, "unclassified": 0}

        try:
            # 1. YOLO
            if self._yolo:
                dets = self._yolo.detect_batch([img_bgr])[0]
                for d in dets:
                    tags.add(d["class"])

            # 2. Faces
            if self._arcface and self._faiss:
                faces = self._arcface.get_faces(img_rgb)
                for bbox, emb, det_conf in faces:
                    name, faiss_conf, tier = self._faiss.search(emb)
                    if name != "Desconocido":
                        identities.add(name)
                        tags.add(name)
                        if tier_rank.get(tier, 0) > tier_rank.get(best_tier, 0):
                            best_tier = tier

                    crop_path = self._save_crop(img_bgr, bbox)
                    self._db.add_detection(
                        file_id=file_id,
                        embedding=emb,
                        bbox=bbox,
                        face_crop_path=crop_path,
                        confidence=faiss_conf if name != "Desconocido" else det_conf,
                        assigned_name=name,
                        triage_tier=tier,
                    )

            # 3. CLIP
            if self._clip:
                emb = self._clip.embed_image(img_rgb)
                if emb is not None:
                    self._db.upsert_clip(file_id, emb)

            # 4. OCR fallback
            if not tags:
                ocr_text = ""
                try:
                    if USE_PYTESSERACT:
                        import pytesseract

                        ocr_text = pytesseract.image_to_string(_PILImage.fromarray(img_rgb))
                    else:
                        reader = ocr_engine.get_reader()
                        if reader:
                            res = reader.readtext(img_rgb)
                            ocr_text = "\n".join([r[1] for r in res])
                except Exception as e:
                    log.warning(f"OCR intermediate fail: {e}")

                if ocr_text and len(ocr_text) >= OCR_MIN_TEXT_LEN:
                    txt = ocr_text.lower()
                    if any(k in txt for k in ("dni", "factura", "cedula", "invoice")):
                        tags.add("Documentos")
                    else:
                        tags.add("Captura")
                else:
                    tags.add("SinClasificar")

            return sorted(tags), best_tier, sorted(identities), None

        except Exception as e:
            err = f"Error en _process_image: {e}"
            log.exception(err)
            return [], "unclassified", [], err

    def _save_crop(self, img_bgr: np.ndarray, bbox: dict[str, int]) -> str:
        t, r, b, left = bbox["top"], bbox["right"], bbox["bottom"], bbox["left"]
        crop = img_bgr[max(0, t) : b, max(0, left) : r]
        if crop.size == 0:
            return ""
        p = DIR_FACES / f"face_{uuid.uuid4().hex[:10]}.jpg"
        cv2.imwrite(str(p), crop)
        return str(p)

    def _emit(self, tipo: str, msg: Any) -> None:
        try:
            self._log_q.put_nowait((tipo, msg))
        except Exception as e:
            log.warning(f"Log emission failed: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _read_exif(filepath: str) -> dict[str, Any]:
    res = {"exif_date": None, "gps": None}
    try:
        with Image.open(filepath) as img:
            exif = img._getexif()
            if not exif:
                return res
            tag_map = {v: k for k, v in ExifTags.TAGS.items()}
            for name in ("DateTimeOriginal", "DateTime"):
                tid = tag_map.get(name)
                if tid in exif:
                    try:
                        dt = datetime.strptime(exif[tid], "%Y:%m:%d %H:%M:%S")
                        res["exif_date"] = dt.strftime("%Y-%m-%dT%H:%M:%S")
                        break
                    except Exception:
                        pass
    except Exception:
        pass
    return res


def _make_thumb(filepath: str) -> Optional[str]:
    try:
        dest = DIR_THUMBS / f"{Path(filepath).stem}_{_h6(filepath)}.webp"
        if dest.exists():
            return str(dest)
        with Image.open(filepath) as img:
            img.thumbnail(THUMB_SIZE, Image.LANCZOS)
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(str(dest), format="WEBP", quality=80)
        return str(dest)
    except Exception:
        return None


def _h6(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:6]


def _safe(name: str) -> str:
    return (
        "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_") or "otros"
    )
