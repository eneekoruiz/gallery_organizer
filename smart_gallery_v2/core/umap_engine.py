"""
core/umap_engine.py — Reducción Dimensional Topológica
Convierte el espacio latente de 512 dimensiones de CLIP en un universo visual 3D interactivo.
"""

from __future__ import annotations

import logging

import pandas as pd

try:
    import umap

    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False

from core.database import DatabaseManager

log = logging.getLogger(__name__)


def generate_umap_projection(db: DatabaseManager, dimensions: int = 3) -> pd.DataFrame:
    """
    Toma todos los embeddings globales (CLIP) de la base de datos y los reduce a `dimensions`
    usando UMAP (Uniform Manifold Approximation and Projection).
    """
    if not HAS_UMAP:
        log.error("UMAP no está instalado. Ejecuta 'pip install umap-learn'.")
        return pd.DataFrame()

    ids, embs = db.load_clip()
    if len(ids) == 0:
        return pd.DataFrame()

    log.info(f"Iniciando proyección UMAP para {len(ids)} vectores...")

    # Ajustar hiperparámetros de UMAP:
    # n_neighbors controla el balance entre topología local vs global (15 es buen default).
    # min_dist controla qué tan agrupados estarán los puntos visualmente.
    reducer = umap.UMAP(n_components=dimensions, random_state=42, n_neighbors=15, min_dist=0.1)

    try:
        projections = reducer.fit_transform(embs)
    except Exception as e:
        log.error(f"Error ejecutando UMAP: {e}")
        return pd.DataFrame()

    # Obtener el DataFrame de archivos de la base de datos respetando los IDs
    df = db.get_files_by_ids_with_thumbs(ids)

    # Añadir proyecciones al DataFrame original
    df_proj = pd.DataFrame(
        projections, columns=["x", "y", "z"] if dimensions == 3 else ["x", "y"], index=ids
    )

    # El join de pandas usa el índice automáticamente
    result_df = df.join(df_proj, how="inner")

    log.info("Proyección UMAP completada.")
    return result_df
