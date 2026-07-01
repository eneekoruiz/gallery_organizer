"""
core/cleanup_tools.py — Herramientas Backend para Limpieza de Disco y Compresión
Agrupamiento por phash, recomendación de mejor toma, compresión nativa y diagnósticos de almacenamiento.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import cv2
import pandas as pd
from PIL import Image, ImageOps

from core.database import DatabaseManager

log = logging.getLogger(__name__)


def get_similar_photo_groups(db: DatabaseManager, max_hamming: int = 8) -> list[pd.DataFrame]:
    """
    Agrupa fotos similares basadas en la distancia de Hamming de sus perceptual hashes (phash).
    Filtra por archivos de tipo imagen y calcula las distancias de forma eficiente.
    """
    sql = """
        SELECT id, filepath, filename, phash, quality_score, exif_date 
        FROM FileQueue 
        WHERE phash IS NOT NULL AND phash != '' AND media_type = 'image'
    """
    conn = db._connect()
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if df.empty:
        return []

    visited = set()
    groups = []

    ids = df["id"].tolist()
    filepaths = df["filepath"].tolist()
    phashes = [int(p, 16) for p in df["phash"].tolist()]

    # Comprobar la existencia física del archivo para evitar procesar fantasmas
    existing_indices = []
    for i, fp in enumerate(filepaths):
        if os.path.exists(fp):
            existing_indices.append(i)

    if not existing_indices:
        return []

    for i in existing_indices:
        if ids[i] in visited:
            continue

        current_group = [i]
        for j in existing_indices:
            if i == j or ids[j] in visited:
                continue

            # Distancia de Hamming rápida usando XOR de enteros
            dist = bin(phashes[i] ^ phashes[j]).count("1")
            if dist <= max_hamming:
                current_group.append(j)

        if len(current_group) > 1:
            for idx in current_group:
                visited.add(ids[idx])

            group_df = df.iloc[current_group].copy()
            group_ids = group_df["id"].tolist()

            # Obtener cached_thumb
            thumbs_df = db.get_files_by_ids_with_thumbs(group_ids)
            group_df = group_df.merge(thumbs_df[["id", "cached_thumb"]], on="id", how="left")
            groups.append(group_df)

    return groups


def propose_best_photo(group_df: pd.DataFrame) -> int:
    """
    Evalúa las fotos en un grupo de similares y propone el ID de la mejor toma
    basándose en la nitidez (quality_score) y en el peso en disco.
    """
    best_id = None
    best_score = -1.0

    for _, row in group_df.iterrows():
        file_id = row["id"]
        filepath = row["filepath"]
        q_score = float(row.get("quality_score", 0.0))

        # Obtener el tamaño del archivo
        size_mb = 0.0
        try:
            if os.path.exists(filepath):
                size_mb = os.path.getsize(filepath) / (1024.0 * 1024.0)
        except OSError:
            pass

        # Ponderación premium: 70% calidad (nitidez/enfoque), 30% tamaño/información del archivo
        score = q_score * 0.7 + min(0.3, (size_mb / 15.0) * 0.3)

        if score > best_score:
            best_score = score
            best_id = file_id

    return best_id or group_df.iloc[0]["id"]


def compress_image(
    input_path: str | Path, output_path: str | Path, quality: int = 75, scale: float = 0.8
) -> bool:
    """
    Comprime una imagen en formato JPEG/WebP reduciendo su calidad y dimensiones.
    Mantiene la orientación EXIF correcta.
    """
    try:
        p_in = Path(input_path)
        p_out = Path(output_path)

        if not p_in.exists():
            return False

        with Image.open(p_in) as img:
            # Auto-rotar según orientación EXIF
            img = ImageOps.exif_transpose(img)

            # Convertir a RGB si es necesario (ej. PNG con alpha a JPG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Escalar si es necesario
            if scale < 1.0:
                new_w = int(img.width * scale)
                new_h = int(img.height * scale)
                # Asegurar dimensiones mínimas razonables
                if new_w > 100 and new_h > 100:
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Guardar comprimida
            img.save(p_out, "JPEG", quality=quality, optimize=True)
            return True

    except Exception as e:
        log.error(f"Error comprimiendo imagen {input_path}: {e}")
        return False


def compress_video_opencv(
    input_path: str | Path, output_path: str | Path, scale: float = 0.5, target_fps: int = 24
) -> bool:
    """
    Comprime un vídeo usando OpenCV nativo (VideoCapture y VideoWriter).
    Reduce la resolución y opcionalmente los FPS para rebajar drásticamente el peso.
    """
    try:
        p_in = Path(input_path)
        p_out = Path(output_path)

        if not p_in.exists():
            return False

        cap = cv2.VideoCapture(str(p_in))
        if not cap.isOpened():
            return False

        orig_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Calcular dimensiones escaladas
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        # Forzar números pares para compatibilidad con codificadores de vídeo
        new_w = (new_w // 2) * 2
        new_h = (new_h // 2) * 2

        if new_w < 16 or new_h < 16:
            cap.release()
            return False

        # Probar codec mp4v (universal)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = min(float(target_fps), orig_fps)

        out = cv2.VideoWriter(str(p_out), fourcc, fps, (new_w, new_h))
        if not out.isOpened():
            # Caída a XVID si falla
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            out = cv2.VideoWriter(str(p_out), fourcc, fps, (new_w, new_h))

        if not out.isOpened():
            cap.release()
            return False

        step = max(1, int(orig_fps / fps))
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_idx % step == 0:
                resized = cv2.resize(frame, (new_w, new_h))
                out.write(resized)
            frame_idx += 1

        cap.release()
        out.release()
        return True

    except Exception as e:
        log.error(f"Error comprimiendo vídeo {input_path}: {e}")
        return False


def get_cleanup_recommendations(db: DatabaseManager) -> dict[str, Any]:
    """
    Escanea la base de datos y el disco para sugerir recomendaciones y oportunidades
    de ahorro de almacenamiento.
    """
    stats = {
        "total_files": 0,
        "total_images": 0,
        "total_videos": 0,
        "total_size_mb": 0.0,
        "large_files": [],
        "blurry_photos": [],
        "potential_savings_mb": 0.0,
    }

    # 1. Obtener todos los archivos procesados
    sql = "SELECT id, filepath, filename, media_type, quality_score, status FROM FileQueue"
    conn = db._connect()
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if df.empty:
        return stats

    stats["total_files"] = len(df)
    stats["total_images"] = len(df[df["media_type"] == "image"])
    stats["total_videos"] = len(df[df["media_type"] == "video"])

    # Obtener tamaños reales y recopilar datos
    large_list = []
    blurry_list = []
    total_size = 0.0

    for _, row in df.iterrows():
        filepath = row["filepath"]
        if not os.path.exists(filepath):
            continue

        try:
            sz_bytes = os.path.getsize(filepath)
            sz_mb = sz_bytes / (1024.0 * 1024.0)
            total_size += sz_mb

            # Registrar para archivos grandes (> 5MB para imágenes, > 15MB para vídeos)
            is_large_img = row["media_type"] == "image" and sz_mb > 5.0
            is_large_vid = row["media_type"] == "video" and sz_mb > 15.0
            if is_large_img or is_large_vid:
                large_list.append(
                    {
                        "id": row["id"],
                        "filepath": filepath,
                        "filename": row["filename"],
                        "media_type": row["media_type"],
                        "size_mb": sz_mb,
                        "quality_score": row.get("quality_score", 0.0),
                    }
                )

            # Registrar para fotos borrosas (quality_score < 0.15 y no es vídeo)
            if row["media_type"] == "image" and float(row.get("quality_score", 0.0)) < 0.15:
                blurry_list.append(
                    {
                        "id": row["id"],
                        "filepath": filepath,
                        "filename": row["filename"],
                        "size_mb": sz_mb,
                        "quality_score": row.get("quality_score", 0.0),
                    }
                )
        except OSError:
            pass

    stats["total_size_mb"] = total_size

    # Ordenar listas
    stats["large_files"] = sorted(large_list, key=lambda x: x["size_mb"], reverse=True)[:15]
    stats["blurry_photos"] = sorted(blurry_list, key=lambda x: x["size_mb"], reverse=True)[:15]

    # Calcular ahorro potencial estimado por duplicados y similares
    duplicates = db.get_duplicate_groups()
    dupe_savings = 0.0
    for g_df in duplicates:
        # Sumar el tamaño de todos menos el primero
        for idx, row in g_df.iterrows():
            if idx == 0:
                continue
            fp = row["filepath"]
            if os.path.exists(fp):
                dupe_savings += os.path.getsize(fp) / (1024.0 * 1024.0)

    stats["potential_savings_mb"] = dupe_savings

    return stats
