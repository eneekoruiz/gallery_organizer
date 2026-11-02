"""Autonomous Apple / iCloud Photos Organizer.

Organizes all remaining unorganized iCloud photos directly into canonical albums:
- Capturas / Screenshots -> Resultados/Publicaciones_Instagram/Capturas
- No faces detected -> Resultados/Revision_Interactiva/Sin_Rostro
- Eneko (pure or sunglasses, >= 0.45) -> Resultados/YO/YO
- Confident known identity (>= 0.52) -> Resultados/<Cat>/<Ident>
- Unknown faces (< 0.52) -> Resultados/Personas Sin Nombre/Desconocidos

Preserves iCloud originals (safe copy2), maintains apple_db.json, updates faces_cache_v2.pkl,
and updates scratch/apple_progress.json periodically.
"""

import os
import sys
import time
import shutil
import pickle
import json
from pathlib import Path
import cv2
import numpy as np

# Set UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Set below normal priority to avoid system freeze
try:
    import psutil
    p = psutil.Process()
    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.globals import detector, recognizer, clear_gallery_cache

ICLOUD_DIR = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")
BASE_RESULTADOS = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
APPLE_DB_FILE = Path(r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\apple_db.json")
PROGRESS_FILE = Path(r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\scratch\apple_progress.json")
FACES_CACHE_FILE = Path(r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\faces_cache_v2.pkl")

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

# Load Eneko centroids
yo_pure = None
if Path("yo_pure_centroid.npy").exists():
    yo_pure = np.load("yo_pure_centroid.npy")
    yo_pure = yo_pure / (np.linalg.norm(yo_pure) + 1e-10)

yo_sunglasses = None
if Path("yo_sunglasses_centroid.npy").exists():
    yo_sunglasses = np.load("yo_sunglasses_centroid.npy")
    yo_sunglasses = yo_sunglasses / (np.linalg.norm(yo_sunglasses) + 1e-10)

# Load caches
faces_cache = {}
if FACES_CACHE_FILE.exists():
    try:
        with open(FACES_CACHE_FILE, 'rb') as f:
            faces_cache = pickle.load(f)
    except Exception:
        pass

apple_db = {}
if APPLE_DB_FILE.exists():
    try:
        with open(APPLE_DB_FILE, 'r', encoding='utf-8') as f:
            apple_db = json.load(f)
    except Exception:
        pass

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

def save_state():
    try:
        with open(APPLE_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(apple_db, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        with open(FACES_CACHE_FILE, 'wb') as f:
            pickle.dump(faces_cache, f)
    except Exception as e:
        print(f"Error saving state: {e}", flush=True)

def main():
    print("=== STARTING AUTONOMOUS APPLE PHOTOS ORGANIZER ===", flush=True)
    if not ICLOUD_DIR.exists():
        print("iCloud Photos directory not found!", flush=True)
        return

    # Scan existing in Resultados
    print("Scanning existing files in Resultados...", flush=True)
    existing = set()
    for r, d, fs in os.walk(BASE_RESULTADOS):
        for f in fs:
            existing.add(f.lower())

    valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}
    candidates = [
        f for f in ICLOUD_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in valid_exts and f.name.lower() not in existing
    ]

    total = len(candidates)
    print(f"Total unorganized candidates: {total}", flush=True)

    stats = {
        'total': total,
        'processed': 0,
        'yo': 0,
        'known_persons': 0,
        'capturas': 0,
        'sin_rostro': 0,
        'desconocidos': 0,
        'errors': 0,
        'start_time': time.time(),
        'status': 'running'
    }

    t0 = time.time()
    for idx, fpath in enumerate(candidates, 1):
        try:
            fname_l = fpath.name.lower()
            ext = fpath.suffix.lower()

            # 1. Screenshots check
            is_screenshot = (
                ext == '.png' and (
                    'screenshot' in fname_l or
                    'screen' in fname_l or
                    'captura' in fname_l or
                    'snapchat' in fname_l
                )
            )

            if is_screenshot:
                dest_dir = BASE_RESULTADOS / "Publicaciones_Instagram" / "Capturas"
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / fpath.name
                shutil.copy2(str(fpath), str(dest_path))
                stats['capturas'] += 1
                apple_db[str(dest_path)] = {
                    'category': 'Publicaciones_Instagram',
                    'identity': 'Capturas',
                    'original': str(fpath),
                    'type': 'screenshot'
                }
            else:
                # 2. Face detection
                b = np.fromfile(str(fpath), dtype=np.uint8)
                img = cv2.imdecode(b, cv2.IMREAD_COLOR)
                if img is None:
                    stats['errors'] += 1
                else:
                    h, w = img.shape[:2]
                    max_d = 960
                    scale = 1.0
                    if max(h, w) > max_d:
                        scale = max_d / max(h, w)
                        det_img = cv2.resize(img, (int(w * scale), int(h * scale)))
                    else:
                        det_img = img

                    dh, dw = det_img.shape[:2]
                    detector.setInputSize((dw, dh))
                    detector.setScoreThreshold(0.35)
                    _, faces = detector.detect(det_img)

                    if faces is None or len(faces) == 0:
                        # No face detected -> Sin_Rostro
                        dest_dir = BASE_RESULTADOS / "Revision_Interactiva" / "Sin_Rostro"
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest_path = dest_dir / fpath.name
                        shutil.copy2(str(fpath), str(dest_path))
                        stats['sin_rostro'] += 1
                        apple_db[str(dest_path)] = {
                            'category': 'Revision_Interactiva',
                            'identity': 'Sin_Rostro',
                            'original': str(fpath),
                            'faces_count': 0
                        }
                    else:
                        # Faces detected: extract features & match
                        feature_vectors = []
                        cached_faces_info = []
                        is_yo = False
                        best_sim = -1.0
                        best_k = None

                        for face in faces:
                            if scale != 1.0:
                                face_full = face.copy()
                                face_full[:14] /= scale
                            else:
                                face_full = face

                            aligned = recognizer.alignCrop(img, face_full)
                            feat = recognizer.feature(aligned)[0]
                            fn = feat / (np.linalg.norm(feat) + 1e-10)
                            feature_vectors.append(fn)

                            # Check YO (pure + sunglasses)
                            yo_sim = 0.0
                            if yo_pure is not None:
                                yo_sim = max(yo_sim, float(np.dot(fn, yo_pure)))
                            if yo_sunglasses is not None:
                                yo_sim = max(yo_sim, float(np.dot(fn, yo_sunglasses)))

                            if yo_sim >= 0.45:
                                is_yo = True

                            # Check against 407 identity centroids
                            sims = np.dot(centroid_matrix, fn)
                            top_idx = np.argmax(sims)
                            top_sim = float(sims[top_idx])
                            if top_sim > best_sim:
                                best_sim = top_sim
                                best_k = keys_list[top_idx]

                            cached_faces_info.append({
                                'x': int(face_full[0]),
                                'y': int(face_full[1]),
                                'width': int(face_full[2]),
                                'height': int(face_full[3]),
                                'img_width': w,
                                'img_height': h,
                                'identity': 'YO' if yo_sim >= 0.45 else (best_k[1] if best_sim >= 0.52 and best_k else 'Desconocido'),
                                'confidence': f"🏷️ Dataset ({max(yo_sim, best_sim)*100:.1f}%)" if (yo_sim >= 0.45 or best_sim >= 0.52) else "❓ Desconocido"
                            })

                        if is_yo:
                            dest_dir = BASE_RESULTADOS / "YO" / "YO"
                            stats['yo'] += 1
                            dest_cat, dest_ident = "YO", "YO"
                        elif best_sim >= 0.52 and best_k:
                            dest_cat, dest_ident = best_k
                            dest_dir = BASE_RESULTADOS / dest_cat / dest_ident
                            stats['known_persons'] += 1
                        else:
                            dest_dir = BASE_RESULTADOS / "Personas Sin Nombre" / "Desconocidos"
                            dest_cat, dest_ident = "Personas Sin Nombre", "Desconocidos"
                            stats['desconocidos'] += 1

                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest_path = dest_dir / fpath.name
                        shutil.copy2(str(fpath), str(dest_path))

                        apple_db[str(dest_path)] = {
                            'category': dest_cat,
                            'identity': dest_ident,
                            'original': str(fpath),
                            'score': round(best_sim, 3),
                            'faces_count': len(feature_vectors)
                        }
                        faces_cache[str(dest_path)] = cached_faces_info

        except Exception as e:
            stats['errors'] += 1

        stats['processed'] = idx

        # Periodic logging and save every 25 images
        if idx % 25 == 0 or idx == total:
            elapsed = time.time() - t0
            rate = idx / (elapsed + 1e-5)
            stats['rate'] = round(rate, 1)
            stats['elapsed'] = round(elapsed, 1)
            eta_s = (total - idx) / (rate + 1e-5)
            stats['eta_minutes'] = round(eta_s / 60, 1)

            print(f"[{idx}/{total}] YO: {stats['yo']} | Known: {stats['known_persons']} | "
                  f"Capturas: {stats['capturas']} | Sin Rostro: {stats['sin_rostro']} | "
                  f"Desconocidos: {stats['desconocidos']} | Rate: {rate:.1f} img/s | ETA: {stats['eta_minutes']}m", flush=True)

            save_state()
            try:
                PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(PROGRESS_FILE, 'w', encoding='utf-8') as pf:
                    json.dump(stats, pf, indent=2, cls=NumpyEncoder)
            except Exception:
                pass

    stats['status'] = 'completed'
    save_state()
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as pf:
            json.dump(stats, pf, indent=2, cls=NumpyEncoder)
    except Exception:
        pass

    clear_gallery_cache()
    print("\n=== COMPLETED AUTONOMOUS APPLE PHOTOS ORGANIZER ===", flush=True)
    print(f"Processed: {stats['processed']}/{total}")
    print(f"YO: {stats['yo']}")
    print(f"Personas Conocidas: {stats['known_persons']}")
    print(f"Capturas: {stats['capturas']}")
    print(f"Sin Rostro: {stats['sin_rostro']}")
    print(f"Desconocidos: {stats['desconocidos']}")
    print(f"Errores: {stats['errors']}")

if __name__ == '__main__':
    main()
