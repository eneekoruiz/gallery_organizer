"""
ui/tab_dashboard.py — Dashboard Principal
Métricas triage · Controles ▶⏸⏹ · Logs terminal · Watchdog status · Sync
"""

from __future__ import annotations

import time
from queue import Empty, Queue
from typing import Optional

import pandas as pd
import streamlit as st

from core.config import CONTROL_STATE_KEY, DIR_ENTRADA
from core.database import DatabaseManager
from core.watchdog_engine import FileSystemWatcher, make_db_callback
from core.worker import ProcessingEngine
from ui.styles import log_line, mc

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None


# ──────────────────────────────────────────────────────────────────────────────
# Session State Bootstrap
# ──────────────────────────────────────────────────────────────────────────────
def _boot(db: DatabaseManager) -> None:
    if "log_q" not in st.session_state:
        st.session_state.log_q = Queue(maxsize=600)
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "engine" not in st.session_state:
        st.session_state.engine = ProcessingEngine(db, st.session_state.log_q)
        # Restaurar estado persistente del motor
        try:
            state = db.get_control_state(CONTROL_STATE_KEY)
            if state == "running":
                st.session_state.engine.start()
            elif state == "paused":
                # arrancar y pausar para mantener posición
                st.session_state.engine.start()
                st.session_state.engine.pause()
        except Exception:
            pass
    if "watcher" not in st.session_state:
        w = FileSystemWatcher(
            st.session_state.log_q,
            watch_path=DIR_ENTRADA,
            db_callback=make_db_callback(db),
        )
        w.start()
        st.session_state.watcher = w

    # Issue 7: Identificador de sesión único para este tab
    if "session_id" not in st.session_state:
        import uuid

        st.session_state.session_id = str(uuid.uuid4())


# ──────────────────────────────────────────────────────────────────────────────
# Render
# ──────────────────────────────────────────────────────────────────────────────
def render_dashboard(db: DatabaseManager) -> None:
    _boot(db)
    engine: ProcessingEngine = st.session_state.engine
    log_q: Queue = st.session_state.log_q
    watcher: FileSystemWatcher = st.session_state.watcher

    # ── Métricas ──────────────────────────────────────────────────────────
    stats = _cached_stats(db)
    total = stats.get("total", 0)
    done = stats.get("done", 0)
    pending = stats.get("pending", 0)
    errors = stats.get("errors", 0)
    safe = stats.get("safe", 0)
    review = stats.get("review", 0)
    unclass = stats.get("unclassified", 0)

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.markdown(mc("Total", total, "c-purple"), unsafe_allow_html=True)
    c2.markdown(mc("Procesados", done, "c-teal"), unsafe_allow_html=True)
    c3.markdown(mc("Cola", pending, "c-amber"), unsafe_allow_html=True)
    c4.markdown(mc("Errores", errors, "c-red"), unsafe_allow_html=True)
    c5.markdown(mc("✅ Seguros", safe, "c-green"), unsafe_allow_html=True)
    c6.markdown(mc("🔶 Revisar", review, "c-amber"), unsafe_allow_html=True)
    c7.markdown(mc("❓ Sin clas.", unclass, "c-blue"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Actividad Temporal ──────────────────────────────────────────────
    st.markdown("#### 📈 Actividad Temporal")
    df_time = db.get_timeline_df()
    if not df_time.empty:
        df_time["exif_date"] = pd.to_datetime(df_time["exif_date"])
        # Agrupar por mes para el gráfico
        df_month = df_time.resample("M", on="exif_date").sum().reset_index()
        st.area_chart(df_month, x="exif_date", y="count", height=180, use_container_width=True)
    else:
        st.info("Sin datos temporales suficientes para mostrar actividad.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Progreso ──────────────────────────────────────────────────────────
    pct = done / total if total else 0.0
    st.progress(pct, text=f"{done}/{total} archivos · {pct * 100:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Guía contextual de uso ───────────────────────────────────────────
    last_tx = db.get_last_tx()
    _render_action_guide(last_tx)

    # ── Controles ─────────────────────────────────────────────────────────
    is_running = engine.is_running()
    is_paused = engine.is_paused()

    ctrl = st.columns([2, 2, 2, 2, 3, 2, 2])
    with ctrl[0]:
        lbl = "▶ Reanudar" if is_paused else "▶ Iniciar"
        # Issue 7: Comprobar si otra sesión ya tiene el control
        current_owner = db.get_control_state("engine_owner")
        is_locked = current_owner and current_owner != st.session_state.session_id and is_running

        if st.button(lbl, type="primary", disabled=(is_running and not is_paused) or is_locked):
            db.set_control_state("engine_owner", st.session_state.session_id)
            engine.start()
            try:
                db.set_control_state(CONTROL_STATE_KEY, "running")
            except Exception:
                pass
            st.rerun()
    with ctrl[1]:
        if st.button("⏸ Pausar", disabled=not is_running or is_paused):
            engine.pause()
            try:
                db.set_control_state(CONTROL_STATE_KEY, "paused")
            except Exception:
                pass
            st.rerun()
    with ctrl[2]:
        if st.button("⏹ Detener", disabled=not is_running):
            engine.stop()
            st.session_state.engine = ProcessingEngine(db, log_q)
            try:
                db.set_control_state(CONTROL_STATE_KEY, "stopped")
            except Exception:
                pass
            st.rerun()
    with ctrl[3]:
        if st.button("🔄 Sincronizar"):
            n = _sync(db, log_q)
            st.toast(f"✔ {n} nuevos archivos en cola.")
    with ctrl[4]:
        undo_disabled = last_tx is None or bool(last_tx.get("undone"))
        if st.button("↩ Deshacer último cambio", disabled=undo_disabled):
            msg = db.undo_last()
            st.toast(msg or "Nada que deshacer.")
    with ctrl[5]:
        # Watchdog toggle
        if watcher.is_running():
            if st.button("👁 Watchdog activo — Desactivar"):
                watcher.stop()
                st.rerun()
        else:
            if st.button("👁 Activar Watchdog", type="primary"):
                watcher.start()
                st.rerun()
    with ctrl[6]:
        if st.button("🧹 Limpiar"):
            res = db.cleanup_db()
            st.toast(f"🧹 Limpieza: {res['removed_files']} archivos huérfanos eliminados.")
            st.rerun()

    # ── Status badges ─────────────────────────────────────────────────────
    sb1, sb2 = st.columns(2)
    with sb1:
        owner = db.get_control_state("engine_owner")
        if is_running and not is_paused:
            if owner == st.session_state.session_id:
                st.success("🟢 Motor activo (esta pestaña)")
            else:
                st.warning(f"🟠 Motor activo (otra pestaña: {owner[:8] if owner else '?'}...)")
        elif is_paused:
            st.warning("🟡 Motor en pausa")
        else:
            st.info("⚪ Motor inactivo")
    with sb2:
        if watcher.is_running():
            st.success(f"👁 Watchdog escuchando → `{DIR_ENTRADA.name}/`")
        else:
            st.error("👁 Watchdog desactivado — los cambios no se detectan en tiempo real")

    st.divider()

    # ── Log Terminal ──────────────────────────────────────────────────────
    st.markdown("#### 📋 Actividad del Motor")
    _drain(log_q)
    html = "\n".join(st.session_state.logs[-40:])
    st.markdown(f'<div class="log-term">{html}</div>', unsafe_allow_html=True)

    # ── Auto-refresh si motor activo ──────────────────────────────────────
    if is_running and not is_paused:
        if st_autorefresh is not None:
            st_autorefresh(interval=1200, key="dashboard_refresh")
        else:
            time.sleep(0.15)
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _sync(db: DatabaseManager, log_q: Queue) -> int:
    count = 0
    from core.scanner import scan_directory

    count = scan_directory(db)
    log_q.put(("INFO", f"Sync: {count} archivos nuevos en cola."))
    return count


def _drain(log_q: Queue) -> None:
    if "logs" not in st.session_state:
        st.session_state.logs = []
    try:
        while True:
            tipo, msg = log_q.get_nowait()
            if tipo == "PROGRESS":
                continue
            st.session_state.logs.append(log_line(tipo, str(msg)))
    except Empty:
        pass


@st.cache_data(ttl=1.5, show_spinner=False)
def _cached_stats(_db: DatabaseManager) -> dict[str, int]:
    return _db.get_stats()


def _render_action_guide(last_tx: Optional[dict]) -> None:
    reversible = {
        "VERIFY": "Validación de rostros seleccionados o confirmados en triaje.",
        "RENAME": "Renombrado masivo o individual de identidades.",
        "FACELESS": "Etiquetado manual de una persona sin rostro visible.",
    }

    if last_tx:
        action = str(last_tx.get("action", ""))
        detail = reversible.get(action, "Cambio reversible reciente.")
        count = int(last_tx.get("before_count", 0) or 0)
        status = "Disponible" if not last_tx.get("undone") else "Ya deshecho"
        st.markdown(
            f'<div style="background:linear-gradient(145deg,#10121a,#14172280);border:1px solid #1c1f2e;border-radius:16px;padding:16px 18px;margin:10px 0 14px">'
            f'<div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap">'
            f'<div><div style="font-size:12px;color:#7f88a8;text-transform:uppercase;letter-spacing:.12em">Ctrl+Z contextual</div>'
            f'<div style="font-size:15px;color:#eef0f8;font-weight:700;margin-top:4px">Última acción: {action or "Ninguna"} · {count} elemento(s)</div>'
            f'<div style="font-size:13px;color:#a6afc9;margin-top:6px">{detail}</div></div>'
            f'<div><span style="display:inline-block;padding:6px 10px;border-radius:999px;background:rgba(99,102,241,.15);color:#8ea0ff;font-weight:700;font-size:12px">{status}</span></div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:linear-gradient(145deg,#10121a,#14172280);border:1px solid #1c1f2e;border-radius:16px;padding:16px 18px;margin:10px 0 14px">'
            '<div style="font-size:12px;color:#7f88a8;text-transform:uppercase;letter-spacing:.12em">Ctrl+Z contextual</div>'
            '<div style="font-size:15px;color:#eef0f8;font-weight:700;margin-top:4px">No hay una acción reversible reciente</div>'
            '<div style="font-size:13px;color:#a6afc9;margin-top:6px">Usa el deshacer después de validar, renombrar o etiquetar manualmente. No revierte navegación ni cambios del sistema de archivos.</div>'
            "</div>",
            unsafe_allow_html=True,
        )
