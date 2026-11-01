import sqlite3
import os
import json
import hashlib
import time
import threading
from pathlib import Path
import numpy as np

DB_PATH = Path(__file__).resolve().parent.parent.parent / "smart_gallery_index.db"
_db_lock = threading.Lock()

def _connect_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA mmap_size = 268435456;") # 256 MB memory-mapped I/O
    return conn

def init_index_db():
    with _db_lock:
        conn = _connect_db()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS media_index (
            file_path TEXT PRIMARY KEY,
            file_name TEXT,
            file_hash TEXT,
            dhash TEXT,
            file_size INTEGER,
            mtime REAL,
            category TEXT,
            identity TEXT,
            confidence REAL DEFAULT 0.0,
            sharpness REAL DEFAULT 0.0,
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            faces_count INTEGER DEFAULT 0,
            embedding_blob BLOB,
            updated_at REAL
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON media_index(file_hash);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dhash_sharpness ON media_index(dhash, sharpness);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_size ON media_index(file_size);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cat_ident ON media_index(category, identity);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_mtime ON media_index(mtime);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_faces ON media_index(faces_count);")
        conn.commit()
        conn.close()

_initialized_paths = set()


def get_db_connection():
    # Schema creation is lazy: importing the module must not touch the library.
    key = str(Path(DB_PATH).resolve())
    if key not in _initialized_paths:
        init_index_db()
        _initialized_paths.add(key)
    return _connect_db()

class VectorIndexEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.paths = []
        self.identities = []
        self.matrix = None
        self.norms = None
        self._loaded = False

    def load_from_db(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT file_path, identity, embedding_blob FROM media_index WHERE embedding_blob IS NOT NULL")
        rows = cur.fetchall()
        conn.close()

        paths, idents, vectors = [], [], []
        for r in rows:
            blob = r["embedding_blob"]
            if blob and len(blob) == 128 * 4:
                vec = np.frombuffer(blob, dtype=np.float32)
                paths.append(r["file_path"])
                idents.append(r["identity"])
                vectors.append(vec)

        with self.lock:
            self.paths = paths
            self.identities = idents
            if vectors:
                self.matrix = np.vstack(vectors).astype(np.float32)
                self.norms = np.linalg.norm(self.matrix, axis=1)
                self.norms[self.norms == 0] = 1e-7
            else:
                self.matrix = np.empty((0, 128), dtype=np.float32)
                self.norms = np.empty((0,), dtype=np.float32)
            self._loaded = True

    def search_similar_vectors(self, target_vector, top_k=20, threshold=0.45):
        if self.matrix is None or len(self.matrix) == 0:
            return []

        target = np.array(target_vector, dtype=np.float32)
        target_norm = np.linalg.norm(target)
        if target_norm == 0:
            return []

        with self.lock:
            dots = np.dot(self.matrix, target)
            similarities = dots / (self.norms * target_norm)
            
            k = min(top_k, len(similarities))
            if k == 0: return []
            
            top_indices = np.argpartition(-similarities, k - 1)[:k]
            top_indices = top_indices[np.argsort(-similarities[top_indices])]

            results = []
            for idx in top_indices:
                score = float(similarities[idx])
                if score >= threshold:
                    results.append({
                        "file_path": self.paths[idx],
                        "identity": self.identities[idx],
                        "similarity": round(score, 4)
                    })
            return results

    def bulk_insert_or_update(self, items):
        conn = get_db_connection()
        cur = conn.cursor()
        insert_sql = """
        INSERT OR REPLACE INTO media_index (
            file_path, file_name, file_hash, dhash, file_size, mtime, 
            category, identity, confidence, sharpness, width, height, 
            faces_count, embedding_blob, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        batch = []
        now = time.time()
        for it in items:
            emb = it.get("embedding")
            emb_blob = emb.astype(np.float32).tobytes() if emb is not None and isinstance(emb, np.ndarray) else None
            batch.append((
                it.get("file_path"),
                it.get("file_name", Path(it.get("file_path", "")).name),
                it.get("file_hash", ""),
                it.get("dhash", ""),
                it.get("file_size", 0),
                it.get("mtime", 0.0),
                it.get("category", "YO"),
                it.get("identity", "YO"),
                it.get("confidence", 1.0),
                it.get("sharpness", 0.0),
                it.get("width", 0),
                it.get("height", 0),
                it.get("faces_count", 1 if emb_blob else 0),
                emb_blob,
                now
            ))
            
        cur.executemany(insert_sql, batch)
        conn.commit()
        conn.close()

vector_engine = VectorIndexEngine()

def query_exact_duplicates_fast(limit=200):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT file_hash, COUNT(*) as count, GROUP_CONCAT(file_path, '|||') as paths, 
           MAX(file_size) as size
    FROM media_index
    WHERE file_hash IS NOT NULL AND file_hash != ''
    GROUP BY file_hash
    HAVING count > 1
    ORDER BY count DESC
    LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    duplicates = []
    for r in rows:
        paths = r["paths"].split("|||")
        duplicates.append({
            "hash": r["file_hash"],
            "count": r["count"],
            "size": r["size"],
            "files": paths
        })
    return duplicates

def query_burst_groups_fast(limit=200):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT dhash, COUNT(*) as count, GROUP_CONCAT(file_path, '|||') as paths
    FROM media_index
    WHERE dhash IS NOT NULL AND dhash != ''
    GROUP BY dhash
    HAVING count > 1
    ORDER BY count DESC
    LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    bursts = []
    for r in rows:
        paths = r["paths"].split("|||")
        bursts.append({
            "dhash": r["dhash"],
            "count": r["count"],
            "best_photo": paths[0] if paths else None,
            "files": paths
        })
    return bursts