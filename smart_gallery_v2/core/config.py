"""
core/config.py — Configuración Centralizada del Sistema
Smart AI Gallery Organizer · Versión Comercial 2.0
"""

from __future__ import annotations
import os
from pathlib import Path

# ─── RUTAS ────────────────────────────────────────────────────────────────────
ROOT          = Path(__file__).parent.parent.resolve()
GALERIA       = ROOT / "Galería"
DIR_ENTRADA   = GALERIA / "Para Organizar"
DIR_FOTOS     = GALERIA / "Fotos"
DIR_RESULT    = GALERIA / "Resultados"
DIR_THUMBS    = ROOT / ".thumbnails"
DIR_FACES     = ROOT / ".face_crops"
DIR_MODELS    = ROOT / "models" / "onnx"
DB_PATH       = ROOT / "gallery.db"
LOG_PATH      = ROOT / "gallery.log"

for _p in [DIR_ENTRADA, DIR_FOTOS, DIR_RESULT, DIR_THUMBS, DIR_FACES, DIR_MODELS]:
    _p.mkdir(parents=True, exist_ok=True)

# ─── EXTENSIONES ──────────────────────────────────────────────────────────────
EXT_IMAGEN: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".heic"})
EXT_VIDEO:  frozenset[str] = frozenset({".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"})
EXT_TODAS:  frozenset[str] = EXT_IMAGEN | EXT_VIDEO

# ─── TRIAJE (TIERS DE CONFIANZA) ─────────────────────────────────────────────
CONF_HIGH   = 0.85   # ≥ 85%  → Bandeja SEGURA   (auto-clasificado)
CONF_MEDIUM = 0.40   # 40-85% → Bandeja DUDOSA    (pide validación)
                     # < 40%  → Bandeja SIN CLASIFICAR

# ─── PARÁMETROS DE IA ─────────────────────────────────────────────────────────
BATCH_SIZE          = 8
FAISS_THRESHOLD     = 0.65
FACE_CONF_MIN       = 0.80
YOLO_CONF_MIN       = 0.50
SSIM_THRESHOLD      = 0.70
HIST_THRESHOLD      = 0.85
ARCFACE_DIM         = 512
CLIP_DIM            = 512
CLIP_RELEVANCE_MIN  = 0.18

YOLO_CLASSES: dict[int, str] = {
    0: "persona", 1: "bicicleta", 2: "coche", 3: "moto",
    15: "gato",  16: "perro",    17: "caballo",
}

# ─── THUMBNAILS ───────────────────────────────────────────────────────────────
THUMB_SIZE    = (512, 512)
THUMB_FORMAT  = "WEBP"
THUMB_QUALITY = 82

# ─── ONNX ─────────────────────────────────────────────────────────────────────
ONNX_YOLO     = DIR_MODELS / "yolov8n.onnx"
ONNX_ARCFACE  = DIR_MODELS / "arcface_r100.onnx"
ONNX_CLIP_VIS = DIR_MODELS / "clip_visual.onnx"
ONNX_CLIP_TXT = DIR_MODELS / "clip_text.onnx"

# ─── UI ───────────────────────────────────────────────────────────────────────
APP_TITLE     = "Smart AI Gallery"
APP_ICON      = "🖼️"
MAX_LOG_LINES = 40

# ─── ENVIRONMENT ──────────────────────────────────────────────────────────────
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("CUDA_VISIBLE_DEVICES",  "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL",  "3")
os.environ.setdefault("ORT_DISABLE_ALL_LOGS",  "1")

# ─── PHASH / DEDUP / BURSTS ─────────────────────────────────────────────────
PHASH_HAMMING_THRESHOLD = 8    # Hamming distance para considerar duplicados
BURST_WINDOW_SECONDS     = 3    # Ventana temporal para agrupar ráfagas

# ─── OCR / DOCUMENTS ───────────────────────────────────────────────────────
USE_PYTESSERACT = True
OCR_MIN_TEXT_LEN = 20

# ─── Control state key
CONTROL_STATE_KEY = "engine_state"
