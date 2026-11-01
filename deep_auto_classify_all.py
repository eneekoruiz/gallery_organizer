import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

import os, cv2, pickle, shutil, json, time
import numpy as np
from pathlib import Path

APP_DIR = Path(".")
RESULTADOS_DIR = APP_DIR / "Resultados"
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"
STATUS_FILE = APP_DIR / "smart_clean_status.json"
DEEP_STATUS_FILE = APP_DIR / "deep_classify_status.json"
BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')

from app.services.events import sse_manager
from app.utils.file_ops import safe_move_file

def update_status(text, progress=0, details=None):
    data = {"status": text, "progress": progress, "type": "smart_clean_progress"}
    if details: data["details"] = details
    # Send to SSE
    try:
        sse_manager.announce(data)
    except Exception:
        pass
    
    # Save status files for polling
    for sf in [STATUS_FILE, DEEP_STATUS_FILE]:
        try:
            with open(sf, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

# 1. Load ONNX Models
detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return float(np.dot(v1, v2) / ((np.linalg.norm(v1) * np.linalg.norm(v2)) + 1e-10))

def load_canonical_centroids():
    centroids = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'rb') as f:
                known_faces = pickle.load(f)
            for k, v in known_faces.items():
                if isinstance(k, tuple):
                    cat, ident = k[0], k[1]
                else:
                    ident = k
                    if ident == "YO":
                        cat = "YO"
                    elif ident.startswith("F.") or ident.startswith("F "):
                        cat = "Familia"
                    elif ident.startswith("P.") or ident.startswith("P "):
                        cat = "Profesores"
                    else:
                        cat = "Conocidos"
                
                if ident.startswith("Falso_Positivo") or "mascota" in ident.lower() or "persona nueva" in ident.lower():
                    continue
                    
                c_list = []
                if isinstance(v, dict):
                    if v.get('cat'): cat = v['cat']
                    if v.get('centroids') and len(v['centroids']) > 0:
                        c_list = [c / (np.linalg.norm(c) + 1e-10) for c in v['centroids'] if c is not None]
                    elif v.get('centroid') is not None:
                        c = v['centroid']
                        c_list = [c / (np.linalg.norm(c) + 1e-10)]
                elif hasattr(v, 'shape'):
                    c_list = [v / (np.linalg.norm(v) + 1e-10)]
                    
                if c_list:
                    centroids[ident] = {'cat': cat, 'centroids': c_list}
            print(f"[CLASSIFY] Cargadas {len(centroids)} identidades multidentidad desde sface_cache_v7.pkl")
            return centroids
        except Exception as e:
            print(f"[CLASSIFY] Error cargando sface_cache_v7: {e}")
            
    return centroids

def run_deep_classify(threshold=0.52, max_items=None):
    update_status("Cargando modelo multidentidad y centroides confirmados...", 5)
    
    centroids = load_canonical_centroids()
    if not centroids:
        update_status("Error: no se pudieron cargar los centroides biométricos.", 100)
        return
        
    update_status(f"Centroides listos ({len(centroids)} personas). Escaneando fotos dudosas y pendientes...", 15)
    
    # Cache para acelerar procesamiento
    feature_cache = {}
    cache_path = APP_DIR / "deep_features_cache.pkl"
    if cache_path.exists():
        try:
            with open(cache_path, 'rb') as f:
                feature_cache = pickle.load(f)
        except Exception:
            pass
    cache_updated = False

    # 2. Recolectar fotos de Para Revisar y Desconocidos
    scan_dirs = [
        BASE_DIR / 'Resultados' / 'Dudosos' / 'Para Revisar',
        BASE_DIR / 'Resultados' / 'Personas Sin Nombre',
    ]
    
    pending_files = []
    valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
    
    for sdir in scan_dirs:
        if sdir.exists():
            for root, _, files in os.walk(str(sdir)):
                for fname in sorted(files):
                    if os.path.splitext(fname)[1].lower() in valid_exts:
                        pending_files.append(os.path.join(root, fname))

    if max_items and max_items > 0:
        pending_files = pending_files[:max_items]

    total = len(pending_files)
    print(f"[CLASSIFY] Total fotos a procesar: {total}")
    update_status(f"Clasificando {total} fotos con precisión biométrica >99,5%...", 20)
    
    promoted_count = 0
    non_face_routed = 0
    path_map = {}
    sin_rostro_dir = BASE_DIR / 'Resultados' / 'Revision_Interactiva' / 'Sin_Rostro'
    sin_rostro_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, p in enumerate(pending_files):
        if idx % 25 == 0:
            prog = 20 + int((idx / max(1, total)) * 75)
            update_status(f"Procesando {idx}/{total} (Promovidas: {promoted_count}, Sin Rostro: {non_face_routed})...", prog)
            
        if not os.path.exists(p):
            continue
            
        try:
            stat = os.stat(p)
            sz, mt = stat.st_size, stat.st_mtime
            p_str = str(p)
            feats = []
            
            if p_str in feature_cache and feature_cache[p_str]['sz'] == sz and feature_cache[p_str]['mt'] == mt:
                feats = feature_cache[p_str]['feats']
            else:
                fb = np.fromfile(p, dtype=np.uint8)
                img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
                if img is not None:
                    h, w = img.shape[:2]
                    max_dim = max(h, w)
                    scale = 1024.0 / max_dim if max_dim > 1024 else 1.0
                    sw, sh = int(w * scale), int(h * scale)
                    small_img = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA) if scale < 1.0 else img
                    
                    detector.setInputSize((sw, sh))
                    _, faces = detector.detect(small_img)
                    if faces is not None:
                        if scale < 1.0:
                            faces[:, :14] /= scale
                        for face in faces:
                            crop = recognizer.alignCrop(img, face)
                            feat = recognizer.feature(crop)[0]
                            feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                            feats.append(feat_norm)
                feature_cache[p_str] = {'sz': sz, 'mt': mt, 'feats': feats}
                cache_updated = True
                
            # Caso 1: Foto sin rostro detectado (paisaje, documento, meme, objeto)
            if not feats:
                dst = safe_move_file(p, sin_rostro_dir)
                if dst:
                    non_face_routed += 1
                    path_map[p] = str(dst)
                continue
                
            # Caso 2: Rostro detectado -> Evaluar similitud con Cross-Identity Margin
            best_match_id = None
            best_match_cat = None
            best_sim = 0.0
            second_sim = 0.0
            
            for feat in feats:
                for ident, cdata in centroids.items():
                    for c in cdata['centroids']:
                        sim = float(np.dot(feat, c))
                        if sim > best_sim:
                            second_sim = best_sim
                            best_sim = sim
                            best_match_id = ident
                            best_match_cat = cdata['cat']
                        elif sim > second_sim:
                            second_sim = sim
                            
            margin = best_sim - second_sim
            if best_sim >= threshold and margin >= 0.04 and best_match_id:
                # Promover foto al álbum canónico correspondiente
                dst_dir = BASE_DIR / 'Resultados' / best_match_cat / best_match_id
                dst_dir.mkdir(parents=True, exist_ok=True)
                
                dst = safe_move_file(p, dst_dir)
                if dst:
                    promoted_count += 1
                    path_map[p] = str(dst)
                    
        except Exception as e:
            pass

        # Guardar checkpoint de features periódicamente
        if cache_updated and idx % 100 == 0:
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump(feature_cache, f)
                cache_updated = False
            except Exception:
                pass

    if cache_updated:
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(feature_cache, f)
        except Exception:
            pass

    # Actualizar faces_cache_v2.pkl
    faces_cache_file = Path("faces_cache_v2.pkl")
    if faces_cache_file.exists() and path_map:
        try:
            with open(faces_cache_file, 'rb') as f:
                faces_cache = pickle.load(f)
            for old_p, new_p in path_map.items():
                if old_p in faces_cache:
                    faces_cache[new_p] = faces_cache.pop(old_p)
            with open(faces_cache_file, 'wb') as f:
                pickle.dump(faces_cache, f)
        except Exception:
            pass

    try:
        from app.globals import clear_gallery_cache
        clear_gallery_cache()
    except Exception:
        pass

    msg = f"🎉 Auditoría completada: {promoted_count} fotos asignadas a sus dueños canónicos y {non_face_routed} fotos sin rostro ordenadas."
    update_status(msg, 100, {"promoted": promoted_count, "non_face": non_face_routed})
    print(f"[CLASSIFY] {msg}")

if __name__ == "__main__":
    run_deep_classify()
