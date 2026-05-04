"""
ui/tab_timeline.py — Línea de Tiempo y Mapa GPS
Navegación cronológica EXIF · Mapa de ubicaciones · Densidad por día
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from core.database import DatabaseManager
from core.worker import get_thumb


def render_timeline(db: DatabaseManager) -> None:
    st.markdown("""
    <div style='margin-bottom:16px'>
      <h3 style='margin:0'>📅 Línea de Tiempo & Mapa</h3>
      <p style='color:#505570;margin:4px 0 0;font-size:14px'>
        Navegación cronológica por metadatos EXIF · Geolocalización GPS
      </p>
    </div>""", unsafe_allow_html=True)

    tl_tab, map_tab = st.tabs(["📅 Cronología", "🗺️ Mapa GPS"])

    with tl_tab:
        _render_timeline(db)
    with map_tab:
        _render_map(db)


# ── Timeline ──────────────────────────────────────────────────────────────────
def _render_timeline(db: DatabaseManager) -> None:
    df = db.get_timeline_df()
    if df.empty:
        st.info("Sin metadatos de fecha. Las fotos con EXIF aparecerán aquí automáticamente.")
        return

    df["exif_date"] = pd.to_datetime(df["exif_date"], errors="coerce")
    df = df.dropna(subset=["exif_date"])
    if df.empty:
        return

    min_d, max_d = df["exif_date"].min().date(), df["exif_date"].max().date()
    c1, c2 = st.columns(2)
    with c1:
        d_from = st.date_input("Desde", value=min_d, min_value=min_d, max_value=max_d)
    with c2:
        d_to   = st.date_input("Hasta", value=max_d, min_value=min_d, max_value=max_d)

    mask = (df["exif_date"].dt.date >= d_from) & (df["exif_date"].dt.date <= d_to)
    df_f = df.loc[mask]
    if df_f.empty:
        st.warning("Sin datos en ese rango.")
        return

    st.markdown("#### Fotos por día")
    st.bar_chart(df_f.set_index("exif_date")[["count"]], use_container_width=True, height=200)

    total    = int(df_f["count"].sum())
    prom     = df_f["count"].mean()
    peak_row = df_f.loc[df_f["count"].idxmax()]
    peak_d   = peak_row["exif_date"].strftime("%d %b %Y")

    s1, s2, s3 = st.columns(3)
    s1.metric("Total en rango",  f"{total:,}")
    s2.metric("Promedio diario", f"{prom:.1f}")
    s3.metric("Día más activo",  f"{peak_d} ({int(peak_row['count'])})")

    st.divider()
    st.markdown("#### Fotos del período")
    _period_thumbs(db, d_from, d_to)


def _period_thumbs(db: DatabaseManager, d_from, d_to) -> None:
    df = db.get_files_df(limit=60)
    df["exif_date"] = pd.to_datetime(df["exif_date"], errors="coerce")
    df = df[(df["exif_date"].dt.date >= d_from) & (df["exif_date"].dt.date <= d_to)]
    if df.empty:
        st.info("Sin fotos en este período.")
        return
    cols_n = 6
    for chunk in [df.iloc[i:i+cols_n] for i in range(0, min(len(df), 48), cols_n)]:
        cols = st.columns(cols_n)
        for col, (_, rec) in zip(cols, chunk.iterrows()):
            with col:
                fp = rec.get("filepath", "")
                if Path(fp).exists():
                    th = get_thumb(fp)
                    if Path(th).exists():
                        st.image(Image.open(th), use_container_width=True)
                        dt = rec.get("exif_date")
                        st.caption(pd.Timestamp(dt).strftime("%d/%m/%Y") if pd.notna(dt) else "")


# ── Mapa GPS ──────────────────────────────────────────────────────────────────
def _render_map(db: DatabaseManager) -> None:
    df = db.get_geo_points()
    if df.empty:
        st.info(
            "Sin coordenadas GPS. Las fotos tomadas con smartphone (con GPS activo) "
            "aparecerán aquí al procesarlas."
        )
        return

    st.caption(f"📍 {len(df)} fotos geolocalizadas")
    st.map(df[["lat", "lon"]], use_container_width=True, zoom=5)

    st.divider()
    st.markdown("#### Detalle de ubicaciones")
    disp = df[["filename", "exif_date", "lat", "lon"]].copy()
    disp.columns = ["Archivo", "Fecha", "Latitud", "Longitud"]
    disp["Fecha"] = pd.to_datetime(disp["Fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
    st.dataframe(disp, use_container_width=True, hide_index=True,
                 column_config={
                     "Latitud":  st.column_config.NumberColumn(format="%.6f"),
                     "Longitud": st.column_config.NumberColumn(format="%.6f"),
                 })
