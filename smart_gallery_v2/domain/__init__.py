"""Modelo de dominio independiente de Streamlit, SQLite y motores de IA."""

from domain.models import BoundingBox, GeoPoint, IdentityName, RegionKind

__all__ = ["BoundingBox", "GeoPoint", "IdentityName", "RegionKind"]
