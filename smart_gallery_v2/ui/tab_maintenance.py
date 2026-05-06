"""
ui/tab_maintenance.py — Herramientas de Mantenimiento (Phase 6)
Limpieza de caché, reconstrucción de índices y reintentos masivos.
"""

from __future__ import annotations

import os
import shutil

import streamlit as st

from core.config import DIR_FACES, DIR_THUMBS
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
        if st.button("🔄 Reconstruir índice CLIP/FAISS"):
            st.info("Esta acción forzará la recarga de embeddings en memoria.")
            # En una app real, esto podría disparar un flag para que el worker lo haga
            st.success(
                "Acción no implementada completamente en este mock, pero el concepto está aquí."
            )

        if st.button("🖼️ Reconstruir Thumbnails"):
            st.warning("Se eliminarán y regenerarán todas las miniaturas.")
            if st.button("Confirmar eliminación de Thumbs"):
                shutil.rmtree(DIR_THUMBS, ignore_errors=True)
                DIR_THUMBS.mkdir(exist_ok=True)
                st.success("Miniaturas eliminadas. Se regenerarán al navegar.")

    with c2:
        st.markdown("#### 🧹 Limpieza")
        if st.button("🗑️ Limpiar caché de rostros"):
            shutil.rmtree(DIR_FACES, ignore_errors=True)
            DIR_FACES.mkdir(exist_ok=True)
            st.success("Recortes de rostros eliminados.")

        if st.button("🔥 Resetear Base de Datos"):
            st.error("⚠️ ESTO ELIMINARÁ TODO EL PROGRESO.")
            if st.checkbox("Entiendo que perderé mis etiquetas y organización"):
                if st.button("EJECUTAR RESET TOTAL"):
                    # Cerrar conexiones y borrar archivo
                    db_file = db._db_path
                    if os.path.exists(db_file):
                        os.remove(db_file)
                        st.success("Base de datos eliminada. Reinicia la app.")
                        st.stop()
