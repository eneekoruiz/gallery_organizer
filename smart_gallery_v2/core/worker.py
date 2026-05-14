"""
core/worker.py — Motor de Procesamiento Local Robusto
Refactor Phase 3: Flujo explícito scan → enqueue → process_one → steps
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
from pathlib import Path
from queue import Queue
from typing import Any, Optional

import cv2
import imagehash
import numpy as np
from PIL import ExifTags, Image
from PIL import Image as _PILImage

from core.ai_engines import (
    ArcFaceEngine,
    CLIPEngine,
    DedupeEngine,
    FaissIndex,
    OCREngine,
    YOLOEngine,
)
from core.config import (
    DIR_THUMBS,
    OCR_MIN_TEXT_LEN,
    PHASH_HAMMING_THRESHOLD,
    THUMB_SIZE,
    USE_PYTESSERACT,
    BATCH_SIZE,
    DIR_RESULT,
    DIR_FACES,
    CONTROL_STATE_KEY,
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
        self._thread = threading.Thread(
            target=self._run, name="ProcessingEngine", daemon=True
        )
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

        # Initial scan (Phase 3)
        from core.scanner import scan_directory

        scan_directory(self._db)

        while not self._stop_evt.is_set():
            if self._pause_evt.is_set():
                time.sleep(0.5)
                continue

            # Batch fetching (Phase 4)
            batch = self._db.next_batch_pending(limit=BATCH_SIZE)
            if not batch:
                self._emit("DONE", "✅ Cola vacía.")
                time.sleep(2)  # Wait for new files
                continue

            for row in batch:
                if self._stop_evt.is_set():
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

            # Collect once per batch
            gc.collect()

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
            log.info(f"[{file_id}] Phase: Thumbnail")
            thumb_res = self.thumbnail(fp)
            if thumb_res.error:
                log.warning(f"[{file_id}] Thumb error: {thumb_res.error}")
                self._db.update_error(file_id, phase="thumbnail", exception=thumb_res.error)

            # 2. EXIF (solo imágenes)
            exif_res = ExifResult()
            if record.media_type == "image":
                log.info(f"[{file_id}] Phase: EXIF")
                exif_res = self.exif(fp)
                if exif_res.error:
                    log.warning(f"[{file_id}] EXIF error: {exif_res.error}")

            # 3. Dedupe (solo imágenes)
            if record.media_type == "image":
                log.info(f"[{file_id}] Phase: Dedupe")
                dedupe_res = self.dedupe(fp, file_id)
                if dedupe_res.error:
                    log.warning(f"[{file_id}] Dedupe error: {dedupe_res.error}")
                elif dedupe_res.is_duplicate:
                    log.info(f"[{file_id}] Duplicate found. Linking.")
                    self._step_persist_duplicate(
                        record, dedupe_res, thumb_res.thumb_path
                    )
                    return ProcessResult(
                        file_id, "DONE", "dedupe", "Duplicado detectado y vinculado."
                    )

            # 4. AI (YOLO, Face, CLIP)
            log.info(f"[{file_id}] Phase: AI")
            ai_res = self.ai(fp, file_id, media_type=record.media_type)

            if ai_res.error:
                log.error(f"[{file_id}] AI error: {ai_res.error}")
                return ProcessResult(file_id, "ERROR", "ai", ai_res.error)

            # 5. Materialize & Persist
            try:
                log.info(f"[{file_id}] Phase: Materialize")
                self.materialize_results(record, ai_res)
                log.info(f"[{file_id}] Phase: Persist")
                self.persist(record, ai_res, exif_res, thumb_res.thumb_path)
            except Exception as e:
                log.error(f"[{file_id}] Persist error: {e}")
                return ProcessResult(
                    file_id,
                    "ERROR",
                    "persist",
                    f"Fallo al mover/copiar archivos: {e}",
                )

            return ProcessResult(file_id, "DONE", "persist", "Procesado correctamente.")

        except Exception as e:
            err_msg = str(e)
            log.exception(f"Unexpected error in process_one for {fp}")
            self._db.update_error(file_id, phase="process_one", exception=err_msg)
            return ProcessResult(
                file_id, "ERROR", "exception", err_msg, exception=err_msg
            )

    # ── Steps ─────────────────────────────────────────────────────────────

    def _check_stability(self, filepath: str, wait_ms: int = 200) -> bool:
        """
        Verifica que el archivo exista, tenga extensión válida y su tamaño sea estable.
        """
        from core.config import EXT_TODAS

        p = Path(filepath)
        if not p.exists():
            log.warning(f"Archivo no existe: {filepath}")
            return False

        if p.suffix.lower() not in EXT_TODAS:
            log.warning(f"Extensión no soportada: {p.suffix}")
            return False

        # Verificar bloqueo (intentar abrir para lectura)
        try:
            with open(filepath, "rb"):
                pass
        except OSError:
            log.warning(f"Archivo bloqueado o sin permisos: {filepath}")
            return False

        # Estabilidad de tamaño
        try:
            s1 = p.stat().st_size
            time.sleep(wait_ms / 1000.0)
            s2 = p.stat().st_size
            if s1 != s2:
                log.info(f"Archivo inestable (escribiendo...): {filepath}")
                return False
        except OSError:
            return False

        return True

    def thumbnail(self, filepath: str) -> ThumbnailResult:
        try:
            path = _make_thumb(filepath)
            return ThumbnailResult(thumb_path=path)
        except Exception as e:
            return ThumbnailResult(error=str(e))

    def exif(self, filepath: str) -> ExifResult:
        try:
            data = _read_exif(filepath)
            return ExifResult(exif_date=data["exif_date"], gps=data["gps"])
        except Exception as e:
            return ExifResult(error=str(e))

    def dedupe(self, filepath: str, file_id: int) -> DedupeResult:
        try:
            with _PILImage.open(filepath) as im:
                ph = imagehash.phash(im)
            ph_hex = str(ph)
            all_hashes = self._db.get_all_phashes()
            matches = DedupeEngine.find_similar(
                ph_hex, all_hashes, PHASH_HAMMING_THRESHOLD
            )
            matches = [m for m in matches if m != file_id]
            if matches:
                return DedupeResult(is_duplicate=True, original_id=matches[0])
            return DedupeResult(is_duplicate=False)
        except Exception as e:
            return DedupeResult(error=str(e))

    def ai(self, filepath: str, file_id: int, media_type: str = "image") -> AIResult:
        if media_type == "image":
            return self._step_ai_image(filepath, file_id)
        return self._step_ai_video(filepath, file_id)

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

            ai_res = self._process_image(img, rgb, filepath, file_id, phash=ph)
            return ai_res
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
                ai_res_kf = self._process_image(kf, rgb, filepath, file_id)
                if ai_res_kf.error:
                    continue
                all_tags.update(ai_res_kf.tags)
                all_ids.update(ai_res_kf.identities)
                if tier_rank.get(ai_res_kf.triage_tier, 0) > tier_rank.get(
                    best_tier, 0
                ):
                    best_tier = ai_res_kf.triage_tier
            return AIResult(
                tags=list(all_tags), triage_tier=best_tier, identities=list(all_ids)
            )
        except Exception as e:
            log.exception(f"Fallo en _step_ai_video: {e}")
            return AIResult(error=str(e))

    def persist(
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

    def materialize_results(self, record: MediaRecord, ai: AIResult):
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
        self,
        img_bgr: np.ndarray,
        img_rgb: np.ndarray,
        filepath: str,
        file_id: int,
        phash: Optional[str] = None,
    ) -> AIResult:
        """
        Analiza una imagen devolviendo un AIResult estructurado.
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

                        ocr_text = pytesseract.image_to_string(
                            _PILImage.fromarray(img_rgb)
                        )
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

            return AIResult(
                tags=sorted(list(tags)),
                triage_tier=best_tier,
                identities=sorted(list(identities)),
                phash=phash,
            )

        except Exception as e:
            err = f"Error en _process_image: {e}"
            log.exception(err)
            return AIResult(error=err)

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
                    except Exception as e:
                        log.debug(f"EXIF date parse fail for {filepath}: {e}")
    except Exception as e:
        log.warning(f"EXIF read fail for {filepath}: {e}")
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
        "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")
        or "otros"
    )
