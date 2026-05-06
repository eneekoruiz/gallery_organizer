"""
ui/tab_errors.py — Panel de Errores Procesables (Phase 2)
Permite visualizar fallos en el pipeline y reintentar.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.database import DatabaseManager


def render_errors(db: DatabaseManager):
    st.markdown(
        """
    <div style='margin-bottom:18px'>
      <h3 style='margin:0'>⚠️ Errores de Procesamiento</h3>
      <p style='color:#505570;margin:4px 0 0;font-size:14px'>
        Archivos que fallaron durante el pipeline. Puedes ver el motivo y reintentar.
      </p>
    </div>""",
        unsafe_allow_html=True,
    )

    # ── Métricas rápidas ──────────────────────────────────────────────────
    conn = db._connect()
    df_err = pd.read_sql_query(
        "SELECT * FROM ProcessingErrors ORDER BY created_at DESC LIMIT 100", conn
    )
    conn.close()

    if df_err.empty:
        st.success("🎉 ¡No hay errores registrados! Todo fluye correctamente.")
        return

    # ── Acciones Globales ──────────────────────────────────────────────────
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🔄 Reintentar todos los errores", type="primary"):
            # Cambiar status a PENDING y resetear retries
            conn = db._connect()
            conn.execute("UPDATE FileQueue SET status='PENDING', retries=0 WHERE status='ERROR'")
            conn.execute("DELETE FROM ProcessingErrors")
            conn.commit()
            conn.close()
            st.toast("Reintentando todos los archivos...")
            st.rerun()
    with c2:
        if st.button("🗑️ Limpiar historial de errores"):
            conn = db._connect()
            conn.execute("DELETE FROM ProcessingErrors")
            conn.commit()
            conn.close()
            st.rerun()

    st.divider()

    # ── Tabla de Errores ──────────────────────────────────────────────────
    for _, row in df_err.iterrows():
        with st.expander(f"❌ {row['phase'].upper()}: {row['filepath']}"):
            st.error(f"**Excepción:** {row['exception']}")
            st.info(
                f"**ID de archivo:** {row['file_id']} | **Fecha:** {row['created_at']} | **Reintentos:** {row['retries']}"
            )

            if st.button("Reintentar este archivo", key=f"retry_{row['id']}"):
                conn = db._connect()
                conn.execute(
                    "UPDATE FileQueue SET status='PENDING', retries=0 WHERE id=?", (row["file_id"],)
                )
                conn.execute("DELETE FROM ProcessingErrors WHERE file_id=?", (row["file_id"],))
                conn.commit()
                conn.close()
                st.rerun()
