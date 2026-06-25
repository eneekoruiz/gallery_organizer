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

from core.config import (
    BATCH_SIZE,
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
from core.date_extractor import DateExtractor
from core.models_types import (
    AIResult,
    DedupeResult,
    ExifResult,
    MediaRecord,
    ProcessResult,
    ThumbnailResult,
)
from core.review_decider import ReviewDecider
from core.symlink_manager import create_group_symlinks
from core.video_processor import VideoKeyframeExtractor

log = logging.getLogger(__name__)


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

        # Motores pesados: se importan y construyen al arrancar el worker.
        self._yolo: Any = None
        self._arcface: Any = None
        self._clip: Any = None
        self._caption: Any = None
        self._ocr: Any = None
        self._dedupe_engine: Any = None
        self._faiss_class: Any = None
        self._video: Optional[VideoKeyframeExtractor] = None
        self._faiss_count = 0  # Para detectar cambios
        self._thumb_lock = threading.Lock()

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
                # Issue 2: Recargar FAISS si ha habido aprendizaje en el HITL
                self._check_reload_faiss()
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
        """Delega la orquestación al caso de uso independiente de infraestructura."""
        from application.media_pipeline import MediaPipeline

        return MediaPipeline(self, self._db).execute(record)

    # ── Steps ─────────────────────────────────────────────────────────────
    def check_stability(self, filepath: str) -> bool:
        return self._check_stability(filepath)

    def persist_duplicate(
        self, record: MediaRecord, dedupe: DedupeResult, thumb: Optional[str]
    ) -> None:
        self._step_persist_duplicate(record, dedupe, thumb)

    def _check_stability(self, filepath: str, wait_ms: int = 400) -> bool:
        """
        Verifica que el archivo exista, tenga extensión válida y su tamaño sea estable.
        Issue 5: Mayor rigor en la estabilidad (comprobación doble).
        """
        from core.config import EXT_TODAS

        p = Path(filepath)
        if not p.exists():
            return False

        if p.suffix.lower() not in EXT_TODAS:
            return False

        # Estabilidad de tamaño
        try:
            s1 = p.stat().st_size
            time.sleep(wait_ms / 2000.0)  # Primer respiro
            s2 = p.stat().st_size
            if s1 != s2 or s1 == 0:
                return False

            time.sleep(wait_ms / 2000.0)  # Segundo respiro para archivos grandes
            s3 = p.stat().st_size
            if s2 != s3:
                return False

            # Verificar bloqueo (intentar abrir para lectura)
            with open(filepath, "rb") as f:
                f.read(1024)  # Leer un poco para asegurar que no hay lock de escritura
        except (OSError, PermissionError):
            return False

        return True

    def thumbnail(self, filepath: str) -> ThumbnailResult:
        try:
            # Issue 15: Evitar carrera entre hilos al generar miniaturas
            with self._thumb_lock:
                path = _make_thumb(filepath)
            return ThumbnailResult(thumb_path=path)
        except (OSError, IOError) as e:
            log.warning(f"Thumbnail save failed for {filepath}: {e}")
            return ThumbnailResult(error=str(e))
        except Exception as e:
            return ThumbnailResult(error=str(e))

    def exif(self, filepath: str) -> ExifResult:
        try:
            data = _read_exif(filepath)
            return ExifResult(
                exif_date=data["exif_date"],
                gps=data["gps"],
                camera_model=data["camera_model"],
                lens_model=data["lens_model"],
                iso=data["iso"],
                f_number=data["f_number"],
                exposure=data["exposure"],
            )
        except (OSError, IOError) as e:
            log.warning(f"Exif read failed for {filepath}: {e}")
            return ExifResult(error=str(e))
        except Exception as e:
            log.exception(f"Unexpected Exif error for {filepath}: {e}")
            return ExifResult(error=str(e))

    def dedupe(self, filepath: str, file_id: int) -> DedupeResult:
        try:
            with _PILImage.open(filepath) as im:
                ph = imagehash.phash(im)
            ph_hex = str(ph)
            all_hashes = self._db.get_all_phashes()
            from core.ai_engines import DedupeEngine

            matches = DedupeEngine.find_similar(ph_hex, all_hashes, PHASH_HAMMING_THRESHOLD)
            matches = [m for m in matches if m != file_id]
            if matches:
                return DedupeResult(is_duplicate=True, original_id=matches[0])
            return DedupeResult(is_duplicate=False)
        except (OSError, IOError) as e:
            log.warning(f"Dedupe hash calculation failed: {e}")
            return DedupeResult(error=str(e))
        except Exception as e:
            log.exception(f"Unexpected dedupe error: {e}")
            return DedupeResult(error=str(e))

    def ai(self, filepath: str, file_id: int, media_type: str = "image") -> AIResult:
        if media_type == "image":
            return self._step_ai_image(filepath, file_id)
        return self._step_ai_video(filepath, file_id)

    def _step_ai_image(self, filepath: str, file_id: int) -> AIResult:
        try:
            # Issue 26: Soporte EXIF Orientation (Auto-rotación)
            # Usamos PIL para leer y corregir antes de pasar a CV2
            from PIL import Image, ImageOps

            with Image.open(filepath) as im_pil:
                im_pil = ImageOps.exif_transpose(im_pil)
                # phash sobre la imagen ya rotada correctamente
                ph = str(imagehash.phash(im_pil))
                # Convertir a CV2 (BGR) y RGB para el pipeline
                rgb = np.array(im_pil.convert("RGB"))
                img = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            tags, identities, triage_tier, quality_score, ocr_txt, detections, clip_emb = (
                self._process_image(img, rgb, filepath, file_id)
            )
            return AIResult(
                tags=tags,
                identities=identities,
                triage_tier=triage_tier,
                phash=ph,
                quality_score=quality_score,
                ocr_text=ocr_txt,
                detections_payload=detections,
                clip_embedding=clip_emb,
            )
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
            q_scores = []

            all_ocr = []
            for kf in keyframes:
                rgb = cv2.cvtColor(kf, cv2.COLOR_BGR2RGB)
                tags_kf, ids_kf, tier_kf, q_kf, ocr_kf, dets_kf, clip_kf = self._process_image(
                    kf, rgb, filepath, file_id
                )
                all_tags.update(tags_kf)

                # Issue 10: Deduplicar identidades por vídeo (no añadir la misma cara 10 veces)
                for iden in ids_kf:
                    if iden not in all_ids:
                        all_ids.add(iden)

                q_scores.append(q_kf)

                if ocr_kf:
                    all_ocr.append(ocr_kf)

                if tier_rank.get(tier_kf, 0) > tier_rank.get(best_tier, 0):
                    best_tier = tier_kf

            final_q = np.mean(q_scores) if q_scores else 0.5
            ocr_text = "\n".join(all_ocr) if all_ocr else None

            return AIResult(
                tags=sorted(list(all_tags)),
                triage_tier=best_tier,
                identities=sorted(list(all_ids)),
                quality_score=float(final_q),
                ocr_text=ocr_text,
                detections_payload=[],  # Videos will need a similar approach if extracting multiple faces
                clip_embedding=None,
            )
        except Exception as e:
            log.exception(f"Fallo en _step_ai_video: {e}")
            return AIResult(error=str(e))

    def persist(self, record: MediaRecord, ai: AIResult, exif: ExifResult, thumb: Optional[str]):
        # Extraer fecha en cascada
        exif_dt, filename_dt, folder_dt, filesystem_dt, best_dt, date_src, date_conf = (
            DateExtractor.extract(record.filepath)
        )

        # update_done inserta las detecciones al final. Decidir con la inferencia
        # actual evita consultar detecciones antiguas o todavía inexistentes.
        detections = ai.detections_payload or []
        face_confidences = [float(row.get("confidence", 0.0)) for row in detections]
        assigned_names = [str(row.get("assigned_name", "Desconocido")) for row in detections]

        # Calcular banderas avanzadas para el ReviewDecider
        has_unknown_person = "Desconocido" in assigned_names
        has_multiple_people = len(face_confidences) > 1
        has_low_face_confidence = any(c < 0.85 for c in face_confidences)
        has_date_uncertain = date_conf in ("low", "unknown")

        # Comprobar conflicto de fecha (folder vs EXIF/filename)
        has_folder_date_conflict = False
        if folder_dt:
            comp_dt = exif_dt or filename_dt
            if comp_dt:
                if folder_dt[:7] != comp_dt[:7]:
                    has_folder_date_conflict = True

        # Comprobar duplicado
        has_duplicate_conflict = "Duplicado" in (ai.tags or [])

        # Comprobar AI disagreement
        has_ai_disagreement = False
        yolo_person = "persona" in [t.lower() for t in (ai.tags or [])]
        has_faces = len(face_confidences) > 0
        if yolo_person != has_faces:
            has_ai_disagreement = True

        is_document = any(t in ("Documentos", "Captura") for t in (ai.tags or []))
        if is_document and has_faces:
            has_ai_disagreement = True

        # Decidir estado final de la cola (AUTO_CLASSIFIED o NEEDS_REVIEW)
        review_required, reasons, confidence_score = ReviewDecider.decide(
            face_confidences=face_confidences,
            date_confidence=date_conf,
            quality_score=ai.quality_score,
            has_unknown_person=has_unknown_person,
            has_multiple_people=has_multiple_people,
            has_low_face_confidence=has_low_face_confidence,
            has_date_uncertain=has_date_uncertain,
            has_folder_date_conflict=has_folder_date_conflict,
            has_duplicate_conflict=has_duplicate_conflict,
            has_ai_disagreement=has_ai_disagreement,
        )

        status = "NEEDS_REVIEW" if review_required else "AUTO_CLASSIFIED"

        self._db.update_done(
            record.id,
            tags=ai.tags,
            triage_tier=ai.triage_tier,
            exif_date=exif.exif_date,
            gps=exif.gps,
            thumb_path=thumb,
            phash=ai.phash,
            camera_model=exif.camera_model,
            lens_model=exif.lens_model,
            iso=exif.iso,
            f_number=exif.f_number,
            exposure=exif.exposure,
            quality_score=ai.quality_score,
            exif_datetime=exif_dt,
            filename_datetime=filename_dt,
            folder_datetime=folder_dt,
            filesystem_datetime=filesystem_dt,
            best_datetime=best_dt,
            date_source=date_src,
            date_confidence=date_conf,
            review_required=review_required,
            review_reasons=reasons,
            confidence_score=confidence_score,
            status=status,
            ocr_text=ai.ocr_text,
            detections_payload=ai.detections_payload,
            clip_embedding=ai.clip_embedding,
        )

    def _step_persist_duplicate(
        self, record: MediaRecord, dedupe: DedupeResult, thumb: Optional[str]
    ):
        self._db.update_done(
            record.id,
            tags=["Duplicado"],
            triage_tier="unclassified",
            thumb_path=thumb,
            review_required=True,
            review_reasons=["duplicate_conflict"],
            confidence_score=0.5,
            status="NEEDS_REVIEW",
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
        from core.ai_engines import (
            ArcFaceEngine,
            CLIPEngine,
            DenseCaptionEngine,
            OCREngine,
            YOLOEngine,
        )

        self._ocr = OCREngine()
        self._yolo = YOLOEngine()
        self._arcface = ArcFaceEngine()
        self._clip = CLIPEngine()
        self._caption = DenseCaptionEngine()
        self._video = VideoKeyframeExtractor()
        self._reload_faiss()
        self._emit("INFO", "✓ Motores listos.")

    def _reload_faiss(self) -> None:
        from core.ai_engines import FaissIndex

        names, embs = self._db.load_known_faces()
        self._faiss = FaissIndex()
        self._faiss.rebuild(names, embs)
        self._faiss_count = len(names)

    def _check_reload_faiss(self) -> None:
        """Issue 2: Recarga el índice si hay nuevas caras en la DB."""
        with self._db._read() as c:
            count = c.execute(
                "SELECT COUNT(*) FROM KnownFaces WHERE embedding IS NOT NULL"
            ).fetchone()[0]
        if count != self._faiss_count:
            log.info(f"Reloading FAISS: {self._faiss_count} -> {count} faces")
            self._reload_faiss()

    def _is_high_quality_face(self, crop: Optional[np.ndarray]) -> bool:
        """Issue 19: Determinar si un recorte de cara es apto para el índice de conocimiento."""
        if crop is None:
            return False
        try:
            h, w = crop.shape[:2]
            if h < 80 or w < 80:
                return False
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            # Nitidez vía Laplaciano
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            return variance > 80  # Umbral empírico para caras "nítidas"
        except (cv2.error, ValueError) as e:
            log.warning(f"Quality check failed for crop: {e}")
        except Exception as e:
            log.exception(f"Unexpected quality check error: {e}")
        return False

    def _process_image(
        self,
        img_bgr: np.ndarray,
        img_rgb: np.ndarray,
        filepath: str,
        file_id: int,
    ) -> tuple[list[str], list[str], str, float, Optional[str], list[dict], Optional[bytes]]:
        """
        Analiza una imagen devolviendo (tags, identities, triage_tier, quality_score, ocr_text, detections_payload, clip_embedding).
        """
        tags, identities = set(), set()
        ocr_text = None
        best_tier = "unclassified"
        tier_rank = {"safe": 2, "review": 1, "unclassified": 0}

        try:
            # 1. YOLO
            if self._yolo:
                dets = self._yolo.detect_batch([img_bgr])[0]
                for d in dets:
                    tags.add(d["class"])

            # 2. Faces
            detections_payload = []
            if self._arcface and self._faiss:
                faces = self._arcface.get_faces(img_rgb)
                for bbox, emb, det_conf, landmarks in faces:
                    face_crop = None
                    try:
                        top = max(0, int(bbox["top"]))
                        bottom = min(img_bgr.shape[0], int(bbox["bottom"]))
                        left = max(0, int(bbox["left"]))
                        right = min(img_bgr.shape[1], int(bbox["right"]))
                        face_crop = img_bgr[top:bottom, left:right]
                        is_high_q = self._is_high_quality_face(face_crop)
                    except (cv2.error, ValueError, IndexError) as e:
                        log.warning(f"Face crop extraction failed for bbox {bbox}: {e}")
                        is_high_q = False
                    except Exception as e:
                        log.debug(f"Unexpected error in face quality check: {e}")
                        is_high_q = False

                    name, faiss_conf, tier = self._faiss.search(emb)

                    if name != "Desconocido":
                        identities.add(name)
                        tags.add(name)
                        if tier_rank.get(tier, 0) > tier_rank.get(best_tier, 0):
                            best_tier = tier

                    crop_path = self._save_crop(img_bgr, bbox)

                    # Estimación de mirada y contacto visual
                    from core.gaze_detector import estimate_gaze_from_landmarks
                    eye_contact, gaze_dir, gaze_vec, landmarks_list = estimate_gaze_from_landmarks(landmarks)

                    detections_payload.append(
                        {
                            "embedding": emb,
                            "bbox": bbox,
                            "face_crop_path": crop_path,
                            "confidence": faiss_conf if name != "Desconocido" else det_conf,
                            "assigned_name": name,
                            "triage_tier": tier,
                            "is_high_quality": is_high_q,
                            "gaze_direction": gaze_dir,
                            "eye_contact": 1 if eye_contact else 0,
                            "landmarks": landmarks_list,
                        }
                    )

            # Global quality score (media de la nitidez completa)
            gray_full = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            full_var = cv2.Laplacian(gray_full, cv2.CV_64F).var()
            final_q_score = min(1.0, full_var / 200.0)

            # 3. CLIP
            clip_embedding = None
            if self._clip:
                emb = self._clip.embed_image(img_rgb)
                if emb is not None:
                    clip_embedding = emb

            # 3.5. Dense Captioning (Moondream2)
            dense_caption = None
            if self._caption:
                cap = self._caption.generate_caption(
                    img_rgb,
                    prompt="Describe what you see in a short paragraph, focusing on objects and context.",
                )
                if cap:
                    dense_caption = cap

            # 4. OCR fallback + Dense Caption integration
            if not tags:
                ocr_text = ""
                try:
                    if USE_PYTESSERACT:
                        import pytesseract

                        ocr_text = pytesseract.image_to_string(_PILImage.fromarray(img_rgb))
                    else:
                        reader = self._ocr.get_reader() if self._ocr else None
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

            if dense_caption:
                ocr_text = (ocr_text or "") + f"\n[AI Context]: {dense_caption}"
                tags.add("AI_Caption")

            return (
                sorted(list(tags)),
                sorted(list(identities)),
                best_tier,
                final_q_score,
                (ocr_text if ocr_text else None),
                detections_payload,
                clip_embedding,
            )

        except Exception as e:
            err = f"Error en _process_image: {e}"
            log.exception(err)
            return [], [], "unclassified", 0.5, None, [], None

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


def _gps_decimal(values: Any, ref: Any) -> float:
    """Convierte grados EXIF (racionales o números) a decimal firmado."""

    def as_float(value: Any) -> float:
        if isinstance(value, tuple):
            return float(value[0]) / float(value[1])
        return float(value)

    degrees, minutes, seconds = (as_float(value) for value in values)
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    return -decimal if str(ref).upper() in {"S", "W"} else decimal


def _read_exif(filepath: str) -> dict[str, Any]:
    res = {
        "exif_date": None,
        "gps": None,
        "camera_model": None,
        "lens_model": None,
        "iso": None,
        "f_number": None,
        "exposure": None,
    }
    try:
        with Image.open(filepath) as img:
            exif = img._getexif()
            if not exif:
                return res

            # Convert tid to name map
            tag_map = {v: k for k, v in ExifTags.TAGS.items()}

            # 1. Date
            for name in ("DateTimeOriginal", "DateTime"):
                tid = tag_map.get(name)
                if tid in exif:
                    try:
                        dt = datetime.strptime(exif[tid], "%Y:%m:%d %H:%M:%S")
                        res["exif_date"] = dt.strftime("%Y-%m-%dT%H:%M:%S")
                        break
                    except Exception:
                        continue

            # 2. Camera & Lens
            res["camera_model"] = exif.get(tag_map.get("Model"))
            res["lens_model"] = exif.get(tag_map.get("LensModel"))
            res["iso"] = exif.get(tag_map.get("ISOSpeedRatings"))

            f_num = exif.get(tag_map.get("FNumber"))
            if f_num:
                res["f_number"] = (
                    float(f_num[0] / f_num[1]) if isinstance(f_num, tuple) else float(f_num)
                )

            exp = exif.get(tag_map.get("ExposureTime"))
            if exp:
                if isinstance(exp, tuple):
                    res["exposure"] = f"{exp[0]}/{exp[1]}"
                else:
                    res["exposure"] = str(exp)

            # 3. GPS EXIF. Pillow devuelve IFDRational o tuplas según el formato.
            gps_tag = tag_map.get("GPSInfo")
            gps_raw = exif.get(gps_tag) if gps_tag else None
            if gps_raw:
                gps = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_raw.items()}

                if "GPSLatitude" in gps and "GPSLongitude" in gps:
                    res["gps"] = (
                        _gps_decimal(gps["GPSLatitude"], gps.get("GPSLatitudeRef", "N")),
                        _gps_decimal(gps["GPSLongitude"], gps.get("GPSLongitudeRef", "E")),
                    )
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
    except Exception as e:
        log.error("Generic embedding error: %s", e)
        return None


def _h6(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:6]


def _safe(name: str) -> str:
    return (
        "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_") or "otros"
    )
