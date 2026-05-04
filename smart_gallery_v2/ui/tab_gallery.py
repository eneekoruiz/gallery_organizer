"""
ui/tab_gallery.py — Galería Principal
Masonry Grid · Búsqueda Semántica CLIP · Filtros por tier/tag · Inspector
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

from core.config import CLIP_RELEVANCE_MIN
from core.database import DatabaseManager
from core.worker import get_thumb


# ──────────────────────────────────────────────────────────────────────────────
# Render principal
# ──────────────────────────────────────────────────────────────────────────────
def render_gallery(db: DatabaseManager) -> None:

    # ── Búsqueda semántica ─────────────────────────────────────────────────
    query = st.text_input(
        "",
        placeholder="🔍  Búsqueda semántica: 'Cumpleaños con pastel', 'Perro en el parque', 'Playa al atardecer'…",
        label_visibility="collapsed",
        key="gallery_query",
    )

    # ── Filtros ────────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns([2, 2, 3])
    with f1:
        status_f = st.selectbox("Estado", ["Todos","DONE","PENDING","ERROR"],
                                label_visibility="collapsed", key="gf_status")
    with f2:
        triage_f = st.selectbox("Bandeja", ["Todas","safe","review","unclassified"],
                                label_visibility="collapsed", key="gf_triage")
    with f3:
        st.caption(f"💡 Arrastra fotos a `Galería/Para Organizar/` y pulsa **Sincronizar** en el Dashboard.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Cargar datos ───────────────────────────────────────────────────────
    status_param = None if status_f  == "Todos"  else status_f
    triage_param = None if triage_f  == "Todas"  else triage_f
    df = db.get_files_df(status=status_param, triage=triage_param, limit=240)

    if df.empty:
        st.info("Sin archivos. Agrega fotos a `Galería/Para Organizar/` y pulsa Sincronizar.")
        return

    # ── Búsqueda semántica CLIP ────────────────────────────────────────────
    if query.strip():
        df = _semantic_search(db, query.strip(), df)
        if df.empty:
            st.warning(f"Sin resultados para: '{query}'")
            return
        st.caption(f"🎯 {len(df)} resultados para: *{query}*")
    else:
        st.caption(f"📁 {len(df)} archivos")

    # ── Bulk selection bar ─────────────────────────────────────────────────
    if "gallery_sel" not in st.session_state:
        st.session_state.gallery_sel = set()
    _bulk_bar(db, df)

    st.divider()

    # ── Masonry Grid ───────────────────────────────────────────────────────
    _masonry(db, df)


# ──────────────────────────────────────────────────────────────────────────────
# Búsqueda Semántica CLIP
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _get_clip():
    try:
        from core.ai_engines import CLIPEngine
        return CLIPEngine()
    except Exception:
        return None


def _semantic_search(db: DatabaseManager, query: str, df: pd.DataFrame) -> pd.DataFrame:
    clip = _get_clip()
    if clip is None:
        st.caption("⚠ Motor CLIP no disponible — instala open-clip-torch.")
        return df

    text_emb = clip.embed_text(query)
    if text_emb is None:
        return df

    ids, embs = db.load_clip()
    if len(ids) == 0:
        return df

    scores  = embs @ text_emb          # similitud coseno (embeddings normalizados)
    top_idx = np.argsort(scores)[::-1]
    top_ids = [ids[i] for i in top_idx if float(scores[i]) > CLIP_RELEVANCE_MIN]

    if not top_ids:
        return pd.DataFrame()
    return df[df["id"].isin(top_ids)].copy()


# ──────────────────────────────────────────────────────────────────────────────
# Bulk Actions
# ──────────────────────────────────────────────────────────────────────────────
def _bulk_bar(db: DatabaseManager, df: pd.DataFrame) -> None:
    selected = st.session_state.gallery_sel
    n        = len(selected)
    if n == 0:
        return

    st.markdown(
        f'<div style="background:#14172280;border:1px solid #252840;border-radius:12px;'
        f'padding:14px 18px;margin-bottom:10px">'
        f'<strong style="color:#a78bfa">{n} archivos seleccionados</strong></div>',
        unsafe_allow_html=True)

    b1, b2, b3 = st.columns([3, 2, 2])
    known = db.get_all_identity_names()

    with b1:
        opts   = ["(Seleccionar…)"] + known + ["➕ Nuevo nombre"]
        bk_sel = st.selectbox("Reasignar identidad:", opts, key="gb_sel")
        bk_new = ""
        if bk_sel == "➕ Nuevo nombre":
            bk_new = st.text_input("Nombre:", key="gb_new")
    with b2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"✅ Aplicar a {n} archivos", type="primary"):
            nombre = bk_new if bk_sel == "➕ Nuevo nombre" else bk_sel
            if nombre and nombre != "(Seleccionar…)":
                _bulk_rename_files(db, list(selected), nombre)
                st.session_state.gallery_sel = set()
                st.toast(f"✅ {n} archivos → '{nombre}'")
                st.rerun()
    with b3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖ Deseleccionar todo"):
            st.session_state.gallery_sel = set()
            st.rerun()


def _bulk_rename_files(db: DatabaseManager, file_ids: list[int], name: str) -> None:
    """Busca todas las detecciones de esos archivos y las renombra en lote."""
    import sqlite3
    from core.config import DB_PATH
    ph   = ",".join("?" * len(file_ids))
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        f"SELECT id FROM Detections WHERE file_id IN ({ph})", file_ids
    ).fetchall()
    conn.close()
    det_ids = [r[0] for r in rows]
    if det_ids:
        db.bulk_verify(det_ids, name)


# ──────────────────────────────────────────────────────────────────────────────
# Masonry Grid
# ──────────────────────────────────────────────────────────────────────────────
def _masonry(db: DatabaseManager, df: pd.DataFrame) -> None:
    n_cols = 4
    rows   = [df.iloc[i:i+n_cols] for i in range(0, len(df), n_cols)]
    for row_df in rows:
        cols = st.columns(n_cols)
        for col, (_, rec) in zip(cols, row_df.iterrows()):
            with col:
                _image_card(rec)


def _image_card(rec: pd.Series) -> None:
    file_id   = int(rec.get("id", 0))
    filepath  = rec.get("filepath", "")
    filename  = rec.get("filename", "")
    triage    = rec.get("triage_tier", "unclassified")
    tags_json = rec.get("tags") or "[]"
    status    = rec.get("status", "")

    try:
        tags = json.loads(tags_json) if isinstance(tags_json, str) else []
    except Exception:
        tags = []

    # ── Checkbox bulk ──────────────────────────────────────────────────────
    selected = file_id in st.session_state.get("gallery_sel", set())
    is_now   = st.checkbox("", value=selected, key=f"gchk_{file_id}",
                            label_visibility="collapsed")
    if is_now != selected:
        if is_now:
            st.session_state.gallery_sel.add(file_id)
        else:
            st.session_state.gallery_sel.discard(file_id)

    # ── Thumbnail ──────────────────────────────────────────────────────────
    thumb = get_thumb(filepath) if Path(filepath).exists() else None
    if thumb and Path(thumb).exists():
        st.image(Image.open(thumb), use_container_width=True)
    else:
        st.markdown(
            '<div style="background:#10121a;border-radius:10px;aspect-ratio:4/3;'
            'display:flex;align-items:center;justify-content:center;font-size:28px">🖼️</div>',
            unsafe_allow_html=True)

    # ── Tags row ───────────────────────────────────────────────────────────
    if tags:
        pills = " ".join(
            f'<span class="tag-pill {"tp-person" if _is_person(t) else "tp-object"}">{t}</span>'
            for t in tags[:4]
        )
        st.markdown(f'<div style="margin:3px 0 1px">{pills}</div>', unsafe_allow_html=True)

    # ── Tier + status ──────────────────────────────────────────────────────
    tb_css = {"safe":"tb-safe","review":"tb-review"}.get(triage,"tb-unk")
    sc     = {"DONE":"#34d399","ERROR":"#f87171","PENDING":"#fbbf24"}.get(status,"#606880")
    st.markdown(
        f'<span class="tier-badge {tb_css}" style="font-size:10px">{triage}</span> '
        f'<span style="font-size:10px;color:{sc}">{status}</span>',
        unsafe_allow_html=True)
    st.caption(filename[:24])

    # ── Botón inspector ────────────────────────────────────────────────────
    if st.button("🔍", key=f"ginsp_{file_id}", help="Abrir inspector"):
        st.session_state.inspect_det_id = None   # inspector de archivo, no de detección
        st.session_state.inspect_path   = filepath
        st.session_state.inspect_file_id = file_id
        st.rerun()


def _is_person(tag: str) -> bool:
    return tag.lower() not in {
        "bicicleta","coche","moto","gato","perro","caballo","sinclasificar","persona"
    }
