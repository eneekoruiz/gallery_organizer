"""Audit and clean canonical albums against their 406 centroids.

Any photo in a person's folder where faces are detected but the owner DOES NOT appear
(similarity < 0.40):
- If it clearly matches another person (>= 0.55), moved to that person's folder.
- If it doesn't match the owner (< 0.40) and is ambiguous, moved to Resultados/Dudosos/Para Revisar.
- Ground-truth reference photos (Fotos <Owner>~...) are strictly preserved.
"""

import sys
import re
import pickle
import time
import unicodedata
from pathlib import Path
import cv2
import numpy as np

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.globals import detector, recognizer, clear_gallery_cache
from app.utils.file_ops import safe_move_file

base = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
para_revisar = base / "Dudosos" / "Para Revisar"
para_revisar.mkdir(parents=True, exist_ok=True)

def norm_str(s):
    if not isinstance(s, str): return ''
    s = s.replace('\ufffd', '')
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower().strip()

with open('centroids.pkl', 'rb') as f:
    centroids_raw = pickle.load(f)

# Normalize centroids
centroids = {}
keys_list = []
matrix_list = []
norm_to_centroid = {}

for k, v in centroids_raw.items():
    if v is not None and isinstance(k, tuple):
        arr = np.array(v, dtype=np.float32).flatten()
        norm = np.linalg.norm(arr)
        if norm > 0:
            norm_v = arr / norm
            centroids[k] = norm_v
            keys_list.append(k)
            matrix_list.append(norm_v)
            norm_to_centroid[norm_str(k[1])] = (k, norm_v)

centroid_matrix = np.stack(matrix_list)
print(f"Loaded {len(centroids)} normalized centroids.")

# Pre-load faces_cache if available for fast evaluation
faces_cache = {}
for p in [Path('faces_cache.pkl'), Path('faces_cache_v2.pkl')]:
    if p.exists():
        try:
            with open(p, 'rb') as f:
                faces_cache.update(pickle.load(f))
        except Exception:
            pass
print(f"Loaded {len(faces_cache)} entries from faces_cache.")

def run_album_cleanse(dry_run=False, limit_folders=None):
    valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}
    
    stats = {
        'total_scanned': 0,
        'ground_truth_kept': 0,
        'owner_confirmed_kept': 0,
        'no_face_kept': 0,
        'relocated_matched': 0,
        'evicted_to_review': 0,
        'errors': 0
    }
    
    audit_cats = ['Conocidos', 'Familia', 'Profesores', 'YO']
    
    folders_to_audit = []
    for cat in audit_cats:
        c_dir = base / cat
        if not c_dir.exists(): continue
        for p_dir in c_dir.iterdir():
            if p_dir.is_dir():
                # Skip group albums
                if any(w in p_dir.name.lower() for w in ['conmigo', 'sin mí', 'sin mi', 'grupal', 'grupo']):
                    continue
                folders_to_audit.append((cat, p_dir))
                
    if limit_folders:
        folders_to_audit = folders_to_audit[:limit_folders]
        
    print(f"Auditing {len(folders_to_audit)} identity folders across {audit_cats}...")
    t0 = time.time()
    
    for f_idx, (cat, p_dir) in enumerate(folders_to_audit, 1):
        ident = p_dir.name
        
        # Lookup folder centroid (exact or normalized)
        owner_centroid = centroids.get((cat, ident))
        owner_key = (cat, ident)
        if owner_centroid is None:
            n_match = norm_to_centroid.get(norm_str(ident))
            if n_match:
                owner_key, owner_centroid = n_match
                    
        if owner_centroid is None:
            # No centroid known for this folder, skip to avoid incorrect eviction
            continue
            
        clean_owner = re.sub(r'^[CFM]\.\s*', '', ident).lower().strip()
        clean_owner_norm = norm_str(clean_owner)
        
        files = [f for f in p_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
        
        for fpath in files:
            stats['total_scanned'] += 1
            try:
                # 1. Ground truth safeguard & misplaced ground truth detection
                m_owner = re.match(r'^(?:(?:Foto|Fotos|Video|Videos|Vídeo|Vídeos)\s+([^~.]+?)(?:~|\.|\s*\()|([^~.]+?)~\d+\.)', fpath.name, re.IGNORECASE)
                named_on_file = None
                if m_owner:
                    raw_name = (m_owner.group(1) or m_owner.group(2) or '').strip()
                    if raw_name.lower() not in {'familia', 'conocidos', 'fotos', 'video', 'videos', 'amigos', 'recuerdos', 'persona'}:
                        named_on_file = norm_str(raw_name)

                if named_on_file:
                    if named_on_file in clean_owner_norm or clean_owner_norm in named_on_file:
                        stats['ground_truth_kept'] += 1
                        continue
                    else:
                        # This named reference photo was misplaced in someone else's folder!
                        match_target = norm_to_centroid.get(named_on_file)
                        if not match_target:
                            for k_norm, (k_tup, k_c) in norm_to_centroid.items():
                                if named_on_file and (named_on_file in k_norm or k_norm in named_on_file):
                                    match_target = (k_tup, k_c)
                                    break
                        if match_target:
                            dest_cat, dest_ident = match_target[0]
                            dest_dir = base / dest_cat / dest_ident
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            stats['relocated_matched'] += 1
                            print(f"  [RELOCATE GT] '{fpath.name}' from '{ident}' -> '{dest_ident}'", flush=True)
                            if not dry_run:
                                safe_move_file(fpath, dest_dir)
                            continue
                        else:
                            # Unknown owner named on file, move to Para Revisar
                            stats['evicted_to_review'] += 1
                            print(f"  [EVICT GT] '{fpath.name}' from '{ident}' -> 'Para Revisar'", flush=True)
                            if not dry_run:
                                safe_move_file(fpath, para_revisar)
                            continue
                        
                # 2. Extract features: check faces_cache first
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
                                
                # If not cached, detect and extract with cv2 YuNet + SFace
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
                    
                    if faces is None or len(faces) == 0:
                        stats['no_face_kept'] += 1
                        continue
                        
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
                            
                    if feature_vectors:
                        faces_cache[str(fpath)] = [{'feature': fv.tolist(), 'identity': 'Desconocido'} for fv in feature_vectors]
                            
                if not feature_vectors:
                    stats['no_face_kept'] += 1
                    continue
                    
                # 3. Compare all detected faces to owner and all centroids
                max_owner_sim = -1.0
                best_overall_sim = -1.0
                best_overall_key = None
                
                for fv in feature_vectors:
                    sim_owner = float(np.dot(fv, owner_centroid))
                    if sim_owner > max_owner_sim:
                        max_owner_sim = sim_owner
                        
                    sims = np.dot(centroid_matrix, fv)
                    top_idx = np.argmax(sims)
                    top_sim = float(sims[top_idx])
                    if top_sim > best_overall_sim:
                        best_overall_sim = top_sim
                        best_overall_key = keys_list[top_idx]
                        
                # DECISION RULE:
                # If owner appears in ANY face with sim >= 0.40:
                if max_owner_sim >= 0.40:
                    stats['owner_confirmed_kept'] += 1
                    continue
                    
                # Owner DOES NOT appear in the photo (max_owner_sim < 0.40):
                # Check if it clearly matches someone else (>= 0.55)
                if best_overall_sim >= 0.55 and best_overall_key and best_overall_key != owner_key:
                    dest_cat, dest_ident = best_overall_key
                    dest_dir = base / dest_cat / dest_ident
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    stats['relocated_matched'] += 1
                    print(f"  [RELOCATE] '{fpath.name}' from '{ident}' -> '{dest_ident}' (Sim: {best_overall_sim:.3f}, Owner: {max_owner_sim:.3f})", flush=True)
                    if not dry_run:
                        safe_move_file(fpath, dest_dir)
                else:
                    # Evict to Para Revisar
                    stats['evicted_to_review'] += 1
                    print(f"  [EVICT] '{fpath.name}' from '{ident}' -> 'Para Revisar' (Owner: {max_owner_sim:.3f}, Best other: {best_overall_sim:.3f})", flush=True)
                    if not dry_run:
                        safe_move_file(fpath, para_revisar)
                        
            except Exception as e:
                stats['errors'] += 1
                
        if f_idx % 25 == 0 or f_idx == len(folders_to_audit):
            if not dry_run:
                try:
                    with open('faces_cache_v2.pkl', 'wb') as fc_f:
                        pickle.dump(faces_cache, fc_f)
                except Exception:
                    pass
            print(f"[{f_idx}/{len(folders_to_audit)} folders] Scanned: {stats['total_scanned']} | "
                  f"Kept (Owner): {stats['owner_confirmed_kept']} | Kept (GT): {stats['ground_truth_kept']} | "
                  f"Kept (NoFace): {stats['no_face_kept']} | Relocated: {stats['relocated_matched']} | "
                  f"Evicted: {stats['evicted_to_review']}", flush=True)

    elapsed = time.time() - t0
    print("\n--- RESUMEN FINAL DE AUDITORÍA Y LIMPIEZA DE ÁLBUMES ---")
    print(f"Total fotos escaneadas: {stats['total_scanned']} en {elapsed:.1f}s")
    print(f"Fotos del dueño confirmadas por IA (sim >= 0.40): {stats['owner_confirmed_kept']}")
    print(f"Fotos Dataset/Ground-Truth intactas: {stats['ground_truth_kept']}")
    print(f"Fotos sin rostros preservadas: {stats['no_face_kept']}")
    print(f"Fotos ajenas reubicadas a su verdadero dueño (sim >= 0.55): {stats['relocated_matched']}")
    print(f"Fotos ajenas/dudosas expulsadas a Para Revisar (owner < 0.40): {stats['evicted_to_review']}")
    print(f"Errores: {stats['errors']}")
    
    if not dry_run:
        clear_gallery_cache()
        print("Caché de galería invalidado exitosamente.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()
    run_album_cleanse(dry_run=args.dry_run, limit_folders=args.limit)
