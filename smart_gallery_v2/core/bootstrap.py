"""
core/bootstrap.py — Inicialización del Entorno
Prepara carpetas y variables de entorno antes de arrancar.
"""

import logging
import os

from core.config import DIR_ENTRADA, DIR_FACES, DIR_FOTOS, DIR_MODELS, DIR_RESULT, DIR_THUMBS

log = logging.getLogger(__name__)


def ensure_dirs():
    """Crea la estructura de carpetas necesaria."""
    for p in [DIR_ENTRADA, DIR_FOTOS, DIR_RESULT, DIR_THUMBS, DIR_FACES, DIR_MODELS]:
        p.mkdir(parents=True, exist_ok=True)
    log.info("Estructura de carpetas verificada.")


def setup_environment():
    """Configura variables de entorno críticas."""
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")  # Forzar CPU por defecto en local
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    os.environ.setdefault("ORT_DISABLE_ALL_LOGS", "1")
