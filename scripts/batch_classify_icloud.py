"""Classify unorganized photos from iCloud Photos into canonical albums.

For each iCloud photo:
- If a face matches a known person (>= 0.60): copy to Resultados/<Cat>/<Persona>/ and record in apple_db.json.
- If no faces are detected: copy to Resultados/Revision_Interactiva/Sin_Rostro/ and record in apple_db.json.
- If ambiguous: leave in iCloud / Para Revisar.
"""

import sys
import os
import json
import time
import pickle
import shutil
import unicodedata
from pathlib import Path
import cv2
import numpy as np

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.globals import detector, recognizer, clear_gallery_cache

ICLOUD_DIR = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")
BASE_RESULTADOS = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
APPLE_DB_FILE = Path(r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\apple_db.json")

def norm_str(s):
    if not isinstance(s, str): return ''
    s = s.replace('\ufffd', '')
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower().strip()

# Set process priority to BelowNormal to avoid CPU starvation
try:
    import psutil
    p = psutil.Process()
    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception:
    pass

# Load centroids
with open('centroids.pkl', 'rb') as f:
    centroids_raw = pickle.load(f)

centroids = {}
keys_list = []
matrix_list = []
for k, v in centroids_raw.items():
    if v is not None and isinstance(k, tuple):
        arr = np.array(v, dtype=np.float32).flatten()
        norm = np.linalg.norm(arr)
        if norm > 0:
            norm_v = arr / norm
            centroids[k] = norm_v
            keys_list.append(k)
            matrix_list.append(norm_v)

centroid_matrix = np.stack(matrix_list)
print(f"Loaded {len(centroids)} normalized centroids.")

# Load faces_cache
faces_cache = {}
for p in [Path('faces_cache.pkl'), Path('faces_cache_v2.pkl')]:
    if p.exists():
        try:
            with open(p, 'rb') as f:
                faces_cache.update(pickle.load(f))
        except Exception:
            pass
print(f"Loaded {len(faces_cache)} faces_cache entries.")

# Load apple_db
apple_db = {}
if APPLE_DB_FILE.exists():
    try:
        with open(APPLE_DB_FILE, 'r', encoding='utf-8') as f:
            apple_db = json.load(f)
    except Exception:
        apple_db = {}
print(f"Loaded {len(apple_db)} apple_db entries.")

def save_apple_db():
    try:
        with open(APPLE_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(apple_db, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving apple_db: {e}")

def run_icloud_classification(max_files=None, dry_run=False):
    if not ICLOUD_DIR.exists():
        print("iCloud Photos directory not found!")
        return

    # Find already existing filenames in Resultados
    existing_in_resultados = set()
    for root, dirs, files in os.walk(str(BASE_RESULTADOS)):
        for file in files:
            existing_in_resultados.add(file.lower())
            
    print(f"Found {len(existing_in_resultados)} existing files in Resultados.")

    valid_img_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}
    
    candidate_files = []
    for f in ICLOUD_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in valid_img_exts:
            if f.name.lower() not in existing_in_resultados:
                candidate_files.append(f)
                
    total_candidates = len(candidate_files)
    if max_files:
        candidate_files = candidate_files[:max_files]
        
    print(f"Found {total_candidates} unorganized iCloud images. Processing {len(candidate_files)}...")

    stats = {
        'total': len(candidate_files),
        'matched_person': 0,
        'sin_rostro': 0,
        'ambiguous_left': 0,
        'errors': 0
    }
    
    t0 = time.time()
    
    for idx, fpath in enumerate(candidate_files, 1):
        try:
            # 1. Feature extraction
            feature_vectors = []
            cached_entries = faces_cache.get(str(fpath)) or faces_cache.get(fpath.name)
            if cached_entries and isinstance(cached_entries, list):
                for entry in cached_entries:
                    feat = entry.get('feature')
                    if feat is not None:
                        arr = np.array(feat, dtype=np.float32).flatten()
                        n = np.linalg.norm(arr)
                        if n > 0:
                            feature_vectors.append(arr / n)

            if not feature_vectors:
                b = np.fromfile(str(fpath), dtype=np.uint8)
                img = cv2.imdecode(b, cv2.IMREAD_COLOR)
                if img is None:
                    continue
                    
                h, w = img.shape[:2]
                max_d = 800
                scale = 1.0
                if max(h, w) > max_d:
                    scale = max_d / max(h, w)
                    det_img = cv2.resize(img, (int(w*scale), int(h*scale)))
                else:
                    det_img = img
                    
                dh, dw = det_img.shape[:2]
                detector.setInputSize((dw, dh))
                _, faces = detector.detect(det_img)
                
                if faces is not None and len(faces) > 0:
                    for face in faces:
                        if scale != 1.0:
                            face_full = face.copy()
                            face_full[:14] /= scale
                        else:
                            face_full = face
                            
                        aligned = recognizer.alignCrop(img, face_full)
                        feat = recognizer.feature(aligned)[0]
                        norm = np.linalg.norm(feat)
                        if norm > 0:
                            feature_vectors.append(feat / norm)
                            
                    faces_cache[str(fpath)] = [{'feature': fv.tolist(), 'identity': 'Desconocido'} for fv in feature_vectors]

            # 2. Decision
            if not feature_vectors:
                # No faces detected -> Sin_Rostro
                dest_dir = BASE_RESULTADOS / "Revision_Interactiva" / "Sin_Rostro"
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / fpath.name
                stats['sin_rostro'] += 1
                if not dry_run:
                    shutil.copy2(str(fpath), str(dest_path))
                    apple_db[str(dest_path)] = {
                        'category': 'Revision_Interactiva',
                        'identity': 'Sin_Rostro',
                        'original_icloud_path': str(fpath),
                        'score': 0.0,
                        'faces_count': 0,
                        'metadata': {}
                    }
                continue

            # Faces found: check similarity to all 406 centroids
            best_sim = -1.0
            best_key = None
            
            for fv in feature_vectors:
                sims = np.dot(centroid_matrix, fv)
                top_idx = np.argmax(sims)
                top_sim = float(sims[top_idx])
                if top_sim > best_sim:
                    best_sim = top_sim
                    best_key = keys_list[top_idx]

            # Threshold for confident assignment: >= 0.60
            if best_sim >= 0.60 and best_key:
                dest_cat, dest_ident = best_key
                dest_dir = BASE_RESULTADOS / dest_cat / dest_ident
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / fpath.name
                stats['matched_person'] += 1
                print(f"  [ICLOUD -> {dest_ident}] '{fpath.name}' (Sim: {best_sim:.3f})", flush=True)
                if not dry_run:
                    shutil.copy2(str(fpath), str(dest_path))
                    apple_db[str(dest_path)] = {
                        'category': dest_cat,
                        'identity': dest_ident,
                        'original_icloud_path': str(fpath),
                        'score': round(best_sim, 3),
                        'faces_count': len(feature_vectors),
                        'metadata': {}
                    }
            else:
                stats['ambiguous_left'] += 1

        except Exception as e:
            stats['errors'] += 1

        if idx % 50 == 0 or idx == len(candidate_files):
            elapsed = time.time() - t0
            rate = idx / (elapsed + 1e-5)
            print(f"[{idx}/{len(candidate_files)}] Matched: {stats['matched_person']} | "
                  f"Sin Rostro: {stats['sin_rostro']} | Ambiguous: {stats['ambiguous_left']} | "
                  f"Rate: {rate:.1f} img/s", flush=True)
            if not dry_run:
                save_apple_db()
                try:
                    with open('faces_cache_v2.pkl', 'wb') as fc_f:
                        pickle.dump(faces_cache, fc_f)
                except Exception:
                    pass

    elapsed = time.time() - t0
    print("\n--- RESUMEN CLASIFICACIÓN ICLOUD ---")
    print(f"Total procesadas: {stats['total']} en {elapsed:.1f}s")
    print(f"Asignadas a personas confirmadas (sim >= 0.60): {stats['matched_person']}")
    print(f"Enviadas a Sin_Rostro: {stats['sin_rostro']}")
    print(f"Ambiguas (en iCloud / Para Revisar): {stats['ambiguous_left']}")
    print(f"Errores: {stats['errors']}")

    if not dry_run:
        save_apple_db()
        clear_gallery_cache()
        print("Caché de galería y apple_db actualizados.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run_icloud_classification(max_files=args.max, dry_run=args.dry_run)
