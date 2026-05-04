"""
ui/tab_dashboard.py — Dashboard Principal
Métricas triage · Controles ▶⏸⏹ · Logs terminal · Watchdog status · Sync
"""

from __future__ import annotations

import time
from pathlib import Path
from queue import Empty, Queue
from typing import Optional

import streamlit as st

from core.config import DIR_ENTRADA, EXT_TODAS, EXT_VIDEO, CONTROL_STATE_KEY
from core.database import DatabaseManager
from core.watchdog_engine import FileSystemWatcher, make_db_callback
from core.worker import ProcessingEngine
from ui.styles import log_line, mc


# ──────────────────────────────────────────────────────────────────────────────
# Session State Bootstrap
# ──────────────────────────────────────────────────────────────────────────────
def _boot(db: DatabaseManager) -> None:
    if "log_q" not in st.session_state:
        st.session_state.log_q   = Queue(maxsize=600)
    if "logs" not in st.session_state:
        st.session_state.logs    = []
    if "engine" not in st.session_state:
        st.session_state.engine  = ProcessingEngine(db, st.session_state.log_q)
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


# ──────────────────────────────────────────────────────────────────────────────
# Render
# ──────────────────────────────────────────────────────────────────────────────
def render_dashboard(db: DatabaseManager) -> None:
    _boot(db)
    engine:  ProcessingEngine = st.session_state.engine
    log_q:   Queue            = st.session_state.log_q
    watcher: FileSystemWatcher= st.session_state.watcher

    # ── Métricas ──────────────────────────────────────────────────────────
    stats      = db.get_stats()
    total      = stats.get("total",      0)
    done       = stats.get("done",       0)
    pending    = stats.get("pending",    0)
    errors     = stats.get("errors",     0)
    safe       = stats.get("safe",       0)
    review     = stats.get("review",     0)
    unclass    = stats.get("unclassified",0)

    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    c1.markdown(mc("Total",      total,   "c-purple"), unsafe_allow_html=True)
    c2.markdown(mc("Procesados", done,    "c-teal"),   unsafe_allow_html=True)
    c3.markdown(mc("Cola",       pending, "c-amber"),  unsafe_allow_html=True)
    c4.markdown(mc("Errores",    errors,  "c-red"),    unsafe_allow_html=True)
    c5.markdown(mc("✅ Seguros", safe,    "c-green"),  unsafe_allow_html=True)
    c6.markdown(mc("🔶 Revisar", review,  "c-amber"),  unsafe_allow_html=True)
    c7.markdown(mc("❓ Sin clas.",unclass,"c-blue"),   unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Progreso ──────────────────────────────────────────────────────────
    pct = done / total if total else 0.0
    st.progress(pct, text=f"{done}/{total} archivos · {pct*100:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Controles ─────────────────────────────────────────────────────────
    is_running = engine.is_running()
    is_paused  = engine.is_paused()

    ctrl = st.columns([2,2,2,2,3,3])
    with ctrl[0]:
        lbl = "▶ Reanudar" if is_paused else "▶ Iniciar"
        if st.button(lbl, type="primary", disabled=is_running and not is_paused):
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
        if st.button("↩ Deshacer último cambio"):
            msg = db.undo_last()
            st.toast(msg or "Nada que deshacer.")
    with ctrl[5]:
        # Watchdog toggle
        if watcher.is_running():
            if st.button("👁 Watchdog activo — Desactivar"):
                watcher.stop(); st.rerun()
        else:
            if st.button("👁 Activar Watchdog", type="primary"):
                watcher.start(); st.rerun()

    # ── Status badges ─────────────────────────────────────────────────────
    sb1, sb2 = st.columns(2)
    with sb1:
        if is_running and not is_paused:
            st.success("🟢 Motor activo")
        elif is_paused:
            st.warning("🟡 Motor en pausa — reanudar para continuar")
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
        time.sleep(0.7)
        st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _sync(db: DatabaseManager, log_q: Queue) -> int:
    count = 0
    for p in DIR_ENTRADA.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXT_TODAS:
            mt = "video" if p.suffix.lower() in EXT_VIDEO else "image"
            if db.upsert_file(str(p), p.name, mt):
                count += 1
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
