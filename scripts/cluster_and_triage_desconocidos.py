import sys
import os
import re
import pickle
import unicodedata
from pathlib import Path
import cv2
import numpy as np
from sklearn.cluster import DBSCAN

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.globals import detector, recognizer, clear_gallery_cache
from app.utils.file_ops import safe_move_file

res = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
desconocidos_dir = res / "Personas Sin Nombre" / "Desconocidos"
sin_rostro_dir = res / "Revision_Interactiva" / "Sin_Rostro"
sin_rostro_dir.mkdir(parents=True, exist_ok=True)
capturas_dir = res / "Publicaciones_Instagram" / "Capturas"
capturas_dir.mkdir(parents=True, exist_ok=True)
yo_dir = res / "YO" / "YO"

def norm_str(s):
    if not isinstance(s, str): return ''
    s = s.replace('\ufffd', '')
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower().strip()

# 1. Load centroids
with open('centroids.pkl', 'rb') as f:
    centroids_raw = pickle.load(f)

yo_c = np.load('yo_pure_centroid.npy')
yo_c = yo_c / np.linalg.norm(yo_c)

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
print(f"Loaded {len(centroids)} centroids for matching.")

# 2. Scan all files in Desconocidos
files = [f for f in desconocidos_dir.iterdir() if f.is_file()]
print(f"Found {len(files)} files in 'Personas Sin Nombre/Desconocidos'.")

valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}

stats = {
    'total': len(files),
    'purged_non_face': 0,
    'purged_capturas': 0,
    'matched_canonical': 0,
    'matched_yo': 0,
    'clustered': 0,
    'unclustered_singletons': 0,
}

unknown_embeddings = []
unknown_file_paths = []

for idx, f in enumerate(files, 1):
    if idx % 100 == 0:
        print(f"Processing {idx}/{len(files)}...", flush=True)
        
    ext = f.suffix.lower()
    fname_l = f.name.lower()
    
    if ext not in valid_exts:
        continue
        
    data = np.fromfile(str(f), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        safe_move_file(f, sin_rostro_dir)
        stats['purged_non_face'] += 1
        continue
        
    h, w = img.shape[:2]
    scale = 1024.0 / max(h, w) if max(h, w) > 1024 else 1.0
    small = cv2.resize(img, (int(w*scale), int(h*scale))) if scale != 1.0 else img
    detector.setInputSize((small.shape[1], small.shape[0]))
    detector.setScoreThreshold(0.55)
    _, faces = detector.detect(small)
    
    # Check if NO face
    if faces is None or len(faces) == 0:
        if any(w in fname_l for w in ['screenshot', 'screenrecorder', 'captura', 'instagram']):
            safe_move_file(f, capturas_dir)
            stats['purged_capturas'] += 1
        else:
            safe_move_file(f, sin_rostro_dir)
            stats['purged_non_face'] += 1
        continue
        
    # Face(s) detected: check against known centroids
    best_sim = -1.0
    best_key = None
    best_yo = -1.0
    primary_feat = None
    
    for face in faces:
        try:
            aligned = recognizer.alignCrop(img, face / scale)
            feat = recognizer.feature(aligned)[0]
            norm = np.linalg.norm(feat)
            if norm == 0: continue
            feat_norm = feat / norm
            
            y_sim = float(np.dot(feat_norm, yo_c))
            if y_sim > best_yo: best_yo = y_sim
            
            sims = np.dot(centroid_matrix, feat_norm)
            top_idx = int(np.argmax(sims))
            top_sim = float(sims[top_idx])
            top_key = keys_list[top_idx]
            
            if top_key != ('YO', 'YO') and top_sim > best_sim:
                best_sim = top_sim
                best_key = top_key
                primary_feat = feat_norm
        except Exception:
            pass
            
    # Decision: match known or cluster?
    if len(faces) == 1 and best_yo >= 0.50 and best_yo > best_sim + 0.08:
        # Solo photo of Eneko!
        safe_move_file(f, yo_dir)
        stats['matched_yo'] += 1
    elif best_sim >= 0.56 and best_key is not None and best_sim > best_yo + 0.04:
        # Match canonical person!
        dest_cat, dest_id = best_key
        dest_dir = res / dest_cat / dest_id
        if dest_dir.exists():
            safe_move_file(f, dest_dir)
            stats['matched_canonical'] += 1
            print(f"  [RESCUED] '{f.name}' -> '{dest_id}' (sim={best_sim:.3f})", flush=True)
        else:
            if primary_feat is not None:
                unknown_embeddings.append(primary_feat)
                unknown_file_paths.append(f)
    else:
        # Truly unknown face -> add to clustering queue
        if primary_feat is not None:
            unknown_embeddings.append(primary_feat)
            unknown_file_paths.append(f)

print("\n" + "=" * 50)
print(f"STAGE 1 FINISHED: {stats}")
print(f"Queued for DBSCAN clustering: {len(unknown_embeddings)} unknown faces.")

# 3. DBSCAN Clustering of unknown faces
if len(unknown_embeddings) >= 2:
    print("Running DBSCAN clustering on unknown faces...", flush=True)
    X = np.array(unknown_embeddings)
    # Cosine distance DBSCAN: eps=0.34 (cosine similarity >= 0.66), min_samples=2
    clustering = DBSCAN(eps=0.34, min_samples=2, metric='cosine').fit(X)
    labels = clustering.labels_
    
    unique_labels = set(labels) - {-1}
    print(f"Found {len(unique_labels)} recurring person clusters!", flush=True)
    
    # Find next available persona ID
    psn_dir = res / "Personas Sin Nombre"
    existing = [d.name for d in psn_dir.iterdir() if d.is_dir() and "Persona Nueva #" in d.name]
    highest_id = 0
    for e in existing:
        try:
            num = int(e.split("#")[1].strip())
            if num > highest_id: highest_id = num
        except:
            pass
            
    for lbl in sorted(unique_labels):
        highest_id += 1
        new_person_dir = psn_dir / f"Persona Nueva #{highest_id}"
        new_person_dir.mkdir(parents=True, exist_ok=True)
        
        cluster_indices = np.where(labels == lbl)[0]
        for c_idx in cluster_indices:
            file_to_move = unknown_file_paths[c_idx]
            if file_to_move.exists():
                safe_move_file(file_to_move, new_person_dir)
                stats['clustered'] += 1
                
        print(f"  [CLUSTER #{highest_id}] Created with {len(cluster_indices)} photos.", flush=True)

stats['unclustered_singletons'] = len([f for f in desconocidos_dir.iterdir() if f.is_file()])
print("\n" + "=" * 50)
print(f"FINAL CLUSTERING & TRIAGE RESULTS: {stats}")
clear_gallery_cache()
