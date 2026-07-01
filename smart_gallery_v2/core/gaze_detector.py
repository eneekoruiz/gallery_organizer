"""
core/gaze_detector.py — Estimación de Contacto Visual y Vector de Mirada
Calcula la orientación de la cabeza y mirada usando los 5 puntos faciales clave.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import cv2
import numpy as np

log = logging.getLogger(__name__)


def estimate_gaze_from_landmarks(
    landmarks: Any,
) -> tuple[bool, str, tuple[float, float], list[list[float]]]:
    """
    Analiza la posición relativa de la nariz respecto al centro de los ojos y la boca
    para determinar el contacto visual y la dirección tridimensional de la mirada.

    Formatos soportados:
      - list de 5 puntos: [[x, y], ...]
      - dict: {"left_eye": [x,y], "right_eye": [x,y], "nose": [x,y], "mouth_left": [x,y], "mouth_right": [x,y]}

    Retorna: (eye_contact: bool, gaze_dir: str, (gaze_dx, gaze_dy): tuple, landmarks_list: list)
    """
    try:
        if not landmarks:
            return True, "front", (0.0, 0.0), []

        # Normalizar landmarks a diccionario con claves estándar
        ld = {}
        if isinstance(landmarks, dict):
            ld = landmarks
        elif isinstance(landmarks, list) and len(landmarks) == 5:
            # Mapeo por orden tradicional: leye, reye, nose, mouth_l, mouth_r
            ld = {
                "left_eye": landmarks[0],
                "right_eye": landmarks[1],
                "nose": landmarks[2],
                "mouth_left": landmarks[3],
                "mouth_right": landmarks[4],
            }
        else:
            return True, "front", (0.0, 0.0), []

        # Extraer puntos individuales asegurando tipo float y [x, y]
        def to_point(p) -> Optional[list[float]]:
            if not p:
                return None
            if isinstance(p, dict):
                return [float(p.get("x", 0)), float(p.get("y", 0))]
            return [float(p[0]), float(p[1])]

        le = to_point(ld.get("left_eye"))
        re = to_point(ld.get("right_eye"))
        nose = to_point(ld.get("nose"))
        ml = to_point(ld.get("mouth_left"))
        mr = to_point(ld.get("mouth_right"))

        if not (le and re and nose and ml and mr):
            return True, "front", (0.0, 0.0), []

        # Calcular punto medio de ojos y boca
        eye_cx = (le[0] + re[0]) / 2.0
        eye_cy = (le[1] + re[1]) / 2.0
        mouth_cx = (ml[0] + mr[0]) / 2.0
        mouth_cy = (ml[1] + mr[1]) / 2.0

        # Centro de la cara
        face_cx = (eye_cx + mouth_cx) / 2.0
        face_cy = (eye_cy + mouth_cy) / 2.0

        # Vector de desviación del eje de la nariz respecto al centro
        dx = nose[0] - face_cx
        dy = nose[1] - face_cy

        # Escalar el vector por la distancia entre los ojos (normalización de escala)
        eye_dist = ((re[0] - le[0]) ** 2 + (re[1] - le[1]) ** 2) ** 0.5
        if eye_dist < 1e-6:
            eye_dist = 1.0

        gaze_dx = dx / eye_dist
        gaze_dy = dy / eye_dist

        # Umbral para decidir contacto visual
        # Si la nariz está desplazada horizontal o verticalmente, la cabeza está girada
        thresh = 0.14
        eye_contact = True
        gaze_dir = "front"

        if abs(gaze_dx) > thresh or abs(gaze_dy) > thresh:
            eye_contact = False
            # Determinar cuadrante principal
            if abs(gaze_dx) > abs(gaze_dy):
                gaze_dir = "right" if gaze_dx > 0 else "left"
            else:
                gaze_dir = "down" if gaze_dy > 0 else "up"

        landmarks_list = [le, re, nose, ml, mr]
        return eye_contact, gaze_dir, (gaze_dx, gaze_dy), landmarks_list

    except Exception as e:
        log.error(f"Error estimando mirada: {e}")
        return True, "front", (0.0, 0.0), []


def draw_gaze_overlay(
    img_bgr: np.ndarray, detections: list[dict], scale: float = 1.0
) -> np.ndarray:
    """
    Dibuja en la imagen (BGR) las cajas de las caras, los landmarks y los vectores de la mirada.
    """
    disp = img_bgr.copy()
    h_img, w_img = disp.shape[:2]

    for det in detections:
        try:
            # 1. Parsear Bounding Box
            bbox = det.get("bbox_json") or det.get("bbox")
            if isinstance(bbox, str):
                bbox = json.loads(bbox)
            if not bbox:
                continue

            top = int(bbox.get("top", 0) * scale)
            bot = int(bbox.get("bottom", 0) * scale)
            left = int(bbox.get("left", 0) * scale)
            right = int(bbox.get("right", 0) * scale)

            # 2. Leer estado de contacto visual (con override)
            eye_contact = bool(det.get("eye_contact", True))
            gaze_dir = det.get("gaze_direction", "front")

            # Color del marcador: Verde para contacto visual, Rojo para mirando a otro lado
            color = (52, 211, 153) if eye_contact else (248, 113, 113)  # BGR: Teal vs Coral

            # Cambiar formato a BGR de OpenCV
            color_bgr = (int(color[2]), int(color[1]), int(color[0]))

            # Dibujar rectángulo de la cara
            cv2.rectangle(disp, (left, top), (right, bot), color_bgr, 2)

            # 3. Parsear Landmarks
            landmarks = det.get("landmarks_json") or det.get("landmarks")
            if isinstance(landmarks, str):
                landmarks = json.loads(landmarks)

            if landmarks and isinstance(landmarks, list) and len(landmarks) == 5:
                # Dibujar los 5 puntos faciales
                for p in landmarks:
                    px = int(p[0] * scale)
                    py = int(p[1] * scale)
                    cv2.circle(disp, (px, py), 3, (255, 255, 255), -1)

                # Calcular vector de mirada
                le, re, nose, ml, mr = landmarks
                eye_cx = (le[0] + re[0]) / 2.0
                eye_cy = (le[1] + re[1]) / 2.0
                mouth_cx = (ml[0] + mr[0]) / 2.0
                mouth_cy = (ml[1] + mr[1]) / 2.0

                face_cx = (eye_cx + mouth_cx) / 2.0
                face_cy = (eye_cy + mouth_cy) / 2.0

                # Punto inicial: Nariz
                start_x = int(nose[0] * scale)
                start_y = int(nose[1] * scale)

                # Vector base
                vx = nose[0] - face_cx
                vy = nose[1] - face_cy

                eye_dist = ((re[0] - le[0]) ** 2 + (re[1] - le[1]) ** 2) ** 0.5
                if eye_dist < 1e-6:
                    eye_dist = 1.0

                # Si hay contacto visual, el vector de mirada apunta al frente (círculo objetivo)
                if eye_contact and gaze_dir == "front":
                    # Dibujar un círculo indicador en la nariz indicando contacto directo
                    cv2.circle(disp, (start_x, start_y), int(5 * scale), color_bgr, 2)
                    cv2.circle(disp, (start_x, start_y), int(1 * scale), color_bgr, -1)
                else:
                    # Si no hay contacto visual, extender el vector para dibujar una flecha
                    # Longitud proporcional a la cara
                    len_factor = 2.5
                    end_x = int((nose[0] + vx * len_factor) * scale)
                    end_y = int((nose[1] + vy * len_factor) * scale)

                    # Limitar coordenadas dentro de la imagen
                    end_x = max(0, min(w_img - 1, end_x))
                    end_y = max(0, min(h_img - 1, end_y))

                    # Dibujar la flecha de mirada
                    cv2.arrowedLine(
                        disp, (start_x, start_y), (end_x, end_y), color_bgr, 3, tipLength=0.35
                    )

            # 4. Rotular
            label = f"{det.get('assigned_name', 'Desconocido')}"
            status_text = "Mirando" if eye_contact else f"No Mirando ({gaze_dir})"
            full_label = f"{label} - {status_text}"

            (tw, th), _ = cv2.getTextSize(full_label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(disp, (left, top - th - 10), (left + tw + 10, top), color_bgr, -1)
            cv2.putText(
                disp,
                full_label,
                (left + 5, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
            )

        except Exception as ex:
            log.debug(f"Fallo al dibujar overlay de mirada: {ex}")

    return disp
