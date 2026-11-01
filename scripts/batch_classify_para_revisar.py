"""Batch classifier for Resultados/Dudosos/Para Revisar.

Processes pending images:
- Non-face images -> Resultados/Revision_Interactiva/Sin_Rostro
- High-confidence faces (>=0.60, margin>=0.06) -> Resultados/<Categoria>/<Persona>
- Ambiguous / unknown images -> Left in Para Revisar ('excepto lo que no sepas')

Thread-safe, atomic moves via safe_move_file. Periodic gallery cache refresh.
"""

import os
import sys
import time
import json
import pickle
import argparse
from pathlib import Path
import cv2
import numpy as np

# Force UTF-8 on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.globals import detector, recognizer, RESULTADOS_DIR, clear_gallery_cache
from app.utils.file_ops import safe_move_file

STATUS_FILE = APP_ROOT / "scripts" / "triage_status.json"

def load_centroid_matrix():
    with open(APP_ROOT / 'centroids.pkl', 'rb') as f:
        raw = pickle.load(f)
    
    keys = []
    vectors = []
    for k, v in raw.items():
        if v is not None:
            arr = np.array(v, dtype=np.float32).flatten()
            norm = np.linalg.norm(arr)
            if norm > 0:
                keys.append(k) # ('Conocidos', 'C. Nombre')
                vectors.append(arr / norm)
                
    matrix = np.stack(vectors) # shape (N, 128)
    return keys, matrix

def run_triage(limit=None, dry_run=False, max_dim=1600, min_sim=0.60, min_margin=0.06):
    keys, centroid_matrix = load_centroid_matrix()
    print(f"Loaded {len(keys)} normalized centroid identities.", flush=True)
    
    para_revisar = RESULTADOS_DIR / "Dudosos" / "Para Revisar"
    sin_rostro_dir = RESULTADOS_DIR / "Revision_Interactiva" / "Sin_Rostro"
    sin_rostro_dir.mkdir(parents=True, exist_ok=True)
    
    valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}
    files = [f for f in para_revisar.iterdir() if f.suffix.lower() in valid_exts]
    total_found = len(files)
    print(f"Total files currently in Para Revisar: {total_found}", flush=True)
    
    if limit:
        files = files[:limit]
        print(f"Processing limit: {len(files)} files", flush=True)
        
    stats = {
        'total': len(files),
        'processed': 0,
        'moved_sin_rostro': 0,
        'moved_canonical': 0,
        'remains_pending': 0,
        'errors': 0,
        'status': 'running'
    }
    
    t0 = time.time()
    last_cache_clear = time.time()
    
    for idx, fpath in enumerate(files, 1):
        stats['processed'] = idx
        try:
            # File might have been moved concurrently
            if not fpath.exists():
                continue
                
            b = np.fromfile(str(fpath), dtype=np.uint8)
            img = cv2.imdecode(b, cv2.IMREAD_COLOR)
            if img is None:
                stats['errors'] += 1
                continue
                
            orig_h, orig_w = img.shape[:2]
            
            # Dynamic scaling for fast detection
            scale = 1.0
            if max(orig_h, orig_w) > max_dim:
                scale = max_dim / max(orig_h, orig_w)
                sw, sh = int(orig_w * scale), int(orig_h * scale)
                detect_img = cv2.resize(img, (sw, sh))
            else:
                detect_img = img
                
            dh, dw = detect_img.shape[:2]
            detector.setInputSize((dw, dh))
            _, faces = detector.detect(detect_img)
            
            # Case 1: No faces detected -> Move to Sin_Rostro
            if faces is None or len(faces) == 0:
                stats['moved_sin_rostro'] += 1
                if not dry_run:
                    safe_move_file(fpath, sin_rostro_dir)
                continue
                
            # Case 2: Faces detected -> Compare against centroid matrix
            best_overall_sim = -1.0
            second_overall_sim = -1.0
            best_overall_key = None
            
            for face in faces:
                if scale != 1.0:
                    face_full = face.copy()
                    face_full[:14] /= scale
                else:
                    face_full = face
                    
                aligned = recognizer.alignCrop(img, face_full)
                feat = recognizer.feature(aligned)[0]
                norm = np.linalg.norm(feat)
                if norm == 0:
                    continue
                feat_norm = feat / norm
                
                # BLAS dot product against all centroids
                sims = np.dot(centroid_matrix, feat_norm)
                
                # Top 2 similarities
                top_indices = np.argpartition(sims, -2)[-2:]
                top_indices = top_indices[np.argsort(sims[top_indices])[::-1]]
                
                f_best_idx = top_indices[0]
                f_best_sim = float(sims[f_best_idx])
                f_sec_sim = float(sims[top_indices[1]]) if len(top_indices) > 1 else 0.0
                
                if f_best_sim > best_overall_sim:
                    best_overall_sim = f_best_sim
                    second_overall_sim = f_sec_sim
                    best_overall_key = keys[f_best_idx]
                    
            margin = best_overall_sim - second_overall_sim
            
            # High confidence threshold
            if best_overall_sim >= min_sim and margin >= min_margin and best_overall_key:
                cat, person = best_overall_key
                dest_dir = RESULTADOS_DIR / cat / person
                dest_dir.mkdir(parents=True, exist_ok=True)
                stats['moved_canonical'] += 1
                if not dry_run:
                    safe_move_file(fpath, dest_dir)
            else:
                stats['remains_pending'] += 1
                
        except Exception:
            stats['errors'] += 1
            
        # Logging & status saving
        if idx % 50 == 0 or idx == len(files):
            elapsed = time.time() - t0
            rate = idx / elapsed if elapsed > 0 else 0
            eta = (len(files) - idx) / rate if rate > 0 else 0
            
            status_data = {
                'processed': idx,
                'total': len(files),
                'moved_sin_rostro': stats['moved_sin_rostro'],
                'moved_canonical': stats['moved_canonical'],
                'remains_pending': stats['remains_pending'],
                'errors': stats['errors'],
                'rate_fps': round(rate, 2),
                'eta_minutes': round(eta / 60, 1),
                'percent': round((idx / len(files)) * 100, 1),
                'status': 'running'
            }
            try:
                with open(STATUS_FILE, 'w', encoding='utf-8') as sf:
                    json.dump(status_data, sf, indent=2)
            except Exception:
                pass
                
            print(f"[{idx}/{len(files)} ({status_data['percent']}%) | "
                  f"Sin_Rostro: {stats['moved_sin_rostro']} | "
                  f"Canónicos: {stats['moved_canonical']} | "
                  f"Pendientes: {stats['remains_pending']} | "
                  f"Speed: {rate:.1f} img/s | ETA: {eta/60:.1f}m", flush=True)
                  
            # Invalidate gallery cache every 300 files so UI updates progressively
            if not dry_run and (time.time() - last_cache_clear > 120 or idx % 300 == 0):
                clear_gallery_cache()
                last_cache_clear = time.time()
                  
    elapsed_total = time.time() - t0
    stats['status'] = 'completed'
    stats['elapsed_seconds'] = round(elapsed_total, 1)
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as sf:
            json.dump(stats, sf, indent=2)
    except Exception:
        pass
        
    print("\n================================", flush=True)
    print("--- RESUMEN FINAL DE ORDENACIÓN ---", flush=True)
    print(f"Total procesados: {stats['processed']} en {elapsed_total:.1f}s ({stats['processed']/elapsed_total:.1f} img/s)", flush=True)
    print(f"Movidos a Sin Rostro: {stats['moved_sin_rostro']}", flush=True)
    print(f"Asignados a Álbumes Canónicos: {stats['moved_canonical']}", flush=True)
    print(f"Permanecen en Para Revisar: {stats['remains_pending']}", flush=True)
    print(f"Errores: {stats['errors']}", flush=True)
    print("================================", flush=True)
    
    if not dry_run:
        clear_gallery_cache()
        print("Caché de galería invalidado exitosamente.", flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run_triage(limit=args.limit, dry_run=args.dry_run)
