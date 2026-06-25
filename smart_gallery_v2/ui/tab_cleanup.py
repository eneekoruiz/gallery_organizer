"""
ui/tab_cleanup.py — Bandeja de Limpieza Inteligente & Herramientas de Compresión
Detección de duplicados, comparación y recomendación de fotos similares, compresión in-situ de imágenes y vídeos, y sugerencias de almacenamiento.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from core.cleanup_tools import (
    compress_image,
    compress_video_opencv,
    get_cleanup_recommendations,
    get_similar_photo_groups,
    propose_best_photo,
)
from core.database import DatabaseManager


def render_cleanup(db: DatabaseManager) -> None:
    st.markdown(
        """
    <div style='margin-bottom:18px'>
      <h3 style='margin:0;font-weight:800;color:#eef0f8;'>🧹 Centro de Limpieza y Optimización</h3>
      <p style='color:#606880;margin:4px 0 0;font-size:14px'>
        Analiza, comprime y elimina archivos redundantes o de baja calidad para liberar almacenamiento en tu galería.
      </p>
    </div>""",
        unsafe_allow_html=True,
    )

    # 4 Sub-pestañas premium
    tab_recs, tab_dupes, tab_similar, tab_compress = st.tabs([
        "💡 Recomendaciones y Diagnóstico",
        "👯 Duplicados Exactos",
        "📸 Comparación de Similares",
        "🗜️ Compresión de Archivos"
    ])

    with tab_recs:
        _render_recommendations(db)

    with tab_dupes:
        _render_duplicates(db)

    with tab_similar:
        _render_similar(db)

    with tab_compress:
        _render_compression(db)

def _render_recommendations(db: DatabaseManager) -> None:
    st.markdown("#### 📊 Diagnóstico del Almacenamiento")
    recs = get_cleanup_recommendations(db)

    # Tarjetas de métricas
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="mc"><div class="mc-l">Total Archivos</div>'
            f'<div class="mc-v c-blue">{recs["total_files"]}</div>'
            f'<div style="font-size:11px;color:#505570">{recs["total_images"]} imágenes · {recs["total_videos"]} vídeos</div></div>',
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f'<div class="mc"><div class="mc-l">Espacio Ocupado</div>'
            f'<div class="mc-v c-purple">{recs["total_size_mb"]:.1f} MB</div>'
            f'<div style="font-size:11px;color:#505570">En la carpeta organizada</div></div>',
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f'<div class="mc"><div class="mc-l">Ahorro en Duplicados</div>'
            f'<div class="mc-v c-green">{recs["potential_savings_mb"]:.1f} MB</div>'
            f'<div style="font-size:11px;color:#505570">Recuperables de inmediato</div></div>',
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f'<div class="mc"><div class="mc-l">Fotos Borrosas</div>'
            f'<div class="mc-v c-amber">{len(recs["blurry_photos"])}</div>'
            f'<div style="font-size:11px;color:#505570">Calidad menor al 15%</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Botón de limpieza rápida
    if recs["potential_savings_mb"] > 0 or len(recs["blurry_photos"]) > 0:
        st.markdown(
            "<div style='background:rgba(99,102,241,0.05);border:1px dashed #6366f1;border-radius:12px;padding:16px;margin-bottom:20px;'>"
            "<h5 style='margin:0 0 6px 0;color:#eef0f8;'>🧹 Limpieza Rápida en Un Clic</h5>"
            "<p style='margin:0 0 12px 0;font-size:13px;color:#a0a8c0;'>Elimina automáticamente todos los duplicados exactos (dejando la versión recomendada) y fotos extremadamente borrosas.</p>"
            "</div>",
            unsafe_allow_html=True
        )
        if st.button("🚀 Ejecutar Limpieza Rápida", type="primary", key="quick_cleanup_btn"):
            with st.spinner("Limpiando..."):
                # Borrar duplicados secundarios
                dupe_groups = db.get_duplicate_groups()
                deleted_dupes = 0
                for g_df in dupe_groups:
                    best_id = propose_best_photo(g_df)
                    for _, row in g_df.iterrows():
                        if row["id"] != best_id:
                            _delete_file_silent(db, row["id"], row["filepath"])
                            deleted_dupes += 1

                # Borrar fotos muy borrosas (< 0.05 de calidad)
                deleted_blurry = 0
                for photo in recs["blurry_photos"]:
                    if photo["quality_score"] < 0.05:
                        _delete_file_silent(db, photo["id"], photo["filepath"])
                        deleted_blurry += 1

                st.success(f"¡Limpieza completada! Se eliminaron {deleted_dupes} duplicados y {deleted_blurry} fotos inservibles.")
                st.rerun()

    # Listados detallados de archivos grandes y borrosos
    col_large, col_blurry = st.columns(2)

    with col_large:
        st.markdown("<h5 style='margin:0 0 10px 0;'>🔥 Archivos Más Pesados</h5>", unsafe_allow_html=True)
        if not recs["large_files"]:
            st.info("No hay archivos grandes detectados.")
        else:
            for item in recs["large_files"]:
                with st.container():
                    c_img, c_info = st.columns([1, 4])
                    with c_img:
                        th = db.get_files_by_ids_with_thumbs([item["id"]]).iloc[0].get("cached_thumb")
                        if th and Path(th).exists():
                            st.image(th, use_container_width=True)
                        else:
                            st.text("🎥" if item["media_type"] == "video" else "🖼️")
                    with c_info:
                        st.markdown(
                            f"**{item['filename']}**<br>"
                            f"<span style='font-size:12px;color:#fbbf24'>{item['size_mb']:.1f} MB</span> · "
                            f"<span style='font-size:11px;color:#606880'>Calidad: {item['quality_score']*100:.0f}%</span>",
                            unsafe_allow_html=True
                        )
                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            if st.button("🗑 Borrar", key=f"del_lrg_{item['id']}"):
                                _delete_file(db, item["id"], item["filepath"])
                                st.rerun()
                        with col_b2:
                            if item["media_type"] == "video":
                                st.caption("Ve a 'Compresión' para reducir este vídeo")
                st.divider()

    with col_blurry:
        st.markdown("<h5 style='margin:0 0 10px 0;'>🌫️ Fotos de Muy Baja Calidad / Borrosas</h5>", unsafe_allow_html=True)
        if not recs["blurry_photos"]:
            st.success("¡Tu galería no tiene fotos borrosas detectadas! Excelente.")
        else:
            for item in recs["blurry_photos"]:
                with st.container():
                    c_img, c_info = st.columns([1, 4])
                    with c_img:
                        th = db.get_files_by_ids_with_thumbs([item["id"]]).iloc[0].get("cached_thumb")
                        if th and Path(th).exists():
                            st.image(th, use_container_width=True)
                    with c_info:
                        st.markdown(
                            f"**{Path(item['filepath']).name}**<br>"
                            f"<span style='font-size:12px;color:#f87171'>Calidad: {item['quality_score']*100:.1f}%</span> · "
                            f"<span style='font-size:11px;color:#606880'>{item['size_mb']:.2f} MB</span>",
                            unsafe_allow_html=True
                        )
                        if st.button("🗑 Eliminar toma borrosa", key=f"del_blr_{item['id']}"):
                            _delete_file(db, item["id"], item["filepath"])
                            st.rerun()
                st.divider()

def _render_duplicates(db: DatabaseManager) -> None:
    groups = db.get_duplicate_groups()

    if not groups:
        st.success("🎉 ¡No se han encontrado duplicados exactos!")
        return

    st.warning(f"Se han detectado {len(groups)} grupos de archivos idénticos (mismo hash perceptual).")

    # Botón para limpiar todos los duplicados del tirón conservando la mejor opción
    if st.button("🧹 Mantener recomendados y borrar todos los duplicados secundarios", key="clean_all_dupes_btn"):
        deleted = 0
        with st.spinner("Eliminando duplicados secundarios..."):
            for g_df in groups:
                best_id = propose_best_photo(g_df)
                for _, row in g_df.iterrows():
                    if row["id"] != best_id:
                        _delete_file_silent(db, row["id"], row["filepath"])
                        deleted += 1
        st.success(f"Se han eliminado {deleted} archivos duplicados.")
        st.rerun()

    for i, df in enumerate(groups):
        best_id = propose_best_photo(df)
        with st.expander(f"Grupo #{i + 1} — {len(df)} archivos coincidentes", expanded=True):
            cols = st.columns(len(df))
            for col, (_, row) in zip(cols, df.iterrows()):
                with col:
                    is_rec = row["id"] == best_id
                    if is_rec:
                        st.markdown("<span class='tier-badge tb-safe'>💡 RECOMENDADA</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span class='tier-badge tb-review'>REDUNDANTE</span>", unsafe_allow_html=True)

                    th = row.get("cached_thumb")
                    if th and Path(th).exists():
                        st.image(th, use_container_width=True)

                    st.caption(f"ID: {row['id']}")
                    st.markdown(
                        f"<p style='font-size:12px;margin:2px 0;'>{Path(row['filepath']).name}</p>"
                        f"<span style='font-size:11px;color:#a0a8c0;'>Calidad: {row.get('quality_score', 0.0)*100:.0f}%</span>",
                        unsafe_allow_html=True
                    )

                    if st.button("🗑 Borrar este", key=f"del_dup_{row['id']}"):
                        _delete_file(db, row["id"], row["filepath"])
                        st.rerun()

def _render_similar(db: DatabaseManager) -> None:
    st.markdown("#### 📸 Agrupación de Fotos Parecidas y Ráfagas")

    # Slider de Tolerancia de Hamming configurable
    hamming_tol = st.slider(
        "Tolerancia de similitud (Distancia de Hamming):", 
        min_value=1, 
        max_value=16, 
        value=8,
        help="Valores más bajos buscan fotos casi idénticas. Valores más altos agrupan fotos más variadas."
    )

    groups = get_similar_photo_groups(db, max_hamming=hamming_tol)

    if not groups:
        st.info("No se han detectado grupos de fotos similares con la tolerancia seleccionada.")
        return

    st.write(f"Se han detectado **{len(groups)}** grupos de secuencias similares.")

    for i, df in enumerate(groups):
        best_id = propose_best_photo(df)

        with st.expander(f"Grupo #{i + 1} — {len(df)} tomas parecidas", expanded=True):
            st.markdown(
                f"<div style='background:rgba(99,102,241,0.03);padding:8px 12px;border-radius:8px;font-size:13px;margin-bottom:12px;color:#a6afc9;'>"
                f"💡 <b>Recomendación:</b> Mantén la foto con ID <b>{best_id}</b> (tiene el mejor encuadre, nitidez o balance de peso)."
                f"</div>",
                unsafe_allow_html=True
            )

            cols = st.columns(len(df))
            for col, (_, row) in zip(cols, df.iterrows()):
                with col:
                    is_rec = row["id"] == best_id
                    if is_rec:
                        st.markdown("<span class='tier-badge tb-safe'>🌟 LA MEJOR TOMA</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span class='tier-badge tb-fp'>BORRAR</span>", unsafe_allow_html=True)

                    th = row.get("cached_thumb")
                    if th and Path(th).exists():
                        st.image(th, use_container_width=True)

                    st.caption(f"🕒 {row.get('exif_date', 'Sin fecha').split('T')[-1]}")
                    st.markdown(
                        f"<p style='font-size:12px;margin:2px 0;'>ID: {row['id']}</p>"
                        f"<span style='font-size:11px;color:#a0a8c0;'>Nitidez: {row.get('quality_score', 0.0)*100:.0f}%</span>",
                        unsafe_allow_html=True
                    )

                    if st.button("🗑 Borrar", key=f"del_sim_{row['id']}"):
                        _delete_file(db, row["id"], row["filepath"])
                        st.rerun()

def _render_compression(db: DatabaseManager) -> None:
    st.markdown("#### 🗜️ Compresión y Reducción de Calidad")

    # 1. Compresión in-situ individual
    st.markdown("##### Opcion 1: Comprimir un archivo pesado")

    # Buscar archivos > 2MB
    sql = "SELECT id, filepath, filename, media_type FROM FileQueue ORDER BY id DESC"
    conn = db._connect()
    all_files_df = pd.read_sql_query(sql, conn)
    conn.close()

    if all_files_df.empty:
        st.info("No hay archivos para comprimir.")
        return

    choices = []
    for _, row in all_files_df.iterrows():
        fp = row["filepath"]
        if os.path.exists(fp):
            sz = os.path.getsize(fp) / (1024*1024)
            choices.append({
                "id": row["id"],
                "filepath": fp,
                "label": f"[{row['media_type'].upper()}] {row['filename']} ({sz:.1f} MB)",
                "size_mb": sz,
                "type": row["media_type"]
            })

    if not choices:
        st.info("No se encontraron archivos en el disco para comprimir.")
        return

    selected_idx = st.selectbox(
        "Selecciona el archivo a comprimir:",
        range(len(choices)),
        format_func=lambda x: choices[x]["label"]
    )

    sel = choices[selected_idx]

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        scale = st.slider("Escalar resolución (dimensiones):", 0.2, 1.0, 0.7, 0.05)
    with col_s2:
        quality = st.slider("Calidad del codec / compresión (10-100):", 10, 100, 75, 5)

    st.markdown(
        f"**Tamaño actual:** `{sel['size_mb']:.2f} MB`  \n"
        f"**Tamaño estimado tras compresión:** `~{(sel['size_mb'] * (scale**2) * (quality/100) * 0.75):.2f} MB` (Ahorro ~70%)"
    )

    if st.button("🗜️ Ejecutar Compresión In-Situ", type="primary", key="compress_btn"):
        with st.spinner("Comprimiendo archivo en disco..."):
            orig_p = Path(sel["filepath"])
            temp_p = orig_p.with_name(f"_temp_{orig_p.name}")

            success = False
            if sel["type"] == "image":
                success = compress_image(orig_p, temp_p, quality=quality, scale=scale)
            else:
                success = compress_video_opencv(orig_p, temp_p, scale=scale, target_fps=24)

            if success and temp_p.exists():
                orig_size = orig_p.stat().st_size
                new_size = temp_p.stat().st_size

                if new_size < orig_size:
                    # Reemplazar original
                    try:
                        os.remove(orig_p)
                        os.rename(temp_p, orig_p)
                        st.success(
                            f"¡Comprimido con éxito!  \n"
                            f"De `{orig_size / (1024*1024):.2f} MB` a `{new_size / (1024*1024):.2f} MB`  \n"
                            f"**Espacio liberado:** `{(orig_size - new_size) / (1024*1024):.2f} MB`"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo reemplazar el archivo original: {e}")
                        if temp_p.exists():
                            os.remove(temp_p)
                else:
                    os.remove(temp_p)
                    st.warning("La compresión no redujo el tamaño del archivo original. Se ha abortado para no perder calidad inútilmente.")
            else:
                st.error("Error al procesar la compresión.")

    st.markdown("---")

    # 2. Compresión masiva
    st.markdown("##### 📦 Opción 2: Compresión Masiva Inteligente")
    st.markdown(
        "Reduce de golpe el tamaño de tus vídeos o imágenes más grandes para ganar espacio de inmediato."
    )

    c_m1, c_m2 = st.columns(2)
    with c_m1:
        batch_type = st.radio("Tipo de archivo a comprimir en lote:", ["Vídeos", "Imágenes"])
    with c_m2:
        threshold_size = st.number_input("Comprimir solo archivos mayores de (MB):", min_value=1.0, value=10.0)

    # Buscar candidatos
    candidates = []
    for c in choices:
        if batch_type == "Vídeos" and c["type"] == "video" and c["size_mb"] >= threshold_size:
            candidates.append(c)
        elif batch_type == "Imágenes" and c["type"] == "image" and c["size_mb"] >= threshold_size:
            candidates.append(c)

    st.write(f"Se han encontrado **{len(candidates)}** archivos candidatos para compresión masiva.")

    if candidates:
        if st.button(f"⚡ Comprimir {len(candidates)} {batch_type.lower()}", key="batch_compress_btn"):
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            saved_total = 0.0

            for idx, item in enumerate(candidates):
                status_text.text(f"Comprimiendo {idx+1}/{len(candidates)}: {Path(item['filepath']).name}...")
                orig_p = Path(item["filepath"])
                temp_p = orig_p.with_name(f"_temp_batch_{orig_p.name}")

                success = False
                if item["type"] == "image":
                    success = compress_image(orig_p, temp_p, quality=70, scale=0.75)
                else:
                    success = compress_video_opencv(orig_p, temp_p, scale=0.5, target_fps=24)

                if success and temp_p.exists():
                    orig_size = orig_p.stat().st_size
                    new_size = temp_p.stat().st_size
                    if new_size < orig_size:
                        try:
                            os.remove(orig_p)
                            os.rename(temp_p, orig_p)
                            saved_total += (orig_size - new_size) / (1024*1024)
                        except Exception:
                            if temp_p.exists():
                                os.remove(temp_p)
                    else:
                        os.remove(temp_p)
                progress_bar.progress((idx + 1) / len(candidates))

            status_text.empty()
            st.success(f"¡Compresión masiva finalizada! Se han liberado **{saved_total:.1f} MB** de almacenamiento.")
            st.rerun()

def _delete_file(db: DatabaseManager, file_id: int, filepath: str):
    """Borra el archivo físicamente y de la base de datos."""
    try:
        p = Path(filepath)
        if p.exists():
            os.remove(p)
        db.delete_file_record(file_id)
        st.toast(f"✅ Archivo eliminado: {p.name}")
    except Exception as e:
        st.error(f"Error al eliminar: {e}")

def _delete_file_silent(db: DatabaseManager, file_id: int, filepath: str):
    """Borra de forma silenciosa para ejecuciones por lotes."""
    try:
        p = Path(filepath)
        if p.exists():
            os.remove(p)
        db.delete_file_record(file_id)
    except Exception:
        pass
