"""Controlador de ubicaciones sin dependencia de Streamlit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from application.ports import FolderOpener, MediaLocationRepository


@dataclass(frozen=True, slots=True)
class LocationView:
    media_id: int
    filename: str
    original_path: Path
    original_folder: Path
    result_folders: tuple[Path, ...]
    identities: tuple[str, ...]
    gps_label: str


class LocationController:
    def __init__(self, repository: MediaLocationRepository, opener: FolderOpener) -> None:
        self._repository = repository
        self._opener = opener

    def search(self, query: str = "") -> list[LocationView]:
        return [
            LocationView(
                media_id=location.media_id,
                filename=location.filename,
                original_path=location.original_path,
                original_folder=location.original_folder,
                result_folders=location.result_folders,
                identities=location.identities,
                gps_label=(
                    f"{location.gps.latitude:.5f}, {location.gps.longitude:.5f}"
                    if location.gps
                    else "—"
                ),
            )
            for location in self._repository.search(query)
        ]

    def open_original(self, view: LocationView) -> None:
        self._opener.open(view.original_folder)

    def open_result(self, folder: Path) -> None:
        self._opener.open(folder)
