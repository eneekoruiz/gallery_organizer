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

    # ── Búsqueda semántica y modo ──────────────────────────────────────────
    col_search, col_mode = st.columns([3, 1])
    with col_search:
        query = st.text_input(
            "",
            placeholder="🔍 Búsqueda: 'perro en la playa en agosto', 'factura en diciembre'...",
            label_visibility="collapsed",
            key="gallery_query",
        )
    with col_mode:
        st.selectbox(
            "Método de búsqueda",
            ["Búsqueda Vectorial (CLIP)", "Búsqueda SQL (Fuzzy/Metadatos)"],
            label_visibility="collapsed",
            key="search_mode",
        )

    # ── Filtros ────────────────────────────────────────────────────────────
    meta = db.get_unique_metadata()
    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
    with f1:
        status_f = st.selectbox(
            "Estado",
            [
                "Todos",
                "PENDING",
                "PROCESSING",
                "AUTO_CLASSIFIED",
                "NEEDS_REVIEW",
                "VERIFIED",
                "ERROR",
                "IGNORED",
            ],
            key="gf_status",
            label_visibility="collapsed",
        )
    with f2:
        triage_f = st.selectbox(
            "Bandeja",
            ["Todas", "safe", "review", "unclassified"],
            key="gf_triage",
            label_visibility="collapsed",
        )
    with f3:
        cam_f = st.selectbox(
            "Cámara",
            ["Todas"] + meta["cameras"],
            key="gf_cam",
            label_visibility="collapsed",
        )
    with f4:
        lens_f = st.selectbox(
            "Lente",
            ["Todas"] + meta["lenses"],
            key="gf_lens",
            label_visibility="collapsed",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Paginación ─────────────────────────────────────────────────────────
    if "gal_page" not in st.session_state:
        st.session_state.gal_page = 0

    # ── Cargar datos ───────────────────────────────────────────────────────
    status_param = None if status_f == "Todos" else status_f
    triage_param = None if triage_f == "Todas" else triage_f
    cam_param = None if cam_f == "Todas" else cam_f
    lens_param = None if lens_f == "Todas" else lens_f

    PAGE_SIZE = 48

    # Obtener total para paginación
    total_files = db.get_files_count(
        status=status_param, triage=triage_param, camera=cam_param, lens=lens_param
    )
    total_pages = (total_files - 1) // PAGE_SIZE + 1 if total_files > 0 else 1

    if st.session_state.gal_page >= total_pages:
        st.session_state.gal_page = total_pages - 1

    offset = st.session_state.gal_page * PAGE_SIZE

    # ── Búsqueda visual (Similitud) ────────────────────────────────────────
    sim_id = st.session_state.get("similarity_root_id")

    if sim_id:
        df = db.get_similar_files(sim_id)
        if st.button("⬅️ Volver a Galería"):
            st.session_state.similarity_root_id = None
            st.rerun()
        st.caption(f"🪄 Mostrando archivos similares al ID {sim_id}")
    elif query.strip():
        search_mode = st.session_state.get("search_mode", "Búsqueda Vectorial (CLIP)")
        if search_mode == "Búsqueda Vectorial (CLIP)":
            df = _semantic_search(db, query.strip())
        else:
            df = db.search_files_fuzzy(query.strip(), limit=100)

        if df.empty:
            st.warning(f"Sin resultados para: '{query}'")
            return
        st.caption(
            f"🎯 {len(df)} resultados ordenados por relevancia para: *{query}* ({search_mode})"
        )
    else:
        df = db.get_files_with_thumbs_df(
            status=status_param,
            triage=triage_param,
            camera=cam_param,
            lens=lens_param,
            limit=PAGE_SIZE,
            offset=offset,
        )
        st.caption(f"📁 {len(df)} de {total_files} archivos")

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
            if st.button("⬅️ Anterior", use_container_width=True):
                st.session_state.gal_page -= 1
                st.rerun()
    with c2:
        pg = st.number_input(
            "Página",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.gal_page + 1,
            step=1,
            label_visibility="collapsed",
        )
        if pg != st.session_state.gal_page + 1:
            st.session_state.gal_page = pg - 1
            st.rerun()
        st.markdown(
            f"<div style='text-align:center;color:#606880;font-size:12px'>Página {pg} de {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        if st.session_state.gal_page < total_pages - 1:
            if st.button("Siguiente ➡️", use_container_width=True):
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
    _db: DatabaseManager,
    status: Optional[str],
    triage: Optional[str],
    limit: int,
    offset: int,
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
    if df.empty:
        return

    if "exif_date" in df.columns:
        df["date_group"] = pd.to_datetime(df["exif_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["date_group"] = df["date_group"].fillna("Sin fecha")
    elif "best_datetime" in df.columns:
        df["date_group"] = pd.to_datetime(df["best_datetime"], errors="coerce").dt.strftime(
            "%Y-%m-%d"
        )
        df["date_group"] = df["date_group"].fillna("Sin fecha")
    else:
        df["date_group"] = "Sin fecha"

    date_groups = df.groupby("date_group", sort=False)

    n_cols = 6

    for date_str, group_df in date_groups:
        st.markdown(
            f"#### 📅 {date_str} <span style='font-size:12px;color:#505570;font-weight:normal'>· {len(group_df)} fotos</span>",
            unsafe_allow_html=True,
        )

        rows = [group_df.iloc[i : i + n_cols] for i in range(0, len(group_df), n_cols)]
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

    # ── Thumbnail con Privacy Mode ─────────────────────────────────────────
    privacy = st.session_state.get("privacy_mode", False)
    # Solo blureamos si no está verificado y hay caras (persona tag)
    should_blur = privacy and triage != "safe" and any(_is_person(t) for t in tags)

    blur_style = "filter:blur(12px);" if should_blur else ""

    b64_thumb = _get_optimized_thumbnail(filepath, size=(250, 250))

    if b64_thumb:
        st.markdown(
            f'<div style="position:relative; margin-bottom:15px; text-align:center;">'
            f'<img src="data:image/webp;base64,{b64_thumb}" '
            f'style="width:100%; aspect-ratio:1/1; object-fit:cover; border-radius:12px; border:1px solid #1c1f2e; box-shadow:0 4px 6px rgba(0,0,0,0.1); {blur_style}">'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#10121a;border-radius:12px;aspect-ratio:1/1;'
            'display:flex;align-items:center;justify-content:center;font-size:28px;margin-bottom:15px">🖼️</div>',
            unsafe_allow_html=True,
        )

    # ── Calidad IA bar ─────────────────────────────────────────────────────
    q_score = rec.get("quality_score", 0.0)
    q_color = "#34d399" if q_score > 0.7 else "#fbbf24" if q_score > 0.4 else "#f87171"
    st.markdown(
        f'<div style="height:3px;background:#1c1f2e;width:100%;margin:4px 0">'
        f'<div style="height:100%;background:{q_color};width:{q_score * 100}%"></div></div>',
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
    sc = {
        "PENDING": "#fbbf24",
        "PROCESSING": "#60a5fa",
        "AUTO_CLASSIFIED": "#34d399",
        "NEEDS_REVIEW": "#fb923c",
        "VERIFIED": "#22c55e",
        "ERROR": "#f87171",
        "IGNORED": "#9ca3af",
    }.get(status, "#606880")
    st.markdown(
        f'<span class="tier-badge {tb_css}" style="font-size:10px">{triage}</span> '
        f'<span style="font-size:10px;color:{sc};font-weight:bold;">{status}</span>',
        unsafe_allow_html=True,
    )
    st.caption(filename[:24])

    # ── Botones ────────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍", key=f"ginsp_{file_id}", help="Abrir inspector"):
            st.session_state.inspect_det_id = None
            st.session_state.inspect_path = filepath
            st.session_state.inspect_file_id = file_id
            st.rerun()
    with c2:
        if st.button("🪄", key=f"gsim_{file_id}", help="Buscar similares"):
            st.session_state.similarity_root_id = file_id
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


CACHE_DIR = Path(".cache_thumbs")
CACHE_DIR.mkdir(exist_ok=True)


def _get_optimized_thumbnail(image_path: str, size: tuple[int, int] = (250, 250)) -> str:
    import base64
    import io
    import os

    from PIL import Image

    path = Path(image_path)
    if not path.exists():
        return ""

    try:
        mtime = os.path.getmtime(image_path)
        cache_filename = f"{path.stem}_{int(mtime)}_{size[0]}x{size[1]}.webp"
        cache_path = CACHE_DIR / cache_filename

        if cache_path.exists():
            with open(cache_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        with Image.open(image_path) as img:
            img.thumbnail(size)
            img.save(cache_path, "WEBP", quality=80)

        with open(cache_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    except Exception:
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size)
                buf = io.BytesIO()
                img.save(buf, format="WEBP", quality=80)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return ""
