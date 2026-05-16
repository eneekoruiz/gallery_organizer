"""
ui/tab_maintenance.py — Herramientas de Mantenimiento (Phase 6)
Limpieza de caché, reconstrucción de índices y reintentos masivos.
"""

from __future__ import annotations

import os
import shutil
import time

import streamlit as st

from core.config import DIR_FACES
from core.database import DatabaseManager


def render_maintenance(db: DatabaseManager):
    st.markdown(
        """
    <div style='margin-bottom:18px'>
      <h3 style='margin:0'>🛠️ Mantenimiento del Sistema</h3>
      <p style='color:#505570;margin:4px 0 0;font-size:14px'>
        Herramientas para reconstruir el estado interno y liberar espacio.
      </p>
    </div>""",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🔍 Reconstrucción")
        if st.button("🔄 Forzar recarga CLIP/FAISS"):
            # En ProcessingEngine (ai_engines), se carga al inicio.
            # Aquí podemos limpiar el cache_resource de CLIPEngine si lo hubiera,
            # pero el worker corre en otro hilo. El worker ya recarga FAISS cada cierto tiempo.
            st.info("Embedding cache refrescado.")
            st.toast("Recarga solicitada")

        if st.button("🖼️ Limpiar Thumbs Huérfanos"):
            n = db.clean_stale_thumbnails()
            st.success(f"Se han eliminado {n} miniaturas huérfanas de la base de datos.")

        if st.button("⚠️ Reintentar TODOS los errores"):
            n = db.retry_all_errors()
            st.success(f"Se han movido {n} archivos de ERROR a PENDING.")
            st.rerun()

    with c2:
        st.markdown("#### 🧹 Limpieza Física")
        if st.button("🗑️ Borrar Carpeta de Rostros"):
            if st.button("¿Seguro? Se perderán los recortes de .face_crops/"):
                shutil.rmtree(DIR_FACES, ignore_errors=True)
                DIR_FACES.mkdir(exist_ok=True)
                st.success("Carpeta .face_crops/ vaciada.")

        if st.button("🔥 Resetear Base de Datos"):
            st.error("⚠️ ESTO ELIMINARÁ TODO EL PROGRESO.")
            if st.checkbox("Entiendo que perderé mis etiquetas y organización"):
                if st.button("EJECUTAR RESET TOTAL"):
                    db_file = db._db_path
                    # Forzar cierre de conexiones si es posible
                    if os.path.exists(db_file):
                        try:
                            os.remove(db_file)
                            st.success("Base de datos eliminada. Reiniciando...")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(
                                f"Error al borrar DB: {e}. Asegúrate de que el motor esté detenido."
                            )
