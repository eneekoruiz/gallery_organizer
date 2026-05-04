"""
core/video_processor.py — Smart Keyframe Extraction
SSIM + Histograma HSV → solo frames donde cambia la escena.
Evita procesar segundos inútiles de vídeo.
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import Generator, Optional

import cv2
import numpy as np

from core.config import HIST_THRESHOLD, SSIM_THRESHOLD

log = logging.getLogger(__name__)


def _hist_corr(a: np.ndarray, b: np.ndarray) -> float:
    hsv_a, hsv_b = cv2.cvtColor(a, cv2.COLOR_BGR2HSV), cv2.cvtColor(b, cv2.COLOR_BGR2HSV)
    scores = []
    for ch in range(3):
        ha = cv2.calcHist([hsv_a], [ch], None, [64], [0, 256])
        hb = cv2.calcHist([hsv_b], [ch], None, [64], [0, 256])
        cv2.normalize(ha, ha); cv2.normalize(hb, hb)
        scores.append(float(cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL)))
    return float(np.mean(scores))


def _ssim_fast(a: np.ndarray, b: np.ndarray) -> float:
    a_l = cv2.cvtColor(a, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float64)
    b_l = cv2.cvtColor(b, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float64)
    C1, C2 = 6.5025, 58.5225
    mu_a = cv2.GaussianBlur(a_l, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(b_l, (11, 11), 1.5)
    s_a2 = cv2.GaussianBlur(a_l**2, (11,11), 1.5) - mu_a**2
    s_b2 = cv2.GaussianBlur(b_l**2, (11,11), 1.5) - mu_b**2
    s_ab = cv2.GaussianBlur(a_l*b_l, (11,11), 1.5) - mu_a*mu_b
    num  = (2*mu_a*mu_b + C1) * (2*s_ab + C2)
    den  = (mu_a**2 + mu_b**2 + C1) * (s_a2 + s_b2 + C2)
    return float((num / (den + 1e-8)).mean())


def _is_scene_change(prev: np.ndarray, curr: np.ndarray) -> bool:
    s = (160, 90)
    p, c = cv2.resize(prev, s), cv2.resize(curr, s)
    if _hist_corr(p, c) < HIST_THRESHOLD:
        return True
    return _ssim_fast(p, c) < SSIM_THRESHOLD


class VideoKeyframeExtractor:
    def __init__(self, sample_interval: int = 15, max_keyframes: int = 50) -> None:
        self._interval = sample_interval
        self._max_kf   = max_keyframes

    def extract(self, video_path: str | Path) -> list[np.ndarray]:
        path = Path(video_path)
        if not path.exists():
            return []
        keyframes: list[np.ndarray] = []
        prev: Optional[np.ndarray]  = None
        idx = 0
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return []
        try:
            while len(keyframes) < self._max_kf:
                ret, frame = cap.read()
                if not ret:
                    break
                idx += 1
                if idx % self._interval != 0:
                    continue
                if prev is None or _is_scene_change(prev, frame):
                    keyframes.append(frame.copy())
                    prev = frame
        finally:
            cap.release()
            gc.collect()
        log.info("Vídeo %s → %d keyframes", path.name, len(keyframes))
        return keyframes

    def stream(self, video_path: str | Path) -> Generator[tuple[int, np.ndarray], None, None]:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return
        fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
        prev: Optional[np.ndarray] = None
        idx = kf_count = 0
        try:
            while kf_count < self._max_kf:
                ret, frame = cap.read()
                if not ret:
                    break
                idx += 1
                if idx % self._interval != 0:
                    continue
                if prev is None or _is_scene_change(prev, frame):
                    yield int((idx / fps) * 1000), frame.copy()
                    prev = frame
                    kf_count += 1
        finally:
            cap.release()
            gc.collect()
