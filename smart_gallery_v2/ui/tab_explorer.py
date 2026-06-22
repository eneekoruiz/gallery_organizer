"""
ui/tab_explorer.py — Galaxia Semántica 3D (UMAP)
Killer Feature: Visualización topológica interactiva de todos los recuerdos usando los embeddings de CLIP.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.database import DatabaseManager
from core.umap_engine import generate_umap_projection


@st.cache_data(show_spinner=False)
def _get_cached_projection(_db: DatabaseManager) -> pd.DataFrame:
    """Cacheamos la proyección para no re-calcular UMAP en cada rerun de Streamlit."""
    return generate_umap_projection(_db, dimensions=3)


def render_semantic_explorer(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div style='margin-bottom:18px'>
          <h3 style='margin:0; font-family:"Inter", sans-serif; font-size: 28px; color:#e2e8f0;'>🌌 Galaxia Semántica</h3>
          <p style='color:#94a3b8;margin:4px 0 0;font-size:14px'>
            Explora tus recuerdos visualmente. La IA (CLIP + UMAP) ha agrupado automáticamente fotos similares 
            formando constelaciones temáticas. Interactúa con el grafo 3D.
          </p>
        </div>""",
        unsafe_allow_html=True,
    )

    with st.spinner("Calculando proyección topológica en 3D..."):
        df = _get_cached_projection(db)

    if df.empty:
        st.info(
            "No hay suficientes datos procesados por CLIP para generar la galaxia 3D. Ve a Triaje e indexa algunas imágenes."
        )
        return

    # Preparar datos para visualización
    # Limpiar y formatear las etiquetas para el hover
    df["hover_name"] = df["filename"].apply(lambda x: x[:20] + "..." if len(str(x)) > 20 else x)
    df["date"] = df["exif_date"].fillna("Sin fecha").astype(str)

    # Extraer primer tag si existe para dar algo de color (opcional)
    def get_primary_tag(tags_json):
        import json

        try:
            tags = json.loads(tags_json)
            return tags[0] if tags else "Sin Etiqueta"
        except (TypeError, json.JSONDecodeError):
            return "Sin Etiqueta"

    df["primary_tag"] = df["tags"].apply(get_primary_tag)

    # Crear gráfico 3D con Plotly
    fig = px.scatter_3d(
        df,
        x="x",
        y="y",
        z="z",
        color="triage_tier",  # Colorear por estado de triaje para dar contraste
        hover_name="hover_name",
        hover_data={
            "x": False,
            "y": False,
            "z": False,
            "date": True,
            "primary_tag": True,
            "triage_tier": False,
        },
        color_discrete_map={
            "safe": "#10b981",  # Esmeralda
            "review": "#f59e0b",  # Ambar
            "unclassified": "#6366f1",  # Indigo
        },
        opacity=0.8,
    )

    # Estilizar el grafo al estilo 'Dark Space'
    fig.update_layout(
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            xaxis=dict(showgrid=False, showbackground=False, showticklabels=False, title=""),
            yaxis=dict(showgrid=False, showbackground=False, showticklabels=False, title=""),
            zaxis=dict(showgrid=False, showbackground=False, showticklabels=False, title=""),
            bgcolor="#0f172a",  # Fondo azul espacial oscuro
        ),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, font=dict(color="#cbd5e1")),
    )

    # Modificar el tamaño y estilo de los puntos
    fig.update_traces(
        marker=dict(size=5, line=dict(width=0.5, color="white")), selector=dict(mode="markers")
    )

    st.markdown(
        """
        <div style="padding: 2px; background: linear-gradient(145deg, #1e293b, #0f172a); border-radius: 16px; border: 1px solid #334155; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
        """,
        unsafe_allow_html=True,
    )

    st.plotly_chart(fig, use_container_width=True, height=700)

    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "🔍 Usa el ratón para rotar (clic izquierdo), hacer zoom (rueda) y explorar tus constelaciones."
    )
