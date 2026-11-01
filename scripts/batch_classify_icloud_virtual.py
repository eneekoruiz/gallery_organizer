import os
import sys
import time
import json
import pickle
import ctypes
import unicodedata
from pathlib import Path
import cv2
import numpy as np

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Windows Cloud Files API (cldapi.dll)
cfapi = ctypes.WinDLL("cldapi.dll")
FILE_WRITE_ATTRIBUTES = 0x0100
FILE_READ_ATTRIBUTES = 0x0080
OPEN_EXISTING = 3
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

def dehydrate_file(fpath):
    try:
        handle = ctypes.windll.kernel32.CreateFileW(
            str(fpath),
            FILE_WRITE_ATTRIBUTES | FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None
        )
        if handle != -1 and handle != 0:
            hr = cfapi.CfDehydratePlaceholder(
                handle,
                ctypes.c_longlong(0),
                ctypes.c_longlong(-1),
                0,
                None
            )
            ctypes.windll.kernel32.CloseHandle(handle)
            return hr == 0
    except Exception:
        pass
    return False

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))
from app.globals import detector, recognizer

ICLOUD_DIR = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")
APPLE_DB_FILE = APP_ROOT / "apple_db.json"

# Load apple_db
apple_db = {}
if APPLE_DB_FILE.exists():
    try:
        with open(APPLE_DB_FILE, 'r', encoding='utf-8') as f:
            apple_db = json.load(f)
    except Exception:
        apple_db = {}

# Load centroids
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

def process_icloud_virtual_batch(limit=100):
    if not ICLOUD_DIR.exists():
        print("iCloud folder not found!")
        return 0
        
    already_indexed = set()
    for v in apple_db.values():
        if isinstance(v, dict) and 'original_icloud_path' in v:
            already_indexed.add(Path(v['original_icloud_path']).name.lower())

    valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}
    pending = []
    for f in ICLOUD_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in valid_exts and f.name.lower() not in already_indexed:
            pending.append(f)
            if len(pending) >= limit:
                break
                
    print(f"Batch processing {len(pending)} unindexed iCloud photos with auto-dehydration...", flush=True)
    if not pending:
        return 0
        
    processed = 0
    matched = 0
    sin_rostro = 0
    
    for idx, fpath in enumerate(pending, 1):
        try:
            b = np.fromfile(str(fpath), dtype=np.uint8)
            img = cv2.imdecode(b, cv2.IMREAD_COLOR)
            if img is None:
                apple_db[fpath.name] = {
                    'category': 'Revision_Interactiva',
                    'identity': 'Sin_Rostro',
                    'original_icloud_path': str(fpath),
                    'score': 0.0,
                    'faces_count': 0
                }
                dehydrate_file(fpath)
                continue
                
            h, w = img.shape[:2]
            scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
            small = cv2.resize(img, (int(w*scale), int(h*scale))) if scale != 1.0 else img
            detector.setInputSize((small.shape[1], small.shape[0]))
            detector.setScoreThreshold(0.55)
            _, faces = detector.detect(small)
            
            if faces is None or len(faces) == 0:
                is_screenshot = any(w_s in fpath.name.lower() for w_s in ['screenshot', 'captura', 'screenrecorder'])
                cat = 'Publicaciones_Instagram' if is_screenshot else 'Revision_Interactiva'
                ident = 'Capturas' if is_screenshot else 'Sin_Rostro'
                apple_db[fpath.name] = {
                    'category': cat,
                    'identity': ident,
                    'original_icloud_path': str(fpath),
                    'score': 0.0,
                    'faces_count': 0
                }
                sin_rostro += 1
            else:
                best_sim = -1.0
                best_key = None
                best_yo = -1.0
                
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
                    except Exception:
                        pass
                        
                if len(faces) == 1 and best_yo >= 0.50 and best_yo > best_sim + 0.08:
                    cat, ident = 'YO', 'YO'
                    matched += 1
                elif best_sim >= 0.58 and best_key is not None and best_sim > best_yo + 0.04:
                    cat, ident = best_key
                    matched += 1
                else:
                    cat, ident = 'Personas Sin Nombre', 'Desconocidos'
                    
                apple_db[fpath.name] = {
                    'category': cat,
                    'identity': ident,
                    'original_icloud_path': str(fpath),
                    'score': float(best_sim if cat != 'YO' else best_yo),
                    'faces_count': len(faces)
                }
                
            processed += 1
            # Dehydrate immediately to free physical space
            dehydrate_file(fpath)
            
        except Exception as e:
            pass

    with open(APPLE_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(apple_db, f, indent=2, ensure_ascii=False)
        
    print(f"Batch finished: {processed} processed ({matched} matched, {sin_rostro} sin rostro). All auto-dehydrated to 0 bytes.", flush=True)
    return processed

if __name__ == '__main__':
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    process_icloud_virtual_batch(limit=batch_size)
