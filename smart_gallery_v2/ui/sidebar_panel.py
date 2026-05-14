"""
ui/sidebar_panel.py — Barra lateral fija de ayuda y estado
Flujo de trabajo · Atajos · Bandejas · Estado del motor y del watchdog
"""

from __future__ import annotations

import logging

import streamlit as st

from core.config import CONTROL_STATE_KEY, DIR_ENTRADA, DIR_RESULT
from core.database import DatabaseManager

log = logging.getLogger(__name__)


def render_help_sidebar(db: DatabaseManager) -> None:
    state = _get_control_state(db)
    engine_state = _runtime_state_label(state)
    watcher_state = _watchdog_label()
    maintenance_pending = _maintenance_pending(db)

    st.markdown(
        """
        <div style='padding:2px 0 10px'>
          <div style='font-size:12px;color:#7f88a8;text-transform:uppercase;letter-spacing:.12em'>Smart AI Gallery</div>
          <div style='font-size:20px;font-weight:800;letter-spacing:-.04em;color:#eef0f8;margin-top:4px'>
            Asistente de flujo
          </div>
          <div style='font-size:13px;color:#a6afc9;margin-top:6px;line-height:1.55'>
            La barra lateral resume el proceso, los atajos y el estado operativo en una sola vista.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _status_card(
        "Motor", engine_state, "Proceso de clasificación y organización", "c-teal"
    )
    _status_card(
        "Watchdog",
        watcher_state,
        f"Vigilancia de `{DIR_ENTRADA.name}` y `{DIR_RESULT.name}`",
        "c-blue",
    )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    _section_title("Flujo de trabajo")
    st.markdown(
        """
        <div style='line-height:1.65;color:#d7dcec;font-size:13px'>
        1. <strong>Arrastra</strong> fotos o vídeos a <code>Para Organizar</code>.
        <br>2. Pulsa <strong>Sincronizar</strong> o deja el watchdog actuar.
        <br>3. Revisa <strong>Seguros</strong>, <strong>Dudosos</strong> y <strong>Sin clasificar</strong>.
        <br>4. Usa <strong>Deshacer último cambio</strong> solo después de validar, renombrar o etiquetar manualmente.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _section_title("Atajos útiles")
    st.markdown(
        """
        <div style='display:grid;gap:8px'>
          <div style='background:#14172280;border:1px solid #1c1f2e;border-radius:12px;padding:10px 12px'>
            <div style='font-size:12px;color:#7f88a8'>Acción principal</div>
            <div style='font-size:13px;color:#eef0f8;font-weight:700'>Start / Pause / Stop desde Dashboard</div>
          </div>
          <div style='background:#14172280;border:1px solid #1c1f2e;border-radius:12px;padding:10px 12px'>
            <div style='font-size:12px;color:#7f88a8'>Corrección rápida</div>
            <div style='font-size:13px;color:#eef0f8;font-weight:700'>Entrar a Triaje y confirmar o denegar con 1 clic</div>
          </div>
          <div style='background:#14172280;border:1px solid #1c1f2e;border-radius:12px;padding:10px 12px'>
            <div style='font-size:12px;color:#7f88a8'>Undo contextual</div>
            <div style='font-size:13px;color:#eef0f8;font-weight:700'>Solo revierte validaciones, renombres y faceless tags</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _section_title("Bandejas")
    st.markdown(
        """
        <div style='line-height:1.6;color:#d7dcec;font-size:13px'>
        <strong>Seguros</strong>: alta confianza, revisa solo si quieres afinar.
        <br><strong>Dudosos</strong>: validación rápida, 1 clic.
        <br><strong>Sin clasificar</strong>: fotos sin detección útil o sin identidad.
        <br><strong>Faceless</strong>: etiquetas manuales cuando la cara no aparece.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _section_title("Mantenimiento")
    st.markdown(
        f"""
        <div style='background:linear-gradient(145deg,#10121a,#14172280);border:1px solid #1c1f2e;border-radius:16px;padding:14px'>
          <div style='font-size:13px;color:#d7dcec;line-height:1.55'>
            Detecta y corrige estados huérfanos: archivos borrados en disco, symlinks rotos o índices desactualizados.
          </div>
          <div style='margin-top:8px;font-size:12px;color:#7f88a8'>Estado: {'Atención requerida' if maintenance_pending else 'Limpio'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🧹 Limpiar huérfanos", use_container_width=True):
        files_removed = db.cleanup_missing_files(limit=500)
        links_removed = db.cleanup_broken_symlinks(limit=500)
        st.toast(
            f"🧹 {files_removed} archivos huérfanos y {links_removed} enlaces rotos limpiados."
        )
        st.rerun()
    if st.button("🔁 Reindexar FAISS", use_container_width=True):
        try:
            engine = st.session_state.get("engine")
            if engine:
                engine._reload_faiss()  # noqa: SLF001 - UI maintenance action
                st.toast("🔁 FAISS reindexado.")
            else:
                st.toast("Motor no disponible para reindexar.")
        except Exception:
            log.exception("FAISS reindex failed from sidebar")
            st.toast("No se pudo reindexar FAISS.")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _section_title("Notas de uso")
    st.caption(
        "La interfaz está pensada para trabajo continuo: deja el motor en marcha, revisa por lotes y usa el panel lateral como referencia rápida."
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _section_title("Programación automática")
    st.caption(
        "Nota: la tarea se ejecuta diariamente a las 03:00 vía Windows Task Scheduler."
    )
    if st.button("📋 Ver programación actual", use_container_width=True):
        try:
            from subprocess import run

            result = run(
                [
                    "schtasks",
                    "/Query",
                    "/TN",
                    "SmartGallery_Maintenance",
                    "/V",
                    "/FO",
                    "LIST",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                st.code(result.stdout, language="text")
            else:
                st.warning("No se pudo obtener detalles de la tarea programada.")
        except Exception as e:
            st.warning(f"Error al consultar tarea: {e}")
    st.caption(
        "Para cambiar hora/frecuencia, edita manualmente vía Panel de Control → Tareas programadas."
    )


def _status_card(title: str, state: str, subtitle: str, css_class: str) -> None:
    st.markdown(
        f"""
        <div style='background:linear-gradient(145deg,#10121a,#14172280);border:1px solid #1c1f2e;border-radius:16px;padding:14px 14px 12px;margin-top:10px'>
          <div style='font-size:12px;color:#7f88a8;text-transform:uppercase;letter-spacing:.12em'>{title}</div>
          <div style='display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:6px'>
            <div style='font-size:14px;color:#eef0f8;font-weight:800'>{state}</div>
            <span class='tier-badge {css_class}' style='font-size:10px'>{state}</span>
          </div>
          <div style='font-size:12px;color:#a6afc9;line-height:1.45;margin-top:6px'>{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section_title(title: str) -> None:
    st.markdown(
        f"<div style='font-size:12px;color:#7f88a8;text-transform:uppercase;letter-spacing:.12em;margin:4px 0 8px'>{title}</div>",
        unsafe_allow_html=True,
    )


def _get_control_state(db: DatabaseManager) -> str:
    try:
        return db.get_control_state(CONTROL_STATE_KEY) or "stopped"
    except Exception:
        log.debug("Control state unavailable; falling back to stopped")
        return "stopped"


def _runtime_state_label(state: str) -> str:
    mapping = {
        "running": "Activo",
        "paused": "En pausa",
        "stopped": "Detenido",
    }
    return mapping.get(state, "Desconocido")


def _watchdog_label() -> str:
    try:
        watcher = st.session_state.get("watcher")
        if watcher and watcher.is_running():
            return "Vigilando"
        return "Inactivo"
    except Exception:
        log.debug("Watchdog state unavailable; falling back to Inactivo")
        return "Inactivo"


def _maintenance_pending(db: DatabaseManager) -> bool:
    try:
        return db.has_pending_maintenance()
    except Exception:
        log.debug("Maintenance status unavailable; assuming clean")
        return False
