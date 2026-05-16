"""
core/bootstrap.py — Inicialización del Entorno
Prepara carpetas y variables de entorno antes de arrancar.
"""

import logging
import os

from core.config import (
    DIR_ENTRADA,
    DIR_FACES,
    DIR_FOTOS,
    DIR_MODELS,
    DIR_RESULT,
    DIR_THUMBS,
    ONNX_ARCFACE,
    ONNX_CLIP_TXT,
    ONNX_CLIP_VIS,
    ONNX_YOLO,
)

log = logging.getLogger(__name__)


def ensure_dirs():
    """Crea la estructura de carpetas necesaria."""
    for p in [DIR_ENTRADA, DIR_FOTOS, DIR_RESULT, DIR_THUMBS, DIR_FACES, DIR_MODELS]:
        p.mkdir(parents=True, exist_ok=True)
    log.info("Estructura de carpetas verificada.")


def check_models():
    """Verifica si los modelos ONNX están presentes."""
    models = {
        "YOLOv8": ONNX_YOLO,
        "ArcFace": ONNX_ARCFACE,
        "CLIP Visual": ONNX_CLIP_VIS,
        "CLIP Text": ONNX_CLIP_TXT,
    }
    missing = []
    for name, path in models.items():
        if not path.exists():
            missing.append(name)

    if missing:
        log.warning(
            "⚠️ Faltan modelos en models/onnx/: %s. La IA no funcionará hasta descargarlos.",
            ", ".join(missing),
        )
    else:
        log.info("✅ Todos los modelos ONNX detectados.")


def setup_environment():
    """Configura variables de entorno críticas."""
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")  # Forzar CPU por defecto en local
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    os.environ.setdefault("ORT_DISABLE_ALL_LOGS", "1")
    check_models()
