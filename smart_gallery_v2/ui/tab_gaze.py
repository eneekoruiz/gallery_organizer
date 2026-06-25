"""
ui/tab_gaze.py — Interfaz Premium de Detección de Miradas y Contacto Visual
Permite visualizar la mirada de las personas mediante flechas de vector,
marcar manualmente a las personas que no están mirando y corregir/guardar el estado en la base de datos.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import cv2
import pandas as pd
import streamlit as st

from core.database import DatabaseManager
from core.gaze_detector import draw_gaze_overlay, estimate_gaze_from_landmarks


def render_gaze_management(db: DatabaseManager) -> None:
    st.markdown(
        """
    <div style='margin-bottom:18px'>
      <h3 style='margin:0;font-weight:800;color:#eef0f8;'>👁️ Análisis de Miradas y Contacto Visual</h3>
      <p style='color:#606880;margin:4px 0 0;font-size:14px'>
        Visualiza la orientación tridimensional de la mirada en tus fotos. Puedes corregir si alguien no está mirando para afinar la clasificación.
      </p>
    </div>""",
        unsafe_allow_html=True,
    )

    # 1. Obtener todas las imágenes de la cola de la base de datos
    sql = """
        SELECT id, filepath, filename, status 
        FROM FileQueue 
        WHERE media_type = 'image' 
        ORDER BY id DESC
    """
    conn = db._connect()
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if df.empty:
        st.info("No hay imágenes procesadas en la galería para analizar miradas.")
        return

    # 2. Selección de Archivo (Selector Visual + Selectbox)
    st.markdown("##### 🔍 Selecciona una imagen para inspeccionar")

    # Selector visual: Mostrar una tira de miniaturas recientes
    recent_ids = df["id"].tolist()[:8]
    thumbs_df = db.get_files_by_ids_with_thumbs(recent_ids)

    st.write("Fotos recientes:")
    t_cols = st.columns(len(thumbs_df))
    selected_file_id = None

    for col, (_, t_row) in zip(t_cols, thumbs_df.iterrows()):
        with col:
            th = t_row.get("cached_thumb")
            if th and Path(th).exists():
                st.image(th, use_container_width=True)
            if st.button("🔍 Ver", key=f"sel_gz_t_{t_row['id']}"):
                st.session_state["gaze_selected_id"] = t_row["id"]
                st.rerun()

    # Dropdown de búsqueda principal
    choices = []
    for _, row in df.iterrows():
        choices.append({
            "id": row["id"],
            "filepath": row["filepath"],
            "label": f"#{row['id']} - {row['filename']} ({row['status']})"
        })

    # Determinar index seleccionado por defecto
    default_idx = 0
    sess_id = st.session_state.get("gaze_selected_id")
    if sess_id:
        for idx, c in enumerate(choices):
            if c["id"] == sess_id:
                default_idx = idx
                break

    selected_idx = st.selectbox(
        "O busca en toda tu galería por nombre de archivo:",
        range(len(choices)),
        index=default_idx,
        format_func=lambda x: choices[x]["label"]
    )

    current_choice = choices[selected_idx]
    file_id = current_choice["id"]
    filepath = current_choice["filepath"]

    st.session_state["gaze_selected_id"] = file_id

    if not os.path.exists(filepath):
        st.error("El archivo físico no se encuentra en el disco.")
        return

    st.markdown("---")

    # 3. Asegurar y calcular landmarks de forma lazy si faltan
    dets = _ensure_gaze_calculated(db, file_id, filepath)

    # 4. Renderizar imagen con BBox y Vector de mirada
    st.markdown(f"##### 🖼️ Imagen Inspeccionada: `{Path(filepath).name}`")

    img_bgr = cv2.imread(filepath)
    if img_bgr is None:
        st.error("No se pudo cargar la imagen para renderizar el overlay.")
        return

    h, w = img_bgr.shape[:2]
    disp_w = 900
    scale = disp_w / w
    disp_h = int(h * scale)

    img_resized = cv2.resize(img_bgr, (disp_w, disp_h))

    # Dibujar la mirada usando el detector
    disp_overlay = draw_gaze_overlay(img_resized, dets, scale=scale)

    col_img, col_info = st.columns([7, 3])

    with col_img:
        st.image(cv2.cvtColor(disp_overlay, cv2.COLOR_BGR2RGB), use_container_width=True)

    with col_info:
        st.markdown(f"📋 **Detecciones ({len(dets)})**")
        if not dets:
            st.info("No se han detectado caras de personas en esta foto.")
        else:
            for det in dets:
                name = det["assigned_name"]
                eye_contact = bool(det.get("eye_contact", True))
                gaze_dir = det.get("gaze_direction", "front")

                with st.container():
                    status_html = "<span style='color:#34d399'>👁️ Mirando a cámara</span>" if eye_contact else f"<span style='color:#f87171'>❌ Mirando a la {gaze_dir}</span>"
                    st.markdown(
                        f"<div style='border:1px solid #1c1f2e;padding:12px;border-radius:12px;margin-bottom:10px;background:#10121a;'>"
                        f"👤 <b>{name}</b><br>"
                        f"📍 Estado: {status_html}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    # Botón interactivo para cambiar mirada
                    if eye_contact:
                        if st.button("🔴 Marcar como 'No está mirando'", key=f"tg_gaze_{det['id']}", use_container_width=True):
                            db.update_detection_gaze(det["id"], False, "away")
                            st.toast(f"Corregida la mirada de {name}: No está mirando")
                            st.rerun()
                    else:
                        if st.button("🟢 Marcar como 'Sí está mirando'", key=f"tg_gaze_{det['id']}", use_container_width=True):
                            db.update_detection_gaze(det["id"], True, "front")
                            st.toast(f"Corregida la mirada de {name}: Mirando a cámara")
                            st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

def _ensure_gaze_calculated(db: DatabaseManager, file_id: int, filepath: str) -> list[dict]:
    """
    Función de cálculo perezoso (lazy): si la imagen tiene detecciones pero
    ninguna tiene landmarks analizados, carga el modelo al vuelo, calcula
    los landmarks de RetinaFace/DeepFace y actualiza la BD de forma transparente.
    """
    dets = db.get_detections_for_file(file_id)
    if not dets:
        return []

    # Comprobar si falta landmarks_json en alguna detección
    needs_calc = any(det.get("landmarks_json") is None for det in dets)
    if needs_calc and os.path.exists(filepath):
        img_bgr = cv2.imread(filepath)
        if img_bgr is not None:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

            # Cargar ArcFace al vuelo para extraer landmarks
            from core.ai_engines import ArcFaceEngine
            arcface = ArcFaceEngine()
            faces = arcface.get_faces(img_rgb)

            if faces:
                for bbox, _emb, _conf, landmarks in faces:
                    # Emparejar con bboxes existentes de la base de datos (por IoU)
                    best_det_id = None
                    best_iou = 0.0
                    for det in dets:
                        db_bbox = det.get("bbox_json")
                        if isinstance(db_bbox, str):
                            db_bbox = json.loads(db_bbox)
                        if not db_bbox:
                            continue

                        iou = _calculate_iou(bbox, db_bbox)
                        if iou > best_iou:
                            best_iou = iou
                            best_det_id = det["id"]

                    # Si coincide razonablemente (>40% IoU)
                    if best_det_id and best_iou > 0.4:
                        eye_contact, gaze_dir, _, landmarks_list = estimate_gaze_from_landmarks(landmarks)
                        db.update_detection_gaze_full(best_det_id, eye_contact, gaze_dir, landmarks_list)

                # Recargar detecciones actualizadas
                dets = db.get_detections_for_file(file_id)

    return dets

def _calculate_iou(box1: dict, box2: dict) -> float:
    """Calcula la Intersección sobre la Unión (IoU) entre dos bounding boxes."""
    t1 = float(box1.get("top", 0))
    r1 = float(box1.get("right", 0))
    b1 = float(box1.get("bottom", 0))
    l1 = float(box1.get("left", 0))

    t2 = float(box2.get("top", 0))
    r2 = float(box2.get("right", 0))
    b2 = float(box2.get("bottom", 0))
    l2 = float(box2.get("left", 0))

    inter_t = max(t1, t2)
    inter_b = min(b1, b2)
    inter_l = max(l1, l2)
    inter_r = min(r1, r2)

    if inter_b <= inter_t or inter_r <= inter_l:
        return 0.0

    inter_area = (inter_b - inter_t) * (inter_r - inter_l)
    area1 = (b1 - t1) * (r1 - l1)
    area2 = (b2 - t2) * (r2 - l2)

    union_area = area1 + area2 - inter_area
    if union_area <= 0:
        return 0.0

    return inter_area / union_area
