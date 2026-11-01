import os
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

def read_image_safe(fpath):
    try:
        data = np.fromfile(str(fpath), dtype=np.uint8)
        if len(data) == 0: return None
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None

print("=" * 60, flush=True)
print("[1] CALCULATING PURE GOLD-STANDARD 'YO' (ENEKO) CENTROID", flush=True)
print("=" * 60, flush=True)

yo_dir = base / "YO" / "YO"
yo_solo_vectors = []
valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}

files_yo = sorted([f for f in yo_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts])
for f in files_yo[:60]:
    try:
        img = read_image_safe(f)
        if img is None: continue
        h, w = img.shape[:2]
        scale = 1024.0 / max(h, w) if max(h, w) > 1024 else 1.0
        small = cv2.resize(img, (int(w*scale), int(h*scale))) if scale != 1.0 else img
        detector.setInputSize((small.shape[1], small.shape[0]))
        _, faces = detector.detect(small)
        if faces is not None and len(faces) == 1:
            fv = recognizer.feature(recognizer.alignCrop(img, faces[0] / scale)).flatten()
            norm = np.linalg.norm(fv)
            if norm > 0:
                yo_solo_vectors.append(fv / norm)
    except Exception:
        pass

if len(yo_solo_vectors) >= 5:
    yo_pure = np.mean(yo_solo_vectors, axis=0)
    yo_pure = yo_pure / np.linalg.norm(yo_pure)
    print(f"Calculated pure YO centroid from {len(yo_solo_vectors)} solo photos.", flush=True)
    np.save('yo_pure_centroid.npy', yo_pure)
else:
    print("Fallback to existing YO centroid.", flush=True)
    with open('centroids.pkl', 'rb') as f:
        yo_pure = pickle.load(f)[('YO', 'YO')]
        yo_pure = yo_pure / np.linalg.norm(yo_pure)

print("\n" + "=" * 60, flush=True)
print("[2] RE-CALIBRATING JUNE SESEN CENTROID", flush=True)
print("=" * 60, flush=True)

with open('centroids.pkl', 'rb') as f:
    centroids_raw = pickle.load(f)

# Update June Sesen from Fotos June Sesen.jpg candidate face 1
june_gt = base / "Conocidos" / "C. June Sesen" / "Fotos June Sesen.jpg"
if june_gt.exists():
    jimg = read_image_safe(june_gt)
    if jimg is not None:
        detector.setInputSize((jimg.shape[1], jimg.shape[0]))
        _, jfaces = detector.detect(jimg)
        if jfaces is not None and len(jfaces) >= 2:
            jfv = recognizer.feature(recognizer.alignCrop(jimg, jfaces[1])).flatten()
            jfv = jfv / np.linalg.norm(jfv)
            centroids_raw[('Conocidos', 'C. June Sesen')] = jfv
            print("Successfully updated June Sesen centroid from ground truth face 1.", flush=True)

centroids_raw[('YO', 'YO')] = yo_pure

with open('centroids.pkl', 'wb') as f:
    pickle.dump(centroids_raw, f)
print("Updated 'centroids.pkl' with pure YO and June Sesen centroids.", flush=True)

# Prepare matrix for fast dot-product
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

print("\n" + "=" * 60, flush=True)
print("[3] RUNNING FINAL ANTI-CONFUSION AUDIT", flush=True)
print("=" * 60, flush=True)

audit_cats = ['Conocidos', 'Familia', 'Profesores']
folders_to_audit = []
for cat in audit_cats:
    c_dir = base / cat
    if not c_dir.exists(): continue
    for p_dir in sorted(c_dir.iterdir()):
        if p_dir.is_dir() and not any(w in p_dir.name.lower() for w in ['conmigo', 'sin mí', 'sin mi', 'grupal', 'grupo']):
            folders_to_audit.append((cat, p_dir))

print(f"Auditing {len(folders_to_audit)} folders against Anti-Confusion Rules...", flush=True)

stats = {'scanned': 0, 'kept': 0, 'relocated': 0, 'evicted': 0, 'yo_evicted': 0}

for f_idx, (cat, p_dir) in enumerate(folders_to_audit, 1):
    ident = p_dir.name
    owner_centroid = centroids.get((cat, ident))
    owner_key = (cat, ident)
    if owner_centroid is None:
        n_match = norm_to_centroid.get(norm_str(ident))
        if n_match:
            owner_key, owner_centroid = n_match

    if owner_centroid is None:
        continue

    files = [f for f in p_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]

    for fpath in files:
        stats['scanned'] += 1
        
        # 1. Handle misplaced ground-truth naming
        if fpath.name.lower().startswith('familia~'):
            dest = base / "Familia" / "Familia conmigo"
            dest.mkdir(parents=True, exist_ok=True)
            stats['relocated'] += 1
            print(f"  [RELOCATE FAMILIA] '{fpath.name}' from '{ident}' -> 'Familia conmigo'", flush=True)
            safe_move_file(fpath, dest)
            continue
            
        if fpath.name.lower().startswith('aitona'):
            dest = base / "Familia" / "Familia sin mí"
            dest.mkdir(parents=True, exist_ok=True)
            stats['relocated'] += 1
            print(f"  [RELOCATE AITONA] '{fpath.name}' from '{ident}' -> 'Familia sin mí'", flush=True)
            safe_move_file(fpath, dest)
            continue

        if re.match(r'^Fotos\s+' + re.escape(re.sub(r'^[CFM]\.\s*', '', ident)) + r'~', fpath.name, re.IGNORECASE):
            stats['kept'] += 1
            continue

        try:
            img = read_image_safe(fpath)
            if img is None:
                stats['kept'] += 1
                continue

            h, w = img.shape[:2]
            scale = 1024.0 / max(h, w) if max(h, w) > 1024 else 1.0
            small = cv2.resize(img, (int(w*scale), int(h*scale))) if scale != 1.0 else img
            detector.setInputSize((small.shape[1], small.shape[0]))
            _, faces = detector.detect(small)

            if faces is None or len(faces) == 0:
                stats['kept'] += 1
                continue

            owner_matched = False
            yo_matched = False
            best_other_sim = -1.0
            best_other_key = None

            for face in faces:
                fv = recognizer.feature(recognizer.alignCrop(img, face / scale)).flatten()
                norm = np.linalg.norm(fv)
                if norm == 0: continue
                fn = fv / norm

                s_owner = float(np.dot(fn, owner_centroid))
                s_yo = float(np.dot(fn, yo_pure))

                # ANTI-CONFUSION CRUCIAL RULE:
                # If s_yo >= s_owner or s_yo >= 0.50: this face is Eneko!
                if s_yo >= 0.50 and s_yo >= s_owner:
                    yo_matched = True
                elif s_owner >= 0.48 and s_owner > s_yo + 0.05:
                    owner_matched = True

                # Compare to all other centroids
                sims = np.dot(centroid_matrix, fn)
                top_idx = np.argmax(sims)
                if sims[top_idx] > best_other_sim:
                    best_other_sim = float(sims[top_idx])
                    best_other_key = keys_list[top_idx]

            # DECISION:
            if owner_matched:
                stats['kept'] += 1
                continue

            # Owner NOT matched:
            if yo_matched and not owner_matched:
                # Eneko was in the photo alone!
                dest = base / "YO" / "YO"
                dest.mkdir(parents=True, exist_ok=True)
                stats['yo_evicted'] += 1
                print(f"  [RELOCATE TO YO] '{fpath.name}' from '{ident}' -> 'YO/YO' (Only Eneko appeared!)", flush=True)
                safe_move_file(fpath, dest)
            elif best_other_sim >= 0.55 and best_other_key and best_other_key != owner_key:
                dest = base / best_other_key[0] / best_other_key[1]
                dest.mkdir(parents=True, exist_ok=True)
                stats['relocated'] += 1
                print(f"  [RELOCATE] '{fpath.name}' from '{ident}' -> '{best_other_key[1]}' (Sim: {best_other_sim:.3f})", flush=True)
                safe_move_file(fpath, dest)
            else:
                stats['evicted'] += 1
                print(f"  [EVICT] '{fpath.name}' from '{ident}' -> 'Para Revisar' (Owner not found)", flush=True)
                safe_move_file(fpath, para_revisar)

        except Exception as e:
            pass

    if f_idx % 25 == 0 or f_idx == len(folders_to_audit):
        print(f"[{f_idx}/{len(folders_to_audit)}] Kept: {stats['kept']} | Relocated: {stats['relocated']} | Eneko->YO: {stats['yo_evicted']} | Evicted: {stats['evicted']}", flush=True)

clear_gallery_cache()
print("\n" + "=" * 60, flush=True)
print(f"AUDITORIA FINAL COMPLETADA:", flush=True)
print(f"Fotos analizadas: {stats['scanned']}", flush=True)
print(f"Fotos legítimas del dueño conservadas: {stats['kept']}", flush=True)
print(f"Fotos con solo Eneko reubicadas a YO/YO: {stats['yo_evicted']}", flush=True)
print(f"Fotos de otros reubicadas a su carpeta real: {stats['relocated']}", flush=True)
print(f"Fotos dudosas/sin dueño expulsadas a Para Revisar: {stats['evicted']}", flush=True)
print("=" * 60, flush=True)
