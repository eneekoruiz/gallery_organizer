"""
app.py — Smart AI Gallery Organizer · Versión Comercial 2.0
Entry point Streamlit.

Arrancar:
    streamlit run app.py --server.port 8501 --server.maxUploadSize 500

Estructura de carpetas esperada:
    Galería/
      Para Organizar/   ← Drop tus fotos aquí
      Resultados/       ← Symlinks y copias organizadas por persona/objeto
      Fotos/            ← Fotos de referencia para identidades
"""

from __future__ import annotations

import gc
import logging
import sys

from core.bootstrap import ensure_dirs, setup_environment
from core.config import APP_ICON, APP_TITLE, LOG_PATH

ensure_dirs()
setup_environment()

import streamlit as st

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Smart AI Gallery Organizer · YOLOv8 + ArcFace + CLIP",
        "Get Help": None,
        "Report a bug": None,
    },
)

from core.database import DatabaseManager
from ui.sidebar_panel import render_help_sidebar
from ui.styles import BBOX_SCRIPT, PREMIUM_CSS
from ui.tab_cleanup import render_cleanup
from ui.tab_dashboard import _boot as _boot_runtime
from ui.tab_dashboard import render_dashboard
from ui.tab_errors import render_errors
from ui.tab_gallery import render_gallery
from ui.tab_maintenance import render_maintenance
from ui.tab_people import render_people_management
from ui.tab_explorer import render_semantic_explorer
from ui.tab_timeline import render_timeline
from ui.tab_triage import render_triage

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_PATH), encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── DB Singleton (compartido entre tabs y reruns) ─────────────────────────────
@st.cache_resource
def get_db() -> DatabaseManager:
    return DatabaseManager()


@st.cache_data(ttl=1.5, show_spinner=False)
def _cached_stats(_db: DatabaseManager) -> dict[str, int]:
    return _db.get_stats()


# ── App Principal ─────────────────────────────────────────────────────────────
def main() -> None:
    # CSS + JS global
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)
    st.markdown(BBOX_SCRIPT, unsafe_allow_html=True)

    db = get_db()
    _boot_runtime(db)

    with st.sidebar:
        render_help_sidebar(db)

    # ── Header ────────────────────────────────────────────────────────────
    h_col, stat_col = st.columns([5, 2])
    with h_col:
        st.markdown(
            "<h1 style='margin:0;font-size:26px;font-weight:800;letter-spacing:-.04em'>"
            "🖼️ Smart AI Gallery</h1>"
            "<p style='color:#505570;margin:2px 0 0;font-size:13px'>"
            "Reconocimiento facial · Búsqueda semántica · Triaje inteligente · Etiquetado manual</p>",
            unsafe_allow_html=True,
        )
    with stat_col:
        stats = _cached_stats(db)
        total = stats.get("total", 0)
        done = stats.get("done", 0)
        pct = done / total * 100 if total else 0.0
        safe = stats.get("safe", 0)
        rev = stats.get("review", 0)
        st.markdown(
            f'<div style="text-align:right;padding-top:10px;line-height:1.6">'
            f'<span style="font-size:12px;color:#505570">{done}/{total} procesados · {pct:.0f}%</span><br>'
            f'<span style="font-size:11px;color:#34d399">✅ {safe} seguros</span> '
            f'<span style="font-size:11px;color:#fbbf24"> · 🔶 {rev} por revisar</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Navegación principal ──────────────────────────────────────────────
    t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs(
        [
            "🎛️  Dashboard",
            "🖼️  Galería",
            "⚖️  Triaje",
            "👥  Personas",
            "🌌  Explorador 3D",
            "🧹  Limpieza",
            "📅  Línea de Tiempo",
            "⚠️  Errores",
            "🛠️  Mantenimiento",
        ]
    )

    with t1:
        render_dashboard(db)

    with t2:
        render_gallery(db)
        # Inspector de archivo desde galería
        if st.session_state.get("inspect_file_id") and not st.session_state.get("inspect_det_id"):
            _render_file_inspector(db)

    with t3:
        render_triage(db)

    with t4:
        render_people_management(db)

    with t5:
        render_semantic_explorer(db)

    with t6:
        render_cleanup(db)

    with t7:
        render_timeline(db)

    with t8:
        render_errors(db)

    with t9:
        render_maintenance(db)

    gc.collect()


# ── Inspector de archivo (desde galería) ──────────────────────────────────────
def _render_file_inspector(db: DatabaseManager) -> None:
    """
    Inspector global: muestra la imagen con bboxes de todas sus detecciones.
    Se activa desde cualquier tab cuando inspect_file_id está en session_state.
    """
    import json
    from pathlib import Path

    import cv2
    import numpy as np

    file_id = st.session_state.get("inspect_file_id")
    filepath = st.session_state.get("inspect_path", "")

    st.divider()
    st.markdown(f"### 🔍 Inspector · `{Path(filepath).name}`")
    if st.button("✖ Cerrar inspector", key="close_file_insp"):
        st.session_state.pop("inspect_file_id", None)
        st.session_state.pop("inspect_path", None)
        st.rerun()

    if not Path(filepath).exists():
        st.error("Archivo no encontrado en disco.")
        return

    dets = db.get_detections_for_file(file_id)

    stream = np.fromfile(filepath, dtype=np.uint8)
    img_bgr = cv2.imdecode(stream, cv2.IMREAD_COLOR)
    if img_bgr is None:
        st.error("No se pudo decodificar la imagen.")
        return

    h, w = img_bgr.shape[:2]
    scale = min(1.0, 860 / w)
    disp = cv2.cvtColor(cv2.resize(img_bgr, (int(w * scale), int(h * scale))), cv2.COLOR_BGR2RGB)

    COLORS = [
        (99, 102, 241),
        (236, 72, 153),
        (52, 211, 153),
        (251, 191, 36),
        (96, 165, 250),
    ]
    for i, det in enumerate(dets):
        try:
            b = json.loads(det["bbox_json"])
            col = COLORS[i % len(COLORS)]
            top = int(b["top"] * scale)
            bot = int(b["bottom"] * scale)
            left = int(b["left"] * scale)
            right = int(b["right"] * scale)
            cv2.rectangle(disp, (left, top), (right, bot), col, 2)
            label = f'{det["assigned_name"]} {det["confidence"]*100:.0f}%'
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(disp, (left, top - th - 10), (left + tw + 10, top), col, -1)
            cv2.putText(
                disp,
                label,
                (left + 5, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )
        except Exception as e:
            log.debug(f"Failed to draw bbox for detection {det.get('id')}: {e}")

    img_c, info_c = st.columns([3, 2])
    with img_c:
        st.image(disp, use_container_width=True)
    with info_c:
        st.markdown(f"**{len(dets)} detecciones**")
        known = db.get_all_identity_names()
        for det in dets:
            with st.expander(f'👤 {det["assigned_name"]} ({det["confidence"]*100:.0f}%)'):
                opts = ["(Sin cambios)"] + known + ["➕ Nuevo nombre"]
                s = st.selectbox("", opts, key=f"fi_sel_{det['id']}", label_visibility="collapsed")
                nw = ""
                if s == "➕ Nuevo nombre":
                    nw = st.text_input("", key=f"fi_n_{det['id']}", label_visibility="collapsed")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Guardar", key=f"fi_sv_{det['id']}", type="primary"):
                        n = nw if s == "➕ Nuevo nombre" else s
                        if n and n != "(Sin cambios)":
                            db.verify_detection(det["id"], n)
                            # Issue 8: Actualizar symlinks en disco
                            from core.symlink_manager import create_group_symlinks

                            create_group_symlinks(Path(filepath), [n], db, file_id)
                            st.toast(f"✅ {n}")
                            st.rerun()
                with c2:
                    if st.button("Falso+", key=f"fi_fp_{det['id']}"):
                        db.mark_false_positive(det["id"])
                        st.rerun()


if __name__ == "__main__":
    main()
