import streamlit as st

from core.database import DatabaseManager
from ui.sidebar_panel import _get_control_state, _runtime_state_label, _watchdog_label


class _WatcherStub:
    def __init__(self, running: bool) -> None:
        self._running = running

    def is_running(self) -> bool:
        return self._running


def test_runtime_state_labels_are_readable():
    assert _runtime_state_label("running") == "Activo"
    assert _runtime_state_label("paused") == "En pausa"
    assert _runtime_state_label("stopped") == "Detenido"


def test_sidebar_state_helpers_use_safe_fallbacks():
    db = DatabaseManager()
    db.set_control_state("engine_state", "running")
    assert _get_control_state(db) == "running"

    original = st.session_state.get("watcher") if "watcher" in st.session_state else None
    try:
        st.session_state.watcher = _WatcherStub(True)
        assert _watchdog_label() == "Vigilando"
        st.session_state.watcher = _WatcherStub(False)
        assert _watchdog_label() == "Inactivo"
    finally:
        if original is None:
            st.session_state.pop("watcher", None)
        else:
            st.session_state.watcher = original
