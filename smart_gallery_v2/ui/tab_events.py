"""Eventos multimodales y trazabilidad de ubicaciones físicas."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
import streamlit as st

from application.event_management import EventManagementService
from core.database import DatabaseManager
from core.event_engine import EventEngine, EventSettings
from infrastructure.filesystem.folder_opener import NativeFolderOpener
from infrastructure.sqlite.location_repository import SqliteMediaLocationRepository
from presentation.location_controller import LocationController, LocationView


def render_events_and_locations(db: DatabaseManager) -> None:
    st.markdown(
        "<div class='page-intro'><h2>Eventos y ubicaciones</h2>"
        "<p>Momentos construidos con tiempo, GPS y contenido; originales y proyecciones siempre localizables.</p></div>",
        unsafe_allow_html=True,
    )
    events_tab, folders_tab = st.tabs(["Eventos", "Dónde están mis imágenes"])
    with events_tab:
        _render_events(db, EventManagementService(db))
    with folders_tab:
        _render_locations(LocationController(SqliteMediaLocationRepository(db), NativeFolderOpener()))


def _render_events(db: DatabaseManager, service: EventManagementService) -> None:
    with st.expander("Ajustar agrupamiento", expanded=False):
        c1, c2, c3 = st.columns(3)
        radius = c1.number_input("Radio máximo (km)", 0.1, 100.0, 5.0, 0.5)
        hours = c2.number_input("Separación máxima (horas)", 0.25, 48.0, 3.0, 0.25)
        semantic = c3.slider("Cohesión semántica", 0.0, 1.0, 0.48, 0.01)
        if st.button("Reconstruir eventos", type="primary", use_container_width=True):
            settings = EventSettings(
                radius_km=float(radius),
                time_window_hours=float(hours),
                semantic_threshold=float(semantic),
            )
            with st.spinner("Agrupando recuerdos..."):
                count = EventEngine(db, settings).rebuild()
            st.toast(f"{count} eventos construidos")
            st.rerun()

    events = EventEngine(db).list_events()
    if not events:
        st.info("Todavía no hay eventos. Reconstrúyelos cuando hayas procesado varias imágenes.")
        return
    geo = pd.DataFrame(
        [{"lat": e["centroid_lat"], "lon": e["centroid_lon"]} for e in events if e["centroid_lat"] is not None]
    )
    if not geo.empty:
        st.map(geo, use_container_width=True, zoom=5)
    for event in events:
        with st.container(border=True):
            cover, details = st.columns([1, 3])
            with cover:
                path = event.get("cover_path")
                if path and Path(path).exists():
                    st.image(path, use_container_width=True)
            with details:
                st.markdown(f"### {event['title']}")
                st.caption(
                    f"{event['starts_at'][:16]} — {event['ends_at'][:16]} · "
                    f"{event['media_count']} imágenes · confianza {event['confidence']:.0%}"
                )
                if event.get("centroid_lat") is not None:
                    st.caption(f"GPS: {event['centroid_lat']:.5f}, {event['centroid_lon']:.5f}")
                title = st.text_input("Nombre del evento", event["title"], key=f"event_title_{event['id']}")
                locked = st.toggle(
                    "Conservar mis cambios al reagrupar",
                    value=bool(event["manually_locked"]),
                    key=f"event_lock_{event['id']}",
                )
                if st.button("Guardar evento", key=f"event_save_{event['id']}"):
                    try:
                        service.rename(int(event["id"]), title, locked=locked)
                    except (ValueError, LookupError) as exc:
                        st.error(str(exc))
                    else:
                        st.toast("Evento guardado")
                        st.rerun()
            with st.expander("Ver todas las imágenes"):
                columns = st.columns(6)
                for index, item in enumerate(service.media(int(event["id"]))):
                    with columns[index % 6]:
                        if item.path.exists():
                            st.image(str(item.path), use_container_width=True)
                        st.caption(item.filename)


def _render_locations(controller: LocationController) -> None:
    st.caption("Encuentra el original y cada carpeta de resultados donde aparece.")
    query = st.text_input("Buscar archivo, carpeta o persona", placeholder="Ej. Bilbao, Ana, IMG_2024")
    views = controller.search(query)
    records = [
        {
            "ID": view.media_id,
            "Imagen": view.filename,
            "Carpeta original": str(view.original_folder),
            "Carpetas organizadas": "\n".join(map(str, view.result_folders)) or "—",
            "Personas": ", ".join(view.identities) or "—",
            "GPS": view.gps_label,
        }
        for view in views
    ]
    st.caption(f"{len(records)} imágenes")
    st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)
    if not views:
        return
    by_id = {view.media_id: view for view in views}
    media_id = st.selectbox(
        "Abrir ubicación de una imagen",
        list(by_id),
        format_func=lambda value: by_id[value].filename,
    )
    selected: LocationView = by_id[media_id]
    original_col, result_col = st.columns(2)
    if original_col.button("Abrir carpeta original", use_container_width=True):
        _open(lambda: controller.open_original(selected))
    folder = (
        result_col.selectbox("Carpeta organizada", selected.result_folders, label_visibility="collapsed")
        if selected.result_folders
        else None
    )
    if result_col.button("Abrir carpeta organizada", disabled=folder is None, use_container_width=True):
        if folder is not None:
            _open(lambda: controller.open_result(folder))
    st.code(str(selected.original_path), language=None)


def _open(action: Callable[[], None]) -> None:
    try:
        action()
    except (FileNotFoundError, OSError) as exc:
        st.error(f"No se pudo abrir la carpeta: {exc}")
