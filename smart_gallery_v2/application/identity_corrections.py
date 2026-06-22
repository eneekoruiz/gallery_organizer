"""Caso de uso de corrección humana, independiente de SQLite y Streamlit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.models import IdentityName, RegionKind


@dataclass(frozen=True, slots=True)
class IdentityRegion:
    kind: RegionKind = RegionKind.WHOLE_IMAGE
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    polygon: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        if self.kind is RegionKind.RECTANGLE:
            values = (self.x, self.y, self.width, self.height)
            if any(value is None or not 0.0 <= value <= 1.0 for value in values):
                raise ValueError("La región debe estar normalizada entre 0 y 1")
            if self.width == 0 or self.height == 0:
                raise ValueError("La región no puede estar vacía")
        if self.kind is RegionKind.POLYGON and len(self.polygon) < 3:
            raise ValueError("Un polígono necesita al menos tres puntos")


@dataclass(frozen=True, slots=True)
class IdentityCorrection:
    media_id: int
    identity: IdentityName
    region: IdentityRegion = IdentityRegion()
    hard_case: str | None = None

    def __post_init__(self) -> None:
        allowed = {None, "occluded", "back_view", "helmet", "small_region", "low_light", "other"}
        if self.media_id <= 0:
            raise ValueError("media_id debe ser positivo")
        if self.hard_case not in allowed:
            raise ValueError("Tipo de caso difícil desconocido")


class IdentityCorrectionRepository(Protocol):
    def save(self, correction: IdentityCorrection) -> int: ...

    def list_for_media(self, media_id: int) -> list[dict[str, object]]: ...


class CorrectIdentity:
    def __init__(self, repository: IdentityCorrectionRepository) -> None:
        self._repository = repository

    def execute(
        self,
        media_id: int,
        display_name: str,
        region: IdentityRegion = IdentityRegion(),
        hard_case: str | None = None,
    ) -> int:
        return self._repository.save(
            IdentityCorrection(
                media_id=media_id,
                identity=IdentityName(display_name),
                region=region,
                hard_case=hard_case,
            )
        )

    def list_for_media(self, media_id: int) -> list[dict[str, object]]:
        return self._repository.list_for_media(media_id)
