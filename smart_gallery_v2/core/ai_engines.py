"""
core/ai_engines.py — Motores de IA con ONNX Runtime
YOLOv8 · ArcFace R100 · CLIP ViT-B/32 · FAISS
Triage tier automático por umbral de confianza.
"""

from __future__ import annotations

import gc
import logging
import warnings
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

from core.config import (
    ARCFACE_DIM, BATCH_SIZE, CONF_HIGH, CONF_MEDIUM,
    FACE_CONF_MIN, FAISS_THRESHOLD,
    ONNX_ARCFACE, ONNX_CLIP_TXT, ONNX_CLIP_VIS, ONNX_YOLO,
    YOLO_CLASSES, YOLO_CONF_MIN,
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _load_ort(model_path: Path):
    try:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.log_severity_level        = 3
        opts.intra_op_num_threads      = 4
        opts.graph_optimization_level  = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        return ort.InferenceSession(str(model_path), sess_options=opts,
                                    providers=["CPUExecutionProvider"])
    except Exception as exc:
        log.debug("ONNX no disponible %s: %s", model_path, exc)
        return None

def _norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / (n + 1e-8)

def _conf_to_tier(conf: float) -> str:
    if conf >= CONF_HIGH:
        return "safe"
    if conf >= CONF_MEDIUM:
        return "review"
    return "unclassified"


# ──────────────────────────────────────────────────────────────────────────────
# YOLOv8 Engine
# ──────────────────────────────────────────────────────────────────────────────
class YOLOEngine:
    INPUT_SZ = 640

    def __init__(self) -> None:
        self._ort    = _load_ort(ONNX_YOLO)
        self._native = None
        if self._ort:
            self._inp = self._ort.get_inputs()[0].name
        else:
            self._load_native()

    def _load_native(self) -> None:
        try:
            from ultralytics import YOLO
            self._native = YOLO("yolov8n.pt", verbose=False)
            log.info("YOLOEngine: ultralytics nativo")
        except Exception as exc:
            log.error("YOLOEngine sin backend: %s", exc)

    def detect_batch(self, imgs_bgr: list[np.ndarray]) -> list[list[dict[str, Any]]]:
        if not imgs_bgr:
            return []
        if self._ort:
            return [self._infer_ort(img) for img in imgs_bgr]
        if self._native:
            return self._infer_native(imgs_bgr)
        return [[] for _ in imgs_bgr]

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        r = cv2.resize(img, (self.INPUT_SZ, self.INPUT_SZ))
        r = cv2.cvtColor(r, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        return r.transpose(2, 0, 1)[np.newaxis]

    def _infer_ort(self, img: np.ndarray) -> list[dict[str, Any]]:
        blob = self._preprocess(img)
        out  = self._ort.run(None, {self._inp: blob})[0][0].T  # (8400,84)
        h, w = img.shape[:2]
        dets: list[dict[str, Any]] = []
        for det in out:
            cid  = int(np.argmax(det[4:]))
            conf = float(det[4 + cid])
            if conf < YOLO_CONF_MIN or cid not in YOLO_CLASSES:
                continue
            cx, cy, bw, bh = det[:4]
            sx, sy = w / self.INPUT_SZ, h / self.INPUT_SZ
            dets.append({"class": YOLO_CLASSES[cid], "conf": conf,
                          "bbox": [int((cx-bw/2)*sx), int((cy-bh/2)*sy),
                                   int((cx+bw/2)*sx), int((cy+bh/2)*sy)]})
        return dets

    def _infer_native(self, imgs: list[np.ndarray]) -> list[list[dict[str, Any]]]:
        results = []
        for chunk in [imgs[i:i+BATCH_SIZE] for i in range(0, len(imgs), BATCH_SIZE)]:
            raw = self._native(chunk, verbose=False, classes=list(YOLO_CLASSES))
            for r in raw:
                dets = []
                for box in r.boxes:
                    cid  = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    if conf >= YOLO_CONF_MIN and cid in YOLO_CLASSES:
                        dets.append({"class": YOLO_CLASSES[cid], "conf": conf,
                                     "bbox": box.xyxy[0].tolist()})
                results.append(dets)
        gc.collect()
        return results


# ──────────────────────────────────────────────────────────────────────────────
# ArcFace Engine
# ──────────────────────────────────────────────────────────────────────────────
class ArcFaceEngine:
    H = W = 112

    def __init__(self) -> None:
        self._ort   = _load_ort(ONNX_ARCFACE)
        self._df_ok = False
        if self._ort:
            self._inp = self._ort.get_inputs()[0].name
        else:
            try:
                from deepface import DeepFace  # noqa: F401
                self._df_ok = True
                log.info("ArcFaceEngine: DeepFace nativo")
            except ImportError:
                log.error("ArcFaceEngine: sin backend.")

    def get_faces(self, img_rgb: np.ndarray) -> list[tuple[dict[str, int], np.ndarray, float]]:
        """Devuelve [(bbox_dict, embedding_float32, confidence)]"""
        if self._ort:
            return self._faces_ort(img_rgb)
        if self._df_ok:
            return self._faces_deepface(img_rgb)
        return []

    def _faces_deepface(self, img_rgb: np.ndarray) -> list[tuple[dict[str, int], np.ndarray, float]]:
        from deepface import DeepFace
        try:
            faces = DeepFace.represent(img_path=img_rgb, model_name="ArcFace",
                                       detector_backend="retinaface", enforce_detection=False)
        except Exception:
            return []
        out = []
        for f in faces:
            if f.get("face_confidence", 0) < FACE_CONF_MIN:
                continue
            fa   = f["facial_area"]
            bbox = {"top": fa["y"], "right": fa["x"]+fa["w"],
                    "bottom": fa["y"]+fa["h"], "left": fa["x"]}
            emb  = _norm(np.array(f["embedding"], dtype=np.float32))
            out.append((bbox, emb, float(f["face_confidence"])))
        return out

    def _faces_ort(self, img_rgb: np.ndarray) -> list[tuple[dict[str, int], np.ndarray, float]]:
        try:
            from retinaface import RetinaFace  # type: ignore
            raw = RetinaFace.detect_faces(img_rgb)
        except Exception:
            return []
        if not isinstance(raw, dict):
            return []
        out = []
        for face in raw.values():
            area = face["facial_area"]
            top, right, bottom, left = area[1], area[2], area[3], area[0]
            conf = float(face.get("score", 1.0))
            if conf < FACE_CONF_MIN:
                continue
            crop = img_rgb[max(0,top):bottom, max(0,left):right]
            if crop.size == 0:
                continue
            emb = self._embed_ort(crop)
            if emb is None:
                continue
            bbox = {"top": top, "right": right, "bottom": bottom, "left": left}
            out.append((bbox, emb, conf))
        return out

    def _embed_ort(self, crop_rgb: np.ndarray) -> Optional[np.ndarray]:
        try:
            img = cv2.resize(crop_rgb, (self.W, self.H)).astype(np.float32)
            img = (img - 127.5) / 128.0
            blob = img.transpose(2,0,1)[np.newaxis]
            out  = self._ort.run(None, {self._inp: blob})[0][0]
            return _norm(out.astype(np.float32))
        except Exception:
            return None


# ──────────────────────────────────────────────────────────────────────────────
# CLIP Engine
# ──────────────────────────────────────────────────────────────────────────────
class CLIPEngine:
    IMG_SZ = 224
    MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
    STD  = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

    def __init__(self) -> None:
        self._vis = _load_ort(ONNX_CLIP_VIS)
        self._txt = _load_ort(ONNX_CLIP_TXT)
        self._native = None
        if self._vis is None:
            self._load_native()
        else:
            self._inp = self._vis.get_inputs()[0].name

    def _load_native(self) -> None:
        try:
            import open_clip  # type: ignore
            model, _, prep = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
            model.eval()
            self._native     = model
            self._prep       = prep
            self._tokenizer  = open_clip.get_tokenizer("ViT-B-32")
            log.info("CLIPEngine: open_clip nativo")
        except Exception:
            try:
                from transformers import CLIPModel, CLIPProcessor  # type: ignore
                self._native    = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self._tokenizer = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                log.info("CLIPEngine: transformers CLIP")
            except Exception as exc:
                log.warning("CLIPEngine sin backend: %s", exc)

    def _pre_img(self, img_rgb: np.ndarray) -> np.ndarray:
        img = cv2.resize(img_rgb, (self.IMG_SZ, self.IMG_SZ)).astype(np.float32) / 255.0
        return ((img - self.MEAN) / self.STD).transpose(2, 0, 1)

    def embed_image(self, img_rgb: np.ndarray) -> Optional[np.ndarray]:
        if self._vis:
            try:
                blob = self._pre_img(img_rgb)[np.newaxis]
                out  = self._vis.run(None, {self._inp: blob})[0][0]
                return _norm(out.astype(np.float32))
            except Exception:
                return None
        if self._native:
            return self._embed_img_native(img_rgb)
        return None

    def _embed_img_native(self, img_rgb: np.ndarray) -> Optional[np.ndarray]:
        try:
            import torch
            from PIL import Image as _PIL
            pil = _PIL.fromarray(img_rgb)
            if hasattr(self, "_prep"):
                t = self._prep(pil).unsqueeze(0)
                with torch.no_grad():
                    f = self._native.encode_image(t)
                return _norm(f.squeeze().numpy().astype(np.float32))
            else:
                inp = self._tokenizer(images=pil, return_tensors="pt")
                with torch.no_grad():
                    f = self._native.get_image_features(**inp)
                return _norm(f.squeeze().numpy().astype(np.float32))
        except Exception:
            return None

    def embed_text(self, text: str) -> Optional[np.ndarray]:
        if self._native is None:
            return None
        try:
            import torch
            if hasattr(self, "_tokenizer") and callable(getattr(self._tokenizer, "__call__", None)):
                if hasattr(self, "_prep"):  # open_clip
                    tok = self._tokenizer([text])
                    with torch.no_grad():
                        f = self._native.encode_text(tok)
                    return _norm(f.squeeze().numpy().astype(np.float32))
                else:  # transformers
                    inp = self._tokenizer(text=text, return_tensors="pt", padding=True)
                    with torch.no_grad():
                        f = self._native.get_text_features(**inp)
                    return _norm(f.squeeze().numpy().astype(np.float32))
        except Exception:
            return None
        return None


# ──────────────────────────────────────────────────────────────────────────────
# FAISS Index con Triage automático
# ──────────────────────────────────────────────────────────────────────────────
class FaissIndex:
    def __init__(self, dim: int = ARCFACE_DIM) -> None:
        import faiss
        self._dim   = dim
        self._index = faiss.IndexFlatL2(dim)
        self._names: list[str] = []

    def rebuild(self, names: list[str], embeddings: np.ndarray) -> None:
        import faiss
        self._index = faiss.IndexFlatL2(self._dim)
        if embeddings.shape[0] > 0:
            self._index.add(embeddings.astype(np.float32))
        self._names = list(names)
        gc.collect()

    def search(self, query: np.ndarray) -> tuple[str, float, str]:
        """
        Devuelve (nombre, distancia_L2, triage_tier).
        La distancia L2 se convierte a score 0-1 para calcular el tier.
        """
        if self._index.ntotal == 0:
            return "Desconocido", 999.0, "unclassified"
        q    = query.astype(np.float32).reshape(1, -1)
        D, I = self._index.search(q, 1)
        dist = float(D[0][0])

        if dist > FAISS_THRESHOLD:
            return "Desconocido", dist, "unclassified"

        # Convertir distancia L2 a confidence normalizado [0,1]
        confidence = max(0.0, 1.0 - dist / FAISS_THRESHOLD)
        tier       = _conf_to_tier(confidence)
        name       = self._names[int(I[0][0])]
        return name, confidence, tier

    def add(self, name: str, embedding: np.ndarray) -> None:
        self._index.add(embedding.astype(np.float32).reshape(1, -1))
        self._names.append(name)

    @property
    def total(self) -> int:
        return self._index.ntotal
