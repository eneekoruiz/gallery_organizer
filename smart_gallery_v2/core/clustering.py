"""
core/clustering.py — Agrupamiento IA de Rostros Desconocidos
Utiliza DBSCAN para encontrar grupos de rostros similares sin intervención humana.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

import numpy as np

if TYPE_CHECKING:
    from core.database import DatabaseManager

try:
    from sklearn.cluster import DBSCAN  # type: ignore

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
            clustering = DBSCAN(
                eps=self._eps, min_samples=self._min_samples, metric="euclidean"
            ).fit(embeddings)
            labels = clustering.labels_
        else:
            log.info(
                "Scikit-learn no disponible. Usando fallback de DBSCAN implementado en NumPy..."
            )
            # Algoritmo DBSCAN implementado directamente en NumPy
            n = len(embeddings)
            labels = np.full(n, -1, dtype=int)
            visited = np.zeros(n, dtype=bool)
            cluster_id = 0

            # Calcular la matriz de distancias Euclidianas
            # dist[i, j] = sqrt(max(0, 2 - 2 * dot_product))
            dot_product = np.dot(embeddings, embeddings.T)
            dot_product = np.clip(dot_product, -1.0, 1.0)
            dists = np.sqrt(np.maximum(0.0, 2.0 - 2.0 * dot_product))

            for i in range(n):
                if visited[i]:
                    continue
                visited[i] = True
                # Encontrar vecinos dentro del radio eps
                neighbors = np.where(dists[i] <= self._eps)[0]
                if len(neighbors) >= self._min_samples:
                    # Es un punto núcleo, iniciar cluster
                    queue = list(neighbors)
                    cluster_set = set(queue)
                    idx = 0
                    while idx < len(queue):
                        curr = queue[idx]
                        if not visited[curr]:
                            visited[curr] = True
                            curr_neighbors = np.where(dists[curr] <= self._eps)[0]
                            if len(curr_neighbors) >= self._min_samples:
                                for neighbor in curr_neighbors:
                                    if neighbor not in cluster_set:
                                        cluster_set.add(neighbor)
                                        queue.append(neighbor)
                        idx += 1

                    # Asignar cluster_id a todos los elementos alcanzables por densidad
                    for member in cluster_set:
                        if labels[member] == -1:
                            labels[member] = cluster_id
                    cluster_id += 1

        # 2. Persistir resultados
        cluster_count = 0
        with self._db._write() as c:
            for det_id, label in zip(ids, labels):
                if label != -1:  # -1 es ruido en DBSCAN
                    # El cluster_id lo guardamos sumando 1 para que sea positivo
                    c.execute(
                        "UPDATE Detections SET cluster_id = ? WHERE id = ?",
                        (int(label + 1), det_id),
                    )
                    cluster_count = max(cluster_count, int(label + 1))

        log.info(f"Clustering finalizado: {cluster_count} grupos encontrados.")
        return cluster_count


def get_cluster_suggestions(db: DatabaseManager) -> List[dict]:
    """Retorna una lista de clusters con ejemplos para la UI."""
    return db.get_clusters_with_samples()
