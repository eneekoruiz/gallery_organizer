"""Value objects estrictos compartidos por aplicación e infraestructura."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RegionKind(str, Enum):
    WHOLE_IMAGE = "whole_image"
    RECTANGLE = "rectangle"
    POLYGON = "polygon"


@dataclass(frozen=True, slots=True)
class IdentityName:
    value: str

    def __post_init__(self) -> None:
        normalized = " ".join(self.value.strip().split())
        if not normalized:
            raise ValueError("La identidad necesita un nombre")
        if len(normalized) > 160:
            raise ValueError("El nombre de identidad es demasiado largo")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("Latitud fuera de rango")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("Longitud fuera de rango")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    top: float
    right: float
    bottom: float
    left: float
    normalized: bool = False

    def __post_init__(self) -> None:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("Bounding box vacío o invertido")
        if self.normalized and any(
            value < 0.0 or value > 1.0 for value in (self.top, self.right, self.bottom, self.left)
        ):
            raise ValueError("Bounding box normalizado fuera de [0,1]")

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def as_dict(self) -> dict[str, float | bool]:
        return {
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "left": self.left,
            "normalized": self.normalized,
        }


@dataclass(frozen=True, slots=True)
class MediaLocation:
    media_id: int
    filename: str
    original_path: Path
    result_paths: tuple[Path, ...] = ()
    identities: tuple[str, ...] = ()
    gps: GeoPoint | None = None

    @property
    def original_folder(self) -> Path:
        return self.original_path.parent

    @property
    def result_folders(self) -> tuple[Path, ...]:
        return tuple(sorted({path.parent for path in self.result_paths}, key=str))
