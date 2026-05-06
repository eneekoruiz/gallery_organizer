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

from core.config import CLIP_RELEVANCE_MIN
from core.database import DatabaseManager


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
        status_f = st.selectbox(
            "Estado",
            ["Todos", "DONE", "PENDING", "ERROR"],
            label_visibility="collapsed",
            key="gf_status",
        )
    with f2:
        triage_f = st.selectbox(
            "Bandeja",
            ["Todas", "safe", "review", "unclassified"],
            label_visibility="collapsed",
            key="gf_triage",
        )
    with f3:
        st.caption(
            "💡 Arrastra fotos a `Galería/Para Organizar/` y pulsa **Sincronizar** en el Dashboard."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Paginación ─────────────────────────────────────────────────────────
    if "gal_page" not in st.session_state:
        st.session_state.gal_page = 0

    # ── Cargar datos ───────────────────────────────────────────────────────
    status_param = None if status_f == "Todos" else status_f
    triage_param = None if triage_f == "Todas" else triage_f

    PAGE_SIZE = 60
    offset = st.session_state.gal_page * PAGE_SIZE

    # ── Búsqueda semántica CLIP (Global) ───────────────────────────────────
    if query.strip():
        df = _semantic_search(db, query.strip())
        if df.empty:
            st.warning(f"Sin resultados para: '{query}'")
            return
        st.caption(f"🎯 {len(df)} resultados ordenados por relevancia para: *{query}*")
    else:
        df = _cached_files_df(db, status_param, triage_param, PAGE_SIZE, offset)
        st.caption(f"📁 {len(df)} archivos")

    # ── Bulk selection bar ─────────────────────────────────────────────────
    if "gallery_sel" not in st.session_state:
        st.session_state.gallery_sel = set()
    _bulk_bar(db, df)

    st.divider()

    # ── Masonry Grid ───────────────────────────────────────────────────────
    _masonry(db, df)

    # ── Controles de página ────────────────────────────────────────────────
    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.session_state.gal_page > 0:
            if st.button("⬅️ Anterior"):
                st.session_state.gal_page -= 1
                st.rerun()
    with c2:
        st.markdown(
            f"<div style='text-align:center;padding-top:10px'>Página {st.session_state.gal_page + 1}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        if len(df) == PAGE_SIZE:
            if st.button("Siguiente ➡️"):
                st.session_state.gal_page += 1
                st.rerun()


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


def _semantic_search(db: DatabaseManager, query: str) -> pd.DataFrame:
    """Búsqueda global por relevancia vectorial."""
    clip = _get_clip()
    if clip is None:
        st.caption("⚠ Motor CLIP no disponible.")
        return pd.DataFrame()

    text_emb = clip.embed_text(query)
    if text_emb is None:
        return pd.DataFrame()

    ids, embs = db.load_clip()
    if len(ids) == 0:
        return pd.DataFrame()

    # Similitud coseno (vectorizada)
    scores = embs @ text_emb

    # Filtrar y ordenar
    valid_mask = scores > CLIP_RELEVANCE_MIN
    valid_ids = [ids[i] for i in range(len(ids)) if valid_mask[i]]
    valid_scores = scores[valid_mask]

    if not valid_ids:
        return pd.DataFrame()

    # Ordenar por score desc
    sorted_indices = np.argsort(valid_scores)[::-1]
    sorted_ids = [valid_ids[i] for i in sorted_indices]

    # Cargar de DB respetando el orden de relevancia
    return db.get_files_by_ids_with_thumbs(sorted_ids[:100])  # Top 100 resultados


@st.cache_data(ttl=5.0, show_spinner=False)
def _cached_files_df(
    _db: DatabaseManager, status: Optional[str], triage: Optional[str], limit: int, offset: int
) -> pd.DataFrame:
    return _db.get_files_with_thumbs_df(status=status, triage=triage, limit=limit, offset=offset)


# ──────────────────────────────────────────────────────────────────────────────
# Bulk Actions
# ──────────────────────────────────────────────────────────────────────────────
def _bulk_bar(db: DatabaseManager, df: pd.DataFrame) -> None:
    selected = st.session_state.gallery_sel
    n = len(selected)
    if n == 0:
        return

    st.markdown(
        f'<div style="background:#14172280;border:1px solid #252840;border-radius:12px;'
        f'padding:14px 18px;margin-bottom:10px">'
        f'<strong style="color:#a78bfa">{n} archivos seleccionados</strong></div>',
        unsafe_allow_html=True,
    )

    b1, b2, b3 = st.columns([3, 2, 2])
    known = db.get_all_identity_names()

    with b1:
        opts = ["(Seleccionar…)"] + known + ["➕ Nuevo nombre"]
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
    det_ids = db.get_detection_ids_for_files(file_ids)
    if det_ids:
        db.bulk_verify(det_ids, name)


# ──────────────────────────────────────────────────────────────────────────────
# Masonry Grid
# ──────────────────────────────────────────────────────────────────────────────
def _masonry(db: DatabaseManager, df: pd.DataFrame) -> None:
    n_cols = 4
    rows = [df.iloc[i : i + n_cols] for i in range(0, len(df), n_cols)]
    for row_df in rows:
        cols = st.columns(n_cols)
        for col, (_, rec) in zip(cols, row_df.iterrows()):
            with col:
                _image_card(rec)


def _image_card(rec: pd.Series) -> None:
    file_id = int(rec.get("id", 0))
    filepath = rec.get("filepath", "")
    filename = rec.get("filename", "")
    triage = rec.get("triage_tier", "unclassified")
    tags_json = rec.get("tags") or "[]"
    status = rec.get("status", "")

    try:
        tags = json.loads(tags_json) if isinstance(tags_json, str) else []
    except Exception:
        tags = []

    # ── Checkbox bulk ──────────────────────────────────────────────────────
    selected = file_id in st.session_state.get("gallery_sel", set())
    is_now = st.checkbox("", value=selected, key=f"gchk_{file_id}", label_visibility="collapsed")
    if is_now != selected:
        if is_now:
            st.session_state.gallery_sel.add(file_id)
        else:
            st.session_state.gallery_sel.discard(file_id)

    # ── Thumbnail ──────────────────────────────────────────────────────────
    thumb = rec.get("cached_thumb")
    if thumb and Path(thumb).exists():
        st.image(thumb, use_container_width=True)
    else:
        # Fallback si no está en caché o se borró el archivo
        st.markdown(
            '<div style="background:#10121a;border-radius:10px;aspect-ratio:4/3;'
            'display:flex;align-items:center;justify-content:center;font-size:28px">🖼️</div>',
            unsafe_allow_html=True,
        )

    # ── Tags row ───────────────────────────────────────────────────────────
    if tags:
        pills = " ".join(
            f'<span class="tag-pill {"tp-person" if _is_person(t) else "tp-object"}">{t}</span>'
            for t in tags[:4]
        )
        st.markdown(f'<div style="margin:3px 0 1px">{pills}</div>', unsafe_allow_html=True)

    # ── Tier + status ──────────────────────────────────────────────────────
    tb_css = {"safe": "tb-safe", "review": "tb-review"}.get(triage, "tb-unk")
    sc = {"DONE": "#34d399", "ERROR": "#f87171", "PENDING": "#fbbf24"}.get(status, "#606880")
    st.markdown(
        f'<span class="tier-badge {tb_css}" style="font-size:10px">{triage}</span> '
        f'<span style="font-size:10px;color:{sc}">{status}</span>',
        unsafe_allow_html=True,
    )
    st.caption(filename[:24])

    # ── Botón inspector ────────────────────────────────────────────────────
    if st.button("🔍", key=f"ginsp_{file_id}", help="Abrir inspector"):
        st.session_state.inspect_det_id = None  # inspector de archivo, no de detección
        st.session_state.inspect_path = filepath
        st.session_state.inspect_file_id = file_id
        st.rerun()


def _is_person(tag: str) -> bool:
    return tag.lower() not in {
        "bicicleta",
        "coche",
        "moto",
        "gato",
        "perro",
        "caballo",
        "sinclasificar",
        "persona",
    }
