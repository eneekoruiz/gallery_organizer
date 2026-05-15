"""
core/clustering.py — Agrupamiento IA de Rostros Desconocidos
Utiliza DBSCAN para encontrar grupos de rostros similares sin intervención humana.
"""

from __future__ import annotations
import logging
import numpy as np
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from core.database import DatabaseManager

try:
    from sklearn.cluster import DBSCAN
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

log = logging.getLogger(__name__)

class FaceClustering:
    def __init__(self, db: DatabaseManager, eps: float = 0.45, min_samples: int = 3):
        self._db = db
        self._eps = eps
        self._min_samples = min_samples

    def run(self) -> int:
        """
        Ejecuta el clustering sobre todas las detecciones de rostros desconocidos.
        Retorna el número de clusters encontrados.
        """
        log.info("Iniciando Face Clustering...")
        
        # 1. Cargar detecciones sin nombre y con embedding
        # format: [(det_id, embedding_blob), ...]
        detections = self._db.get_unlabeled_face_embeddings()
        if len(detections) < self._min_samples:
            log.info("No hay suficientes rostros para clustering.")
            return 0
        
        ids = [d[0] for d in detections]
        # Convertir blobs a numpy array
        embeddings = np.array([np.frombuffer(d[1], dtype=np.float32) for d in detections])
        
        # Normalizar embeddings para similitud coseno (distancia L2 en esfera unidad es proporcional a coseno)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / (norms + 1e-8)

        if HAS_SKLEARN:
            # DBSCAN sobre embeddings normalizados
            clustering = DBSCAN(eps=self._eps, min_samples=self._min_samples, metric='euclidean').fit(embeddings)
            labels = clustering.labels_
        else:
            log.warning("Scikit-learn no disponible. Usando fallback simple (K-Means/Distancia no implementado).")
            return 0

        # 2. Persistir resultados
        cluster_count = 0
        with self._db._write() as c:
            for det_id, label in zip(ids, labels):
                if label != -1:  # -1 es ruido en DBSCAN
                    # El cluster_id lo guardamos sumando 1 para que sea positivo
                    c.execute("UPDATE Detections SET cluster_id = ? WHERE id = ?", (int(label + 1), det_id))
                    cluster_count = max(cluster_count, label + 1)
        
        log.info(f"Clustering finalizado: {cluster_count} grupos encontrados.")
        return int(cluster_count)

def get_cluster_suggestions(db: DatabaseManager) -> List[dict]:
    """Retorna una lista de clusters con ejemplos para la UI."""
    return db.get_clusters_with_samples()
