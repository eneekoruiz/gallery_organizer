"""
ui/tab_cleanup.py — Bandeja de Limpieza
Gestión de Duplicados Exactos · Detección de Ráfagas · Recomendación de "Mejor Foto"
"""

from __future__ import annotations
import os
from pathlib import Path
import streamlit as st
import pandas as pd
from core.database import DatabaseManager

def render_cleanup(db: DatabaseManager) -> None:
    st.markdown(
        """
    <div style='margin-bottom:18px'>
      <h3 style='margin:0'>🧹 Bandeja de Limpieza</h3>
      <p style='color:#505570;margin:4px 0 0;font-size:14px'>
        Libera espacio eliminando duplicados exactos y seleccionando las mejores tomas de tus ráfagas.
      </p>
    </div>""",
        unsafe_allow_html=True,
    )

    tab_dupes, tab_bursts = st.tabs(["👯 Duplicados Exactos", "📸 Ráfagas y Similares"])

    with tab_dupes:
        _render_duplicates(db)

    with tab_bursts:
        _render_bursts(db)

def _render_duplicates(db: DatabaseManager) -> None:
    groups = db.get_duplicate_groups()
    
    if not groups:
        st.success("🎉 ¡No se han encontrado duplicados exactos!")
        return

    st.warning(f"Se han detectado {len(groups)} grupos de archivos idénticos (mismo hash visual).")
    
    for i, df in enumerate(groups):
        with st.expander(f"Grupo #{i+1} — {len(df)} archivos coincidentes", expanded=True):
            cols = st.columns(len(df))
            for col, (_, row) in zip(cols, df.iterrows()):
                with col:
                    th = row.get("cached_thumb")
                    if th and Path(th).exists():
                        st.image(th, use_container_width=True)
                    st.caption(f"ID: {row['id']}")
                    st.text(Path(row['filepath']).name)
                    
                    if st.button("🗑 Borrar este", key=f"del_dup_{row['id']}"):
                        _delete_file(db, row['id'], row['filepath'])
                        st.rerun()

def _render_bursts(db: DatabaseManager) -> None:
    # Ventana de ráfaga configurable
    window = st.slider("Ventana de ráfaga (segundos):", 1, 10, 3)
    groups = db.get_burst_groups(window_seconds=window)

    if not groups:
        st.info("No se han detectado ráfagas con la ventana seleccionada.")
        return

    st.write(f"Se han detectado {len(groups)} secuencias de fotos rápidas.")

    for i, df in enumerate(groups):
        with st.expander(f"Ráfaga #{i+1} — {len(df)} fotos", expanded=True):
            # Recomendación: La que tenga mejor tier o mayor resolución (aquí simplificamos)
            st.info("💡 Recomendación: Mantén la foto con mejor encuadre o iluminación.")
            
            cols = st.columns(len(df))
            for col, (_, row) in zip(cols, df.iterrows()):
                with col:
                    th = row.get("cached_thumb")
                    if th and Path(th).exists():
                        st.image(th, use_container_width=True)
                    st.caption(f"🕒 {row['exif_date'].split('T')[-1]}")
                    
                    if st.button("🗑 Borrar", key=f"del_bst_{row['id']}"):
                        _delete_file(db, row['id'], row['filepath'])
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
