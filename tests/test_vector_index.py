import os
import sys
import unittest
import tempfile
from unittest.mock import patch
import time
import hashlib
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.services.vector_index as vector_index

from app.services.vector_index import (
    VectorIndexEngine, query_exact_duplicates_fast, query_burst_groups_fast,
    get_db_connection, init_index_db
)

class TestVectorIndexPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="gallery-index-test-")
        cls.addClassCleanup(temporary.cleanup)
        database = patch.object(vector_index, "DB_PATH", Path(temporary.name) / "index.db")
        database.start()
        cls.addClassCleanup(database.stop)
        init_index_db()
        cls.engine = VectorIndexEngine()
        
        print("\n[BENCHMARK] Generando dataset simulado de 20.000 fotos...")
        items = []
        now = time.time()
        
        cluster_centers = [np.random.randn(128).astype(np.float32) for _ in range(10)]
        for c in cluster_centers:
            c /= np.linalg.norm(c)

        for i in range(20000):
            is_dup = (i % 50 == 0 and i > 0)
            hash_idx = i - 1 if is_dup else i
            file_hash = f"hash_sha256_{hash_idx:06d}"
            
            burst_group = i % 500
            dhash = f"dhash_burst_{burst_group:04d}"
            
            cluster_id = i % 10
            noise = np.random.randn(128).astype(np.float32) * 0.08
            vec = cluster_centers[cluster_id] + noise
            vec /= np.linalg.norm(vec)

            items.append({
                "file_path": f"C:/Simulated/Photos/img_{i:05d}.jpg",
                "file_name": f"img_{i:05d}.jpg",
                "file_hash": file_hash,
                "dhash": dhash,
                "file_size": 2048000 + (i % 100) * 1024,
                "mtime": now - (i * 3600),
                "category": "Conocidos" if cluster_id > 2 else "YO",
                "identity": f"Persona_{cluster_id:02d}",
                "confidence": 0.95,
                "sharpness": 150.0 + (i % 50),
                "width": 1920,
                "height": 1080,
                "embedding": vec
            })

        t0 = time.time()
        cls.engine.bulk_insert_or_update(items)
        insert_time = time.time() - t0
        print(f"[BENCHMARK] 20.000 items insertados en SQLite en {insert_time:.3f}s")
        
        cls.engine.load_from_db()
        cls.cluster_centers = cluster_centers

    def test_01_exact_duplicates_sub_second(self):
        t0 = time.time()
        dups = query_exact_duplicates_fast(limit=200)
        elapsed_ms = (time.time() - t0) * 1000.0
        print(f"[BENCHMARK] Consulta Duplicados Exactos (20.000 items): {elapsed_ms:.2f} ms ({len(dups)} grupos encontrados)")
        
        self.assertGreater(len(dups), 0)
        self.assertLess(elapsed_ms, 500.0)  # Sub-second guarantee (< 500ms)

    def test_02_burst_groups_sub_second(self):
        t0 = time.time()
        bursts = query_burst_groups_fast(limit=200)
        elapsed_ms = (time.time() - t0) * 1000.0
        print(f"[BENCHMARK] Consulta RÃ¡fagas pHash (20.000 items): {elapsed_ms:.2f} ms ({len(bursts)} grupos encontrados)")
        
        self.assertGreater(len(bursts), 0)
        self.assertLess(elapsed_ms, 500.0)  # Sub-second guarantee (< 500ms)

    def test_03_vector_similarity_search_sub_second(self):
        target_vec = self.cluster_centers[0]
        
        t0 = time.time()
        results = self.engine.search_similar_vectors(target_vec, top_k=50, threshold=0.70)
        elapsed_ms = (time.time() - t0) * 1000.0
        print(f"[BENCHMARK] BÃºsqueda Vectorial Facial (20.000 vectores 128-D): {elapsed_ms:.2f} ms ({len(results)} matches)")
        
        self.assertGreater(len(results), 0)
        self.assertLess(elapsed_ms, 250.0)  # Vector similarity < 250ms on 20,000 vectors

    def test_04_category_identity_index_query_sub_second(self):
        conn = get_db_connection()
        cur = conn.cursor()
        
        t0 = time.time()
        cur.execute("SELECT file_path, file_name, confidence FROM media_index WHERE category = 'YO' LIMIT 60")
        rows = cur.fetchall()
        elapsed_ms = (time.time() - t0) * 1000.0
        conn.close()
        
        print(f"[BENCHMARK] Consulta Paginada B-Tree Index: {elapsed_ms:.2f} ms ({len(rows)} filas)")
        self.assertEqual(len(rows), 60)
        self.assertLess(elapsed_ms, 20.0)

if __name__ == "__main__":
    unittest.main()