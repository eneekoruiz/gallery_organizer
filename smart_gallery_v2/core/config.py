"""
core/config.py — Constantes y Configuración Centralizada
Este archivo solo define valores estáticos. No tiene efectos secundarios.
"""

from __future__ import annotations

from pathlib import Path

# ─── RUTAS ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()
GALERIA = ROOT / "Galería"
DIR_ENTRADA = GALERIA / "Para Organizar"
DIR_FOTOS = GALERIA / "Fotos"
DIR_RESULT = GALERIA / "Resultados"
DIR_THUMBS = ROOT / ".thumbnails"
DIR_FACES = ROOT / ".face_crops"
DIR_MODELS = ROOT / "models" / "onnx"
DB_PATH = ROOT / "gallery.db"
LOG_PATH = ROOT / "gallery.log"

# ─── EXTENSIONES ──────────────────────────────────────────────────────────────
EXT_IMAGEN: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".heic"})
EXT_VIDEO: frozenset[str] = frozenset({".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"})
EXT_TODAS: frozenset[str] = EXT_IMAGEN | EXT_VIDEO

# ─── TRIAJE (TIERS DE CONFIANZA) ─────────────────────────────────────────────
CONF_HIGH = 0.85
CONF_MEDIUM = 0.40

# ─── PARÁMETROS DE IA ─────────────────────────────────────────────────────────
BATCH_SIZE = 8
FAISS_THRESHOLD = 0.65
FACE_CONF_MIN = 0.80
YOLO_CONF_MIN = 0.50
SSIM_THRESHOLD = 0.70
HIST_THRESHOLD = 0.85
ARCFACE_DIM = 512
CLIP_DIM = 512
CLIP_RELEVANCE_MIN = 0.18

YOLO_CLASSES: dict[int, str] = {
    0: "persona",
    1: "bicicleta",
    2: "coche",
    3: "moto",
    15: "gato",
    16: "perro",
    17: "caballo",
}

# ─── THUMBNAILS ───────────────────────────────────────────────────────────────
THUMB_SIZE = (512, 512)
THUMB_FORMAT = "WEBP"
THUMB_QUALITY = 82

# ─── ONNX ─────────────────────────────────────────────────────────────────────
ONNX_YOLO = DIR_MODELS / "yolov8n.onnx"
ONNX_ARCFACE = DIR_MODELS / "arcface_r100.onnx"
ONNX_CLIP_VIS = DIR_MODELS / "clip_visual.onnx"
ONNX_CLIP_TXT = DIR_MODELS / "clip_text.onnx"

# ─── UI ───────────────────────────────────────────────────────────────────────
APP_TITLE = "Smart AI Gallery"
APP_ICON = "🖼️"
MAX_LOG_LINES = 40

# ─── PHASH / DEDUP / BURSTS ─────────────────────────────────────────────────
PHASH_HAMMING_THRESHOLD = 8
BURST_WINDOW_SECONDS = 3

# ─── OCR / DOCUMENTS ───────────────────────────────────────────────────────
USE_PYTESSERACT = True
OCR_MIN_TEXT_LEN = 20

# ─── CONTROL STATE
CONTROL_STATE_KEY = "engine_state"
